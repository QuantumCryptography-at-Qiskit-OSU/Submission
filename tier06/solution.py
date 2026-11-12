"""Tier 6 solution: Grover search with many marked keys, then a checksum filter.

The checker runs this file from the repo root. Keep these imports; they work
there, while the notebook's `import helper` does not.

Method
------
Same cipher and same oracle compiler as tier 5, with a 14-bit key and only the
first byte 'Q' trusted. As in tier 5,

    byte 0 decrypts to 'Q'   <=>   mask(k, 0) = C0 xor SBOX^-1(PERM^-1('Q'))

which is 8 equations  k[j] xor k[8 + j mod 6] xor (k[j+1] and k[j+3]) = t[j].

How many keys pass? Equation j can be written in place onto key qubit j, in the
order j = 0..7, because it only reads qubits with a larger index. So the map
(k0..k7) -> (mask bits) is a bijection for every choice of k8..k13. Exactly one
value of k0..k7 matches for each of the 2^6 values of k8..k13:

    M = 2^(14 - 8) = 64 marked keys out of N = 16384.

This changes the circuit in one place only: the number of Grover rounds drops
from (pi/4) sqrt(N) = 100 to floor((pi/4) sqrt(N / M)) = 12. With sin(theta) =
sqrt(M/N) = 1/16, 12 rounds rotate the state to (2*12+1)*theta = 89.6 degrees,
so almost every shot is one of the 64 passing keys, each equally likely.

The circuit cannot tell those 64 apart. Each measured candidate is decrypted
classically and kept only if the plaintext checksum matches the public one.
"""
import math
from collections import Counter

from qiskit import QuantumCircuit, transpile
from qiskit.synthesis import synth_mcx_2_clean_kg24
from qiskit_aer import AerSimulator

from common import load_locked
from common.toy_cipher import ROUND_CONSTANT, ToyCipher, inverse_permute, inverse_sbox_layer, mask_gates
from tier06 import helper

BASIS = ["rz", "sx", "x", "cx"]
TIER = 6
SHOTS = 4096


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


def first_byte_equations():
    """The equations for this tier: only byte 0 = 'Q' is used."""
    locked = load_locked(TIER)
    key_bits = locked["public_parameters"]["key_bits"]
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    known = locked["public_parameters"]["known_prefix"].encode()[:1]
    equations = byte_equations(key_bits, 0, ciphertext[0], known[0])
    return simplify(equations), key_bits


def count_marked(equations, key_bits):
    """Number of keys that pass the oracle, from the structure of the oracle.

    When every equation is evaluated in place on its own key qubit, the
    compute block is a bijection on the key register, so each equation halves
    the number of passing keys exactly.
    """
    _, checks, n_scratch = plan_oracle(equations, key_bits)
    if n_scratch:
        raise ValueError("the bijection argument needs an oracle without scratch qubits")
    return 2 ** (key_bits - len(checks))


def build_circuit():
    """Return your main circuit. Used for diagrams only, never for scoring."""
    equations, key_bits = first_byte_equations()
    return grover_circuit(equations, key_bits, n_marked=count_marked(equations, key_bits))[0]


def run_search(shots=SHOTS, seed=6):
    """Run Grover on Aer. Returns the measurement counts {key integer: shots}."""
    circuit = transpile(build_circuit(), basis_gates=BASIS, optimization_level=2, seed_transpiler=1)
    backend = AerSimulator(method="statevector", seed_simulator=seed)
    counts = backend.run(circuit, shots=shots).result().get_counts()
    return Counter({int(bits, 2): n for bits, n in counts.items()})


def filter_candidates(counts):
    """Keep the measured keys whose full decryption has the public checksum."""
    locked = load_locked(TIER)
    parameters = locked["public_parameters"]
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    prefix = parameters["known_prefix"].encode()
    survivors = []
    for key, _ in counts.most_common():
        plaintext = ToyCipher(key, parameters["key_bits"]).decrypt(ciphertext)
        if plaintext.startswith(prefix) and helper.checksum(plaintext) == parameters["checksum"]:
            survivors.append((key, plaintext))
    return survivors


def solve():
    """Run your circuit on Aer and return the decrypted line as a string."""
    survivors = filter_candidates(run_search())
    if len(survivors) != 1:
        raise RuntimeError(f"expected one key to pass the checksum, found {len(survivors)}")
    return survivors[0][1].decode("utf-8")
