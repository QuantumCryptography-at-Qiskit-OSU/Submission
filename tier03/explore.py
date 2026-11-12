"""Tier 3 experiments: compare approaches on OUR OWN test oracles.

The challenge oracles may each be used once, so every experiment here uses
small oracles we build ourselves (constant or balanced on 6 input bits).
solution.py is the only file that touches oracle_00..oracle_23.

Run from the repo root:  python submissions/<team>/tier03/explore.py

Experiments
  A. Classical, one input per question (on Aer): how many questions?
  B. Classical, random guessing: how sure after k questions?
  C. "Quantum" but target left in |0>: why the |-> trick matters.
  D. Deutsch-Jozsa: one question, always right.
  E. Noise: what happens to Deutsch-Jozsa on a noisy machine.
"""
import random

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

N = 6                    # input bits
TARGET = N               # target qubit index
INPUTS = range(2 ** N)   # the 64 possible inputs
backend = AerSimulator(seed_simulator=7)
rng = random.Random(2026)


# --------------------------------------------------------------------------
# Test oracles. Each is a truth table f[x] for x = 0..63, turned into a
# circuit |x>|y> -> |x>|y XOR f(x)> with one multi-controlled X per x with
# f(x) = 1. Slow but simple, and fine for our own test functions.
# --------------------------------------------------------------------------

def oracle_from_table(table, name):
    qc = QuantumCircuit(N + 1, name=name)
    if sum(table) == 2 ** N:          # constant 1: just flip the target
        qc.x(TARGET)
        return qc
    for x, fx in enumerate(table):
        if fx:
            zeros = [q for q in range(N) if not (x >> q) & 1]
            if zeros:
                qc.x(zeros)
            qc.mcx(list(range(N)), TARGET)
            if zeros:
                qc.x(zeros)
    return qc


def random_balanced():
    ones = set(rng.sample(list(INPUTS), 2 ** (N - 1)))
    return [int(x in ones) for x in INPUTS]


TESTS = {
    "constant 0": [0] * 64,
    "constant 1": [1] * 64,
    "balanced: f = x0": [x & 1 for x in INPUTS],
    "balanced: f = x1^x3^x5": [((x >> 1) ^ (x >> 3) ^ (x >> 5)) & 1 for x in INPUTS],
    "balanced: random": random_balanced(),
    # Sneaky: 0 on the first 32 inputs we would ask about, 1 on the rest.
    "balanced: sneaky": [int(x >= 32) for x in INPUTS],
}


def run(circuit, shots=64, noise=None):
    sim = AerSimulator(seed_simulator=7, noise_model=noise) if noise else backend
    return sim.run(transpile(circuit, sim), shots=shots).result().get_counts()


# --------------------------------------------------------------------------
# A. Classical: ask f(x) for one x at a time, on Aer.
# --------------------------------------------------------------------------

def ask_one_input(oracle, x):
    """One classical question: set inputs to x (X gates), read the target."""
    qc = QuantumCircuit(N + 1, 1)
    for q in range(N):
        if (x >> q) & 1:
            qc.x(q)
    qc.compose(oracle, range(N + 1), inplace=True)
    qc.measure(TARGET, 0)
    return int(next(iter(run(qc, shots=1))))


def classical_deterministic(oracle):
    """Ask x = 0, 1, 2, ... until two answers differ or 33 answers agree."""
    first = ask_one_input(oracle, 0)
    for questions, x in enumerate(range(1, 33), start=2):
        if ask_one_input(oracle, x) != first:
            return "balanced", questions
    return "constant", 33


# --------------------------------------------------------------------------
# B. Classical, random guessing with k questions (pure Python, no circuits).
# --------------------------------------------------------------------------

def random_guess_error(table, k, trials=20000):
    """Ask k random inputs; say 'constant' if all agree. How often wrong?"""
    wrong = 0
    for _ in range(trials):
        answers = {table[x] for x in rng.sample(list(INPUTS), k)}
        guess = "constant" if len(answers) == 1 else "balanced"
        truth = "constant" if len(set(table)) == 1 else "balanced"
        wrong += guess != truth
    return wrong / trials


# --------------------------------------------------------------------------
# C and D. Superposition circuits.
# --------------------------------------------------------------------------

def superposition_circuit(oracle, target_minus=True):
    qc = QuantumCircuit(N + 1, N)
    if target_minus:
        qc.x(TARGET)
        qc.h(TARGET)                  # target = |->  -> phase kickback
    qc.h(range(N))
    qc.compose(oracle, range(N + 1), inplace=True)
    qc.h(range(N))
    qc.measure(range(N), range(N))
    return qc


def p_zero(counts):
    return counts.get("0" * N, 0) / sum(counts.values())


def main():
    oracles = {name: oracle_from_table(t, name) for name, t in TESTS.items()}

    print("A. Classical, one input per question (each question = one Aer run)")
    print(f"   {'oracle':26s} answer     questions needed")
    for name, oracle in oracles.items():
        answer, questions = classical_deterministic(oracle)
        print(f"   {name:26s} {answer:10s} {questions}")
    print("   Worst case is 2^(n-1) + 1 = 33 questions: 32 equal answers can still")
    print("   be the first half of a balanced function (the 'sneaky' oracle).\n")

    print("B. Classical, random guessing: chance of being wrong (constant guessed")
    print("   when the function is actually balanced)")
    for k in (1, 2, 3, 5, 10, 20):
        error = random_guess_error(TESTS["balanced: random"], k)
        print(f"   k = {k:2d} questions -> wrong {error:6.2%}   (about 2^-(k-1) = {2 ** -(k - 1):.2%})")
    print("   Never exactly zero below 33 questions.\n")

    print("C. Superposition but target left in |0> (no phase kickback)")
    print("   P(000000) is the 'constant' signal; it should be 1 or 0")
    for name, oracle in oracles.items():
        print(f"   {name:26s} P(000000) = {p_zero(run(superposition_circuit(oracle, False))):.2f}")
    print("   Constant oracles look the same as before, but balanced ones give a")
    print("   muddy mix: the answer sits in the target, which we never measured.\n")

    print("D. Deutsch-Jozsa (target in |->): ONE question per oracle")
    for name, oracle in oracles.items():
        counts = run(superposition_circuit(oracle))
        verdict = "constant" if p_zero(counts) == 1 else "balanced" if p_zero(counts) == 0 else "??"
        top = max(counts, key=counts.get)
        print(f"   {name:26s} P(000000) = {p_zero(counts):.2f} -> {verdict:9s} (most common: {top})")
    print("   For f = s.x (a parity), DJ reads out s exactly: that is Bernstein-Vazirani")
    print("   (f = x0 -> 000001, f = x1^x3^x5 -> 101010, bit 0 printed rightmost).\n")

    print("E. Noise: Deutsch-Jozsa with random errors after every 2-qubit gate")
    print("   (depolarizing, probability p). 'constant, with gates' is the random")
    print("   balanced oracle applied twice (f XOR f = 0), so it has as many gates")
    print("   as the balanced one but is constant.")
    busy_constant = oracles["balanced: random"].compose(oracles["balanced: random"])
    n_cx = transpile(busy_constant, basis_gates=["rz", "sx", "x", "cx"]).count_ops().get("cx", 0)
    print(f"   ({n_cx} CX gates in the constant one)")
    for p in (0.0, 0.0001, 0.001, 0.01):
        noise = NoiseModel()
        if p:
            noise.add_all_qubit_quantum_error(depolarizing_error(p, 2), ["cx"])
        pc = p_zero(run(superposition_circuit(busy_constant), 400, noise))
        pb = p_zero(run(superposition_circuit(oracles["balanced: random"]), 400, noise))
        print(f"   p = {p:<6}  constant: P(000000) = {pc:.2f}   balanced: P(000000) = {pb:.2f}")
    print("   Fully scrambled, P(000000) drops to 1/64 = 0.016 for both kinds.")
    print("   At p = 0.0001 a threshold (P > 0.25 means constant) still works. At")
    print("   p = 0.001, typical for today's hardware, the two kinds look the same:")
    print("   ~7800-CX oracles are too deep without error correction.")


if __name__ == "__main__":
    main()
