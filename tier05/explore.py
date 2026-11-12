"""Tier 5 experiments: compare classical and quantum ways to find the 10-bit key.

Run from the repo root (the folder that holds common/ and tier05/):
    python submissions/<team>/tier05/explore.py
It reads solution.py next to this file, writes explore_output.txt-style text to
stdout, benchmark.json and the two diagrams next to this file. The classical
searches run on the real locked data for COMPARISON ONLY; the submitted
solve() still finds the key with a quantum circuit.

Experiments
  A. Classical brute force over all 2^10 keys (no early stop).
  B. Classical, stop at the first key that decrypts to the known prefix.
  C. Grover: success probability against the number of rounds (too few, right, too many).
  D. Three ways to build the oracle: gate counts and depth.
  E. Unknown number of marked keys: randomised rounds (BBHT) instead of a fixed count.
  F. Grover under depolarizing noise on every CX.
  G. Scaling with the key size.
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

spec = importlib.util.spec_from_file_location("tier_solution", HERE / "solution.py")
sol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sol)

TIER = 5
locked = load_locked(TIER)
KEY_BITS = locked["public_parameters"]["key_bits"]
PREFIX = locked["public_parameters"]["known_prefix"].encode()[:2]  # 'QC', what the oracle checks
CIPHERTEXT = bytes.fromhex(locked["ciphertext_hex"])
N = 2 ** KEY_BITS
rng = random.Random(2026)
results = []   # rows for benchmark.json


def passes(key):
    return ToyCipher(key, KEY_BITS).decrypt(CIPHERTEXT[: len(PREFIX)]) == PREFIX


def compile_circuit(circuit):
    return transpile(circuit, basis_gates=sol.BASIS, optimization_level=2, seed_transpiler=1)


def size(compiled):
    ops = compiled.count_ops()
    return dict(qubits=compiled.num_qubits, two_qubit_gates=ops.get("cx", 0), depth=compiled.depth(),
                total_gates=sum(n for g, n in ops.items() if g != "measure"))


def run_counts(compiled, shots, noise=None, seed=5):
    backend = AerSimulator(method="statevector", seed_simulator=seed, noise_model=noise)
    counts = backend.run(compiled, shots=shots).result().get_counts()
    return {int(b, 2): n for b, n in counts.items()}


equations, _ = sol.known_text_equations()
GATES, CHECKS, N_SCRATCH = sol.plan_oracle(equations, KEY_BITS)


# --------------------------------------------------------------------------
# A and B. Classical.
# --------------------------------------------------------------------------

def timed(function, repeats=5):
    best, value = None, None
    for _ in range(repeats):
        start = time.perf_counter()
        value = function()
        elapsed = time.perf_counter() - start
        best = elapsed if best is None else min(best, elapsed)
    return value, best


def brute_force_all():
    found = [k for k in range(N) if passes(k)]
    return found


def early_stop():
    for trials, k in enumerate(range(N), start=1):
        if passes(k):
            return k, trials


def main():
    print(f"Tier {TIER}: {KEY_BITS}-bit key, {N} keys, known prefix {PREFIX!r}, "
          f"oracle = {len(CHECKS)} checks, {N_SCRATCH} scratch qubits\n")

    print("A. Classical brute force: try every key, no early stop (comparison only)")
    found, seconds = timed(brute_force_all)
    true_key = found[0]
    assert len(found) == 1
    print(f"   {N} trials, {seconds * 1000:.1f} ms, keys passing both bytes: {len(found)} (key = {true_key})")
    one_byte = [k for k in range(N) if ToyCipher(k, KEY_BITS).decrypt(CIPHERTEXT[:1]) == PREFIX[:1]]
    print(f"   Checking only byte 'Q' lets {len(one_byte)} keys through, so the oracle checks both bytes (README).")
    results.append(dict(name="Classical brute force, all keys", kind="classical", success_rate=1.0,
                        queries_or_oracle_calls=N, wall_seconds=seconds, qubits=None, two_qubit_gates=None,
                        depth=None, noisy_success=None, notes="comparison only; every key tried"))

    print("\nB. Classical with early stop")
    (key_b, trials_b), seconds_b = timed(early_stop)
    average = sum(sorted(range(N), key=lambda _: rng.random()).index(true_key) + 1 for _ in range(2000)) / 2000
    print(f"   numeric order: {trials_b} trials ({seconds_b * 1000:.1f} ms); random order averages "
          f"{average:.0f} trials (about N/2 = {N // 2})")
    results.append(dict(name="Classical, stop at first hit", kind="classical", success_rate=1.0,
                        queries_or_oracle_calls=trials_b, wall_seconds=seconds_b, qubits=None,
                        two_qubit_gates=None, depth=None, noisy_success=None,
                        notes=f"{trials_b} trials here; N/2 = {N // 2} on average"))

    # ------------------------------------------------------------------
    print("\nC. Grover: success probability against the number of rounds k (1 marked key)")
    theta = math.asin(math.sqrt(1 / N))
    k_best = math.floor(math.pi / 4 * math.sqrt(N))
    print(f"   theory: P(k) = sin^2((2k+1)*theta), theta = asin(sqrt(1/{N})); best k = {k_best}")
    print(f"   {'k':>3s} {'theory':>8s} {'Aer':>8s}   2Q gates")
    submitted = None
    for k in (0, 1, 2, 5, 10, 15, 20, k_best, 30, 40, 50):
        circuit, _ = sol.grover_circuit(equations, KEY_BITS, iterations=k)
        compiled = compile_circuit(circuit)
        counts = run_counts(compiled, 2000)
        measured = counts.get(true_key, 0) / 2000
        theory = math.sin((2 * k + 1) * theta) ** 2
        print(f"   {k:3d} {theory:8.3f} {measured:8.3f}   {size(compiled)['two_qubit_gates']}")
        if k == k_best:
            submitted = (compiled, measured, k)
    print("   Too few rounds: the key is still hidden. Too many: the state rotates past the key")
    print("   and the success drops again (k = 50 is worse than k = 25). Peak at k = 25.")

    compiled, measured, k = submitted
    _, seconds_q = timed(sol.solve, repeats=3)
    print(f"   time to solution, solve() end to end (build, compile, run, check; best of 3): {seconds_q:.2f} s")
    info = submitted_info = size(compiled)
    results.append(dict(name=f"Grover, {k} rounds (submitted)", kind="quantum", success_rate=measured,
                        queries_or_oracle_calls=k, wall_seconds=seconds_q, noisy_success=None,
                        notes="shared Toffolis, in-place equations, relative-phase Toffolis", **info))

    # ------------------------------------------------------------------
    print("\nD. Three oracle builds (same Grover, same result)")
    raw = []
    for position, plain_byte in enumerate(PREFIX):
        raw += sol.byte_equations(KEY_BITS, position, CIPHERTEXT[position], plain_byte)
    variants = {
        "submitted (simplified, RCCX)": (equations, True),
        "simplified, plain Toffoli": (equations, False),
        "raw equations, RCCX": (raw, True),
    }
    print(f"   {'oracle build':32s} qubits  CX   depth  success")
    for name, (eqs, relative) in variants.items():
        circuit, rounds = grover_variant(eqs, relative)
        compiled = compile_circuit(circuit)
        info = size(compiled)
        if info["qubits"] <= 24:
            success = run_counts(compiled, 1000).get(true_key, 0) / 1000
            shown = f"{success:7.3f}"
        else:
            success, shown = None, "  (too big to simulate)"
        print(f"   {name:32s} {info['qubits']:6d} {info['two_qubit_gates']:5d} {info['depth']:6d} {shown}")
        if not name.startswith("submitted"):
            results.append(dict(name=f"Grover, oracle: {name}", kind="quantum", success_rate=success,
                                queries_or_oracle_calls=rounds, wall_seconds=None, noisy_success=None,
                                notes="oracle-construction comparison", **info))
    print("   Plain Toffolis (6 CX each) instead of relative-phase ones (3 CX) add about a third more CX")
    print("   overall; the extra phases of the RCCX cancel because the oracle is W^-1 Z W. Skipping the")
    print("   shared-Toffoli trick costs 2 more qubits, about 45% more CX and nearly double the depth.\n")

    # ------------------------------------------------------------------
    print("E. Number of marked keys unknown: BBHT (random rounds, grow the range by 6/5)")
    calls = []
    for _ in range(3000):
        m, total = 1.0, 0
        while True:
            j = rng.randrange(int(m))
            total += j + 1   # j Grover rounds plus the classical check counts as one more oracle use
            if rng.random() < math.sin((2 * j + 1) * theta) ** 2:
                break
            m = min(m * 6 / 5, math.sqrt(N))
        calls.append(total)
    print(f"   average oracle uses: {sum(calls) / len(calls):.0f} (fixed k = {k_best} is {k_best + 1};"
          f" classical N/2 = {N // 2})")
    print("   Costs about 2x the best fixed k but needs no knowledge of M. Here M = 1 is known, so we use fixed k.")
    results.append(dict(name="Grover, BBHT randomised rounds", kind="quantum", success_rate=1.0,
                        queries_or_oracle_calls=round(sum(calls) / len(calls)), wall_seconds=None,
                        qubits=submitted_info["qubits"], two_qubit_gates=None, depth=None, noisy_success=None,
                        notes="simulated with the exact success formula; average oracle uses until a verified key"))

    # ------------------------------------------------------------------
    print("\nF. Noise: depolarizing error after each CX (40 noisy runs per setting, submitted circuit)")
    noisy = {}
    submitted_compiled = compile_circuit(sol.build_circuit())
    for p in (1e-5, 1e-4, 1e-3):
        noise = NoiseModel()
        noise.add_all_qubit_quantum_error(depolarizing_error(p, 2), ["cx"])
        start = time.perf_counter()
        counts = run_counts(submitted_compiled, 40, noise)
        ok = counts.get(true_key, 0) / 40
        noisy[str(p)] = ok
        print(f"   error {p:g} per CX: key found in {ok:5.0%} of runs ({time.perf_counter() - start:.0f} s)")
    cx = size(submitted_compiled)["two_qubit_gates"]
    print(f"   Rule of thumb: the circuit survives while p x (number of CX) is well below 1. With {cx} CX")
    print(f"   gates that means p below about 1/{cx} = {1 / cx:.0e}. Today's devices (about 1e-3 per CX) need error correction.")
    for row in results:
        if row["name"].endswith("(submitted)"):
            row["noisy_success"] = {"cx_error": noisy}

    # ------------------------------------------------------------------
    print("\nG. Scaling with the key size n (N = 2^n keys, one marked)")
    print(f"   {'n':>4s} {'classical avg':>16s} {'Grover rounds':>16s}   CX if rounds x {cx // k_best}/round")
    for n in (10, 14, 20, 32, 64, 128):
        total = 2 ** n
        rounds = math.pi / 4 * math.sqrt(total)
        print(f"   {n:4d} {total / 2:16.3g} {rounds:16.3g}   {rounds * cx / k_best:.3g}")
    print("   Grover is only a square-root speed-up: 128-bit keys still need ~2^64 rounds of a big oracle.")
    print("   Doubling the key length is the standard defence.")

    benchmark = dict(tier=TIER, answer=sol.solve(), methods=results)
    (HERE / "benchmark.json").write_text(json.dumps(benchmark, indent=2), encoding="utf-8")
    draw_diagrams()


# --------------------------------------------------------------------------
# Oracle variants (copies of the solution's builders with a switch).
# --------------------------------------------------------------------------

def grover_variant(eqs, relative_phase):
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
    rounds = math.floor(math.pi / 4 * math.sqrt(N))
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
