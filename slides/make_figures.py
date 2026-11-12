"""Make the measurement figures used in the slides, from our own solutions.

Run from the challenge repo root:
  python <team folder>/slides/make_figures.py

Writes PNG files and slide_data.json into slides/figures/.
"""
import importlib.util
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit.visualization import plot_bloch_vector, plot_histogram

TEAM = Path(__file__).resolve().parent.parent
OUT = TEAM / "slides" / "figures"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(Path.cwd()))

from common import load_locked  # noqa: E402

SCARLET, SLATE, INK = "#BA0C2F", "#5B6770", "#1F2933"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.edgecolor": SLATE,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False})
data = {}


def load(tier):
    path = TEAM / f"tier{tier:02d}" / "solution.py"
    spec = importlib.util.spec_from_file_location(f"solution{tier:02d}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def histogram(counts, name, title, colors=SCARLET, figsize=(7, 4), legend=None, **kwargs):
    fig, ax = plt.subplots(figsize=figsize)
    plot_histogram(counts, ax=ax, color=colors, legend=legend, **kwargs)
    ax.set_title(title, color=INK, fontsize=13)
    ax.set_ylabel("shots")
    ax.grid(False)
    save(fig, name)


def bloch(vectors, labels, name):
    fig = plt.figure(figsize=(3.2 * len(vectors), 3.6))
    for i, (vector, label) in enumerate(zip(vectors, labels)):
        ax = fig.add_subplot(1, len(vectors), i + 1, projection="3d")
        plot_bloch_vector(vector, ax=ax)
        ax.set_title(label, color=INK, fontsize=15, y=1.08)
    save(fig, name)


# Tier 1: Bernstein-Vazirani, every shot is the same string.
t1 = load(1)
counts = t1.run()
data["tier1"] = {"counts": counts, "shots": t1.SHOTS}
histogram(counts, "t1_hist.png", "Tier 1: all 16 shots give the same 24-bit string", figsize=(5, 4))

# Bloch spheres: the |-> target and the four BB84 states.
bloch([[-1, 0, 0]], ["target qubit in |−⟩"], "bloch_minus.png")
bloch([[0, 0, 1], [0, 0, -1], [1, 0, 0], [-1, 0, 0]],
      ["Z basis, bit 0: |0⟩", "Z basis, bit 1: |1⟩", "X basis, bit 0: |+⟩", "X basis, bit 1: |−⟩"],
      "bloch_bb84.png")

# Tier 2: error rate on the public check bits of each link.
t2 = load(2)
links = t2.run_links()
data["tier2"] = {name: {"qber": q, "check_bits": n, "key_bits": len(k)} for name, (q, k, _, n) in links.items()}

# Tier 3: one constant and one balanced oracle.
t3 = load(3)
key3, all_counts = t3.run_all()
constant, balanced = key3.index("0"), key3.index("1")
data["tier3"] = {"key": key3, "constant_oracle": constant, "balanced_oracle": balanced,
                 "constant_counts": all_counts[constant], "balanced_counts": all_counts[balanced]}
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
plot_histogram(all_counts[constant], ax=axes[0], color=SLATE)
axes[0].set_title(f"Oracle {constant}: constant → always 000000 → bit 0", fontsize=12)
plot_histogram(all_counts[balanced], ax=axes[1], color=SCARLET)
axes[1].set_title(f"Oracle {balanced}: balanced → never 000000 → bit 1", fontsize=12)
for ax in axes:
    ax.set_ylabel("shots")
    ax.grid(False)
save(fig, "t3_hist.png")

# Tier 4: Simon. Every measured y satisfies y.s = 0.
t4 = load(4)
ys, counts4 = t4.run_simon()
s = t4.solve_for_s(ys)[0]
dots = [bin(y & s).count("1") % 2 for y in ys]
data["tier4"] = {"s": format(s, "010b"), "shots": t4.SHOTS, "distinct_y": len(ys),
                 "sample_y": [format(y, "010b") for y in ys[:6]], "y_dot_s_zero": dots.count(0),
                 "y_dot_s_one": dots.count(1)}
histogram({"y·s = 0": dots.count(0), "y·s = 1": dots.count(1)}, "t4_hist.png",
          f"Tier 4: {len(ys)} different strings y, all with y·s = 0", figsize=(5, 4))

# Tier 5: Grover at the best number of rounds.
t5 = load(5)
counts5 = t5.run_search()
data["tier5"] = {"shots": t5.SHOTS, "top": counts5.most_common(3)}
histogram({format(k, "010b"): n for k, n in counts5.items()}, "t5_hist.png",
          "Tier 5: 256 shots after 25 Grover rounds", figsize=(5, 4))

# Tier 6: Grover with 64 marked keys, then the classical checksum filter.
t6 = load(6)
counts6 = t6.run_search()
ordered = sorted(counts6.values(), reverse=True)
data["tier6"] = {"shots": t6.SHOTS, "distinct_keys": len(counts6), "top5": counts6.most_common(5)}
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(range(len(ordered)), ordered, color=[SCARLET if i < 64 else SLATE for i in range(len(ordered))], width=1.0)
ax.set_xlabel("measured keys, most frequent first")
ax.set_ylabel("shots")
ax.set_title(f"Tier 6: {t6.SHOTS} shots land on the 64 keys that pass the first byte", fontsize=13)
save(fig, "t6_hist.png")

# Tier 7: one bit per round.
t7 = load(7)
k7, log7 = t7.run_phase_estimation()
data["tier7"] = {"k": k7, "bits": [row["value"] for row in log7], "shots_per_round": t7.SHOTS}

# Tiers 8 and 9: Shor. More shots than solve() uses, so the peaks are visible.
for tier in (8, 9):
    module = load(tier)
    modulus = load_locked(tier)["public_parameters"]["N"]
    p, q, details = module.factor(modulus)
    a = details["a"] if isinstance(details, dict) and "a" in details else 2
    t_bits = module.counting_bits(modulus)
    counts = module.run_order_finding(a, modulus, shots=2048)
    r = module.order_from_counts(counts, a, modulus)
    data[f"tier{tier}"] = {"N": modulus, "p": p, "q": q, "a": a, "r": r, "counting_bits": t_bits,
                           "details": str(details)[:400], "solve_shots": module.SHOTS}
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(list(counts), list(counts.values()), width=2 ** t_bits / 300, color=SCARLET)
    for j in range(r + 1):
        ax.axvline(j * 2 ** t_bits / r, color=SLATE, lw=0.5, ls=":", zorder=0)
    ax.set_xlim(0, 2 ** t_bits)
    ax.set_xlabel(f"measured y (0 to 2^{t_bits} − 1)")
    ax.set_ylabel("shots (of 2048)")
    ax.set_title(f"Tier {tier}: peaks sit at multiples of 2^{t_bits} / r, with r = {r} for a = {a}", fontsize=13)
    save(fig, f"t{tier}_hist.png")

# Tier 10: discrete log. Each shot (y_g, y_A) votes for an exponent.
t10 = load(10)
parameters = load_locked(10)["public_parameters"]
a10, votes = t10.recover_exponent(parameters)
data["tier10"] = {"parameters": {k: v for k, v in parameters.items() if isinstance(v, int)},
                  "a": a10, "votes_top3": votes.most_common(3), "shots": t10.SHOTS}
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(list(votes), list(votes.values()), color=[SCARLET if v == a10 else SLATE for v in votes])
ax.set_xlabel("candidate exponent a")
ax.set_ylabel("votes (shots)")
ax.set_title(f"Tier 10: {t10.SHOTS} shots vote for the exponent, a = {a10} wins", fontsize=13)
save(fig, "t10_hist.png")

# Scaling: classical tries against Grover rounds, for one marked key in 2^n.
n = np.arange(8, 129)
fig, ax = plt.subplots(figsize=(7, 4))
ax.semilogy(n, 2.0 ** (n - 1), color=SLATE, lw=2.5, label="classical: 2^n / 2 tries")
ax.semilogy(n, np.pi / 4 * 2.0 ** (n / 2), color=SCARLET, lw=2.5, label="Grover: (π/4)·√(2^n) rounds")
ax.scatter([10], [25], color=SCARLET, zorder=3)
ax.annotate("tier 5: 25 rounds", (10, 25), textcoords="offset points", xytext=(10, -4))
ax.set_xlabel("key size n (bits)")
ax.set_ylabel("oracle calls")
ax.legend(frameon=False)
save(fig, "scaling_grover.png")

# Grover success against rounds: theory, and what explore.py measured on Aer (tier 5).
rounds = np.arange(0, 51)
theta = np.arcsin(np.sqrt(1 / 1024))
measured = {0: 0.001, 1: 0.011, 2: 0.032, 5: 0.125, 10: 0.382, 15: 0.696, 20: 0.934, 25: 1.000,
            30: 0.904, 40: 0.344, 50: 0.000}
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(rounds, np.sin((2 * rounds + 1) * theta) ** 2, color=SLATE, lw=2.5, label="theory: sin²((2k+1)θ)")
ax.scatter(list(measured), list(measured.values()), color=SCARLET, zorder=3, s=60, label="measured on Aer")
ax.annotate("25 rounds: key found", (25, 1.0), textcoords="offset points", xytext=(-165, 2), color=SCARLET)
ax.annotate("50 rounds: back to zero", (50, 0.0), textcoords="offset points", xytext=(-175, 12), color=SCARLET)
ax.set_xlabel("Grover rounds k")
ax.set_ylabel("chance of measuring the key")
ax.legend(frameon=False, loc="upper right", fontsize=11)
ax.set_xlim(-1, 62)
save(fig, "t5_rounds.png")

(OUT / "slide_data.json").write_text(json.dumps(data, indent=1, default=str))
print(json.dumps(data, indent=1, default=str))
