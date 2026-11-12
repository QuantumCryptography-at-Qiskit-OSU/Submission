"""Tier 7 on real IBM hardware (or a noisy local simulation).

solution.py feeds each measured bit into the next circuit, which on hardware
would mean 14 jobs and 14 waits in the queue. Here the same correction is done
afterwards in software, so all circuits go in ONE job:

  for each of the 14 powers U^(2^j) we run two circuits, reading the control
  qubit in the X basis and in the Y basis. Together they give the direction
  of the kicked-back phase (cos and sin). Bit m of the key is then "which of
  the two allowed directions is closer", starting from the lowest bit.

Run from the challenge repo root:
  python ../Submission/tier07/run_hardware.py --sim            # local, noisy Aer
  python ../Submission/tier07/run_hardware.py                  # least busy IBM device
  python ../Submission/tier07/run_hardware.py --backend ibm_fez

The hardware run needs `pip install qiskit-ibm-runtime` and a saved account.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path.cwd()))

from qiskit import QuantumCircuit, transpile  # noqa: E402

from common import is_correct, keystream, load_locked, xor_bytes  # noqa: E402
from tier07 import helper  # noqa: E402
from solution import controlled_power  # noqa: E402

N_BITS = load_locked(7)["public_parameters"]["key_bits"]


def quadrature_circuit(m, basis):
    """Kick the phase of U^(2^(13-m)) onto qubit 0 and read it in X or Y."""
    circuit = QuantumCircuit(2, 1, name=f"bit{m}_{basis}")
    circuit.compose(helper.build_eigenstate(), [1], inplace=True)
    circuit.h(0)
    circuit.append(controlled_power(2 ** (N_BITS - 1 - m)), [0, 1])
    if basis == "Y":
        circuit.sdg(0)
    circuit.h(0)
    circuit.measure(0, 0)
    return circuit


def all_circuits():
    return [quadrature_circuit(m, basis) for m in range(N_BITS) for basis in "XY"]


def decode(p0_list):
    """p0_list[2m], p0_list[2m+1] = P(read 0) in X and Y for bit m. Returns k, log."""
    k, log = 0, []
    for m in range(N_BITS):
        cos_est, sin_est = 2 * p0_list[2 * m] - 1, 2 * p0_list[2 * m + 1] - 1
        angle0 = 2 * math.pi * k / 2 ** (m + 1)          # direction if bit m is 0
        overlap = cos_est * math.cos(angle0) + sin_est * math.sin(angle0)
        bit = int(overlap < 0)                           # bit 1 points the opposite way
        k |= bit << m
        log.append({"bit": m, "cos": round(cos_est, 3), "sin": round(sin_est, 3),
                    "contrast": round(abs(overlap), 3), "value": bit})
    return k, log


def run_sim(shots, cx_error):
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error

    noise = NoiseModel()
    noise.add_all_qubit_quantum_error(depolarizing_error(cx_error, 2), ["cx"])
    backend = AerSimulator(noise_model=noise, seed_simulator=7)
    circuits = transpile(all_circuits(), basis_gates=["rz", "sx", "x", "cx"], optimization_level=3)
    counts = backend.run(circuits, shots=shots).result().get_counts()
    return f"aer_noisy(cx_error={cx_error})", [c.get("0", 0) / shots for c in counts], None


def run_hardware(shots, backend_name):
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()
    backend = (service.backend(backend_name) if backend_name
               else service.least_busy(operational=True, simulator=False))
    print("backend:", backend.name)
    isa = generate_preset_pass_manager(backend=backend, optimization_level=3).run(all_circuits())
    print("two-qubit gates per circuit:", max(c.num_nonlocal_gates() for c in isa))
    job = SamplerV2(mode=backend).run(isa, shots=shots)
    print("job id:", job.job_id(), "(waiting in the queue...)")
    result = job.result()
    p0 = [pub.data.c.get_counts().get("0", 0) / shots for pub in result]
    return backend.name, p0, job.job_id()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim", action="store_true", help="noisy local simulation instead of hardware")
    parser.add_argument("--cx-error", type=float, default=0.01)
    parser.add_argument("--backend", default=None)
    parser.add_argument("--shots", type=int, default=1024)
    args = parser.parse_args()

    name, p0, job_id = run_sim(args.shots, args.cx_error) if args.sim else run_hardware(args.shots, args.backend)
    k, log = decode(p0)
    for row in log:
        print(row)
    key_bits = format(k, f"0{N_BITS}b")
    ciphertext = bytes.fromhex(load_locked(7)["ciphertext_hex"])
    try:
        line = xor_bytes(ciphertext, keystream(key_bits, len(ciphertext))).decode("utf-8")
    except UnicodeDecodeError:
        line = "(not readable text)"
    correct = is_correct(7, line)
    print(f"k = {k} ({key_bits})  ->  {line}   correct: {correct}")

    out = HERE / ("hardware_result_sim.json" if args.sim else "hardware_result.json")
    out.write_text(json.dumps({"backend": name, "job_id": job_id, "shots": args.shots, "k": k,
                               "correct": bool(correct), "p0": p0, "log": log}, indent=1))
    print("saved", out)


if __name__ == "__main__":
    main()
