"""Tier 4 solution: Simon's algorithm, plus a GF(2) solver for the equations.

The checker runs this file from the repo root. Keep these imports; they work
there, while the notebook's `import helper` does not.

Method
------
f on 10 bits is exactly 2-to-1 with f(x) = f(x XOR s). We want s.

1. H on all 10 input qubits: an equal mix of all 1024 values of x.
2. One oracle call: the output register now holds f(x) next to every x.
3. H on the inputs again, then measure them.

Each run returns a random string y with  y . s = 0 (mod 2): the paired values
x and x XOR s interfere, and only y with y.s = 0 survive. About 9 independent
runs give 9 independent equations, which leave exactly one non-zero s.
Solving those equations is ordinary linear algebra over GF(2), done here by
Gaussian elimination.
"""
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common import load_locked, keystream, xor_bytes
from tier04 import helper

TIER = 4
N = 10
SHOTS = 40  # about 9 are needed; 40 makes a failure vanishingly unlikely


def build_circuit():
    """Simon circuit: one oracle call, 10 measured qubits."""
    circuit = QuantumCircuit(2 * N, N)
    circuit.h(range(N))
    circuit.compose(helper.build_oracle(), range(2 * N), inplace=True)
    circuit.h(range(N))
    circuit.measure(range(N), range(N))
    return circuit


def gf2_reduce(rows):
    """Row-reduce bit-vectors (ints) over GF(2). Returns {pivot bit: row}."""
    pivots = {}
    for row in rows:
        while row:
            top = row.bit_length() - 1
            if top not in pivots:
                pivots[top] = row
                break
            row ^= pivots[top]
    return pivots


def solve_for_s(equations):
    """All non-zero s with y . s = 0 (mod 2) for every y in equations."""
    pivots = gf2_reduce(equations)
    # Fully reduce, then each free bit gives one null-space vector.
    for top in sorted(pivots):
        for other in pivots:
            if other != top and (pivots[other] >> top) & 1:
                pivots[other] ^= pivots[top]
    free = [b for b in range(N) if b not in pivots]
    solutions = []
    for b in free:
        s = 1 << b
        for top, row in pivots.items():
            if (row >> b) & 1:
                s |= 1 << top
        solutions.append(s)
    return solutions


def run_simon(shots=SHOTS, backend=None):
    """Run the circuit. Returns (list of y strings as ints, counts)."""
    backend = backend or AerSimulator(seed_simulator=4)
    circuit = build_circuit()
    counts = backend.run(transpile(circuit, backend), shots=shots).result().get_counts()
    return [int(y, 2) for y in counts], counts


def solve():
    """Run your circuit on Aer and return the decrypted line as a string."""
    ciphertext = bytes.fromhex(load_locked(TIER)["ciphertext_hex"])
    equations, _ = run_simon()
    solutions = solve_for_s(equations)
    if len(solutions) != 1:
        raise RuntimeError(f"{len(solutions)} null-space dimensions left: need more shots")
    key_bits = format(solutions[0], "010b")
    return xor_bytes(ciphertext, keystream(key_bits, len(ciphertext))).decode("utf-8")
