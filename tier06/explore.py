"""Tier 6 experiments: compare classical and quantum ways to find the 14-bit key.

Run from the repo root (the folder that holds common/ and tier06/):
    python submissions/<team>/tier06/explore.py
It reads solution.py next to this file, prints the results, and writes
benchmark.json and two diagrams next to this file. The classical searches run
on the real locked data for COMPARISON ONLY; the submitted solve() still
finds the key with a quantum circuit.

Experiments
  A. Classical brute force over all 2^14 keys (full decrypt, and staged).
  B. Classical, stop at the first key that passes the checksum.
  C. Grover with M = 64 marked keys: success against the number of rounds.
  D. What if we guess M wrong?
  E. Finding M from the circuit itself, and BBHT (random rounds, M unknown).
  F. Oracle builds: submitted, plain Toffoli, and an oracle that trusts 2 bytes.
  G. Grover under depolarizing noise on every CX.
  H. Scaling with the key size.
"""
import importlib.util
import json
import math
import os
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, os.getcwd())
sys.path.insert(0, str(HERE))

import matplotlib

matplotlib.use("Agg")
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

from common import load_locked
from common.toy_cipher import ToyCipher
from tier06 import helper

spec = importlib.util.spec_from_file_location("tier_solution", HERE / "solution.py")
sol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sol)

TIER = 6
locked = load_locked(TIER)
PARAMS = locked["public_parameters"]
KEY_BITS = PARAMS["key_bits"]
PREFIX = PARAMS["known_prefix"].encode()          # 'Q'
CHECKSUM = PARAMS["checksum"]
CIPHERTEXT = bytes.fromhex(locked["ciphertext_hex"])
N = 2 ** KEY_BITS
rng = random.Random(2026)
results = []   # rows for benchmark.json


def first_byte_ok(key):
    return ToyCipher(key, KEY_BITS).decrypt(CIPHERTEXT[:1]) == PREFIX


def fully_ok(key):
    plaintext = ToyCipher(key, KEY_BITS).decrypt(CIPHERTEXT)
    return plaintext.startswith(PREFIX) and helper.checksum(plaintext) == CHECKSUM


def compile_circuit(circuit):
    return transpile(circuit, basis_gates=sol.BASIS, optimization_level=2, seed_transpiler=1)


def size(compiled):
    ops = compiled.count_ops()
    return dict(qubits=compiled.num_qubits, two_qubit_gates=ops.get("cx", 0), depth=compiled.depth(),
                total_gates=sum(n for g, n in ops.items() if g != "measure"))


def run_counts(compiled, shots, noise=None, seed=6):
    backend = AerSimulator(method="statevector", seed_simulator=seed, noise_model=noise)
    counts = backend.run(compiled, shots=shots).result().get_counts()
    return {int(b, 2): n for b, n in counts.items()}


def timed(function, repeats=3):
    best, value = None, None
    for _ in range(repeats):
        start = time.perf_counter()
        value = function()
        elapsed = time.perf_counter() - start
        best = elapsed if best is None else min(best, elapsed)
    return value, best


equations, _ = sol.first_byte_equations()
M = sol.count_marked(equations, KEY_BITS)
GATES, CHECKS, N_SCRATCH = sol.plan_oracle(equations, KEY_BITS)
PASSING = None  # filled in main(): the 64 keys that pass the first byte


def pass_fraction(counts, shots):
    return sum(n for key, n in counts.items() if key in PASSING) / shots


def main():
    global PASSING
    print(f"Tier {TIER}: {KEY_BITS}-bit key, {N} keys, known prefix {PREFIX!r}, checksum {CHECKSUM}; "
          f"oracle = {len(CHECKS)} checks, {N_SCRATCH} scratch qubits, M = {M} keys pass\n")

    print("A. Classical brute force over all keys (comparison only)")
    start = time.perf_counter()
    survivors = [k for k in range(N) if fully_ok(k)]
    naive_seconds = time.perf_counter() - start
    print(f"   full decrypt of every key: {N} trials, {naive_seconds:.2f} s")
    PASSING, staged_seconds = timed(lambda: {k for k in range(N) if first_byte_ok(k)})
    true_key = survivors[0]
    assert len(survivors) == 1 and len(PASSING) == M
    print(f"   staged (check byte 0, then decrypt only the {len(PASSING)} that pass): {staged_seconds:.2f} s")
    print(f"   keys passing byte 0: {len(PASSING)}; passing the checksum too: {len(survivors)} (key = {true_key})")
    results.append(dict(name="Classical brute force, full decrypt of every key", kind="classical",
                        success_rate=1.0, queries_or_oracle_calls=N, wall_seconds=naive_seconds, qubits=None,
                        two_qubit_gates=None, depth=None, noisy_success=None, notes="comparison only"))
    results.append(dict(name="Classical brute force, staged (byte 0 first)", kind="classical",
                        success_rate=1.0, queries_or_oracle_calls=N, wall_seconds=staged_seconds, qubits=None,
                        two_qubit_gates=None, depth=None, noisy_success=None,
                        notes="comparison only; one cheap test per key, then the checksum on the 64 passers"))

    print("\nB. Classical with early stop (first key passing byte 0 and the checksum)")

    def early():
        for trials, k in enumerate(range(N), start=1):
            if first_byte_ok(k) and fully_ok(k):
                return trials

    trials_b, seconds_b = timed(early)
    average = sum(sorted(range(N), key=lambda _: rng.random()).index(true_key) + 1 for _ in range(300)) / 300
    print(f"   numeric order: {trials_b} trials ({seconds_b:.2f} s); random order averages {average:.0f} "
          f"(about N/2 = {N // 2})")
    results.append(dict(name="Classical, stop at first full match", kind="classical", success_rate=1.0,
                        queries_or_oracle_calls=trials_b, wall_seconds=seconds_b, qubits=None,
                        two_qubit_gates=None, depth=None, noisy_success=None,
                        notes=f"{trials_b} trials here; N/2 = {N // 2} on average"))

    # ------------------------------------------------------------------
    theta = math.asin(math.sqrt(M / N))
    k_best = math.floor(math.pi / 4 * math.sqrt(N / M))
    print(f"\nC. Grover with M = {M} marked keys: P(measure a passing key) against rounds k")
    print(f"   theory: sin^2((2k+1)*theta), theta = asin(sqrt(M/N)) = {theta:.4f}; best k = {k_best}")
    print(f"   {'k':>3s} {'theory':>8s} {'Aer':>8s}   2Q gates")
    submitted = None
    for k in (0, 1, 2, 4, 6, 8, 10, k_best, 14, 18, 24, 36):
        circuit, _ = sol.grover_circuit(equations, KEY_BITS, n_marked=M, iterations=k)
        compiled = compile_circuit(circuit)
        measured = pass_fraction(run_counts(compiled, 4000), 4000)
        theory = math.sin((2 * k + 1) * theta) ** 2
        print(f"   {k:3d} {theory:8.3f} {measured:8.3f}   {size(compiled)['two_qubit_gates']}")
        if k == k_best:
            submitted = (compiled, measured, k)
    print("   Overshooting hurts: at 24 rounds the state has rotated past the marked keys (k = 24 is")
    print("   about the same as k = 0 again). The 64 passing keys are equally likely, so one shot gives")
    print("   a random passer; the checksum picks the right one (1 in 64 chance per shot, 4096 shots cover it).")

    compiled, measured, k = submitted
    counts = run_counts(compile_circuit(sol.build_circuit()), 4096)
    survivors_q = [key for key in counts if fully_ok(key)]
    _, seconds_q = timed(sol.solve, repeats=3)
    info = submitted_info = size(compiled)
    print(f"   submitted run: {len(counts)} distinct keys seen, {len(survivors_q)} pass the checksum "
          f"({'right key' if survivors_q == [true_key] else 'MISMATCH'})")
    print(f"   time to solution, solve() end to end (best of 3): {seconds_q:.2f} s")
    results.append(dict(name=f"Grover, {k} rounds, M = {M} (submitted)", kind="quantum", success_rate=measured,
                        queries_or_oracle_calls=k, wall_seconds=seconds_q, noisy_success=None,
                        notes="success_rate = chance one shot is a passing key; checksum filter picks the key. "
                              "Oracle runs in place with no scratch qubits", **info))

    # ------------------------------------------------------------------
    print("\nD. Guessing M wrong (rounds = floor(pi/4 * sqrt(N / guess)))")
    print(f"   {'guessed M':>10s} {'rounds':>7s} {'theory':>8s} {'Aer':>8s}")
    for guess in (1, 4, 16, 64, 256, 1024):
        rounds = math.floor(math.pi / 4 * math.sqrt(N / guess))
        circuit, _ = sol.grover_circuit(equations, KEY_BITS, iterations=rounds)
        measured = pass_fraction(run_counts(compile_circuit(circuit), 3000), 3000)
        print(f"   {guess:10d} {rounds:7d} {math.sin((2 * rounds + 1) * theta) ** 2:8.3f} {measured:8.3f}")
    print("   Guessing M too small (1, 4, 16) runs far too many rounds and rotates past the target: success is")
    print("   near the random baseline (0.4%). Guessing too large (256, 1024) stops short: about 53% and 18%.")
    print("   Both directions lose, and Aer matches theory.\n")

    # ------------------------------------------------------------------
    print("E. M unknown")
    ks = (1, 2, 3, 4, 5, 6, 8)
    observed = []
    for k in ks:
        circuit, _ = sol.grover_circuit(equations, KEY_BITS, iterations=k)
        observed.append(pass_fraction(run_counts(compile_circuit(circuit), 8000), 8000))
    best_m, best_err = None, None
    for candidate in range(1, 1025):
        t = math.asin(math.sqrt(candidate / N))
        err = sum((math.sin((2 * k + 1) * t) ** 2 - o) ** 2 for k, o in zip(ks, observed))
        if best_err is None or err < best_err:
            best_m, best_err = candidate, err
    print(f"   Estimate M from the curve: run k = {ks}, fit sin^2((2k+1) asin(sqrt(M/N))) -> M = {best_m} (true {M})")
    calls = []
    for _ in range(3000):
        m, total = 1.0, 0
        while True:
            j = rng.randrange(int(m))
            total += j + 1
            if rng.random() < math.sin((2 * j + 1) * theta) ** 2:
                break
            m = min(m * 6 / 5, math.sqrt(N))
        calls.append(total)
    bbht = sum(calls) / len(calls)
    print(f"   BBHT (random rounds, grow range by 6/5, no knowledge of M): {bbht:.0f} oracle uses on average "
          f"to see a passing key (fixed k = {k_best} is {k_best + 1})")
    results.append(dict(name="Grover, BBHT randomised rounds (M unknown)", kind="quantum", success_rate=1.0,
                        queries_or_oracle_calls=round(bbht), wall_seconds=None, qubits=submitted_info["qubits"],
                        two_qubit_gates=None, depth=None, noisy_success=None,
                        notes="simulated with the exact success formula; average oracle uses to a passing key"))

    # ------------------------------------------------------------------
    print("\nF. Oracle builds")
    two_byte = list(sol.byte_equations(KEY_BITS, 0, CIPHERTEXT[0], PREFIX[0]))
    two_byte += sol.byte_equations(KEY_BITS, 1, CIPHERTEXT[1], ord("C"))
    two_byte = sol.simplify(two_byte)
    variants = {
        "submitted (1 byte, RCCX, M = 64)": (equations, True, b"Q"),
        "1 byte, plain Toffoli": (equations, False, b"Q"),
        "trust 2 bytes 'QC'": (two_byte, True, b"QC"),
    }
    print(f"   {'oracle build':36s} qubits    CX   depth rounds  success")
    for name, (eqs, relative, prefix) in variants.items():
        ok = {k for k in range(N) if ToyCipher(k, KEY_BITS).decrypt(CIPHERTEXT[: len(prefix)]) == prefix}
        marked = len(ok)
        circuit, rounds = grover_variant(eqs, relative, marked)
        compiled = compile_circuit(circuit)
        info = size(compiled)
        if info["qubits"] <= 24:
            counts = run_counts(compiled, 3000)
            success = sum(n for key, n in counts.items() if key in ok) / 3000
            shown = f"{success:7.3f}"
        else:
            success, shown = None, "   too big"
        print(f"   {name:36s} {info['qubits']:6d} {info['two_qubit_gates']:6d} {info['depth']:6d} {rounds:6d} {shown}   (M = {marked})")
        if not name.startswith("submitted"):
            results.append(dict(name=f"Grover, oracle: {name}", kind="quantum", success_rate=success,
                                queries_or_oracle_calls=rounds, wall_seconds=None, noisy_success=None,
                                notes=f"oracle-construction comparison, M = {marked}", **info))
    print("   Trusting two bytes cuts M from 64 to 2, so the checksum filter has almost nothing to do, but the")
    print("   search then needs about 6x the rounds (sqrt(64/2) = 5.7) and a bigger oracle per round, so about")
    print("   8x the total CX. The one-byte build wins: a large M shrinks the rounds, and the checksum filter is cheap.\n")

    # ------------------------------------------------------------------
    print("G. Noise: depolarizing error after each CX (100 noisy runs per setting, submitted circuit)")
    noisy = {}
    submitted_compiled = compile_circuit(sol.build_circuit())
    for p in (1e-5, 1e-4, 1e-3):
        noise = NoiseModel()
        noise.add_all_qubit_quantum_error(depolarizing_error(p, 2), ["cx"])
        start = time.perf_counter()
        ok = pass_fraction(run_counts(submitted_compiled, 100, noise), 100)
        noisy[str(p)] = ok
        print(f"   error {p:g} per CX: {ok:5.0%} of shots are passing keys ({time.perf_counter() - start:.0f} s)"
              f"   (random guessing: {M / N:.1%})")
    cx = submitted_info["two_qubit_gates"]
    print(f"   {cx} CX gates: the circuit survives while p x CX is well below 1, so p below about {1 / cx:.0e}.")
    for row in results:
        if row["name"].endswith("(submitted)"):
            row["noisy_success"] = {"cx_error": noisy}

    # ------------------------------------------------------------------
    print("\nH. Scaling with the key size n (M = 2^(n-8) keys pass the 8-bit first-byte test)")
    print(f"   {'n':>4s} {'classical avg':>14s} {'Grover rounds':>14s}")
    for n in (14, 20, 32, 64, 128):
        total, marked = 2 ** n, 2 ** (n - 8)
        print(f"   {n:4d} {total / 2:14.3g} {math.pi / 4 * math.sqrt(total / marked):14.3g}")
    print("   Here M grows with the key, so the rounds stay at about 12 for the first-byte test alone;")
    print("   the real cost moves to the classical checksum filter over the M survivors (and to deciding")
    print("   which of them is right). Trusting more known bytes gives M = 1 and the full sqrt(N) rounds.")

    benchmark = dict(tier=TIER, answer=sol.solve(), methods=results)
    (HERE / "benchmark.json").write_text(json.dumps(benchmark, indent=2), encoding="utf-8")
    draw_diagrams()


def grover_variant(eqs, relative_phase, n_marked):
    gates, checks, n_scratch = sol.plan_oracle(eqs, KEY_BITS)
    n_qubits = KEY_BITS + n_scratch + 2
    clean = [n_qubits - 2, n_qubits - 1]
    compute = QuantumCircuit(n_qubits)
    for gate in gates:
        if gate[0] == "cx":
            compute.cx(gate[1], gate[2])
        elif relative_phase:
            compute.rccx(gate[1], gate[2], gate[3])
        else:
            compute.ccx(gate[1], gate[2], gate[3])
    oracle = QuantumCircuit(n_qubits)
    oracle.compose(compute, inplace=True)
    zeros = [q for q, wanted in checks if wanted == 0]
    if zeros:
        oracle.x(zeros)
    sol.multi_controlled_z(oracle, [q for q, _ in checks], clean)
    if zeros:
        oracle.x(zeros)
    oracle.compose(compute.inverse(), inplace=True)
    diffusion = sol.build_diffusion(KEY_BITS, n_qubits, clean)
    rounds = math.floor(math.pi / 4 * math.sqrt(N / n_marked))
    circuit = QuantumCircuit(n_qubits, KEY_BITS)
    circuit.h(range(KEY_BITS))
    for _ in range(rounds):
        circuit.compose(oracle, inplace=True)
        circuit.compose(diffusion, inplace=True)
    circuit.measure(range(KEY_BITS), range(KEY_BITS))
    return circuit, rounds


def draw_diagrams():
    """Block diagram of the Grover circuit and the oracle's compute block."""
    n_qubits = KEY_BITS + N_SCRATCH + 2
    clean = [n_qubits - 2, n_qubits - 1]
    oracle = sol.build_oracle(GATES, CHECKS, n_qubits, clean)
    diffusion = sol.build_diffusion(KEY_BITS, n_qubits, clean)
    overview = QuantumCircuit(n_qubits, KEY_BITS)
    overview.h(range(KEY_BITS))
    overview.append(oracle.to_gate(label="Oracle\n(phase flip)"), range(n_qubits))
    overview.append(diffusion.to_gate(label="Diffusion"), range(n_qubits))
    overview.measure(range(KEY_BITS), range(KEY_BITS))
    overview.draw("mpl", fold=-1, filename=str(HERE / "diagram_grover.png"), scale=0.6)
    compute = QuantumCircuit(n_qubits)
    for gate in GATES:
        if gate[0] == "cx":
            compute.cx(gate[1], gate[2])
        else:
            compute.rccx(gate[1], gate[2], gate[3])
    compute.draw("mpl", fold=40, filename=str(HERE / "diagram_oracle.png"), scale=0.5)


if __name__ == "__main__":
    main()
