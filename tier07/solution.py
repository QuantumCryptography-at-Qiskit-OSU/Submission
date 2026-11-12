"""Tier 7 solution: iterative phase estimation on two qubits.

The checker runs this file from the repo root. Keep these imports; they work
there, while the notebook's `import helper` does not.

Method
------
U has the eigenvalue e^(2 pi i phi) on the supplied eigenstate, with
phi = k / 2^14. A controlled U^(2^j) acting on that eigenstate leaves it alone
and kicks the phase 2 pi phi 2^j onto the control qubit (phase kickback).

Textbook phase estimation uses 14 control qubits and an inverse QFT. Here the
QFT is done "semiclassically": one control qubit is reused for 14 rounds.
Round m (m = 0 is the least significant bit of k) applies U^(2^(13-m)), so the
control picks up the phase

    2 pi * (k mod 2^(m+1)) / 2^(m+1) = pi * k_m + 2 pi * (k mod 2^m) / 2^(m+1).

The second term depends only on bits already measured, so a phase gate removes
it. What is left is pi * k_m, and a Hadamard turns that into a definite 0 or 1.
Because phi has an exact 14-bit expansion every round is deterministic.

U^(2^j) is built from the matrix of U by repeated squaring (allowed by the tier
rules). No eigenvalue of U is ever computed classically: the phase is read
from the measurements only.
"""
from collections import Counter

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

from common import load_locked, keystream, xor_bytes
from tier07 import helper

BASIS = ["rz", "sx", "x", "cx"]
SHOTS = 64


def controlled_power(power):
    """Return controlled-U^power as a gate (control first, then target).

    Operator() keeps the global phase of U, which becomes a relative phase
    once U is controlled, so it must not be dropped.
    """
    u = Operator(helper.build_unitary()).data
    return UnitaryGate(np.linalg.matrix_power(u, power), label=f"U^{power}").control(1)


def round_circuit(m, known_low, n_bits):
    """Circuit that measures bit m of k, given the lower bits `known_low`."""
    circuit = QuantumCircuit(2, 1)
    circuit.compose(helper.build_eigenstate(), [1], inplace=True)  # target = V|1>
    circuit.h(0)
    circuit.append(controlled_power(2 ** (n_bits - 1 - m)), [0, 1])
    # Feed-forward: remove the phase caused by the bits measured so far.
    circuit.p(-2 * np.pi * known_low / 2 ** (m + 1), 0)
    circuit.h(0)
    circuit.measure(0, 0)
    return circuit


def run_phase_estimation(shots=SHOTS, seed=7):
    """Measure the 14 bits of k, least significant first. Returns (k, log)."""
    n_bits = load_locked(7)["public_parameters"]["key_bits"]
    backend = AerSimulator(seed_simulator=seed)
    k = 0
    log = []
    for m in range(n_bits):
        circuit = transpile(round_circuit(m, k, n_bits), basis_gates=BASIS, optimization_level=3)
        counts = backend.run(circuit, shots=shots).result().get_counts()
        bit = int(Counter(counts).most_common(1)[0][0])
        log.append({"bit": m, "power": 2 ** (n_bits - 1 - m), "counts": dict(counts), "value": bit})
        k |= bit << m
    return k, log


def build_circuit():
    """Return your main circuit. Used for diagrams only, never for scoring."""
    # The last round with a placeholder correction of 0.
    return round_circuit(13, 0, 14)


def solve():
    """Run your circuit on Aer and return the decrypted line as a string."""
    locked = load_locked(7)
    n_bits = locked["public_parameters"]["key_bits"]
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    k, _ = run_phase_estimation()
    key_bits = format(k, f"0{n_bits}b")
    return xor_bytes(ciphertext, keystream(key_bits, len(ciphertext))).decode("utf-8")
