"""Tier 3 solution: Deutsch-Jozsa, one circuit and one oracle call per seal.

The checker runs this file from the repo root. Keep these imports; they work
there, while the notebook's `import helper` does not.

Method
------
Each oracle computes |x>|y> -> |x>|y XOR f(x)> on 6 input qubits (0..5) and
one target (6). f is promised to be constant or balanced.

1. Put the target in |-> (X then H). Now the oracle does not change the
   target at all; it multiplies |x> by the sign (-1)^f(x). ("Phase kickback")
2. Put the 6 inputs in an equal mix of all 64 values (H on each).
3. Apply the oracle once: all 64 inputs get their sign at the same time.
4. H on the inputs again, and measure them.

The chance of reading 000000 is (average of (-1)^f(x) over all x)^2:
  constant f -> every sign equal  -> average +-1 -> always 000000 -> key bit 0
  balanced f -> 32 plus, 32 minus -> average 0   -> never 000000  -> key bit 1
It is exact, so one shot is already enough. We take a few shots only as
evidence for the write-up; every shot of a circuit agrees.
"""
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common import load_locked, keystream, xor_bytes
from tier03 import helper

TIER = 3
N_INPUTS = 6
TARGET = 6
SHOTS = 16


def build_circuit(i=0):
    """Deutsch-Jozsa circuit for oracle i (one oracle application)."""
    circuit = QuantumCircuit(N_INPUTS + 1, N_INPUTS)
    circuit.x(TARGET)               # target = |1>
    circuit.h(range(N_INPUTS + 1))  # inputs = all 64 values, target = |->
    circuit.compose(helper.build_oracle(i), range(N_INPUTS + 1), inplace=True)
    circuit.h(range(N_INPUTS))      # undo the mix on the inputs
    circuit.measure(range(N_INPUTS), range(N_INPUTS))
    return circuit


def classify(counts):
    """Key bit from one oracle's counts: 0 if we always read all zeros."""
    zeros = counts.get("0" * N_INPUTS, 0)
    if zeros == sum(counts.values()):
        return "0"  # constant
    if zeros == 0:
        return "1"  # balanced
    raise RuntimeError(f"mixed result {counts}: the promise is broken or the run is noisy")


def run_all(shots=SHOTS):
    """Run the 24 circuits. Returns (key_bits, list of counts per oracle)."""
    n_oracles = load_locked(TIER)["public_parameters"]["n_oracles"]
    backend = AerSimulator(seed_simulator=3)
    key, all_counts = "", []
    for i in range(n_oracles):
        circuit = build_circuit(i)
        assert helper.count_oracle_calls(circuit) == 1
        counts = backend.run(transpile(circuit, backend), shots=shots).result().get_counts()
        all_counts.append(counts)
        key += classify(counts)
    return key, all_counts


def solve():
    """Run your circuit on Aer and return the decrypted line as a string."""
    ciphertext = bytes.fromhex(load_locked(TIER)["ciphertext_hex"])
    key_bits, _ = run_all()
    return xor_bytes(ciphertext, keystream(key_bits, len(ciphertext))).decode("utf-8")
