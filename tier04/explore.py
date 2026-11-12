"""Tier 4 experiments: compare ways to find the hidden XOR repeat s.

Quantum runs use the real oracle (Simon is a measurement of it, as the tier
allows). Classical methods only ask the oracle questions x -> f(x) through Aer,
and are comparison-only: solution.py never uses them. The scaling experiment
uses small oracles we build ourselves.

Run from the repo root:  python submissions/<team>/tier04/explore.py
Writes explore_output.txt-style text to stdout, plus diagram_simon.png and
benchmark.json next to this file.

Experiments
  A. Classical brute force: ask all 1024 inputs, find the pair that collides.
  B. Classical birthday search: random inputs until two answers match.
  C. Simon (ideal): how many runs are needed, and the GF(2) solve.
  D. Simon under noise: strict GF(2) solve versus majority vote.
  E. Simon with the output measured first (the README's hint 1).
  F. Grover search for s using the oracle twice per round (other algorithm).
  G. Scaling with the number of bits.
"""
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

HERE = Path(__file__).resolve().parent
sys.path.insert(0, os.getcwd())
sys.path.insert(0, str(HERE))

import solution as sol  # noqa: E402
from common import load_locked, keystream, xor_bytes  # noqa: E402
from tier04 import helper  # noqa: E402

N = 10
BASIS = ["cx", "rz", "sx", "x"]
backend = AerSimulator(seed_simulator=4)
# Classical questions start from a basis state, so a matrix-product simulator is exact and fast.
classical_backend = AerSimulator(method="matrix_product_state", seed_simulator=4)
rng = random.Random(2026)
BENCH = []

ORACLE = helper.build_oracle()
FLAT = transpile(ORACLE, basis_gates=["cx", "ccx", "x"], optimization_level=0)
PARITY_OK = np.array([[bin(s & y).count("1") % 2 == 0 for y in range(1 << N)]
                      for s in range(1 << N)], dtype=np.int32)


def gate_stats(circuit):
    """Two-qubit gates and depth after lowering to {cx, rz, sx, x}."""
    t = transpile(circuit, basis_gates=BASIS, optimization_level=1)
    ops = t.count_ops()
    return ops.get("cx", 0), t.depth(), circuit.num_qubits


def add(name, kind, success, calls, seconds, circuit, noisy=None, notes=""):
    cx, depth, qubits = gate_stats(circuit)
    BENCH.append({"name": name, "kind": kind, "success_rate": success,
                  "queries_or_oracle_calls": calls, "wall_seconds": round(seconds, 3),
                  "qubits": qubits, "two_qubit_gates": cx, "depth": depth,
                  "noisy_success": noisy, "notes": notes})


# --------------------------------------------------------------------------
# Classical question: set the inputs to x, read f(x). One oracle call each.
# --------------------------------------------------------------------------

def query_circuit(x):
    qc = QuantumCircuit(2 * N, N)
    for j in range(N):
        if (x >> j) & 1:
            qc.x(j)
    qc.compose(FLAT, range(2 * N), inplace=True)
    qc.measure(range(N, 2 * N), range(N))
    return qc


def ask(xs):
    """Answers f(x) for each x in xs, on Aer."""
    result = classical_backend.run([query_circuit(x) for x in xs], shots=1).result()
    return [int(next(iter(result.get_counts(i))), 2) for i in range(len(xs))]


def collision_s(seen, x, fx):
    """If fx was already seen at another input, return s = x XOR that input."""
    if fx in seen:
        return x ^ seen[fx]
    seen[fx] = x
    return None


def birthday_stats(table, trials=3000):
    """Queries until the first collision in random order, from a cached table."""
    counts = []
    order = list(range(1 << N))
    for _ in range(trials):
        rng.shuffle(order)
        seen = {}
        for q, x in enumerate(order, start=1):
            if collision_s(seen, x, table[x]) is not None:
                counts.append(q)
                break
    return counts


def rank_needed(ys):
    """Index of the first prefix of ys with a unique non-zero solution, or None."""
    for k in range(1, len(ys) + 1):
        if len(sol.solve_for_s(ys[:k])) == 1:
            return k
    return None


def vote(counts):
    """Best s by majority: the candidate orthogonal to the most measured y."""
    tally = np.zeros(1 << N)
    for y, c in counts.items():
        tally[int(y, 2)] += c
    scores = PARITY_OK @ tally
    scores[0] = -1          # s = 0 is always orthogonal; the promise says s != 0
    return int(np.argmax(scores))


def main():
    s_true = None
    answer = sol.solve()

    # ---------------- A. classical brute force -----------------------------
    print("A. Classical brute force: ask all 1024 inputs (comparison-only)")
    t0 = time.perf_counter()
    table = ask(range(1 << N))
    seen, s_found = {}, None
    for x, fx in enumerate(table):
        s_found = collision_s(seen, x, fx) if s_found is None else s_found
    t_brute = time.perf_counter() - t0
    s_true = s_found
    eq, _ = sol.run_simon()
    assert sol.solve_for_s(eq) == [s_true], "Simon and brute force disagree"
    pairs = sum(1 for x in range(1 << N) if table[x] == table[x ^ s_true]) // 2
    print(f"   queries: {1 << N}, found s = {s_true:010b} in {t_brute:.1f} s ({pairs} colliding pairs)")
    print(f"   f takes {len(set(table))} distinct values, exactly 2-to-1: {len(set(table)) == 512}")
    print("   Sequential scan needs only 2^(top bit of s) + 1 queries here")
    top = s_true.bit_length() - 1
    print(f"   (top bit {top}: {2 ** top + 1} queries), but the worst case is 2^(n-1) + 1 = 513.\n")
    add("Classical brute force (ask all 1024 inputs)", "classical", 1.0, 1 << N, t_brute,
        query_circuit(0), notes="Comparison only. Deterministic; each query is one Aer run of the oracle.")

    # ---------------- B. classical birthday ---------------------------------
    print("B. Classical birthday search: random inputs until two answers match")
    order = list(range(1 << N))
    rng.shuffle(order)
    t0 = time.perf_counter()
    seen, q = {}, 0
    for x in order:
        q += 1
        if collision_s(seen, x, ask([x])[0]) is not None:
            break
    t_birthday = time.perf_counter() - t0
    counts = birthday_stats(table)
    mean_q = sum(counts) / len(counts)
    print(f"   one live run on Aer: {q} queries, {t_birthday:.2f} s")
    print(f"   3000 simulated runs: mean {mean_q:.1f}, median {sorted(counts)[len(counts) // 2]}, "
          f"max {max(counts)} queries (theory sqrt(pi x 1024 / 2) = {math.sqrt(math.pi * 1024 / 2):.0f})")
    print("   chance to have found s within a budget of q questions:")
    for budget in (8, 16, 32, 64, 128):
        print(f"     q = {budget:3d}: {sum(c <= budget for c in counts) / len(counts):6.1%}")
    print()
    add("Classical birthday search (random order)", "classical",
        1.0, round(mean_q, 1), t_birthday, query_circuit(0),
        notes=f"Comparison only. Mean queries over 3000 runs; worst seen {max(counts)}; "
              f"success within 32 queries: {sum(c <= 32 for c in counts) / len(counts):.0%}.")

    # ---------------- C. Simon ideal ---------------------------------------
    print("C. Simon's algorithm, ideal (Aer), real oracle")
    t0 = time.perf_counter()
    circuit = sol.build_circuit()
    shots_total = 4000
    result = backend.run(transpile(circuit, backend), shots=shots_total, memory=True).result()
    t_simon = time.perf_counter() - t0
    ys = [int(b, 2) for b in result.get_memory()]
    print(f"   4000 shots in {t_simon:.2f} s; first runs: {[format(y, '010b') for y in ys[:5]]}")
    print(f"   check: every y has y.s = 0: {all(bin(y & s_true).count('1') % 2 == 0 for y in ys)}")
    print("   number of runs k -> chance the k equations pin s down (measured / theory):")
    needed = []
    for k in (6, 8, 9, 10, 12, 15, 20, 40):
        chunks = [ys[i:i + k] for i in range(0, 4000 - k + 1, k)]
        ok = sum(sol.solve_for_s(c) == [s_true] for c in chunks) / len(chunks)
        theory = math.prod(1 - 2.0 ** (i - k) for i in range(N - 1)) if k >= N - 1 else 0.0
        print(f"     k = {k:2d}: {ok:6.1%}   (theory {theory:6.1%})")
    for i in range(0, 4000, 40):
        k = rank_needed(ys[i:i + 40])
        if k:
            needed.append(k)
    mean_k = sum(needed) / len(needed)
    chunks40 = [ys[i:i + 40] for i in range(0, 4000, 40)]
    success40 = sum(sol.solve_for_s(c) == [s_true] for c in chunks40) / len(chunks40)
    print(f"   runs until s is unique: mean {mean_k:.1f}, max {max(needed)} (theory n - 1 + 1.6 = {N - 1 + 1.6:.1f})")
    print(f"   our solution uses 40 runs: success {success40:.1%} over {len(chunks40)} trials\n")
    t0 = time.perf_counter()
    sol.solve()
    t_solve = time.perf_counter() - t0

    # ---------------- D. noise ---------------------------------------------
    print("D. Simon under noise: depolarizing error after every cx")
    t_circ = transpile(circuit, basis_gates=BASIS, optimization_level=1)
    cx = t_circ.count_ops().get("cx", 0)
    print(f"   {cx} cx gates in the circuit; two decoders per run: strict GF(2) solve versus majority vote")
    print(f"   {'p(cx)':8s} {'strict':>8s} {'vote':>8s}   (trials of {NOISE_SHOTS} shots)")
    strict_d, vote_d = {}, {}
    for p in NOISE_P:
        nm = NoiseModel()
        if p:
            nm.add_all_qubit_quantum_error(depolarizing_error(p, 2), ["cx"])
        sim = AerSimulator(noise_model=nm)
        strict_ok = vote_ok = 0
        for trial in range(NOISE_TRIALS):
            counts = sim.run(t_circ, shots=NOISE_SHOTS, seed_simulator=100 + trial).result().get_counts()
            strict_ok += sol.solve_for_s([int(b, 2) for b in counts]) == [s_true]
            vote_ok += vote(counts) == s_true
        strict_d[str(p)], vote_d[str(p)] = strict_ok / NOISE_TRIALS, vote_ok / NOISE_TRIALS
        print(f"   {p:<8} {strict_d[str(p)]:8.0%} {vote_d[str(p)]:8.0%}")
    print("   Strict solving breaks at the first wrong y (one noisy equation can rule out")
    print("   the true s). Voting only needs the true s to win a majority of the runs.\n")
    add("Simon + GF(2) elimination (submitted)", "quantum", success40, round(mean_k, 1), t_solve,
        circuit, strict_d, notes=f"Ideal: {success40:.0%} with 40 runs; mean {mean_k:.1f} runs to pin s. "
        "noisy_success = strict GF(2) solve at those cx error rates.")
    add("Simon + majority vote", "quantum", 1.0, NOISE_SHOTS, t_simon, circuit, vote_d,
        notes=f"Noise-robust decoder, {NOISE_SHOTS} runs per attempt; "
              "noisy_success = vote decoder at those cx error rates.")

    # ---------------- E. output measured first -----------------------------
    print("E. Simon with the output register measured first (hint 1 version)")
    qc = QuantumCircuit(2 * N, 2 * N)
    qc.h(range(N))
    qc.compose(FLAT, range(2 * N), inplace=True)
    qc.measure(range(N, 2 * N), range(N, 2 * N))
    qc.h(range(N))
    qc.measure(range(N), range(N))
    t0 = time.perf_counter()
    res = backend.run(transpile(qc, backend), shots=60, memory=True).result()
    t_e = time.perf_counter() - t0
    ys_e = [int(m[-N:], 2) for m in res.get_memory()]
    ok = sol.solve_for_s(ys_e) == [s_true]
    print(f"   60 runs, s recovered: {ok}; every y.s = 0: "
          f"{all(bin(y & s_true).count('1') % 2 == 0 for y in ys_e)}")
    print("   Same equations, same cost. Collapsing the output first only makes the picture")
    print("   easier to explain: the inputs hold x and x XOR s, and H turns that into y.s = 0.\n")
    add("Simon, output measured first", "quantum", 1.0 if ok else 0.0, 60, t_e, qc,
        notes="Equivalent to the submitted circuit; extra measurement of the output register.")

    # ---------------- F. Grover ---------------------------------------------
    print("F. Grover search for s (different algorithm, oracle used twice per round)")
    f0 = ask([0])[0]
    marked = 2          # x = 0 and x = s both satisfy f(x) = f(0)
    theta = math.asin(math.sqrt(marked / (1 << N)))
    rounds = round(math.pi / (4 * theta) - 0.5)
    g = QuantumCircuit(2 * N, N)
    g.h(range(N))
    for _ in range(rounds):
        g.compose(FLAT, range(2 * N), inplace=True)
        flips = [N + j for j in range(N) if not (f0 >> j) & 1]
        if flips:
            g.x(flips)
        g.h(2 * N - 1)
        g.mcx(list(range(N, 2 * N - 1)), 2 * N - 1)
        g.h(2 * N - 1)
        if flips:
            g.x(flips)
        g.compose(FLAT.inverse(), range(2 * N), inplace=True)
        g.h(range(N))
        g.x(range(N))
        g.h(N - 1)
        g.mcx(list(range(N - 1)), N - 1)
        g.h(N - 1)
        g.x(range(N))
        g.h(range(N))
    g.measure(range(N), range(N))
    t0 = time.perf_counter()
    gc = backend.run(transpile(g, backend), shots=400).result().get_counts()
    t_g = time.perf_counter() - t0
    p_s = gc.get(format(s_true, "010b"), 0) / 400
    p_0 = gc.get("0" * N, 0) / 400
    nonzero_best = max((k for k in gc if int(k, 2)), key=gc.get)
    calls = 1 + 2 * rounds
    print(f"   f(0) = {f0}; {rounds} rounds, {calls} oracle calls in one circuit (1 classical + 2/round)")
    print(f"   400 shots: P(s) = {p_s:.2f}, P(0) = {p_0:.2f}, most common non-zero = "
          f"{nonzero_best} (s = {s_true:010b})")
    gcx, gdepth, _ = gate_stats(g)
    print(f"   {gcx} cx gates, depth {gdepth}: about {gcx // max(gate_stats(circuit)[0], 1)}x bigger than Simon")
    print("   Quadratic speed-up only (about sqrt(2^n) rounds), so Simon's exponential win is lost.\n")
    add("Grover search for s (f(x) = f(0), two marked states)", "quantum",
        round(p_s + p_0, 3), calls, t_g, g, None,
        notes=f"P(s)={p_s:.2f}, P(0)={p_0:.2f}; any non-zero outcome is s. {rounds} rounds, "
              "about sqrt(N) oracle calls: quadratic, not exponential.")

    # ---------------- G. scaling --------------------------------------------
    print("G. Scaling with n (our own small oracles; Simon on Aer, classical by simulation)")
    print(f"   {'n':>3s} {'Simon runs (mean)':>18s} {'classical queries (mean)':>26s} {'classical worst':>16s}")
    for n in range(3, 12):
        runs, cl = [], []
        for _ in range(5):
            s = rng.randrange(1, 1 << n)
            pivot = (s & -s).bit_length() - 1
            o = QuantumCircuit(2 * n)
            for i in range(n):
                o.cx(i, n + i)
            for i in range(n):
                if (s >> i) & 1:
                    o.cx(pivot, n + i)
            q = QuantumCircuit(2 * n, n)
            q.h(range(n))
            q.compose(o, range(2 * n), inplace=True)
            q.h(range(n))
            q.measure(range(n), range(n))
            res = backend.run(transpile(q, backend), shots=6 * n, memory=True).result()
            yy = [int(m, 2) for m in res.get_memory()]
            k = next(k for k in range(1, len(yy) + 1)
                     if len(_solve_n(yy[:k], n)) == 1)
            runs.append(k)
            tbl = {x: min(x, x ^ s) for x in range(1 << n)}
            order = list(range(1 << n))
            c = []
            for _ in range(200):
                rng.shuffle(order)
                seen_n = {}
                for qn, x in enumerate(order, 1):
                    if tbl[x] in seen_n:
                        c.append(qn)
                        break
                    seen_n[tbl[x]] = x
            cl.append(sum(c) / len(c))
        print(f"   {n:3d} {sum(runs) / 5:18.1f} {sum(cl) / 5:26.1f} {2 ** (n - 1) + 1:16d}")
    print("   Extrapolated: n = 64: Simon ~ 66 runs, classical ~ 1.25 x 2^32 = 5.4e9 queries;")
    print("                 n = 128: Simon ~ 130 runs, classical ~ 2.3e19 queries.")
    print("   (Each Simon run still costs one oracle call, and the oracle itself grows with n.)")

    draw_diagram()
    (HERE / "benchmark.json").write_text(
        json.dumps({"tier": 4, "answer": answer, "methods": BENCH}, indent=2), encoding="utf-8")


def _solve_n(equations, n):
    """Same as sol.solve_for_s, for n bits."""
    pivots = sol.gf2_reduce(equations)
    for top in sorted(pivots):
        for other in pivots:
            if other != top and (pivots[other] >> top) & 1:
                pivots[other] ^= pivots[top]
    out = []
    for b in (b for b in range(n) if b not in pivots):
        s = 1 << b
        for top, row in pivots.items():
            if (row >> b) & 1:
                s |= 1 << top
        out.append(s)
    return out


def draw_diagram():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = sol.build_circuit().draw("mpl", fold=-1)
    fig.suptitle("Simon circuit: H on 10 inputs, one oracle call (20 qubits), H, measure inputs")
    fig.savefig(HERE / "diagram_simon.png", dpi=130, bbox_inches="tight")


NOISE_P = [0.0, 0.0001, 0.001, 0.003, 0.01, 0.03, 0.1]
NOISE_SHOTS = 200
NOISE_TRIALS = 5

if __name__ == "__main__":
    main()
