"""Tier 10, alternative method: discrete logarithm by Grover search.

This is NOT our main tier 10 solution (that is Shor's discrete log in
solution.py). It is a second quantum method we tried, to compare.

Idea (beginner version)
-----------------------
"Find a with g^a = A mod p" is a search over exponents. Grover searches M
candidates in about (pi/4) sqrt(M) rounds instead of about M/2 checks.

Search space: a 6-qubit register x holds exponents 0..63 (g has order 41, so
exponent x and x + 41 give the same answer; when both fit, two items are
marked). The oracle is real modular exponentiation:
  1. Work register |1>, then for each bit x_j of x: multiply the work register
     by g^(2^j) mod p, controlled on x_j. The work register now holds g^x.
     (The same controlled-multiplier blocks as Shor, from solution.py.)
  2. Flip the sign if the work register equals A.
  3. Undo step 1.
Then the usual diffusion step.
"""
import math
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator

from solution import BASIS, N_ANCILLAS, controlled_multiplier, subgroup

X_BITS = 6


def exponentiation(g, modulus, order):
    """|x>|1> -> |x>|g^x mod p>, for x < 2^X_BITS."""
    n_bits = modulus.bit_length()
    valid = subgroup(modulus, order)
    x = QuantumRegister(X_BITS, "x")
    work = QuantumRegister(n_bits, "work")
    anc = QuantumRegister(N_ANCILLAS, "anc")
    qc = QuantumCircuit(x, work, anc, name="g^x")
    qc.x(work[0])
    for j in range(X_BITS):
        block = transpile(controlled_multiplier(pow(g, 2 ** j, modulus), modulus, n_bits, valid),
                          basis_gates=BASIS, optimization_level=2, seed_transpiler=1)
        qc.compose(block, [x[j], *work, *anc], inplace=True)
    return qc


def oracle(g, big_a, modulus, order):
    """Phase -1 on every x with g^x = A mod p."""
    n_bits = modulus.bit_length()
    power = exponentiation(g, modulus, order)
    qc = QuantumCircuit(*power.qregs, name="oracle")
    work = qc.qregs[1]
    qc.compose(power, inplace=True)
    zeros = [work[l] for l in range(n_bits) if not (big_a >> l) & 1]
    if zeros:
        qc.x(zeros)
    qc.mcp(math.pi, list(work[:-1]), work[-1])
    if zeros:
        qc.x(zeros)
    qc.compose(power.inverse(), inplace=True)
    return qc


def diffusion(search):
    qc = QuantumCircuit(search, name="diffusion")
    qc.h(search)
    qc.x(search)
    qc.mcp(math.pi, list(search[:-1]), search[-1])
    qc.x(search)
    qc.h(search)
    return qc


def grover_circuit(g, big_a, modulus, order, rounds):
    orc = oracle(g, big_a, modulus, order)
    x, work, anc = orc.qregs
    out = ClassicalRegister(X_BITS, "x_out")
    qc = QuantumCircuit(x, work, anc, out)
    qc.h(x)
    dif = diffusion(list(x))
    orc = transpile(orc, basis_gates=BASIS, optimization_level=1, seed_transpiler=1)
    for _ in range(rounds):
        qc.compose(orc, inplace=True)
        qc.compose(dif, qubits=list(x), inplace=True)
    qc.measure(x, out)
    return qc


def sweep_probabilities(g, big_a, modulus, order, max_rounds):
    """One noiseless run that records P(x) after every Grover round.

    Returns {rounds: {x: probability}}. The circuit is the same as
    grover_circuit, with a probability snapshot after each round instead of
    one final measurement. Simulating each round count separately would repeat
    the same (large) gate sequence over and over.
    """
    import qiskit_aer.library  # noqa: F401  (adds save_probabilities_dict)

    orc = oracle(g, big_a, modulus, order)
    x, work, anc = orc.qregs
    qc = QuantumCircuit(x, work, anc)
    qc.h(x)
    dif = diffusion(list(x))
    orc = transpile(orc, basis_gates=BASIS, optimization_level=1, seed_transpiler=1)
    qc.save_probabilities_dict(list(x), label="r0")
    for k in range(1, max_rounds + 1):
        qc.compose(orc, inplace=True)
        qc.compose(dif, qubits=list(x), inplace=True)
        qc.save_probabilities_dict(list(x), label=f"r{k}")
    backend = AerSimulator(method="statevector", seed_simulator=10)
    data = backend.run(transpile(qc, backend), shots=1).result().data()
    return {k: {int(bits, 2) if isinstance(bits, str) else int(bits): p for bits, p in data[f"r{k}"].items()}
            for k in range(max_rounds + 1)}


def exponent_probability(probabilities, a, order):
    """Total probability of the x values with x mod order == a."""
    return sum(p for x, p in probabilities.items() if x % order == a)


def build_circuit():
    """Grover circuit with 4 rounds (for diagrams and gate counts)."""
    from common import load_locked
    p = load_locked(10)["public_parameters"]
    return grover_circuit(p["g"], p["A"], p["p"], p["order"], 4)
