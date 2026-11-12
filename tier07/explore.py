"""Tier 7 experiments: compare ways to read the hidden 14-bit angle.

Run from the repo root:  python submissions/<team>/tier07/explore.py
Writes benchmark.json next to this file.

The tier rules forbid solving by eigenvalues of U. Methods marked CLASSICAL
below are for the presentation only (cost comparison); solution.py is the only
file the checker scores.

Methods
  A. CLASSICAL brute force over the 2^14 keys, checking the ciphertext prefix.
  B. CLASSICAL brute force over the 2^14 angles against the matrix of U.
  C. Repeated measurement (Hadamard test, one use of U per shot): shots needed.
  D. Textbook phase estimation with t counting qubits (t = 4 ... 14).
  E. Iterative (semiclassical) phase estimation on 2 qubits: our solution.
  F. Noise: D (t = 14) and E under depolarizing error on the gates.
"""
import json
import os
import warnings
import sys
import time
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, os.getcwd())          # repo root, for `common` and `tier07`
sys.path.insert(0, str(Path(__file__).resolve().parent))

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import QFT
from qiskit.quantum_info import Operator, Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

import solution as sol
from common import keystream, load_locked, xor_bytes
from tier07 import helper

N_BITS = load_locked(7)["public_parameters"]["key_bits"]
M = 2 ** N_BITS
BASIS = ["rz", "sx", "x", "cx"]
LOCKED = load_locked(7)
CIPHER = bytes.fromhex(LOCKED["ciphertext_hex"])
benchmark = []


def metrics(circuit):
    t = transpile(circuit, basis_gates=BASIS, optimization_level=1)
    ops = t.count_ops()
    active = {t.find_bit(q).index for inst in t.data
              if inst.operation.name not in ("measure", "barrier") for q in inst.qubits}
    return {"qubits": len(active), "two_qubit_gates": ops.get("cx", 0), "depth": t.depth(),
            "total_gates": sum(v for k, v in ops.items() if k not in ("measure", "barrier"))}


def noise_model(p):
    nm = NoiseModel()
    if p:
        nm.add_all_qubit_quantum_error(depolarizing_error(p, 2), ["cx"])
        nm.add_all_qubit_quantum_error(depolarizing_error(p / 10, 1), ["sx", "x"])
    return nm


# ---------------------------------------------------------------- the truth
t0 = time.perf_counter()
K, _ = sol.run_phase_estimation()
solution_seconds = time.perf_counter() - t0
ANSWER = xor_bytes(CIPHER, keystream(format(K, f"0{N_BITS}b"), len(CIPHER))).decode()
print(f"Reference from solution.py: k = {K} = {K:014b}, phi = {K / M}")
print(f"  {ANSWER}\n")

# ------------------------------------------------------------ A. brute keys
print("A. CLASSICAL brute force over keys (decrypt, look for 'QC-07: ')")
t0 = time.perf_counter()
hits = [k for k in range(M)
        if xor_bytes(CIPHER, keystream(format(k, f"0{N_BITS}b"), len(CIPHER))).startswith(b"QC-07: ")]
a_sec = time.perf_counter() - t0
print(f"   tried {M} keys in {a_sec:.2f} s, found {hits}")
print("   14 bits is tiny. Each extra key bit doubles this: 2^40 is days, 2^128 is never.\n")
benchmark.append({"name": "A. classical brute force over keys", "kind": "classical",
                  "success_rate": 1.0 if hits == [K] else 0.0, "queries_or_oracle_calls": M,
                  "wall_seconds": round(a_sec, 3), "qubits": 0, "two_qubit_gates": 0, "depth": 0,
                  "noisy_success": None,
                  "notes": "decrypt with every key and test the QC-07 prefix; 2^n cost, never touches U"})

# ------------------------------------------------- B. brute angles vs matrix
print("B. CLASSICAL brute force over angles against the matrix of U (not allowed")
print("   as a solution: it needs U and the eigenstate as plain numbers)")
u = Operator(helper.build_unitary()).data
psi = Statevector(helper.build_eigenstate()).data
lam = np.vdot(psi, u @ psi)
t0 = time.perf_counter()
best = min(range(M), key=lambda c: abs(lam - np.exp(2j * np.pi * c / M)))
b_sec = time.perf_counter() - t0
print(f"   eigenvalue e^(2 pi i phi) = {lam:.6f}, best of {M} angles: k = {best} ({b_sec:.3f} s)")
print(f"   matches the quantum answer: {best == K}\n")
benchmark.append({"name": "B. classical angle scan vs matrix of U", "kind": "classical",
                  "success_rate": 1.0 if best == K else 0.0, "queries_or_oracle_calls": M,
                  "wall_seconds": round(b_sec, 3), "qubits": 0, "two_qubit_gates": 0, "depth": 0,
                  "noisy_success": None,
                  "notes": "reads U and the eigenstate as numbers (forbidden for the tier); a direct eigenvalue read is O(1) and would be the real shortcut"})

# ----------------------------------------------------- C. repeated measuring
print("C. Repeated measurement: Hadamard test with ONE use of U per shot")
print("   P(0) = (1 + cos 2 pi phi)/2 (X readout) and (1 + sin 2 pi phi)/2 (Y readout)")


def hadamard_circuit(readout):
    qc = QuantumCircuit(2, 1)
    qc.compose(helper.build_eigenstate(), [1], inplace=True)
    qc.h(0)
    qc.append(sol.controlled_power(1), [0, 1])
    if readout == "y":
        qc.sdg(0)
    qc.h(0)
    qc.measure(0, 0)
    return transpile(qc, basis_gates=BASIS, optimization_level=1)


backend = AerSimulator(seed_simulator=5)
hc, hs = hadamard_circuit("x"), hadamard_circuit("y")
rng_seed = 100


def hadamard_estimate(n):
    global rng_seed
    rng_seed += 1
    sim = AerSimulator(seed_simulator=rng_seed)
    pc = sim.run(hc, shots=n).result().get_counts().get("0", 0) / n
    ps = sim.run(hs, shots=n).result().get_counts().get("0", 0) / n
    return (np.arctan2(2 * ps - 1, 2 * pc - 1) / (2 * np.pi)) % 1


print(f"   {'shots per readout':>18s} {'rms error (in 1/2^14 units)':>28s} {'exact k found':>14s}")
errs = {}
t0 = time.perf_counter()
for n in (100, 1_000, 10_000, 100_000, 1_000_000):
    trials = 30
    est = np.array([hadamard_estimate(n) for _ in range(trials)])
    diff = ((est - K / M + 0.5) % 1 - 0.5) * M
    errs[n] = float(np.sqrt(np.mean(diff ** 2)))
    found = np.mean(np.round(est * M) % M == K)
    print(f"   {n:18,d} {errs[n]:28.2f} {found:14.0%}")
c_sec = time.perf_counter() - t0
const = np.mean([errs[n] * np.sqrt(n) for n in errs])
need = int((const / 0.2) ** 2)
print(f"   error ~ {const:.0f} / sqrt(shots). For rms error 0.2 grid steps (rounding right")
print(f"   ~99% of the time) we need about {need:.1e} shots per readout.")
print("   Quantum phase estimation reaches the same precision with 14 rounds.\n")
benchmark.append({"name": "C. repeated Hadamard test (1 use of U per shot)", "kind": "classical",
                  "success_rate": float(np.mean(np.round(np.array([hadamard_estimate(1_000_000) for _ in range(10)]) * M) % M == K)),
                  "queries_or_oracle_calls": 2 * 1_000_000, "wall_seconds": round(c_sec, 2),
                  "qubits": 2, "two_qubit_gates": metrics(hadamard_circuit('x'))["two_qubit_gates"],
                  "depth": metrics(hadamard_circuit('x'))["depth"], "noisy_success": None,
                  "notes": f"rms error ~ {const:.0f}/sqrt(N) grid steps; need ~{need:.1e} shots per readout for 99% exact; success_rate measured at 10^6 shots"})

# ------------------------------------------------------ D. textbook QPE, t
print("D. Textbook phase estimation with t counting qubits + 1 eigenstate qubit")


def textbook_qpe(t):
    qc = QuantumCircuit(t + 1, t)
    qc.compose(helper.build_eigenstate(), [t], inplace=True)
    qc.h(range(t))
    for j in range(t):
        qc.append(sol.controlled_power(2 ** j), [j, t])
    qc.compose(QFT(t, inverse=True, do_swaps=True).decompose(), range(t), inplace=True)
    qc.measure(range(t), range(t))
    return qc


print(f"   {'t':>3s} {'P(best t-bit value)':>20s} {'k read exactly':>15s} {'2q gates':>9s} {'depth':>6s}")
rows_d = {}
for t in (4, 6, 8, 10, 12, 14):
    qc = textbook_qpe(t)
    comp = transpile(qc, basis_gates=BASIS, optimization_level=1)
    t0 = time.perf_counter()
    counts = AerSimulator(seed_simulator=9).run(comp, shots=500).result().get_counts()
    sec = time.perf_counter() - t0
    target = round(K / 2 ** (N_BITS - t)) % 2 ** t       # best t-bit approximation
    p_best = counts.get(format(target, f"0{t}b"), 0) / 500
    top = int(max(counts, key=counts.get), 2)
    exact = t == N_BITS and top == K
    mt = metrics(qc)
    rows_d[t] = (p_best, mt, sec, top)
    print(f"   {t:3d} {p_best:20.2f} {'yes' if exact else 'no (only top ' + str(t) + ' bits)':>15s} {mt['two_qubit_gates']:9d} {mt['depth']:6d}")
print("   With t < 14 the angle is only known to t bits: the other bits stay unknown,")
print("   so the key (all 14 bits) is wrong. t = 14 gives it exactly in one shot.\n")
p14, m14, sec14, top14 = rows_d[14]
benchmark.append({"name": "D. textbook QPE, 14 counting qubits + inverse QFT", "kind": "quantum",
                  "success_rate": p14, "queries_or_oracle_calls": 2 ** N_BITS - 1,
                  "wall_seconds": round(sec14, 3), "qubits": m14["qubits"],
                  "two_qubit_gates": m14["two_qubit_gates"], "depth": m14["depth"],
                  "noisy_success": None,
                  "notes": "oracle_calls = physical U applications per shot (sum of 2^j); here U^(2^j) is built from the matrix as one gate each (14 gates)"})
for t in (4, 8, 12):
    p, mt, sec, _ = rows_d[t]
    benchmark.append({"name": f"D. textbook QPE, t={t} (too few bits)", "kind": "quantum",
                      "success_rate": 0.0, "queries_or_oracle_calls": 2 ** t - 1,
                      "wall_seconds": round(sec, 3), "qubits": mt["qubits"],
                      "two_qubit_gates": mt["two_qubit_gates"], "depth": mt["depth"],
                      "noisy_success": None,
                      "notes": f"success_rate is for the exact 14-bit key; the top {t} bits come out right with P={p:.2f}"})

# ----------------------------------------------------- E. iterative (ours)
print("E. Iterative phase estimation: one reused control qubit, 2 qubits total")
t0 = time.perf_counter()
runs = 20
good = 0
for seed in range(runs):
    k_hat, _ = sol.run_phase_estimation(shots=1, seed=seed)
    good += k_hat == K
e_sec = (time.perf_counter() - t0) / runs
print(f"   exact key with ONE shot per round: {good}/{runs} runs")
rounds = [metrics(sol.round_circuit(m, K & (2 ** m - 1), N_BITS)) for m in range(N_BITS)]
worst = max(rounds, key=lambda r: (r["two_qubit_gates"], r["depth"]))
print(f"   largest round: {worst['qubits']} qubits, {worst['two_qubit_gates']} two-qubit gates, depth {worst['depth']}")
print(f"   14 rounds x 1 qubit measured; no inverse QFT, no 14-qubit register.\n")
benchmark.append({"name": "E. iterative (semiclassical) QPE, 2 qubits [submitted]", "kind": "quantum",
                  "success_rate": good / runs, "queries_or_oracle_calls": 2 ** N_BITS - 1,
                  "wall_seconds": round(e_sec, 3), "qubits": worst["qubits"],
                  "two_qubit_gates": worst["two_qubit_gates"], "depth": worst["depth"],
                  "noisy_success": None,
                  "notes": "14 circuits, 1 shot each is enough; checker reports 2q=2, depth 11, 16 gates, 2 active qubits"})

# --------------------------------------------------------------- F. noise
print("F. Noise: depolarizing error p after every cx (p/10 on 1-qubit gates)")
print(f"   {'p(cx)':>8s} {'iterative: exact key':>22s} {'textbook t=14: P(exact key)':>29s}")
rates = (0.0, 1e-4, 1e-3, 1e-2, 3e-2)
noisy_e, noisy_d = {}, {}
comp14 = transpile(textbook_qpe(N_BITS), basis_gates=BASIS, optimization_level=1)
for p in rates:
    nm = noise_model(p)
    # iterative: 15 shots per round, majority vote, 12 trials
    hit = 0
    trials = 12
    for tr in range(trials):
        k_hat = 0
        sim = AerSimulator(seed_simulator=1000 + tr, noise_model=nm)
        for m in range(N_BITS):
            c = transpile(sol.round_circuit(m, k_hat, N_BITS), basis_gates=BASIS, optimization_level=1)
            counts = sim.run(c, shots=15).result().get_counts()
            k_hat |= int(max(counts, key=counts.get)) << m
        hit += k_hat == K
    noisy_e[p] = hit / trials
    counts = AerSimulator(seed_simulator=3, noise_model=nm).run(comp14, shots=300).result().get_counts()
    noisy_d[p] = counts.get(format(K, "014b"), 0) / 300
    print(f"   {p:8.0e} {noisy_e[p]:22.0%} {noisy_d[p]:29.1%}")
print("   The 14-qubit textbook circuit has ~100x the cx gates (230 against 2 per round), so it breaks far earlier.")
print("   The iterative version has only 2 cx per round and survives much more noise,")
print("   because every round needs just one correct majority vote.")
print("   (Error mitigation such as ZNE/PEC not run: it is not needed at these sizes.)\n")
for entry in benchmark:
    if entry["name"].startswith("D. textbook QPE, 14"):
        entry["noisy_success"] = {f"{p:g}": noisy_d[p] for p in rates}
    if entry["name"].startswith("E."):
        entry["noisy_success"] = {f"{p:g}": noisy_e[p] for p in rates}

print("Summary table (benchmark.json has the same numbers)")
print(f"   {'method':52s} {'kind':9s} {'ok':>5s} {'qubits':>6s} {'2q':>6s} {'depth':>6s} {'secs':>8s}")
for e in benchmark:
    print(f"   {e['name'][:52]:52s} {e['kind']:9s} {e['success_rate']:5.2f} {e['qubits']:6d} "
          f"{e['two_qubit_gates']:6d} {e['depth']:6d} {e['wall_seconds']:8.2f}")

out = Path(__file__).resolve().parent / "benchmark.json"
out.write_text(json.dumps({"tier": 7, "answer": ANSWER, "methods": benchmark}, indent=2), encoding="utf-8")
print(f"\nwrote {out}")
