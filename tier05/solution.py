"""Tier 5 solution: Grover search over the 10-bit key of the toy cipher.

The checker runs this file from the repo root. Keep these imports; they work
there, while the notebook's `import helper` does not.

Method
------
Decrypting byte i is  P = PERM(SBOX(C xor mask(k, i))).  PERM and SBOX are fixed
bijections that do not involve the key, so "byte i decrypts to the known
plaintext P" is the same statement as

    mask(k, i) = C xor SBOX^-1(PERM^-1(P))            (a known 8-bit constant)

Each mask bit is  k[a] xor k[b] xor (k[c] and k[d]),  so every known byte gives
8 small equations on the key qubits. The oracle computes the left-hand sides
with CX and Toffoli gates, flips the phase when all of them match (one
multi-controlled Z), and uncomputes. Three tricks keep it small:

1. Shared Toffolis. Bytes 0 and 1 use many of the same AND terms. If two
   equations share their AND term, "A and B" is the same as "A and (A xor B)",
   and A xor B has no AND term at all. It becomes a CX-only parity check.
2. In-place evaluation. An equation  k[j] xor ... = t  can be written onto key
   qubit j itself when no later equation still needs k[j]. No scratch qubit.
3. Relative-phase Toffolis (RCCX, 3 CX instead of 6). The oracle is
   W^-1 . Z . W with Z diagonal, so the extra phases of RCCX cancel exactly.

Grover's algorithm then runs  floor(pi/4 * sqrt(2^10)) = 25  rounds of
(oracle, reflection about the uniform state) and the key is the likely outcome.
"""
import math
from collections import Counter

from qiskit import QuantumCircuit, transpile
from qiskit.synthesis import synth_mcx_2_clean_kg24
from qiskit_aer import AerSimulator

from common import load_locked
from common.toy_cipher import ROUND_CONSTANT, ToyCipher, inverse_permute, inverse_sbox_layer, mask_gates
from tier05 import helper

BASIS = ["rz", "sx", "x", "cx"]
TIER = 5
SHOTS = 256


# --------------------------------------------------------------------------
# Step 1: turn "known plaintext byte" into equations on the key bits.
# --------------------------------------------------------------------------

def byte_equations(key_bits, position, cipher_byte, plain_byte):
    """Equations that say: byte `position` decrypts to `plain_byte`.

    Each equation is [linear, product, constant] and means
        XOR of key bits in `linear`  xor  (k[a] and k[b])  ==  constant
    where product = (a, b) or None.
    """
    target = cipher_byte ^ inverse_sbox_layer(inverse_permute(plain_byte))
    target ^= (ROUND_CONSTANT * position) % 256
    # Rotating the key left by 3*position only relabels the key wires.
    wire = lambda n: (n - 3 * position) % key_bits
    equations = [[frozenset(), None, (target >> j) & 1] for j in range(8)]
    for gate in mask_gates(key_bits):
        if gate[0] == "cx":
            equations[gate[2]][0] ^= {wire(gate[1])}
        else:
            equations[gate[3]][1] = tuple(sorted((wire(gate[1]), wire(gate[2]))))
    return equations


def simplify(equations):
    """Replace equations that share an AND term by CX-only parity checks."""
    quadratic, parities = {}, []
    for linear, product, constant in equations:
        if product in quadratic:
            other_linear, other_constant = quadratic[product]
            parities.append((linear ^ other_linear, constant ^ other_constant))
        else:
            quadratic[product] = (linear, constant)

    # Keep an independent set of parity checks (Gaussian elimination mod 2).
    basis = {}
    for linear, constant in parities:
        while linear and max(linear) in basis:
            pivot_linear, pivot_constant = basis[max(linear)]
            linear, constant = linear ^ pivot_linear, constant ^ pivot_constant
        if linear:
            basis[max(linear)] = (linear, constant)
        elif constant:
            raise ValueError("the known bytes contradict each other: no key exists")

    # Use the parity checks to shorten the linear part of the other equations.
    result = []
    for product, (linear, constant) in quadratic.items():
        for pivot_linear, pivot_constant in basis.values():
            if len(linear ^ pivot_linear) < len(linear):
                linear, constant = linear ^ pivot_linear, constant ^ pivot_constant
        result.append((linear, product, constant))
    result += [(linear, None, constant) for linear, constant in basis.values()]
    return result


# --------------------------------------------------------------------------
# Step 2: compile the equations into a reversible "compute" block.
# --------------------------------------------------------------------------

def plan_oracle(equations, key_bits):
    """Decide where each equation is evaluated.

    Returns (gates, checks, n_scratch). `gates` is a list of ("cx", a, b) and
    ("ccx", a, b, target). `checks` is a list of (qubit, wanted_value): the
    key is marked when every check qubit holds its wanted value.
    """
    uses = lambda eq: set(eq[0]) | set(eq[1] or ())
    scratch_eqs = [eq for eq in equations if not (eq[0] and eq[1])]
    pending = [eq for eq in equations if eq[0] and eq[1]]
    in_place = []

    def runnable(candidates):
        """Greedy order in which equations can overwrite one of their own qubits."""
        candidates, order = list(candidates), []
        progress = True
        while progress:
            progress = False
            for eq in candidates:
                others = set().union(*[uses(o) for o in candidates if o is not eq], set())
                homes = [h for h in sorted(eq[0]) if h not in (eq[1] or ()) and h not in others]
                if homes:
                    order.append((eq, homes[0]))
                    candidates.remove(eq)
                    progress = True
                    break
        return order, candidates

    while True:
        order, stuck = runnable(pending)
        if not stuck:
            in_place = order
            break
        # Deadlock: move the equation whose removal frees the most others.
        best = max(stuck, key=lambda eq: len(runnable([p for p in pending if p is not eq])[0]))
        pending.remove(best)
        scratch_eqs.append(best)

    gates, checks = [], []
    for index, (linear, product, constant) in enumerate(scratch_eqs):
        qubit = key_bits + index
        gates += [("cx", source, qubit) for source in sorted(linear)]
        if product:
            gates.append(("ccx", product[0], product[1], qubit))
        checks.append((qubit, constant))
    for (linear, product, constant), home in in_place:
        gates += [("cx", source, home) for source in sorted(linear - {home})]
        gates.append(("ccx", product[0], product[1], home))
        checks.append((home, constant))
    return gates, checks, len(scratch_eqs)


def classical_oracle(key, gates, checks, n_qubits):
    """Evaluate the compute block on one key with plain bits (for testing)."""
    bits = [(key >> j) & 1 for j in range(n_qubits)]
    for gate in gates:
        if gate[0] == "cx":
            bits[gate[2]] ^= bits[gate[1]]
        else:
            bits[gate[3]] ^= bits[gate[1]] & bits[gate[2]]
    return all(bits[qubit] == wanted for qubit, wanted in checks)


# --------------------------------------------------------------------------
# Step 3: Grover circuit.
# --------------------------------------------------------------------------

def multi_controlled_z(circuit, qubits, clean):
    """Phase -1 when all `qubits` are 1. Uses two clean ancillas (linear cost)."""
    *controls, target = qubits
    circuit.h(target)
    circuit.compose(synth_mcx_2_clean_kg24(len(controls)), controls + [target] + list(clean), inplace=True)
    circuit.h(target)


def build_oracle(gates, checks, n_qubits, clean):
    """Phase oracle: -1 on every key that satisfies all the equations."""
    compute = QuantumCircuit(n_qubits)
    for gate in gates:
        if gate[0] == "cx":
            compute.cx(gate[1], gate[2])
        else:
            compute.rccx(gate[1], gate[2], gate[3])
    oracle = QuantumCircuit(n_qubits, name="oracle")
    oracle.compose(compute, inplace=True)
    zeros = [qubit for qubit, wanted in checks if wanted == 0]
    if zeros:
        oracle.x(zeros)
    multi_controlled_z(oracle, [qubit for qubit, _ in checks], clean)
    if zeros:
        oracle.x(zeros)
    oracle.compose(compute.inverse(), inplace=True)
    return oracle


def build_diffusion(key_bits, n_qubits, clean):
    """Reflection about the uniform superposition of all keys."""
    diffusion = QuantumCircuit(n_qubits, name="diffusion")
    keys = list(range(key_bits))
    diffusion.h(keys)
    diffusion.x(keys)
    multi_controlled_z(diffusion, keys, clean)
    diffusion.x(keys)
    diffusion.h(keys)
    return diffusion


def grover_circuit(equations, key_bits, n_marked=1, iterations=None):
    """Full Grover circuit. Returns (circuit, iterations)."""
    gates, checks, n_scratch = plan_oracle(equations, key_bits)
    n_qubits = key_bits + n_scratch + 2
    clean = [n_qubits - 2, n_qubits - 1]
    if iterations is None:
        iterations = math.floor(math.pi / 4 * math.sqrt(2 ** key_bits / n_marked))
    oracle = build_oracle(gates, checks, n_qubits, clean)
    diffusion = build_diffusion(key_bits, n_qubits, clean)
    circuit = QuantumCircuit(n_qubits, key_bits)
    circuit.h(range(key_bits))
    for _ in range(iterations):
        circuit.compose(oracle, inplace=True)
        circuit.compose(diffusion, inplace=True)
    circuit.measure(range(key_bits), range(key_bits))
    return circuit, iterations


def known_text_equations():
    """The simplified equations for this tier: bytes 0 and 1 must be 'QC'."""
    locked = load_locked(TIER)
    key_bits = locked["public_parameters"]["key_bits"]
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    known = locked["public_parameters"]["known_prefix"].encode()[:2]
    equations = []
    for position, plain_byte in enumerate(known):
        equations += byte_equations(key_bits, position, ciphertext[position], plain_byte)
    return simplify(equations), key_bits


def build_circuit():
    """Return your main circuit. Used for diagrams only, never for scoring."""
    equations, key_bits = known_text_equations()
    return grover_circuit(equations, key_bits)[0]


def run_search(shots=SHOTS, seed=5):
    """Run Grover on Aer. Returns the measurement counts {key integer: shots}."""
    circuit = transpile(build_circuit(), basis_gates=BASIS, optimization_level=2, seed_transpiler=1)
    backend = AerSimulator(method="statevector", seed_simulator=seed)
    counts = backend.run(circuit, shots=shots).result().get_counts()
    return Counter({int(bits, 2): n for bits, n in counts.items()})


def solve():
    """Run your circuit on Aer and return the decrypted line as a string."""
    locked = load_locked(TIER)
    key_bits = locked["public_parameters"]["key_bits"]
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    prefix = locked["public_parameters"]["known_prefix"].encode()
    counts = run_search()
    # Classical check of the measured candidates, most frequent first.
    for key, _ in counts.most_common():
        plaintext = ToyCipher(key, key_bits).decrypt(ciphertext)
        if plaintext.startswith(prefix):
            return plaintext.decode("utf-8")
    raise RuntimeError("no measured key decrypts the known prefix")
