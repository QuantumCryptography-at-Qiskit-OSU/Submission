"""Tier 2 experiments: compare approaches on OUR OWN simulated BB84 links.

The real links may only be measured once, so every experiment here builds its
own Alice -> (Eve) -> Bob link on Aer. solution.py is the only file that
touches helper.Channel.

Run from the repo root:  python Submission/tier02/explore.py   (needs qiskit_aer)

Experiments
  A. BB84 with random bases: sifting, QBER on a clean and a tapped link.
  B. Bob always measures in Z: also works, but throws the same half away.
  C. Skip sifting (keep every bit): why that fails.
  D. Eve taps only a fraction of the qubits: how many check bits to catch her.
  E. Noise instead of Eve: why a threshold, not "zero errors", is the rule.
"""
import random

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

N = 1024
CHECK = 256   # public check bits
Z, X = 0, 1
rng = random.Random(2026)
backend = AerSimulator(seed_simulator=11)


def prepare(qc, bit, basis):
    if bit:
        qc.x(0)
    if basis == X:
        qc.h(0)


def measure_all(prep, bases, noise=None):
    """prep(i) puts qubit i in its state. Measure each in bases[i]; return bits."""
    sim = AerSimulator(seed_simulator=11, noise_model=noise) if noise else backend
    circuits = []
    for i, basis in enumerate(bases):
        qc = QuantumCircuit(1, 1)
        prep(i, qc)
        if basis == X:
            qc.h(0)
        qc.measure(0, 0)
        circuits.append(qc)
    result = sim.run(transpile(circuits, sim, optimization_level=0), shots=1).result()
    return [int(next(iter(result.get_counts(i)))) for i in range(len(bases))]


def make_link(eve_fraction=0.0, noise=None):
    """Alice's data, plus the bits Eve forwards (a list of (bit, basis) states)."""
    a_bits = [rng.randint(0, 1) for _ in range(N)]
    a_bases = [rng.randint(Z, X) for _ in range(N)]
    states = [(a_bits[i], a_bases[i]) for i in range(N)]
    for i in range(N):
        if rng.random() < eve_fraction:
            e_basis = rng.randint(Z, X)
            e_bit = measure_all(lambda _, qc: prepare(qc, *states[i]), [e_basis])[0]
            states[i] = (e_bit, e_basis)   # Eve resends what she saw
    return a_bits, a_bases, states


def receive(states, bob_bases, noise=None):
    return measure_all(lambda i, qc: prepare(qc, *states[i]), bob_bases, noise)


def sift_and_check(a_bits, a_bases, bob_bases, bob_bits, n_check=CHECK):
    """Keep matching-basis qubits; the first n_check of them are the public check."""
    kept = [i for i in range(N) if a_bases[i] == bob_bases[i]]
    check, key = kept[:n_check], kept[n_check:]
    errors = sum(a_bits[i] != bob_bits[i] for i in check)
    return len(kept), errors / len(check), sum(a_bits[i] != bob_bits[i] for i in key), len(key)


def main():
    rand_bases = [rng.randint(Z, X) for _ in range(N)]

    print("A. BB84, Bob picks random bases")
    print(f"   {'link':14s} kept  QBER(check)  wrong key bits")
    for label, frac in (("clean", 0.0), ("Eve on all", 1.0)):
        a_bits, a_bases, states = make_link(frac)
        bits = receive(states, rand_bases)
        kept, q, wrong, total = sift_and_check(a_bits, a_bases, rand_bases, bits)
        print(f"   {label:14s} {kept:4d}  {q:9.1%}  {wrong}/{total}")
    print("   About half the qubits survive sifting. Eve guesses Alice's basis wrong")
    print("   half the time, and a wrong guess flips Bob's result half the time:")
    print("   1/2 x 1/2 = 25% errors. Clean links have none.\n")

    print("B. Bob always measures in Z (no basis choice)")
    z_bases = [Z] * N
    for label, frac in (("clean", 0.0), ("Eve on all", 1.0)):
        a_bits, a_bases, states = make_link(frac)
        bits = receive(states, z_bases)
        kept, q, wrong, total = sift_and_check(a_bits, a_bases, z_bases, bits)
        print(f"   {label:14s} kept {kept:4d}  QBER(check) {q:6.1%}  wrong key bits {wrong}/{total}")
    print("   Also fine on these links: Alice's bases are already random. Random")
    print("   bases on Bob's side are what BB84 prescribes, and they matter once an")
    print("   attacker could predict or steer Bob's choices.\n")

    print("C. No sifting: use every bit Bob measured, ignoring Alice's bases")
    a_bits, a_bases, states = make_link(0.0)
    bits = receive(states, rand_bases)
    wrong = sum(a_bits[i] != bits[i] for i in range(N))
    print(f"   clean link, all {N} bits: {wrong} wrong ({wrong / N:.0%})")
    print("   The mismatched-basis half is a coin flip, so about 25% of ALL bits are")
    print("   wrong, even without Eve. A key with 25% errors decrypts to garbage.\n")

    print("D. Eve taps only a fraction of the qubits: QBER on the check set")
    print(f"   {'fraction tapped':16s} QBER   (theory 25% x fraction)")
    for frac in (0.0, 0.1, 0.25, 0.5, 1.0):
        a_bits, a_bases, states = make_link(frac)
        bits = receive(states, rand_bases)
        _, q, _, _ = sift_and_check(a_bits, a_bases, rand_bases, bits)
        print(f"   {frac:16.0%} {q:6.1%}   {0.25 * frac:6.1%}")
    print("   Catching a full tap with k check bits fails with probability (3/4)^k:")
    for k in (5, 10, 20, 50):
        print(f"     k = {k:2d}: missed {0.75 ** k:.2%}")
    print("   We had about 140 sifted check bits per link, so a miss is impossible in practice.\n")

    print("E. Noise instead of Eve (clean link, depolarizing error on Bob's gates)")
    for p in (0.0, 0.02, 0.1):
        noise = NoiseModel()
        if p:
            noise.add_all_qubit_quantum_error(depolarizing_error(p, 1), ["h", "id", "x"])
        a_bits, a_bases, states = make_link(0.0)
        bits = receive(states, rand_bases, noise)
        _, q, _, _ = sift_and_check(a_bits, a_bases, rand_bases, bits)
        print(f"   p = {p:<5} QBER(check) = {q:5.1%}")
    print("   Real hardware has some noise, so BB84 compares QBER against a threshold")
    print("   (about 11% for the simplest proof) instead of requiring zero errors.")
    print("   Here the gap is huge: 0% versus ~21-25%, so a simple 'lowest QBER wins' works.")


if __name__ == "__main__":
    main()
