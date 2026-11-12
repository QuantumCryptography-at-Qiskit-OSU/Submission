"""Tier 1 solution: Bernstein-Vazirani, one oracle call for all 24 bits.

The checker runs this file from the repo root. Keep these imports; they work
there, while the notebook's `import helper` does not.

Method
------
The oracle computes |x>|t> -> |x>|t XOR (s.x mod 2)> on 24 input qubits
(0..23) and one target (24). We want the hidden 24-bit string s.

1. Put the target in |-> (X then H). Now the oracle does not change the
   target; it multiplies |x> by the sign (-1)^(s.x). ("Phase kickback")
2. Put the 24 inputs in an equal mix of all 2^24 values (H on each).
3. Apply the oracle once: every x gets its sign at the same time.
4. H on the inputs again. The sign pattern (-1)^(s.x) is exactly the
   Hadamard transform of the basis state |s>, so the inputs now read s.
   Measure them: s comes out with probability 1, so one shot is enough.
"""
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common import load_locked, xor_repeating
from tier01 import helper

TIER = 1
N_BITS = 24
TARGET = N_BITS
SHOTS = 16


def build_circuit(oracle=None):
    """Bernstein-Vazirani circuit with one oracle application."""
    oracle = oracle if oracle is not None else helper.build_oracle()
    circuit = QuantumCircuit(N_BITS + 1, N_BITS)
    circuit.x(TARGET)                # target = |1>
    circuit.h(range(N_BITS + 1))     # inputs = all values, target = |->
    circuit.compose(oracle, range(N_BITS + 1), inplace=True)
    circuit.h(range(N_BITS))         # signs -> bits of s
    circuit.measure(range(N_BITS), range(N_BITS))
    return circuit


def run(shots=SHOTS):
    """Run on Aer. Returns the counts. Every shot should be the same string."""
    circuit = build_circuit()
    assert helper.count_oracle_calls(circuit) == 1
    backend = AerSimulator(seed_simulator=1)
    return backend.run(transpile(circuit, backend), shots=shots).result().get_counts()


def solve():
    """Run your circuit on Aer and return the decrypted line as a string."""
    counts = run()
    if len(counts) != 1:
        raise RuntimeError(f"expected one outcome, got {counts}")
    s = int(next(iter(counts)), 2)  # clbit j holds bit j, printed rightmost-first
    ciphertext = bytes.fromhex(load_locked(TIER)["ciphertext_hex"])
    return xor_repeating(ciphertext, s.to_bytes(3, "big")).decode("utf-8")
