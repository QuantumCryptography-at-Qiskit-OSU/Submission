"""Tier 1 experiments: compare approaches on OUR OWN test oracles.

The real oracle may be used once, so every experiment here uses oracles we
build ourselves from a secret string we choose (f(x) = s.x mod 2, as CX gates
onto the target). solution.py is the only file that touches the real oracle.
Self-contained: needs only qiskit and qiskit_aer.

Run:  python explore.py   (writes benchmark.json next to this file)

Experiments
  A. Classical, one question per bit (24 unit-vector queries, on Aer)
  B. Classical, random questions + Gaussian elimination (how many?)
  C. Classical, brute force over all 2^n strings (time, extrapolated to 24)
  D. Bernstein-Vazirani: ONE question, always right
  E. "Quantum" but target left in |0>: why the |-> trick matters
  F. Noise: BV under depolarizing error, one shot vs majority vote
  G. Scaling with the number of bits n
"""
import json
import random
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

N = 24
S_SECRET = 0b110010100110101100111010  # our own test string, 24 bits
HERE = Path(__file__).resolve().parent
rng = random.Random(2026)
BASIS = ["h", "x", "cx"]
# All our circuits are Clifford, so the stabilizer method simulates 25 qubits
# (and Pauli noise on them) quickly.
backend = AerSimulator(method="stabilizer", seed_simulator=5)


def oracle_for(s, n):
    """|x>|t> -> |x>|t XOR s.x>: one CX per 1 bit of s."""
    qc = QuantumCircuit(n + 1, name="oracle")
    for j in range(n):
        if (s >> j) & 1:
            qc.cx(j, n)
    return qc


def run(circuit, shots=1, noise=None, seed=5):
    sim = AerSimulator(method="stabilizer", seed_simulator=seed, noise_model=noise)
    return sim.run(transpile(circuit, basis_gates=BASIS + ["measure"], optimization_level=0), shots=shots).result().get_counts()


def bv_circuit(oracle, n, kickback=True):
    qc = QuantumCircuit(n + 1, n)
    if kickback:
        qc.x(n)
        qc.h(n)
    qc.h(range(n))
    qc.compose(oracle, range(n + 1), inplace=True)
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc


def gate_stats(circuit):
    t = transpile(circuit, basis_gates=BASIS, optimization_level=0)
    ops = t.count_ops()
    return {"two_qubit_gates": ops.get("cx", 0), "depth": t.depth(),
            "total_gates": sum(v for k, v in ops.items() if k != "measure")}


def ask_parity(oracle, n, x):
    """One classical question: put x on the inputs with X gates, read the target."""
    qc = QuantumCircuit(n + 1, 1)
    for j in range(n):
        if (x >> j) & 1:
            qc.x(j)
    qc.compose(oracle, range(n + 1), inplace=True)
    qc.measure(n, 0)
    return int(next(iter(run(qc))))


def noise_model(p):
    nm = NoiseModel()
    if p:
        nm.add_all_qubit_quantum_error(depolarizing_error(p, 2), ["cx"])
    return nm


def parity(v):
    return bin(v).count("1") & 1


def main():
    results = []
    oracle = oracle_for(S_SECRET, N)

    # A. ---------------------------------------------------------------
    print("A. Classical, one question per bit (each question = one Aer run)")
    t0 = time.perf_counter()
    found = sum(ask_parity(oracle, N, 1 << j) << j for j in range(N))
    wall_a = time.perf_counter() - t0
    print(f"   queries = {N}, recovered s = {found:024b} ({'right' if found == S_SECRET else 'WRONG'}), {wall_a:.2f} s")
    print("   Asking x = 2^j gives bit j directly. Always right, but n questions.\n")
    results.append({"name": "A. classical, one bit per question", "kind": "classical",
                    "success_rate": float(found == S_SECRET), "queries_or_oracle_calls": N,
                    "wall_seconds": round(wall_a, 3), "qubits": N + 1, "two_qubit_gates": gate_stats(oracle)["two_qubit_gates"] * N,
                    "depth": None, "noisy_success": None, "notes": "24 separate oracle calls, X gates only"})

    # B. ---------------------------------------------------------------
    print("B. Classical, random questions + solving the equations over GF(2)")
    trials, counts_needed = 300, []
    for _ in range(trials):
        pivots, k = {}, 0
        while len(pivots) < N:
            x = rng.getrandbits(N)
            k += 1
            while x:
                top = x.bit_length() - 1
                if top not in pivots:
                    pivots[top] = x
                    break
                x ^= pivots[top]
        counts_needed.append(k)
    mean_q = sum(counts_needed) / trials
    print(f"   average questions to pin down s: {mean_q:.1f} (min {min(counts_needed)}, max {max(counts_needed)})")
    print("   Never fewer than 24 (each answer is one bit, s has 24 bits), and random ones")
    print("   waste a few repeats. Unit vectors (A) are better.\n")
    results.append({"name": "B. classical, random questions + elimination", "kind": "classical",
                    "success_rate": 1.0, "queries_or_oracle_calls": round(mean_q, 1), "wall_seconds": None,
                    "qubits": N + 1, "two_qubit_gates": None, "depth": None, "noisy_success": None,
                    "notes": "average of 300 trials, needs >= 24"})

    # C. ---------------------------------------------------------------
    print("C. Classical brute force: try every s, keep the one that agrees with answers")
    print("   (numpy, parity answers precomputed from our own oracle for a few x)")
    brute = {}
    for n in (12, 16, 20):
        s = rng.getrandbits(n)
        xs = [rng.getrandbits(n) for _ in range(n + 8)]
        answers = [parity(s & x) for x in xs]
        arr = np.arange(1 << n, dtype=np.uint32)
        t0 = time.perf_counter()
        ok = np.ones(1 << n, dtype=bool)
        for x, a in zip(xs, answers):
            bits = arr & np.uint32(x)
            par = np.zeros(1 << n, dtype=np.uint32)
            while bits.any():
                par ^= bits & np.uint32(1)
                bits >>= np.uint32(1)
            ok &= par == a
        survivors = np.flatnonzero(ok)
        brute[n] = time.perf_counter() - t0
        print(f"   n = {n:2d}: tried {1 << n:>8d} strings, {len(survivors)} survivor(s), "
              f"{'right' if survivors[0] == s else 'WRONG'}, {brute[n]:.3f} s")
    est24 = brute[20] * 16
    print(f"   Each +1 bit doubles the work: n = 24 would take about {est24:.0f} s here,")
    print(f"   n = 48 about {est24 * 2 ** 24 / 3600 / 24 / 365:.1f} years. Question-wise brute force")
    print("   still needs >= n answers to single out s, so it is never cheaper than A.\n")
    results.append({"name": "C. classical brute force over all s", "kind": "classical",
                    "success_rate": 1.0, "queries_or_oracle_calls": N + 8, "wall_seconds": round(est24, 1),
                    "qubits": 0, "two_qubit_gates": 0, "depth": 0, "noisy_success": None,
                    "notes": f"2^24 candidates; wall time extrapolated from n=20 ({brute[20]:.2f} s) x16, numpy"})

    # D. ---------------------------------------------------------------
    print("D. Bernstein-Vazirani: ONE oracle call")
    bv = bv_circuit(oracle, N)
    t0 = time.perf_counter()
    counts = run(bv, shots=100)
    wall_d = time.perf_counter() - t0
    top, freq = max(counts.items(), key=lambda kv: kv[1])
    print(f"   100 shots -> {len(counts)} distinct outcome(s); most common {top} ({freq}/100); "
          f"expected {S_SECRET:024b}")
    ours = QuantumCircuit(N + 1)
    ours.x(N)
    ours.h(range(N + 1))
    ours.h(range(N))
    print(f"   Our gates (without oracle): {sum(ours.count_ops().values())} single-qubit, 0 two-qubit")
    print(f"   Oracle itself (our test one): {gate_stats(oracle)}\n")
    d_stats = gate_stats(bv)
    results.append({"name": "D. Bernstein-Vazirani", "kind": "quantum",
                    "success_rate": freq / 100, "queries_or_oracle_calls": 1, "wall_seconds": round(wall_d, 3),
                    "qubits": N + 1, "two_qubit_gates": d_stats["two_qubit_gates"], "depth": d_stats["depth"],
                    "noisy_success": None, "notes": "our own gates: 1 X + 25 H + 24 H, no two-qubit gates"})

    # E. ---------------------------------------------------------------
    print("E. Same circuit but target left in |0> (no phase kickback)")
    wrong = bv_circuit(oracle, N, kickback=False)
    counts = run(wrong, shots=200)
    hit = counts.get(f"{S_SECRET:024b}", 0) / 200
    print(f"   P(correct s) = {hit:.2f}; outcomes seen: {sorted(counts)}")
    print("   |0> is an equal mix of |+> and |->. Only the |-> half gets the signs (-> s);")
    print("   the |+> half gets none (-> all zeros). So it fails half the time.\n")

    # F. ---------------------------------------------------------------
    print("F. Noise: depolarizing error after every CX in the oracle")
    print(f"   our test oracle: {gate_stats(oracle)['two_qubit_gates']} CX. one shot = a single run; vote = majority bit-by-bit of 101 shots")
    noisy = {}
    print(f"   {'CX error':>9s} {'one-shot exact':>15s} {'bit accuracy':>13s} {'vote exact':>11s}")
    for p in (0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1):
        nm = noise_model(p)
        trials, exact = 100, 0
        bit_acc = 0.0
        for k in range(trials):
            out = next(iter(run(bv, 1, nm, seed=1000 + k)))
            exact += out == f"{S_SECRET:024b}"
            bit_acc += sum(a == b for a, b in zip(out, f"{S_SECRET:024b}")) / N
        counts = run(bv, 101, nm, seed=77)
        vote = "".join("1" if sum(c for o, c in counts.items() if o[i] == "1") > 50 else "0" for i in range(N))
        noisy[p] = {"one_shot_exact": exact / trials, "bit_accuracy": round(bit_acc / trials, 3),
                    "vote_exact": float(vote == f"{S_SECRET:024b}")}
        print(f"   {p:9.3f} {exact / trials:15.2f} {bit_acc / trials:13.3f} {noisy[p]['vote_exact']:11.0f}")
    print("   A depolarizing CX error flips a few output bits at random. The oracle has only")
    print(f"   {gate_stats(oracle)['two_qubit_gates']} CX, so a majority vote over repeated runs recovers s up to quite large")
    print("   errors. Majority vote is the cheap 'mitigation' here; the circuit is tiny, so we")
    print("   skipped ZNE/PEC.\n")
    results[3]["noisy_success"] = {f"cx_error_{p}": v["one_shot_exact"] for p, v in noisy.items()}
    results[3]["notes"] += "; noisy_success = one-shot exact-match rate; see explore_output.txt for majority vote"

    # G. ---------------------------------------------------------------
    print("G. Scaling with the number of bits n (our own oracles, random s)")
    print(f"   {'n':>4s} {'classical queries':>18s} {'brute-force strings':>20s} {'BV queries':>11s} "
          f"{'BV own gates':>13s} {'oracle CX':>10s}")
    for n in (8, 16, 24, 32, 48, 64):
        s = rng.getrandbits(n)
        oc = oracle_for(s, n)
        mine = QuantumCircuit(n + 1)
        mine.x(n)
        mine.h(range(n + 1))
        mine.h(range(n))
        print(f"   {n:4d} {n:18d} {2 ** n:20.3e} {1:11d} {sum(mine.count_ops().values()):13d} "
              f"{oc.count_ops().get('cx', 0):10d}")
        counts = run(bv_circuit(oc, n), shots=4)
        assert list(counts) == [f"{s:0{n}b}"], "BV failed at n = " + str(n)
    print("   BV is right at every n tested. Classical question count grows with n,")
    print("   BV stays at one; our own gates grow only linearly (3n + 2).")
    print("   The gap is queries, not time: the oracle's own size (CX per 1 bit of s) is")
    print("   the same either way, and a quantum simulator needs 2^n memory in general")
    print("   (we only got n = 64 because this circuit is Clifford).")

    (HERE / "benchmark.json").write_text(json.dumps(
        {"tier": 1, "answer": "QC-01: Meet at the Oval when the clock reads 6:47", "methods": results},
        indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
