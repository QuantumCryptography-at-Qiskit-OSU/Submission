"""Tier 8 experiments: every way we tried to factor N = 35, side by side.

Run from anywhere inside the Submission folder:
    python tier08/explore.py
It also writes benchmark.json, diagram_shor.png and diagram_grover.png here.

  1. Classical methods: trial division, Fermat, Pollard rho, classical order
     finding (comparison only; the submitted solve() never uses them).
  2. Shor, our main solution (solution.py): one recycled control qubit.
     2a. which base a works, and how many shots we need (success vs shots)
     2b. how many phase bits t we need (success vs t)
  3. Shor, textbook version: a full counting register + inverse QFT.
  4. Grover factoring (grover_factoring.py): search p, q with p * q = 35.
  5. Noise: depolarizing error on every CX, Shor against Grover.
  6. Unwrap the RSA key and decrypt.
  7. Circuit sizes, measured the way the checker measures them.
"""
import importlib.util
import json
import math
import random
import sys
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = next(
    folder
    for folder in [HERE, *HERE.parents, HERE.parent.parent / "Quantum-Cryptography-Challenge"]
    if (folder / "common" / "check.py").exists()
)
sys.path.insert(0, str(REPO))

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile  # noqa: E402
from qiskit.circuit import Gate  # noqa: E402
from qiskit.circuit.library import QFTGate  # noqa: E402
from qiskit_aer import AerSimulator  # noqa: E402
from qiskit_aer.noise import NoiseModel, depolarizing_error  # noqa: E402

from common import is_correct, keystream, load_locked, xor_bytes  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(f"t8_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shor = load("solution")
grover = load("grover_factoring")
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

def trial_division(n):
    steps = 0
    for d in range(2, math.isqrt(n) + 1):
        steps += 1
        if n % d == 0:
            return d, n // d, steps


def fermat(n):
    a, steps = math.isqrt(n), 0
    if a * a < n:
        a += 1
    while True:
        steps += 1
        b2 = a * a - n
        if math.isqrt(b2) ** 2 == b2:
            b = math.isqrt(b2)
            return a - b, a + b, steps
        a += 1


def pollard_rho(n, c=1):
    x = y = 2
    d, steps = 1, 0
    while d == 1:
        x = (x * x + c) % n
        y = (y * y + c) % n
        y = (y * y + c) % n
        d = math.gcd(abs(x - y), n)
        steps += 1
    return d, n // d, steps


def classical_order(a, n):
    value, r = a % n, 1
    while value != 1:
        value = value * a % n
        r += 1
    return r


def timed(function, *args, repeat=2000):
    start = time.perf_counter()
    for _ in range(repeat):
        result = function(*args)
    return result, (time.perf_counter() - start) / repeat


# --------------------------------------------------------------------------
# Shor helpers
# --------------------------------------------------------------------------

def factors_from_order(a, r, n):
    if r is None or r % 2:
        return None
    half = pow(a, r // 2, n)
    p, q = math.gcd(half - 1, n), math.gcd(half + 1, n)
    return (p, q) if 1 < p < n and p * q == n else None


def shots_of(circuit, shots, noise=None, seed=8):
    backend = AerSimulator(method="statevector", seed_simulator=seed, noise_model=noise) \
        if noise else AerSimulator(method="statevector", seed_simulator=seed)
    counts = backend.run(circuit, shots=shots).result().get_counts()
    return [int(bits, 2) for bits, k in counts.items() for _ in range(k)]


def success_after(samples, a, n, k, trials=2000):
    """Chance that k random shots from `samples` give the factors."""
    wins = 0
    for _ in range(trials):
        picked = Counter(rng.sample(samples, k))
        if factors_from_order(a, shor.order_from_counts(picked, a, n), n):
            wins += 1
    return wins / trials


def peak_hit_rate(samples, r, t):
    """Fraction of shots within 1 count of a multiple of 2^t / r (an ideal peak)."""
    def near(y):
        return min(abs(y - s * 2 ** t / r) for s in range(r + 1)) <= 1.0
    return sum(near(y) for y in samples) / len(samples)


def phase_table(counts, t, n):
    print("        y  shots   y/2^t    nearest s/r   -> r candidate")
    for y, shots in sorted(counts.items()):
        frac = Fraction(y, 2 ** t).limit_denominator(n // 2)
        print(f"   {y:6d}  {shots:5d}   {y / 2 ** t:.4f}   {str(frac):>9s}      {frac.denominator}")


def textbook_shor_circuit(a, n):
    n_bits = n.bit_length()
    t = shor.counting_bits(n)
    count = QuantumRegister(t, "count")
    work = QuantumRegister(n_bits, "work")
    anc = QuantumRegister(shor.N_ANCILLAS, "anc")
    out = ClassicalRegister(t, "phase")
    qc = QuantumCircuit(count, work, anc, out)
    qc.x(work[0])
    qc.h(count)
    blocks = {}
    for j in range(t):
        b = pow(a, 2 ** j, n)
        if j == 0:
            for q in range(n_bits):
                if ((1 ^ b) >> q) & 1:
                    qc.cx(count[0], work[q])
            continue
        if b not in blocks:
            blocks[b] = transpile(shor.controlled_multiplier(b, n, n_bits),
                                  basis_gates=shor.BASIS, optimization_level=2, seed_transpiler=1)
        qc.compose(blocks[b], [count[j], *work, *anc], inplace=True)
    qc.append(QFTGate(t).inverse(), count)
    qc.measure(count, out)
    return qc


# --------------------------------------------------------------------------
# Diagrams (schematic: each controlled multiplier is one box)
# --------------------------------------------------------------------------

def make_diagrams(n):
    import matplotlib
    matplotlib.use("Agg")
    n_bits = n.bit_length()
    width = 1 + n_bits + shor.N_ANCILLAS
    ctrl, work, anc = QuantumRegister(1, "ctrl"), QuantumRegister(n_bits, "work"), QuantumRegister(shor.N_ANCILLAS, "anc")
    bits = ClassicalRegister(3, "bits")
    qc = QuantumCircuit(ctrl, work, anc, bits)
    qc.x(work[0])
    qc.barrier()
    a = 2
    t = shor.counting_bits(n)
    for i in range(3):
        b = pow(a, 2 ** (t - 1 - i), n)
        if i:
            qc.reset(ctrl)
        qc.h(ctrl)
        qc.append(Gate("mult", width, [], label=f"x{b} mod {n}"), [*ctrl, *work, *anc])
        if i:
            qc.append(Gate("fix", 1, [], label=f"fix phase (bits 0..{i - 1})"), ctrl)
        qc.h(ctrl)
        qc.measure(ctrl, bits[i])
        qc.barrier()
    qc.draw("mpl", filename=str(HERE / "diagram_shor.png"), fold=-1)

    u, v, acc = QuantumRegister(grover.U_BITS, "u"), QuantumRegister(grover.V_BITS, "v"), QuantumRegister(grover.ACC_BITS, "acc")
    out = ClassicalRegister(grover.U_BITS + grover.V_BITS, "uv")
    gq = QuantumCircuit(u, v, acc, out)
    search = [*u, *v]
    gq.h(search)
    gq.barrier()
    for _ in range(2):
        gq.append(Gate("oracle", len(search) + grover.ACC_BITS, [], label="oracle: p*q = 35 ?"), [*search, *acc])
        gq.append(Gate("diff", len(search), [], label="diffusion"), search)
        gq.barrier()
    gq.measure(search, out)
    gq.draw("mpl", filename=str(HERE / "diagram_grover.png"), fold=-1)


def main():
    locked = load_locked(8)
    params = locked["public_parameters"]
    n, e, c = params["N"], params["e"], params["wrapped_key"]
    t = shor.counting_bits(n)
    a = 2
    print(f"N = {n}, e = {e}, wrapped key c = {c}, key width {params['key_width_bits']} bits\n")

    # ---------------------------------------------------------------- 1
    print("1. Classical factoring (comparison only; steps = basic operations)")
    for name, function in (("trial division", trial_division), ("Fermat", fermat), ("Pollard rho", pollard_rho)):
        (p, q, steps), secs = timed(function, n)
        print(f"   {name:15s}: {n} = {p} x {q} after {steps} steps, {secs * 1e6:.1f} microseconds")
        BENCH.append({"name": f"classical {name}", "kind": "classical", "success_rate": 1.0,
                      "queries_or_oracle_calls": steps, "wall_seconds": secs, "qubits": 0,
                      "two_qubit_gates": 0, "depth": steps, "noisy_success": None,
                      "notes": "deterministic, tiny N; comparison only"})
    r_cl, secs = timed(classical_order, a, n)
    print(f"   classical order finding: order of {a} mod {n} is {r_cl} ({r_cl} multiplications)")
    print("   Every classical method finishes in microseconds at N = 35. Quantum is")
    print("   slower here; the point is how the cost GROWS (section 7 of EXPLAINED.md).\n")

    # ---------------------------------------------------------------- 2
    print(f"2. Shor (main solution): a = {a}, {t} phase bits, one recycled control qubit")
    print("   multipliers a^(2^j) mod N:", [pow(a, 2 ** j, n) for j in range(t)])
    start = time.time()
    counts = shor.run_order_finding(a, n)
    print(f"   {sum(counts.values())} shots in {time.time() - start:.1f} s")
    phase_table(counts, t, n)
    r = shor.order_from_counts(counts, a, n)
    half = pow(a, r // 2, n)
    p, q = math.gcd(half - 1, n), math.gcd(half + 1, n)
    print(f"   order r = {r} (check {a}^{r} mod {n} = {pow(a, r, n)}), r is even")
    print(f"   {a}^(r/2) mod N = {half};  gcd({half - 1}, {n}) = {p},  gcd({half + 1}, {n}) = {q}\n")

    print("2a. Which base a? Success chance after k shots (2000 bootstrap draws from 240 real shots)")
    print(f"   {'a':>3s} {'order r':>8s} {'gives factors?':>15s}   k=1    k=2    k=4    k=8    k=24")
    base_rows = {}
    for base in (2, 3, 4, 8, 34):
        r_true = classical_order(base, n)
        works = factors_from_order(base, r_true, n) is not None
        circuit = shor.order_finding_circuit(base, n)
        samples = shots_of(circuit, 240)
        rates = [success_after(samples, base, n, k) for k in (1, 2, 4, 8, 24)]
        base_rows[base] = rates
        print(f"   {base:3d} {r_true:8d} {str(works):>15s}   " + "  ".join(f"{x:5.1%}" for x in rates))
    print("   a = 34 has order 2 and a^(r/2) = -1 mod N: 'trivial', never works. We")
    print("   cannot know that in advance without the factors, so Shor tries another a.")
    print("   a = 4, 8: r = 6, 4 give factors with fewer phase peaks to find.\n")

    print("2b. How many phase bits t? (a = 2, 300 shots each, success of ONE shot and of 8 shots)")
    print("   t   shot ok   8 shots ok   (needs 2^t >= 2 r^2 = 288, so t >= 9)")
    original = shor.counting_bits
    t_rows = {}
    for tt in range(4, 11):
        shor.counting_bits = lambda m, tt=tt: tt
        circuit = shor.order_finding_circuit(a, n)
        samples = shots_of(circuit, 300)
        s1, s8 = success_after(samples, a, n, 1, 1000), success_after(samples, a, n, 8, 1000)
        t_rows[tt] = (s1, s8)
        print(f"   {tt:2d}   {s1:6.1%}   {s8:9.1%}")
    shor.counting_bits = original
    print("   Too few phase bits blur s/r so continued fractions cannot see r = 12;")
    print("   the formula t = ceil(log2(N^2 / 2)) = 10 is safe. Each extra bit costs one more round.\n")

    # ---------------------------------------------------------------- 3
    print("3. Shor, textbook version (full counting register, 10 + 6 + 2 = 18 qubits)")
    textbook = textbook_shor_circuit(a, n)
    start = time.time()
    backend = AerSimulator(seed_simulator=8)
    raw = backend.run(transpile(textbook, backend), shots=240).result().get_counts()
    textbook_samples = [int(bits, 2) for bits, k in raw.items() for _ in range(k)]
    rng.shuffle(textbook_samples)
    counts_tb = Counter(textbook_samples[:24])
    textbook_secs = time.time() - start
    print(f"   240 shots in {textbook_secs:.1f} s (first 24 shown; one simulation, then sampling)")
    phase_table(counts_tb, t, n)
    print(f"   order from these shots: r = {shor.order_from_counts(counts_tb, a, n)}\n")

    # ---------------------------------------------------------------- 4
    print("4. Grover factoring (search 32 pairs (p, q) for p * q = 35; two are right: (5,7), (7,5))")
    start = time.time()
    gp, gq, pairs, grover_qc = grover.factor_with_grover(n)
    grover_secs = time.time() - start
    print("   most common measured pairs:", pairs.most_common(3), f"({grover_secs:.1f} s)")
    print(f"   -> {n} = {gp} x {gq}")
    print("   Success chance by number of Grover rounds (theory sin^2((2k+1) theta), theta = asin(sqrt(2/32))):")
    theta = grover.grover_rounds(32)[1]
    grover_success = {}
    for rounds in range(0, 7):
        circuit = grover.grover_circuit(n, rounds)
        raw = AerSimulator(seed_simulator=8).run(transpile(circuit, AerSimulator()), shots=1000).result().get_counts()
        hit = sum(k for bits, k in raw.items() if (lambda pq: pq[0] * pq[1] == n and pq[0] > 1)(grover.decode(bits)))
        grover_success[rounds] = hit / 1000
        print(f"   rounds = {rounds}: measured {hit / 1000:5.1%}   theory {math.sin((2 * rounds + 1) * theta) ** 2:5.1%}")
    print("   Rounds past the best one rotate the state PAST the answer: more is worse.\n")

    # ---------------------------------------------------------------- 5
    print("5. Noise: depolarizing error probability p on every CX")
    print(f"   {'p':>8s}   Shor: peak hits   Shor: 8 shots give factors   Grover: success")
    noisy = {"shor": {}, "grover": {}}
    ideal_shor = shor.order_finding_circuit(a, n)
    chance = peak_hit_rate(list(range(2 ** t)), 12, t)
    for p_err in (0.0, 1e-4, 3e-4, 1e-3):
        model = noise_model(p_err)
        samples = shots_of(ideal_shor, 60, model)
        hits = peak_hit_rate(samples, 12, t)
        ok8 = success_after(samples, a, n, 8, 500)
        gc = grover.grover_circuit(n)
        raw = AerSimulator(seed_simulator=8, noise_model=model).run(transpile(gc, AerSimulator(noise_model=model)), shots=400).result().get_counts()
        gwin = sum(k for bits, k in raw.items() if (lambda pq: pq[0] * pq[1] == n and pq[0] > 1)(grover.decode(bits))) / 400
        noisy["shor"][p_err] = {"peak_hits": hits, "factors_from_8_shots": ok8}
        noisy["grover"][p_err] = gwin
        print(f"   {p_err:8.4f}   {hits:12.1%}   {ok8:22.1%}   {gwin:14.1%}")
    print(f"   A random bit string lands on a peak {chance:.1%} of the time, so Shor's peak hits fall to")
    print("   about that when it is scrambled. Today's hardware is around p = 0.001 and these")
    print("   circuits have thousands of CX gates: neither would survive without error correction.")
    print("   Zero-noise extrapolation and error cancellation could stretch this a little, but")
    print("   with ~5000 CX gates the signal is gone long before extrapolation can recover it.\n")

    # ---------------------------------------------------------------- 6
    print("6. Unwrap the RSA key")
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    k = pow(c, d, n)
    key_bits = format(k, f"0{params['key_width_bits']}b")
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    line = xor_bytes(ciphertext, keystream(key_bits, len(ciphertext))).decode()
    print(f"   phi = ({p}-1)({q}-1) = {phi};  d = {e}^-1 mod {phi} = {d}")
    print(f"   k = {c}^{d} mod {n} = {k} = {key_bits}  (check: {k}^{e} mod {n} = {pow(k, e, n)})")
    print(f"   {line}   correct: {is_correct(8, line)}\n")

    # ---------------------------------------------------------------- 7
    print("7. Circuit size, measured like the checker (basis rz/sx/x/cx, opt level 1)")
    rows = {
        "Shor, recycled control (main)": ideal_shor,
        "Shor, textbook (full register)": textbook,
        "Grover factoring": grover_qc,
    }
    sizes = {}
    print(f"   {'method':32s} {'2Q gates':>9s} {'depth':>7s} {'gates':>7s} {'qubits':>7s}")
    for name, circuit in rows.items():
        m = metrics(circuit)
        sizes[name] = m
        print(f"   {name:32s} {m['two_qubit_gates']:9d} {m['depth']:7d} {m['total_gates']:7d} {m['qubits']:7d}")

    start = time.time()
    shor.factor(n)
    main_secs = time.time() - start
    BENCH.append({"name": "Shor, recycled control (submitted)", "kind": "quantum",
                  "success_rate": success_after(shots_of(ideal_shor, 240), a, n, shor.SHOTS),
                  "queries_or_oracle_calls": shor.SHOTS, "wall_seconds": main_secs,
                  **sizes["Shor, recycled control (main)"],
                  "noisy_success": {f"cx_error={k}": v["factors_from_8_shots"] for k, v in noisy["shor"].items()},
                  "notes": f"a=2, t={t} phase bits, {shor.SHOTS} shots per run; success is chance one run factors N"})
    BENCH.append({"name": "Shor, textbook full register", "kind": "quantum",
                  "success_rate": success_after(textbook_samples, a, n, 24),
                  "queries_or_oracle_calls": 24, "wall_seconds": textbook_secs,
                  **sizes["Shor, textbook (full register)"], "noisy_success": None,
                  "notes": "same multipliers, 10 counting qubits + inverse QFT"})
    BENCH.append({"name": "Grover factoring", "kind": "quantum",
                  "success_rate": grover_success[grover.grover_rounds(32)[0]],
                  "queries_or_oracle_calls": grover.grover_rounds(32)[0], "wall_seconds": grover_secs,
                  **sizes["Grover factoring"],
                  "noisy_success": {f"cx_error={k}": v for k, v in noisy["grover"].items()},
                  "notes": "3 Grover rounds over 32 candidates, success = one shot is a valid pair"})
    (HERE / "benchmark.json").write_text(json.dumps({"tier": 8, "answer": line, "methods": BENCH}, indent=2))
    make_diagrams(n)
    print("\n   wrote benchmark.json, diagram_shor.png, diagram_grover.png")


if __name__ == "__main__":
    main()
