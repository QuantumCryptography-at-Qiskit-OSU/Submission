"""Tier 10 experiments: every way we tried to recover the Diffie-Hellman exponent.

Run from anywhere inside the Submission folder:
    python tier10/explore.py
It also writes benchmark.json, diagram_shor.png and diagram_grover.png here.

p = 83, g = 3 (order 41), A = g^a, B = g^b. We need a, then secret = B^a mod p.

  1. Classical methods (comparison only; the submitted solve() never uses them):
     brute force, lookup table, baby-step giant-step, Pollard rho.
  2. Shor's discrete log, our main solution (solution.py): one recycled control.
     2a. success against the number of shots, 2b. against the phase bits t.
  3. Shor's discrete log, textbook version: two counting registers at once.
  4. Grover search over exponents (grover_dlog.py).
  5. Noise: depolarizing error on every CX.
  6. Rebuild the shared secret and decrypt.
  7. Circuit sizes, measured the way the checker measures them.
"""
import importlib.util
import json
import math
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = next(
    folder
    for folder in [HERE, *HERE.parents, HERE.parent.parent / "Quantum-Cryptography-Challenge"]
    if (folder / "common" / "check.py").exists()
)
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile  # noqa: E402
from qiskit.circuit import Gate  # noqa: E402
from qiskit.circuit.library import QFTGate  # noqa: E402
from qiskit_aer import AerSimulator  # noqa: E402
from qiskit_aer.noise import NoiseModel, depolarizing_error  # noqa: E402

from common import is_correct, keystream, load_locked, xor_bytes  # noqa: E402

import solution as shor  # noqa: E402
import grover_dlog as grover  # noqa: E402

rng = random.Random(2026)
SCORING = dict(basis_gates=["rz", "sx", "x", "cx"], coupling_map=None,
               optimization_level=1, seed_transpiler=12345)
BENCH = []


def metrics(circuit):
    t = transpile(circuit, **SCORING)
    skip = {"measure", "reset", "barrier", "delay"}
    gates, two_q, active = 0, 0, set()

    def walk(circ, qubit_map):
        nonlocal gates, two_q
        for inst in circ.data:
            op = inst.operation
            qs = [qubit_map[q] for q in inst.qubits]
            if op.name in skip:
                continue
            if getattr(op, "blocks", None):
                for block in op.blocks:
                    walk(block, {bq: qs[i] for i, bq in enumerate(block.qubits)})
                continue
            gates += 1
            two_q += len(qs) == 2
            active.update(qs)

    walk(t, {q: q for q in t.qubits})
    return {"two_qubit_gates": two_q, "depth": t.depth(), "total_gates": gates, "qubits": len(active)}


def noise_model(p):
    model = NoiseModel()
    if p:
        model.add_all_qubit_quantum_error(depolarizing_error(p, 2), ["cx"])
    return model


# --------------------------------------------------------------------------
# 1. Classical methods
# --------------------------------------------------------------------------

def brute_force(g, big_a, p):
    value, steps = 1, 0
    for x in range(p):
        steps += 1
        if value == big_a:
            return x, steps
        value = value * g % p


def lookup_table(g, big_a, p, order):
    table = {pow(g, x, p): x for x in range(order)}
    return table[big_a], order  # building the table costs `order` multiplications


def baby_step_giant_step(g, big_a, p, order):
    m = math.isqrt(order - 1) + 1
    baby, value = {}, 1
    for j in range(m):
        baby[value] = j
        value = value * g % p
    factor = pow(g, -m, p)
    gamma, steps = big_a, m
    for i in range(m):
        steps += 1
        if gamma in baby:
            return i * m + baby[gamma], steps
        gamma = gamma * factor % p


def pollard_rho_dlog(g, big_a, p, order):
    """Floyd cycle on x -> g^a A^b with 3 branches; solve a1 + x1 d = a2 + x2 d mod order."""
    def step(x, a, b):
        if x % 3 == 0:
            return x * x % p, 2 * a % order, 2 * b % order
        if x % 3 == 1:
            return x * g % p, (a + 1) % order, b
        return x * big_a % p, a, (b + 1) % order

    for start in range(1, 50):
        x, a, b = pow(g, start, p), start, 0
        X, A_, B_ = x, a, b
        steps = 0
        while True:
            x, a, b = step(x, a, b)
            X, A_, B_ = step(*step(X, A_, B_))
            steps += 1
            if x == X:
                break
        db = (b - B_) % order
        if db == 0:
            continue
        return ((A_ - a) * pow(db, -1, order)) % order, steps


def timed(function, *args, repeat=500):
    start = time.perf_counter()
    for _ in range(repeat):
        result = function(*args)
    return result, (time.perf_counter() - start) / repeat


# --------------------------------------------------------------------------
# Shor helpers
# --------------------------------------------------------------------------

def run_shots(circuit, shots, noise=None, seed=10, transpile_first=False):
    backend = AerSimulator(method="statevector", seed_simulator=seed, noise_model=noise) \
        if noise else AerSimulator(method="statevector", seed_simulator=seed)
    if transpile_first:
        circuit = transpile(circuit, backend)
    counts = backend.run(circuit, shots=shots).result().get_counts()
    samples = []
    for bits, k in counts.items():
        y_a, y_g = bits.split()
        samples += [(int(y_g, 2), int(y_a, 2))] * k
    return samples


def candidate(samples, order, t):
    votes = shor.exponent_votes(Counter(samples), order, t)
    return votes.most_common(1)[0][0] if votes else None


def success_after(samples, params, t, k, trials=1500):
    """Chance that the top-voted exponent from k random shots reproduces A."""
    wins = 0
    for _ in range(trials):
        a = candidate(rng.sample(samples, k), params["order"], t)
        wins += a is not None and pow(params["g"], a, params["p"]) == params["A"]
    return wins / trials


def vote_ok(samples, params, t, truth):
    """Fraction of single shots whose vote equals the true exponent."""
    good = 0
    for sample in samples:
        votes = shor.exponent_votes(Counter([sample]), params["order"], t)
        good += bool(votes) and next(iter(votes)) == truth
    return good / len(samples)


def textbook_circuit(params, t=shor.PHASE_BITS):
    g, big_a, p, order = params["g"], params["A"], params["p"], params["order"]
    n_bits = p.bit_length()
    valid = shor.subgroup(p, order)
    cg, ca = QuantumRegister(t, "count_g"), QuantumRegister(t, "count_A")
    work, anc = QuantumRegister(n_bits, "work"), QuantumRegister(shor.N_ANCILLAS, "anc")
    og, oa = ClassicalRegister(t, "s_g"), ClassicalRegister(t, "s_A")
    qc = QuantumCircuit(cg, ca, work, anc, og, oa)
    qc.x(work[0])
    qc.h(cg)
    qc.h(ca)
    blocks, first = {}, True
    for base, reg in ((g, cg), (big_a, ca)):
        for j in range(t):
            b = pow(base, 2 ** j, p)
            if first:
                for q in range(n_bits):
                    if ((1 ^ b) >> q) & 1:
                        qc.cx(reg[0], work[q])
                first = False
                continue
            if b not in blocks:
                blocks[b] = transpile(shor.controlled_multiplier(b, p, n_bits, valid),
                                      basis_gates=shor.BASIS, optimization_level=2, seed_transpiler=1)
            qc.compose(blocks[b], [reg[j], *work, *anc], inplace=True)
    qc.append(QFTGate(t).inverse(), cg)
    qc.append(QFTGate(t).inverse(), ca)
    qc.measure(cg, og)
    qc.measure(ca, oa)
    return qc


# --------------------------------------------------------------------------
# Diagrams (schematic: each controlled multiplier is one box)
# --------------------------------------------------------------------------

def make_diagrams(params):
    import matplotlib
    matplotlib.use("Agg")
    p, g, big_a = params["p"], params["g"], params["A"]
    n_bits = p.bit_length()
    width = 1 + n_bits + shor.N_ANCILLAS
    t = shor.PHASE_BITS
    ctrl, work, anc = QuantumRegister(1, "ctrl"), QuantumRegister(n_bits, "work"), QuantumRegister(shor.N_ANCILLAS, "anc")
    bits = ClassicalRegister(4, "bits")
    qc = QuantumCircuit(ctrl, work, anc, bits)
    qc.x(work[0])
    qc.barrier()
    rounds = [(g, 0), (g, 1), (big_a, 0), (big_a, 1)]
    for index, (base, i) in enumerate(rounds):
        b = pow(base, 2 ** (t - 1 - i), p)
        name = "g" if base == g else "A"
        if index:
            qc.reset(ctrl)
        qc.h(ctrl)
        qc.append(Gate("mult", width, [], label=f"x{b} mod {p}  ({name}^2^{t - 1 - i})"), [*ctrl, *work, *anc])
        if i:
            qc.append(Gate("fix", 1, [], label=f"fix phase (bits 0..{i - 1})"), ctrl)
        qc.h(ctrl)
        qc.measure(ctrl, bits[index])
        qc.barrier()
    qc.draw("mpl", filename=str(HERE / "diagram_shor.png"), fold=-1)

    x = QuantumRegister(grover.X_BITS, "x")
    gw, ga = QuantumRegister(n_bits, "work"), QuantumRegister(shor.N_ANCILLAS, "anc")
    out = ClassicalRegister(grover.X_BITS, "x_out")
    gq = QuantumCircuit(x, gw, ga, out)
    gq.h(x)
    gq.barrier()
    for _ in range(2):
        gq.append(Gate("oracle", grover.X_BITS + n_bits + shor.N_ANCILLAS, [], label="oracle: g^x = A ?  (g^x, flip, undo)"),
                  [*x, *gw, *ga])
        gq.append(Gate("diff", grover.X_BITS, [], label="diffusion"), x)
        gq.barrier()
    gq.measure(x, out)
    gq.draw("mpl", filename=str(HERE / "diagram_grover.png"), fold=-1)


def main():
    locked = load_locked(10)
    params = locked["public_parameters"]
    p, g, big_a, big_b, order = params["p"], params["g"], params["A"], params["B"], params["order"]
    t = shor.PHASE_BITS
    print(f"p = {p}, g = {g} (order {order}), A = {big_a}, B = {big_b}, key width {params['key_width_bits']} bits\n")

    # ---------------------------------------------------------------- 1
    print("1. Classical discrete log (comparison only; steps = basic operations)")
    classical = {
        "brute force": lambda: brute_force(g, big_a, p),
        "lookup table": lambda: lookup_table(g, big_a, p, order),
        "baby-step giant-step": lambda: baby_step_giant_step(g, big_a, p, order),
        "Pollard rho": lambda: pollard_rho_dlog(g, big_a, p, order),
    }
    truth = None
    for name, function in classical.items():
        (a, steps), secs = timed(function)
        truth = a
        print(f"   {name:21s}: a = {a:2d} after {steps:3d} steps, {secs * 1e6:7.1f} microseconds")
        BENCH.append({"name": f"classical {name}", "kind": "classical", "success_rate": 1.0,
                      "queries_or_oracle_calls": steps, "wall_seconds": secs, "qubits": 0,
                      "two_qubit_gates": 0, "depth": steps, "noisy_success": None,
                      "notes": "deterministic, tiny group; comparison only"})
    worst = brute_force(g, pow(g, order - 1, p), p)[1]
    print(f"   brute force worst case: {worst} steps (group order {order}).")
    print("   All of these finish in microseconds here. BSGS and rho scale like sqrt(order),")
    print("   brute force like order: the group is too small for quantum to win on time.\n")

    # ---------------------------------------------------------------- 2
    print(f"2. Shor discrete log (main solution): {t} phase bits for U_g and again for U_A, one recycled control")
    print("   multipliers g^(2^j):", [pow(g, 2 ** j, p) for j in range(t)])
    print("   multipliers A^(2^j):", [pow(big_a, 2 ** j, p) for j in range(t)])
    main_circuit = shor.dlog_circuit(g, big_a, p, order)
    start = time.time()
    counts = shor.run_dlog(params)
    print(f"   {sum(counts.values())} shots in {time.time() - start:.1f} s")
    print("   (y_g, y_A)  shots   s = y_g*q/2^t   s*a = y_A*q/2^t   a = (s*a)/s mod q")
    for (yg, ya), k in sorted(counts.items()):
        s, sa = round(yg * order / 2 ** t) % order, round(ya * order / 2 ** t) % order
        answer = (sa * pow(s, -1, order)) % order if s else None
        print(f"   ({yg:3d},{ya:3d})  {k:4d}   {s:12d}   {sa:15d}   {answer if answer is not None else '-'}")
    votes = shor.exponent_votes(counts, order)
    print("   votes:", dict(votes.most_common(4)), " (s = 0 shots carry no information)\n")

    print("2a. Success chance after k shots (1500 bootstrap draws from 300 real shots)")
    samples = run_shots(main_circuit, 300)
    print(f"   one shot gives the right vote {vote_ok(samples, params, t, truth):.1%} of the time")
    print("      k=1     k=2     k=4     k=8     k=16    k=40")
    row = [success_after(samples, params, t, k) for k in (1, 2, 4, 8, 16, 40)]
    print("   " + "  ".join(f"{x:6.1%}" for x in row))
    print("   Wrong shots vote for scattered exponents, right shots vote for the same one,")
    print("   so the top vote wins after a handful of shots, then one classical check g^a = A.\n")

    print("2b. How many phase bits t? (success of ONE shot's vote, and of 16 shots)")
    print("   t   shot ok   16 shots ok   (needs 2^t > 2 order = 82, so t >= 7)")
    t_rows = {}
    for tt in range(4, 10):
        circuit = shor.dlog_circuit(g, big_a, p, order, t=tt)
        sm = run_shots(circuit, 200)
        s1, s16 = vote_ok(sm, params, tt, truth), success_after(sm, params, tt, 16, 600)
        t_rows[tt] = (s1, s16)
        print(f"   {tt:2d}   {s1:6.1%}   {s16:10.1%}")
    print("   t = 7 (2^t > 2q) is the size where rounding y*q/2^t is guaranteed to return s for the")
    print("   closest peaks. Smaller t blurs s, but voting over many shots still works down to t = 5;")
    print("   t = 4 is too coarse. Fewer phase bits means fewer rounds, so fewer gates.\n")

    # ---------------------------------------------------------------- 3
    print(f"3. Shor discrete log, textbook version (two counting registers of {t} qubits at once, {2 * t + 7 + 2} qubits)")
    textbook = textbook_circuit(params)
    tb_success, textbook_secs = None, None
    if os.environ.get("TIER10_SIMULATE_TEXTBOOK"):
        start = time.time()
        tb_samples = run_shots(textbook, 120, transpile_first=True)
        textbook_secs = time.time() - start
        tb_success = success_after(tb_samples, params, t, 40)
        print(f"   120 shots in {textbook_secs:.0f} s; 40 shots find a: {tb_success:.1%}")
    else:
        print("   Built and measured, not simulated by default: 23 qubits means a 2^23-amplitude statevector")
        print("   and ~37 000 gates (set TIER10_SIMULATE_TEXTBOOK=1 to run it, many minutes).")
    print("   Same multipliers and same result as the recycled version: U_g and U_A commute, so the two")
    print("   phase estimations give the same pair (s, s*a) whether run in parallel or one after the other.\n")

    # ---------------------------------------------------------------- 4
    print(f"4. Grover search over exponents x = 0..63 (oracle computes g^x mod {p} and compares with A)")
    print("   Marked items: x and x + 41 when both fit in 6 bits (g^x = A has 1 or 2 solutions in 0..63).")
    max_rounds = int(os.environ.get("TIER10_GROVER_ROUNDS", "5"))
    start = time.time()
    probabilities = grover.sweep_probabilities(g, big_a, p, order, max_rounds)
    grover_secs = time.time() - start
    theta = math.asin(math.sqrt(2 / 64))
    grover_success = {}
    print(f"   One noiseless simulation, probability recorded after every round ({grover_secs:.0f} s).")
    print("   Chance that a shot gives x with x mod 41 = a, against rounds (theory with 2 marked items):")
    for rounds in range(max_rounds + 1):
        grover_success[rounds] = grover.exponent_probability(probabilities[rounds], truth, order)
        theory = math.sin((2 * rounds + 1) * theta) ** 2
        print(f"   rounds = {rounds}: {grover_success[rounds]:6.1%}   theory {theory:6.1%}")
    best = max(grover_success, key=grover_success.get)
    print(f"   Best at {best} rounds, about (pi/4) sqrt(64/2) = 4.4. More rounds overshoot.")
    grover_qc = grover.grover_circuit(g, big_a, p, order, 4)
    print(f"   Rounds needed at 6 qubits: 4. Brute force over 41 values needs up to 41 checks, so even at")
    print("   this size Grover's oracle (full modular exponentiation, twice per round) costs more than")
    print("   brute force itself: speed-up only shows once the search space is huge.\n")

    # ---------------------------------------------------------------- 5
    n_shor = metrics(main_circuit)["two_qubit_gates"]
    n_grover = metrics(grover_qc)["two_qubit_gates"]
    print("5. Noise: depolarizing error probability p on every CX")
    print(f"   {'p':>8s}   Shor: right votes   Shor: 16 shots find a   Grover: estimate")
    noisy = {"shor": {}, "grover": {}}
    for p_err in (0.0, 1e-4, 1e-3):
        model = noise_model(p_err)
        sm = run_shots(main_circuit, 40, model)
        ok1, ok16 = vote_ok(sm, params, t, truth), success_after(sm, params, t, 16, 400)
        clean = (1 - p_err) ** n_grover
        gwin = clean * grover_success[4] + (1 - clean) / order
        noisy["shor"][p_err] = {"right_votes": ok1, "a_from_16_shots": ok16}
        noisy["grover"][p_err] = gwin
        print(f"   {p_err:8.4f}   {ok1:13.1%}   {ok16:19.1%}   {gwin:13.1%}")
    print(f"   Shor columns are simulated ({n_shor} CX). The Grover column is an ESTIMATE, not a simulation:")
    print(f"   a run with no CX error at all (probability (1 - p)^{n_grover}) succeeds as ideal, any error is")
    print("   treated as a random guess (1/41). Simulating the noisy Grover circuit is too slow here.")
    print("   Random guessing gets the right vote 1/41 = 2.4% of the time. Today's hardware is around")
    print("   p = 0.001. Error mitigation (zero-noise extrapolation, error cancellation) cannot rescue")
    print("   circuits this deep; error correction is needed.\n")

    # ---------------------------------------------------------------- 6
    print("6. Rebuild the shared secret")
    secret = pow(big_b, truth, p)
    key_bits = format(secret, f"0{params['key_width_bits']}b")
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    line = xor_bytes(ciphertext, keystream(key_bits, len(ciphertext))).decode()
    print(f"   a = {truth} (check: {g}^{truth} mod {p} = {pow(g, truth, p)} = A)")
    print(f"   secret = B^a mod p = {big_b}^{truth} mod {p} = {secret} = {key_bits}")
    print(f"   {line}   correct: {is_correct(10, line)}\n")

    # ---------------------------------------------------------------- 7
    print("7. Circuit size, measured like the checker (basis rz/sx/x/cx, opt level 1)")
    rows = {
        "Shor dlog, recycled control (main)": main_circuit,
        "Shor dlog, textbook (2 registers)": textbook,
        "Grover over exponents (4 rounds)": grover_qc,
    }
    sizes = {}
    print(f"   {'method':36s} {'2Q gates':>9s} {'depth':>7s} {'gates':>7s} {'qubits':>7s}")
    for name, circuit in rows.items():
        m = metrics(circuit)
        sizes[name] = m
        print(f"   {name:36s} {m['two_qubit_gates']:9d} {m['depth']:7d} {m['total_gates']:7d} {m['qubits']:7d}")

    start = time.time()
    shor.recover_exponent(params)
    main_secs = time.time() - start
    BENCH.append({"name": "Shor dlog, recycled control (submitted)", "kind": "quantum",
                  "success_rate": success_after(samples, params, t, shor.SHOTS),
                  "queries_or_oracle_calls": shor.SHOTS, "wall_seconds": main_secs,
                  **sizes["Shor dlog, recycled control (main)"],
                  "noisy_success": {f"cx_error={k}": v["a_from_16_shots"] for k, v in noisy["shor"].items()},
                  "notes": f"t={t} phase bits for each of U_g, U_A; {shor.SHOTS} shots; success = top vote reproduces A"})
    BENCH.append({"name": "Shor dlog, textbook two registers", "kind": "quantum",
                  "success_rate": tb_success, "queries_or_oracle_calls": 40, "wall_seconds": textbook_secs,
                  **sizes["Shor dlog, textbook (2 registers)"], "noisy_success": None,
                  "notes": "14 counting qubits + inverse QFTs, same multipliers; circuit sized but not simulated by default (success_rate and wall_seconds null)"})
    BENCH.append({"name": "Grover over exponents", "kind": "quantum",
                  "success_rate": grover_success[4], "queries_or_oracle_calls": 4,
                  "wall_seconds": grover_secs, **sizes["Grover over exponents (4 rounds)"],
                  "noisy_success": {f"cx_error={k}": v for k, v in noisy["grover"].items()},
                  "notes": "4 rounds, oracle = full modular exponentiation; success_rate = probability one shot gives x mod 41 = a; wall_seconds = noiseless probability sweep over 5 rounds; noisy_success is an analytic estimate, not simulated"})
    (HERE / "benchmark.json").write_text(json.dumps({"tier": 10, "answer": line, "methods": BENCH}, indent=2))
    make_diagrams(params)
    print("\n   wrote benchmark.json, diagram_shor.png, diagram_grover.png")


if __name__ == "__main__":
    main()
