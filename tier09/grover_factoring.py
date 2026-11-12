"""Tier 9, alternative method: factor N = 77 with Grover search.

This is NOT our main tier 9 solution (that is Shor's algorithm in
solution.py). It is a second quantum method we tried, to compare.

Idea (beginner version)
-----------------------
"Find p and q with p * q = 77" is a search problem. Grover's algorithm finds
the one right answer among M candidates in about (pi/4) sqrt(M) tries,
instead of about M/2 tries for checking one candidate at a time.

Search space (uses only N, never the answer):
  * N is odd, so both factors are odd.
  * The smaller factor p is at most sqrt(77) = 8.8, so p is in {1, 3, 5, 7}:
    p = 1 + 2*u0 + 4*u1                        (2 qubits u)
  * Then q = 77 / p is at most 77 / 3 = 25.7, so q fits in 5 bits, odd:
    q = 1 + 2*v0 + 4*v1 + 8*v2 + 16*v3         (4 qubits v)
  That is 2^6 = 64 candidate pairs. p = 1 would need q = 77, which does not
  fit, so exactly ONE pair has p * q = 77.

The oracle ("is this pair right?") is real arithmetic, built from N only:
  1. Multiply: acc = p * q mod 128, on 7 qubits. We add numbers in the
     Fourier basis (Draper adder): after H gates, "add c" is just one phase
     gate per acc qubit, and "add c only if u_i and v_j are 1" is the same
     phase gates with those two controls. p * q expands into a sum of such
     terms (1, 2*v_j, 2*u_i, 4*u_i*v_j * 2^(i+j)). An inverse QFT turns the
     phases back into the number p * q.
     mod 128 is safe: p * q is at most 7 * 31 = 217, and the only other
     value equal to 77 mod 128 is 205 = 5 * 41, with 41 out of range.
  2. Flip the sign if acc == 77 (X on the 0-bits of 77, multi-controlled Z).
  3. Undo step 1, so acc goes back to 0.
Then the usual Grover "diffusion" step reflects about the average.
"""
import math
from collections import Counter

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import QFTGate
from qiskit_aer import AerSimulator

BASIS = ["rz", "sx", "x", "cx"]
U_BITS, V_BITS, ACC_BITS = 2, 4, 7


def multiply_terms():
    """p * q as a list of (constant c, control qubit names): add c if all controls are 1."""
    u = [("u", i, 2 ** (i + 1)) for i in range(U_BITS)]   # p = 1 + sum
    v = [("v", j, 2 ** (j + 1)) for j in range(V_BITS)]   # q = 1 + sum
    terms = [(1, [])]
    terms += [(w, [(name, k)]) for name, k, w in u + v]
    terms += [(wu * wv, [("u", i), ("v", j)]) for _, i, wu in u for _, j, wv in v]
    return terms


def multiplier(regs):
    """|u>|v>|0> -> |u>|v>|p*q mod 2^ACC_BITS>, Fourier-basis adder."""
    u, v, acc = regs
    qc = QuantumCircuit(u, v, acc, name="p*q")
    qc.h(acc)  # QFT of |0> is just H on every qubit
    lookup = {"u": u, "v": v}
    for c, controls in multiply_terms():
        ctrl = [lookup[name][k] for name, k in controls]
        for l in range(ACC_BITS):
            angle = 2 * math.pi * ((c << l) % 2 ** ACC_BITS) / 2 ** ACC_BITS
            if angle == 0:
                continue
            if not ctrl:
                qc.p(angle, acc[l])
            else:
                qc.mcp(angle, ctrl, acc[l])
    qc.append(QFTGate(ACC_BITS).inverse(), acc)
    return qc


def oracle(regs, n_value):
    """Phase -1 on every |u, v> with p * q == N (mod 2^ACC_BITS)."""
    u, v, acc = regs
    qc = QuantumCircuit(u, v, acc, name="oracle")
    mult = multiplier(regs)
    qc.compose(mult, inplace=True)
    zeros = [acc[l] for l in range(ACC_BITS) if not (n_value >> l) & 1]
    qc.x(zeros)
    qc.mcp(math.pi, list(acc[:-1]), acc[-1])  # multi-controlled Z
    qc.x(zeros)
    qc.compose(mult.inverse(), inplace=True)
    return qc


def diffusion(search):
    qc = QuantumCircuit(search, name="diffusion")
    qc.h(search)
    qc.x(search)
    qc.mcp(math.pi, list(search[:-1]), search[-1])
    qc.x(search)
    qc.h(search)
    return qc


def grover_rounds(n_candidates, n_marked=1):
    theta = math.asin(math.sqrt(n_marked / n_candidates))
    return round(math.pi / (4 * theta) - 0.5), theta


def grover_circuit(n_value):
    u = QuantumRegister(U_BITS, "u")
    v = QuantumRegister(V_BITS, "v")
    acc = QuantumRegister(ACC_BITS, "acc")
    out = ClassicalRegister(U_BITS + V_BITS, "uv")
    regs = (u, v, acc)
    search = list(u) + list(v)
    qc = QuantumCircuit(u, v, acc, out)
    qc.h(search)
    rounds, _ = grover_rounds(2 ** len(search))
    orc = transpile(oracle(regs, n_value), basis_gates=BASIS, optimization_level=2, seed_transpiler=1)
    dif = diffusion(search)
    for _ in range(rounds):
        qc.compose(orc, inplace=True)
        qc.compose(dif, qubits=search, inplace=True)
    qc.measure(search, out)
    return qc


def decode(bits):
    """Measured bitstring (u bits rightmost) -> (p, q)."""
    value = int(bits, 2)
    uu, vv = value & 0b11, value >> U_BITS
    return 1 + 2 * uu, 1 + 2 * vv


def factor_with_grover(n_value, shots=64, seed=9):
    qc = grover_circuit(n_value)
    backend = AerSimulator(seed_simulator=seed)
    counts = backend.run(transpile(qc, backend), shots=shots).result().get_counts()
    pairs = Counter()
    for bits, n in counts.items():
        pairs[decode(bits)] += n
    for (p, q), _ in pairs.most_common():
        if p > 1 and p * q == n_value:  # checking a product is cheap and classical
            return p, q, pairs, qc
    raise RuntimeError("Grover did not find a factor pair")


if __name__ == "__main__":
    N = 77
    rounds, theta = grover_rounds(64)
    print(f"64 candidates, 1 right -> {rounds} Grover rounds, "
          f"success chance {math.sin((2 * rounds + 1) * theta) ** 2:.4f}")
    p, q, pairs, qc = factor_with_grover(N)
    print("top measured pairs (p, q): shots")
    for pair, n in pairs.most_common(5):
        print(f"   {pair}: {n}")
    print(f"factors: {N} = {p} x {q}")
    t = transpile(qc, basis_gates=BASIS, optimization_level=1, seed_transpiler=12345)
    ops = t.count_ops()
    gates = sum(n for name, n in ops.items() if name not in ("measure", "barrier", "reset"))
    print(f"scored-style metrics: 2Q gates {ops.get('cx', 0)}, depth {t.depth()}, "
          f"gates {gates}, qubits {qc.num_qubits}")


# --------------------------------------------------------------------------
# Drop-in entry points, in case the team wants to submit this method instead
# of Shor: copy this file over solution.py. (Not done by default.)
# --------------------------------------------------------------------------

def build_circuit():
    """Grover factoring circuit for N = 77 (for diagrams)."""
    from common import load_locked
    return grover_circuit(load_locked(9)["public_parameters"]["N"])


def solve():
    """Factor N with Grover on Aer, unwrap the RSA key, decrypt."""
    from common import keystream, load_locked, xor_bytes
    locked = load_locked(9)
    params = locked["public_parameters"]
    p, q, _, _ = factor_with_grover(params["N"])
    d = pow(params["e"], -1, (p - 1) * (q - 1))
    k = pow(params["wrapped_key"], d, params["N"])
    key_bits = format(k, f"0{params['key_width_bits']}b")
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    return xor_bytes(ciphertext, keystream(key_bits, len(ciphertext))).decode("utf-8")
