#!/usr/bin/env python
"""Local submission pipeline: check, zip, re-check the zip.

  python ci/package.py                  # full run
  python ci/package.py --metrics-only   # skip answer hashes (much faster)
  python ci/package.py --no-zip         # check only
  python ci/package.py --require-docs   # also fail if WRITEUP.md / README.md are missing

Stages, in order. Any failure stops the run with a non-zero exit code.
  1. Layout: tier01..tier10 each have a solution.py with solve() and build_circuit().
  2. Check: a fresh copy of the challenge repo gets this folder as
     submissions/<team>/, and tools/check_submission.py runs on it, so nothing
     in the real repo is touched. Gate: every tier hash-matches, ran a circuit,
     has metrics, no repeated measurements, no solve() timeout.
  3. Zip: a single top-level folder named after the team, without caches,
     virtual envs, .git or this ci/ folder.
  4. Verify the zip: unzip into another fresh repo copy and run the check again.

Settings come from the environment: CHALLENGE_REPO (default ../Quantum-Cryptography-Challenge),
PYTHON (default: this interpreter; it needs qiskit and qiskit-aer).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUBMISSION = HERE.parent
TEAM = "Cryptographers"
REPO = Path(os.environ.get("CHALLENGE_REPO", SUBMISSION.parent / "Quantum-Cryptography-Challenge")).resolve()
PYTHON = os.environ.get("PYTHON", sys.executable)
SKIP_DIRS = {"__pycache__", ".ipynb_checkpoints", ".venv", "venv", ".git", "ci", ".github", "node_modules"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
DOCS = ["README.md", "WRITEUP.md"]


def step(text):
    print(f"\n== {text}", flush=True)


def fail(text):
    print(f"FAIL: {text}", flush=True)
    sys.exit(1)


def wanted(path):
    return not (set(path.parts) & SKIP_DIRS) and path.suffix not in SKIP_SUFFIXES


def copy_team(dest):
    for path in sorted(SUBMISSION.rglob("*")):
        rel = path.relative_to(SUBMISSION)
        if path.is_file() and wanted(rel):
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def check_layout(args):
    problems = []
    for tier in range(1, 11):
        solution = SUBMISSION / f"tier{tier:02d}" / "solution.py"
        if not solution.exists():
            problems.append(f"missing {solution.relative_to(SUBMISSION)}")
            continue
        source = solution.read_text(encoding="utf-8")
        for name in ("def solve(", "def build_circuit("):
            if name not in source:
                problems.append(f"tier{tier:02d}/solution.py has no {name})")
        if "raise NotImplementedError" in source:
            problems.append(f"tier{tier:02d}/solution.py still raises NotImplementedError")
    missing_docs = [d for d in DOCS if not (SUBMISSION / d).exists()]
    for doc in missing_docs:
        print(f"{'FAIL' if args.require_docs else 'warning'}: {doc} is missing (a required deliverable)")
    if problems or (missing_docs and args.require_docs):
        fail("; ".join(problems) or "documents missing")
    print("layout ok")


def prepare_repo(root):
    """Fresh copy of the challenge repo without any team folders."""
    repo = root / "repo"
    shutil.copytree(REPO, repo, ignore=shutil.ignore_patterns("__pycache__", ".git", ".ipynb_checkpoints"))
    for old in (repo / "submissions").iterdir():
        if old.name != "TEAM_TEMPLATE":
            shutil.rmtree(old)
    return repo


def run_checker(repo, out_dir, metrics_only):
    command = [PYTHON, "tools/check_submission.py", f"submissions/{TEAM}", "--out", str(out_dir)]
    if metrics_only:
        command.append("--metrics-only")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(command, cwd=repo, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        print(result.stdout[-2000:], result.stderr[-2000:])
        fail("check_submission.py crashed (is pyyaml installed? pip install pyyaml)")
    return json.loads((out_dir / "report.json").read_text())


def gate(report, metrics_only):
    rows, bad = [], []
    for tier in sorted(report["tiers"], key=int):
        t = report["tiers"][tier]
        m = t.get("metrics") or {}
        rows.append(f"  tier {int(tier):2d}  {t['status']:<12} hash={t['hash_ok']!s:<5} 2Q={m.get('two_qubit_gates', '-'):>6} "
                    f"depth={m.get('depth', '-'):>6} qubits={m.get('active_qubits', '-'):>3} solve={t.get('solve_seconds', '-')}s"
                    + (f"  flags: {'; '.join(t['flags'])}" if t["flags"] else ""))
        want = "metrics_only" if metrics_only else "full"
        if t["status"] != want:
            bad.append(f"tier {tier}: status {t['status']} (wanted {want})")
        if not metrics_only and t["hash_ok"] is not True:
            bad.append(f"tier {tier}: answer hash does not match")
        if not t["circuit_executed"]:
            bad.append(f"tier {tier}: no circuit was executed in solve()")
        if t["metrics_status"] != "ok":
            bad.append(f"tier {tier}: {t['metrics_status']}")
        if t.get("repeat_measurements"):
            bad.append(f"tier {tier}: qubits measured more than once")
        if any("solve_timeout" in flag for flag in t["flags"]):
            bad.append(f"tier {tier}: solve() went over the time limit")
    print("\n".join(rows))
    if bad:
        fail("\n  ".join(bad))
    print("gate ok: every tier passes")


def make_zip(target):
    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(SUBMISSION.rglob("*")):
            rel = path.relative_to(SUBMISSION)
            if path.is_file() and wanted(rel):
                archive.write(path, Path(TEAM) / rel)
                count += 1
    print(f"{target.name}: {count} files, {target.stat().st_size / 1e6:.1f} MB")


def verify_zip(target, root, metrics_only):
    with zipfile.ZipFile(target) as archive:
        names = archive.namelist()
        tops = {n.split("/")[0] for n in names}
        if tops != {TEAM}:
            fail(f"zip must hold exactly one top-level folder named {TEAM}, found {sorted(tops)}")
        junk = [n for n in names if set(Path(n).parts) & SKIP_DIRS or n.endswith((".pyc", ".pyo"))]
        if junk:
            fail(f"zip contains files that should be left out: {junk[:5]}")
        repo = prepare_repo(root / "verify")
        archive.extractall(repo / "submissions")
    report = run_checker(repo, root / "verify_report", metrics_only)
    gate(report, metrics_only)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics-only", action="store_true")
    parser.add_argument("--no-zip", action="store_true")
    parser.add_argument("--require-docs", action="store_true")
    parser.add_argument("--out", default=str(SUBMISSION.parent / f"{TEAM}.zip"))
    args = parser.parse_args()

    step("1. layout")
    check_layout(args)

    with tempfile.TemporaryDirectory(prefix="ci_submission_") as tmp:
        root = Path(tmp)
        step("2. checker on a fresh copy of the challenge repo")
        repo = prepare_repo(root / "work")
        copy_team(repo / "submissions" / TEAM)
        report = run_checker(repo, root / "report", args.metrics_only)
        print(f"qiskit {report['qiskit']}, qiskit-aer {report['qiskit_aer']}")
        gate(report, args.metrics_only)
        shutil.copy(root / "report" / "report.md", SUBMISSION.parent / "last_check_report.md")

        if args.no_zip:
            return
        step("3. zip")
        target = Path(args.out)
        make_zip(target)
        step("4. verify the zip by unpacking it and checking again")
        verify_zip(target, root, args.metrics_only)

    print(f"\nREADY: upload {target}  (the form wants the folder name to be exactly {TEAM})")


if __name__ == "__main__":
    main()
