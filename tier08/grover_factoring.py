"""Tier 8, alternative method: factor N = 35 with Grover search.

This is NOT our main tier 8 solution (that is Shor's algorithm in
solution.py). It is a second quantum method we tried, to compare. Same idea
as tier09/grover_factoring.py, with a smaller search box.

Search space (uses only N, never the answer):
  * N is odd, so both factors are odd.
  * Smaller factor p is at most sqrt(35) = 5.9, so we let p = 1 + 2*u,
    u in 0..3 (2 qubits): p in {1, 3, 5, 7}.
  * Then q = 35 / p is at most 35 / 3 = 11.7, so q = 1 + 2*v, v in 0..7
    (3 qubits): q in {1, 3, ..., 15}.
  32 candidate pairs. p = 1 would need q = 35, which does not fit. The pairs
  (5, 7) and (7, 5) both fit, so exactly TWO pairs are right (a factor pair
  and its mirror image; this is why we plan for two marked items).

Oracle ("is p * q = 35?"): multiply with phase gates in the Fourier basis
(Draper adder), flip the sign if the product is 35, undo the multiplication.
Product mod 128 on 7 qubits: p * q is at most 7 * 15 = 105 < 128, so mod 128
loses nothing.
"""
import math
from collections import Counter

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import QFTGate
from qiskit_aer import AerSimulator

BASIS = ["rz", "sx", "x", "cx"]
U_BITS, V_BITS, ACC_BITS = 2, 3, 7
N_MARKED = 2


def multiply_terms():
    """p * q as (constant c, control qubit names): add c if all controls are 1."""
    u = [("u", i, 2 ** (i + 1)) for i in range(U_BITS)]
    v = [("v", j, 2 ** (j + 1)) for j in range(V_BITS)]
    terms = [(1, [])]
    terms += [(w, [(name, k)]) for name, k, w in u + v]
    terms += [(wu * wv, [("u", i), ("v", j)]) for _, i, wu in u for _, j, wv in v]
    return terms


def multiplier(regs):
    """|u>|v>|0> -> |u>|v>|p*q mod 2^ACC_BITS>, Fourier-basis adder."""
    u, v, acc = regs
    qc = QuantumCircuit(u, v, acc, name="p*q")
    qc.h(acc)
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
    """Phase -1 on every |u, v> with p * q == N."""
    u, v, acc = regs
    qc = QuantumCircuit(u, v, acc, name="oracle")
    mult = multiplier(regs)
    qc.compose(mult, inplace=True)
    zeros = [acc[l] for l in range(ACC_BITS) if not (n_value >> l) & 1]
    qc.x(zeros)
    qc.mcp(math.pi, list(acc[:-1]), acc[-1])
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


def grover_rounds(n_candidates, n_marked=N_MARKED):
    theta = math.asin(math.sqrt(n_marked / n_candidates))
    return round(math.pi / (4 * theta) - 0.5), theta


def grover_circuit(n_value, rounds=None):
    u = QuantumRegister(U_BITS, "u")
    v = QuantumRegister(V_BITS, "v")
    acc = QuantumRegister(ACC_BITS, "acc")
    out = ClassicalRegister(U_BITS + V_BITS, "uv")
    regs = (u, v, acc)
    search = list(u) + list(v)
    qc = QuantumCircuit(u, v, acc, out)
    qc.h(search)
    if rounds is None:
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
    uu, vv = value & ((1 << U_BITS) - 1), value >> U_BITS
    return 1 + 2 * uu, 1 + 2 * vv


def factor_with_grover(n_value, shots=64, seed=8, noise=None, rounds=None):
    qc = grover_circuit(n_value, rounds)
    backend = AerSimulator(seed_simulator=seed, noise_model=noise) if noise else AerSimulator(seed_simulator=seed)
    counts = backend.run(transpile(qc, backend), shots=shots).result().get_counts()
    pairs = Counter()
    for bits, n in counts.items():
        pairs[decode(bits)] += n
    for (p, q), _ in pairs.most_common():
        if p > 1 and p * q == n_value:  # checking a product is cheap and classical
            return p, q, pairs, qc
    raise RuntimeError("Grover did not find a factor pair")


def build_circuit():
    """Grover factoring circuit for N = 35 (for diagrams)."""
    from common import load_locked
    return grover_circuit(load_locked(8)["public_parameters"]["N"])


def solve():
    """Factor N with Grover on Aer, unwrap the RSA key, decrypt."""
    from common import keystream, load_locked, xor_bytes
    locked = load_locked(8)
    params = locked["public_parameters"]
    p, q, _, _ = factor_with_grover(params["N"])
    d = pow(params["e"], -1, (p - 1) * (q - 1))
    k = pow(params["wrapped_key"], d, params["N"])
    key_bits = format(k, f"0{params['key_width_bits']}b")
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    return xor_bytes(ciphertext, keystream(key_bits, len(ciphertext))).decode("utf-8")
