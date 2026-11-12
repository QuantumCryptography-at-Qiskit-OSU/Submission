"""Tier 2 solution: BB84 key exchange with an eavesdropper check.

The checker runs this file from the repo root. Keep these imports; they work
there, while the notebook's `import helper` does not.

Method
------
Alice sent 1024 qubits per link, each in a random basis (Z or X). Eve taps one
link: she measures every qubit in a random basis and resends it.

1. Pick a random basis for every qubit, blind (before finish()).
   Basis Z: measure directly. Basis X: H first, then measure.
2. After finish() Alice tells us her bases. Keep ("sift") only the qubits
   where our basis matched hers (about half). The rest are random noise.
3. Some of her bits are public (the check set). Compare them with ours:
   - clean link: they match exactly, error rate (QBER) 0
   - tapped link: Eve guessed the wrong basis half the time, and a wrong
     guess flips the result half the time, so QBER is about 25%
4. Drop the check-set bits (public) and rebuild the key from the clean link's
   remaining sifted bits with reconcile().
"""
import random

from qiskit import QuantumCircuit

from common import load_locked, xor_bytes
from tier02 import helper

TIER = 2
SEED = 2026
Z, X = 0, 1


def measurement_circuit(basis):
    """One qubit, one clbit: measure in the Z (0) or X (1) basis."""
    circuit = QuantumCircuit(1, 1)
    if basis == X:
        circuit.h(0)
    circuit.measure(0, 0)
    return circuit


def build_circuit(basis=X):
    """Our per-qubit circuit (X basis shown). Used for diagrams only."""
    return measurement_circuit(basis)


def measure_link(name, rng):
    """Measure every qubit of one link once. Returns our bases, bits, Alice's data."""
    channel = helper.Channel(name)
    my_bases = [rng.randint(Z, X) for _ in range(channel.n_qubits)]
    my_bits = channel.receive_all([measurement_circuit(b) for b in my_bases])
    return my_bases, my_bits, channel.finish()


def sift(my_bases, my_bits, public):
    """Split matching-basis bits into the public check set and the key bits."""
    check_pairs, key_bits = [], {}
    for i, (mine, alice) in enumerate(zip(my_bases, public["alice_bases"])):
        if mine != alice:
            continue
        if i in public["check_bits"]:
            check_pairs.append((my_bits[i], public["check_bits"][i]))
        else:
            key_bits[i] = my_bits[i]
    return check_pairs, key_bits


def qber(check_pairs):
    return sum(a != b for a, b in check_pairs) / len(check_pairs)


def run_links():
    """Measure both links once. Returns {link: (qber, sifted key bits, public)}."""
    rng = random.Random(SEED)
    results = {}
    for name in helper.LINKS:
        bases, bits, public = measure_link(name, rng)
        check_pairs, key_bits = sift(bases, bits, public)
        results[name] = (qber(check_pairs), key_bits, public, len(check_pairs))
    return results


def solve():
    """Run your circuit on Aer and return the decrypted line as a string."""
    ciphertext = bytes.fromhex(load_locked(TIER)["ciphertext_hex"])
    results = run_links()
    clean = min(results, key=lambda name: results[name][0])
    _, key_bits, public, _ = results[clean]
    key = helper.reconcile(key_bits, public["reconcile"])
    return xor_bytes(ciphertext, key).decode("utf-8")
