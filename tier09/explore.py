"""Tier 9 experiments: every way we tried to factor N = 77, side by side.

Run from the Submission folder (or anywhere inside it):
    python tier09/explore.py

  1. Classical methods: trial division, Fermat, Pollard rho, and classical
     order finding (the slow part Shor replaces).
  2. Shor, our main solution (solution.py): one recycled control qubit.
     Prints the measured phases and how they become the factors.
  3. Shor, textbook version: a full 12-qubit counting register + inverse QFT.
  4. Grover factoring (grover_factoring.py): search p, q with p * q = 77.
  5. Unwrap the RSA key and decrypt.
  6. Circuit sizes of 2, 3, 4, measured the way the checker measures them.
"""
import importlib.util
import math
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
from qiskit.circuit.library import QFTGate  # noqa: E402
from qiskit_aer import AerSimulator  # noqa: E402

from common import check, keystream, load_locked, xor_bytes  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shor = load("solution")
grover = load("grover_factoring")

# Same settings as tools/scoring_config.yaml.
SCORING = dict(basis_gates=["rz", "sx", "x", "cx"], coupling_map=None,
               optimization_level=1, seed_transpiler=12345)


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
            if getattr(op, "blocks", None):  # if_test: count every branch
                for block in op.blocks:
                    walk(block, {bq: qs[i] for i, bq in enumerate(block.qubits)})
                continue
            gates += 1
            two_q += len(qs) == 2
            active.update(qs)

    walk(t, {q: q for q in t.qubits})
    return {"2Q gates": two_q, "depth": t.depth(), "gates": gates, "active qubits": len(active)}


# --------------------------------------------------------------------------
# 1. Classical methods (each counts its basic steps)
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


# --------------------------------------------------------------------------
# 3. Textbook Shor: t counting qubits, all controlled multiplications, then
#    one inverse QFT. Same multiplier blocks as solution.py.
# --------------------------------------------------------------------------

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
    for j in range(t):  # count[j] controls multiplication by a^(2^j)
        b = pow(a, 2 ** j, n)
        if j == 0:  # work is exactly |1>: "multiply by b" = "write b"
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


def phase_table(counts, t, n):
    print("        y  shots   y/2^t    nearest s/r   -> r candidate")
    for y, shots in sorted(counts.items()):
        frac = Fraction(y, 2 ** t).limit_denominator(n // 2)
        print(f"   {y:6d}  {shots:5d}   {y / 2 ** t:.4f}   {str(frac):>9s}      {frac.denominator}")


def main():
    locked = load_locked(9)
    params = locked["public_parameters"]
    n, e, c = params["N"], params["e"], params["wrapped_key"]
    a = 2
    print(f"N = {n}, e = {e}, wrapped key c = {c}, key width {params['key_width_bits']} bits\n")

    print("1. Classical factoring (steps = basic operations)")
    p, q, s = trial_division(n)
    print(f"   trial division : {n} = {p} x {q} after {s} divisions")
    p, q, s = fermat(n)
    print(f"   Fermat         : {n} = {p} x {q} after {s} square checks")
    p, q, s = pollard_rho(n)
    print(f"   Pollard rho    : {n} = {p} x {q} after {s} rounds")
    r = classical_order(a, n)
    print(f"   classical order finding: order of {a} mod {n} is {r} ({r} multiplications)")
    print("   This last step is the one Shor's algorithm does with a quantum circuit.\n")

    t = shor.counting_bits(n)
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

    print("3. Shor, textbook version (full counting register, 21 qubits)")
    textbook = textbook_shor_circuit(a, n)
    start = time.time()
    backend = AerSimulator(seed_simulator=9)
    raw = backend.run(transpile(textbook, backend), shots=24).result().get_counts()
    counts_tb = Counter({int(bits, 2): k for bits, k in raw.items()})
    print(f"   24 shots in {time.time() - start:.1f} s")
    phase_table(counts_tb, t, n)
    print(f"   order from these shots: r = {shor.order_from_counts(counts_tb, a, n)}\n")

    print("4. Grover factoring (search 64 pairs (p, q) for p * q = 77)")
    gp, gq, pairs, grover_qc = grover.factor_with_grover(n)
    print("   most common measured pairs:", pairs.most_common(3))
    print(f"   -> {n} = {gp} x {gq}\n")

    print("5. Unwrap the RSA key")
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    k = pow(c, d, n)
    key_bits = format(k, f"0{params['key_width_bits']}b")
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    line = xor_bytes(ciphertext, keystream(key_bits, len(ciphertext))).decode()
    print(f"   phi = ({p}-1)({q}-1) = {phi};  d = {e}^-1 mod {phi} = {d}")
    print(f"   k = {c}^{d} mod {n} = {k} = {key_bits}  (check: {k}^{e} mod {n} = {pow(k, e, n)})")
    print(f"   {line}")
    check(9, line)
    print()

    print("6. Circuit size, measured like the checker (basis rz/sx/x/cx, opt level 1)")
    rows = {
        "Shor, recycled control (main)": shor.order_finding_circuit(a, n),
        "Shor, textbook (full register)": textbook,
        "Grover factoring": grover_qc,
    }
    print(f"   {'method':32s} {'2Q gates':>9s} {'depth':>7s} {'gates':>7s} {'qubits':>7s}")
    for name, circuit in rows.items():
        m = metrics(circuit)
        print(f"   {name:32s} {m['2Q gates']:9d} {m['depth']:7d} {m['gates']:7d} {m['active qubits']:7d}")


if __name__ == "__main__":
    main()
