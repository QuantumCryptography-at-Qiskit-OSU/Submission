"""Tier 8 solution: Shor's order finding with one recycled control qubit.

The checker runs this file from the repo root. Keep these imports; they work
there.

Method
------
Pick a base a coprime to N. The map U|x> = |a x mod N> has eigenvalues
e^(2 pi i s / r), where r is the order of a (smallest r with a^r = 1 mod N).
The state |1> is an equal mix of those eigenstates, so phase estimation on U
starting from |1> returns s / r for a random s. Continued fractions turn the
measured fraction into r, and gcd(a^(r/2) +- 1, N) gives the factors.

Circuit
-------
* Phase estimation is done one bit at a time (semiclassical QFT): a single
  control qubit is measured, reset and reused for t rounds. Round i applies a
  controlled multiplication by a^(2^(t-1-i)) mod N, then a phase correction
  that depends on the bits already measured, then H and a measurement.
  The work register is never measured, so its eigenstate stays fixed across
  rounds. Total width: 1 control + n work qubits + 2 ancillas.
* t = ceil(log2(N^2 / 2)) rounds are enough: r divides lcm(p-1, q-1) < N/2,
  so 2^t >= 2 r^2, which is what the continued-fraction step needs.
* The constants a^(2^j) mod N are computed classically by repeated squaring.
* Controlled multiplication by a constant b is a permutation of 1..N-1. It is
  written as a product of swaps of two basis states; each swap (u v) is
  CX gates that make u and v differ in one bit, then one multi-controlled X on
  that bit, then the CX gates again. A control is left out when that only
  disturbs bit patterns the register never holds (0 and values >= N).
  This is exact for every x in 1..N-1. It costs O(N) gates per multiplication,
  so it is a toy construction that only works at these sizes.
* The first round acts on the known state |1>, where "multiply by b" is just
  "write b": a few CX gates.
"""
import math
from collections import Counter
from fractions import Fraction

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.synthesis import synth_mcx_1_clean_kg24, synth_mcx_2_clean_kg24
from qiskit_aer import AerSimulator

from common import load_locked, keystream, xor_bytes

BASIS = ["rz", "sx", "x", "cx"]
TIER = 8
SHOTS = 24
# Clean ancillas for the multi-controlled X gates, and the matching synthesis.
N_ANCILLAS = 2
MCX_SYNTHESIS = {1: synth_mcx_1_clean_kg24, 2: synth_mcx_2_clean_kg24}[N_ANCILLAS]


# --------------------------------------------------------------------------
# Controlled modular multiplication as a permutation circuit.
# --------------------------------------------------------------------------

def mcx_cost(n_controls):
    """CX count of a multi-controlled X with clean ancillas (measured)."""
    return {0: 0, 1: 1, 2: 6}.get(n_controls, 6 * n_controls - 6)


def swap_gate(u, v, n_bits, free):
    """Cheapest gates that swap basis states u and v of the work register.

    Returns (cost, cx_list, pattern, pivot): apply the CX gates, flip `pivot`
    when the work bits match `pattern`, undo the CX gates.

    The CX gates make u and v differ in the pivot bit only. A control on
    another bit can be left out when that only adds swaps between `free`
    states, the bit patterns the work register can never hold.
    """
    best = None
    difference = u ^ v
    for pivot in range(n_bits):
        if not (difference >> pivot) & 1:
            continue
        others = [q for q in range(n_bits) if q != pivot and (difference >> q) & 1]
        fixed, moved = (u, v) if not (u >> pivot) & 1 else (v, u)
        dropped, deltas = [], [0]
        for q in reversed(range(n_bits)):
            if q == pivot:
                continue
            extra = [delta | (1 << q) for delta in deltas]
            if all((fixed ^ delta) in free and (moved ^ delta) in free for delta in extra):
                dropped.append(q)
                deltas += extra
        pattern = {q: (fixed >> q) & 1 for q in range(n_bits) if q != pivot and q not in dropped}
        cost = 2 * len(others) + mcx_cost(1 + len(pattern))
        if best is None or cost < best[0]:
            best = (cost, [(pivot, q) for q in others], pattern, pivot)
    return best


def swap_sequence(permutation, n_bits, free):
    """Write a permutation {x: image} as a list of swap gates, in time order.

    Swapping two values that sit in the same cycle splits that cycle in two,
    so repeating this ends with the identity. The cheapest swap is taken each
    time.
    """
    remaining = dict(permutation)
    cache = {}
    gates = []
    while True:
        best = None
        seen = set()
        for start in remaining:
            if start in seen or remaining[start] == start:
                continue
            cycle, x = [], start
            while x not in seen:
                seen.add(x)
                cycle.append(x)
                x = remaining[x]
            for i, u in enumerate(cycle):
                for v in cycle[i + 1:]:
                    if (u, v) not in cache:
                        cache[u, v] = swap_gate(u, v, n_bits, free)
                    if best is None or cache[u, v][0] < best[0][0]:
                        best = (cache[u, v], u, v)
        if best is None:
            return gates
        gate, u, v = best
        gates.append(gate[1:])
        remaining[u], remaining[v] = remaining[v], remaining[u]


def apply_classically(gates, x):
    """Run the swap gates on one basis state with plain bits (for testing)."""
    for cx_list, pattern, pivot in gates:
        for control, target in cx_list:
            x ^= ((x >> control) & 1) << target
        if all((x >> q) & 1 == value for q, value in pattern.items()):
            x ^= 1 << pivot
        for control, target in reversed(cx_list):
            x ^= ((x >> control) & 1) << target
    return x


def controlled_multiplier(b, modulus, n_bits):
    """Circuit for |c>|x> -> |c>|b^c x mod modulus>, for every x in 1..modulus-1.

    Qubit 0 is the control, qubits 1..n_bits the work register (bit j has
    value 2^j), and the last N_ANCILLAS qubits are clean ancillas.

    The work register starts at 1 and is only ever multiplied by numbers
    coprime to the modulus, so it never holds 0 or a value >= modulus. Those
    bit patterns are "free": the circuit may do anything to them.
    """
    valid = range(1, modulus)
    free = set(range(2 ** n_bits)) - set(valid)
    permutation = {x: (b * x) % modulus for x in valid}
    gates = swap_sequence(permutation, n_bits, free)
    for x, image in permutation.items():
        assert apply_classically(gates, x) == image

    circuit = QuantumCircuit(1 + n_bits + N_ANCILLAS, name=f"x{b} mod {modulus}")
    work = lambda q: 1 + q
    ancillas = list(range(1 + n_bits, 1 + n_bits + N_ANCILLAS))
    for cx_list, pattern, pivot in gates:
        zeros = [work(q) for q, value in pattern.items() if value == 0]
        for control, target in cx_list:
            circuit.cx(work(control), work(target))
        if zeros:
            circuit.x(zeros)
        controls = [0] + [work(q) for q in pattern]
        if len(controls) <= 2:
            circuit.mcx(controls, work(pivot))
        else:
            circuit.compose(MCX_SYNTHESIS(len(controls)), controls + [work(pivot)] + ancillas, inplace=True)
        if zeros:
            circuit.x(zeros)
        for control, target in reversed(cx_list):
            circuit.cx(work(control), work(target))
    return circuit


# --------------------------------------------------------------------------
# One-control-qubit phase estimation.
# --------------------------------------------------------------------------

def counting_bits(modulus):
    """Smallest t with 2^t >= N^2 / 2."""
    return math.ceil(math.log2(modulus * modulus / 2))


def order_finding_circuit(a, modulus, optimization_level=2):
    """Phase estimation of x -> a x mod N on |1>, with a recycled control."""
    n_bits = modulus.bit_length()
    t = counting_bits(modulus)
    control = QuantumRegister(1, "ctrl")
    work = QuantumRegister(n_bits, "work")
    ancilla = QuantumRegister(N_ANCILLAS, "anc")
    bits = ClassicalRegister(t, "phase")
    circuit = QuantumCircuit(control, work, ancilla, bits)
    circuit.x(work[0])  # work register = |1>

    blocks = {}
    for i in range(t):
        b = pow(a, 2 ** (t - 1 - i), modulus)
        if i > 0:
            circuit.reset(control)
        circuit.h(control)
        if i == 0:
            # The work register is exactly |1>: multiplying by b writes b.
            for q in range(n_bits):
                if ((1 ^ b) >> q) & 1:
                    circuit.cx(control[0], work[q])
        else:
            if b not in blocks:
                blocks[b] = transpile(
                    controlled_multiplier(b, modulus, n_bits),
                    basis_gates=BASIS, optimization_level=optimization_level, seed_transpiler=1,
                )
            circuit.compose(blocks[b], inplace=True)
        # Semiclassical inverse QFT: undo the phase from the bits already read.
        for earlier in range(i):
            with circuit.if_test((bits[earlier], 1)):
                circuit.p(-2 * math.pi / 2 ** (i - earlier + 1), control)
        circuit.h(control)
        circuit.measure(control, bits[i])
    return circuit


def run_order_finding(a, modulus, shots=SHOTS, seed=8):
    """Run the circuit on Aer. Returns counts {measured integer y: shots}."""
    circuit = order_finding_circuit(a, modulus)
    backend = AerSimulator(method="statevector", seed_simulator=seed)
    counts = backend.run(circuit, shots=shots).result().get_counts()
    return Counter({int(bits, 2): n for bits, n in counts.items()})


# --------------------------------------------------------------------------
# Classical post-processing.
# --------------------------------------------------------------------------

def order_from_counts(counts, a, modulus):
    """Continued fractions: y / 2^t ~ s / r. Returns r, or None."""
    t = counting_bits(modulus)
    denominators = set()
    for y in counts:
        denominators.add(Fraction(y, 2 ** t).limit_denominator(modulus // 2).denominator)
    # A shot with gcd(s, r) > 1 only shows a divisor of r, so also try lcms.
    candidates = set(denominators)
    for d1 in denominators:
        for d2 in denominators:
            candidates.add(math.lcm(d1, d2))
    for r in sorted(candidates):
        if 1 < r < modulus and pow(a, r, modulus) == 1:
            return r
    return None


def factor(modulus, bases=(2, 3, 5, 7, 11, 13)):
    """Factor N with quantum order finding. Returns (p, q, details)."""
    for a in bases:
        if math.gcd(a, modulus) != 1:
            continue  # sharing a factor would be classical luck, not Shor
        counts = run_order_finding(a, modulus)
        r = order_from_counts(counts, a, modulus)
        if r is None or r % 2:
            continue
        half = pow(a, r // 2, modulus)
        p, q = math.gcd(half - 1, modulus), math.gcd(half + 1, modulus)
        if 1 < p < modulus and p * q == modulus:
            return p, q, {"a": a, "r": r, "counts": counts}
    raise RuntimeError("order finding did not produce a factor")


def unwrap_key(parameters, p, q):
    """RSA: d = e^-1 mod (p-1)(q-1), k = c^d mod N, as a bit string."""
    d = pow(parameters["e"], -1, (p - 1) * (q - 1))
    k = pow(parameters["wrapped_key"], d, parameters["N"])
    return format(k, f"0{parameters['key_width_bits']}b")


def build_circuit():
    """Return your main circuit. Used for diagrams only, never for scoring."""
    return order_finding_circuit(2, load_locked(TIER)["public_parameters"]["N"])


def solve():
    """Run your circuit on Aer and return the decrypted line as a string."""
    locked = load_locked(TIER)
    parameters = locked["public_parameters"]
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    p, q, _ = factor(parameters["N"])
    key_bits = unwrap_key(parameters, p, q)
    return xor_bytes(ciphertext, keystream(key_bits, len(ciphertext))).decode("utf-8")
