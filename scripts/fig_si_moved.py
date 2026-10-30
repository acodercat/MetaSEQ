"""Supplementary figures moved out of the main text, plus the headroom relation.

    uv run --project phase3_replication --with matplotlib --with scipy python scripts/fig_si_moved.py

si_multiturn.pdf   Experiment 2: turn pass rate after a failed and after a passed turn, and third turns.
si_categories.pdf  Experiment 1: gain by task category (descriptive).
si_headroom.pdf    Both experiments: gain D - A against single-agent accuracy, 15 comparisons.
si_fixrate.pdf     Experiment 2: share of wrong numeric outputs the verifier corrected, by size of the error.
"""
import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.stats import spearmanr

import replication_tables as rt
from data_figure_style import setup, save, clean_axis, WIDTH, MM, INK, MUTED, GRID, SINGLE, SINGLE_LIGHT, MULTI

setup()
ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "manuscript/figures"
E1 = ROOT / "phase2_benchmark/experiments/metaseq/summary"
CATS = {"cross_domain_analysis": "Cross-domain analysis", "data_retrieval": "Data retrieval",
        "source_attribution": "Source attribution", "statistical_characterization": "Statistical characterization",
        "spatial_analysis": "Spatial analysis", "exposure_assessment": "Exposure assessment",
        "comparative_assessment": "Comparative assessment", "exceedance_anomaly_detection": "Exceedance detection"}


def multiturn():
    fig, ax = plt.subplots(figsize=(110 * MM, 48 * MM))
    mt = rt.multiturn()
    for y, col in enumerate(["after_failed", "after_passed", "third"]):
        a, d = mt.loc[rt.A, col], mt.loc[rt.D, col]
        ax.plot([a, d], [y, y], lw=.8, color=SINGLE_LIGHT)
        ax.plot(a, y, "o", ms=4.5, mfc="white", mec=SINGLE)
        ax.plot(d, y, "o", ms=4.5, color=MULTI)
        ax.annotate(f"{a:.1f}", (a, y), xytext=(-6, 0), textcoords="offset points", ha="right", va="center", fontsize=6.3)
        ax.annotate(f"{d:.1f}", (d, y), xytext=(6, 0), textcoords="offset points", ha="left", va="center", fontsize=6.3)
    ax.set(xlim=(48, 103), xticks=[50, 75, 100], ylim=(2.6, -.6), xlabel="Turn pass rate (%)",
           yticks=[0, 1, 2], yticklabels=["After a failed turn", "After a passed turn", "Third turn"])
    clean_axis(ax)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", mfc="white", mec=SINGLE, label="Single agent"),
                       Line2D([], [], marker="o", ls="", color=MULTI, label="MetaSEQ")],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
    fig.tight_layout(pad=.4)
    save(fig, FIG / "si_multiturn.pdf")


def categories():
    with open(E1 / "per_category.csv") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: -float(r["delta_pp"]))
    fig, ax = plt.subplots(figsize=(110 * MM, 58 * MM))
    ys = range(len(rows))
    vals = [float(r["delta_pp"]) for r in rows]
    ax.barh(list(ys), vals, height=.6, color=MULTI, zorder=2)
    for y, v in zip(ys, vals):
        ax.text(v + .4, y, f"{v:.1f}", va="center", fontsize=6, color=MUTED)
    ax.set_yticks(list(ys)); ax.set_yticklabels([f"{CATS.get(r['category'], r['category'])} ({r['n_tasks']})" for r in rows])
    ax.set(ylim=(len(rows) - .4, -.6), xlim=(0, 25), xticks=[0, 10, 20], xlabel="Gain, MetaSEQ − single agent (percentage points)")
    clean_axis(ax)
    fig.tight_layout(pad=.4)
    save(fig, FIG / "si_categories.pdf")


def headroom():
    with open(E1 / "per_backbone.csv") as f:
        e1 = [(r["public_name"], 2 * int(r["single"]), 2 * (int(r["multi"]) - int(r["single"]))) for r in csv.DictReader(f)]
    acc = rt.accuracy().set_index("model")
    e2 = [(rt.LABELS[m], acc.loc[m].A, acc.loc[m].D - acc.loc[m].A) for m in rt.models()]
    rho, p = spearmanr([x for _, x, _ in e1 + e2], [y for _, _, y in e1 + e2])
    fig, ax = plt.subplots(figsize=(110 * MM, 72 * MM))
    ax.axhline(0, color=MUTED, lw=.6, ls=(0, (3, 2)))
    ax.plot([x for _, x, _ in e1], [y for _, _, y in e1], "s", ms=4.6, mfc="white", mec=MULTI, mew=.9, label="Experiment 1 (one run per cell)")
    ax.plot([x for _, x, _ in e2], [y for _, _, y in e2], "o", ms=4.6, color=MULTI, label="Experiment 2 (three repeats)")
    # name only the points the text cites; per-backbone values are in Table 1
    for name, x, y in e1 + e2:
        if name in ("Qwen2.5-72B-Instruct", "GPT-5.5", "Claude Sonnet 5.5", "Qwen3.8-27B", "DeepSeek-V4-Pro") and not (name == "DeepSeek-V4-Pro" and y > 2):
            ax.annotate(name, (x, y), xytext=(5, 0), textcoords="offset points", fontsize=5.8, color=MUTED, va="center")
    ax.set(xlim=(30, 102), ylim=(-3, 25), xlabel="Single-agent task pass rate (%)", ylabel="Gain, D − A (percentage points)")
    clean_axis(ax, grid="y", left=True)
    ax.legend(loc="upper right", fontsize=6)
    ax.text(.02, .04, f"Spearman ρ = {rho:.2f}, p = {p:.3f} (15 comparisons; exploratory)", transform=ax.transAxes, fontsize=6, color=INK)
    fig.tight_layout(pad=.4)
    save(fig, FIG / "si_headroom.pdf")
    return rho, p


def fixrate():
    """Of D's numeric outputs that held a wrong value before the verifier, the share corrected, by
    the size of the error (Supplementary Table 29)."""
    tr = rt.verifier_transitions()["by_magnitude"]
    labels = {"order of magnitude": "Ratio ≥10\nor ≤0.1", ">=50%": "≥50%", "10-50%": "10–50%", "1-10%": "1–10%", "<1%": "<1%"}
    fig, ax = plt.subplots(figsize=(110 * MM, 52 * MM))
    xs = range(len(rt.MAGNITUDE_BINS))
    rates = [tr.loc[k, "fix_rate"] for k in rt.MAGNITUDE_BINS]
    ax.bar(list(xs), rates, width=.62, color=MULTI, zorder=2)
    for x, k, v in zip(xs, rt.MAGNITUDE_BINS, rates):
        ax.text(x, v + 1.5, f"{int(tr.loc[k, 'fixed'])}/{int(tr.loc[k, 'fixed'] + tr.loc[k, 'survived'])}", ha="center", va="bottom", fontsize=6.3, color=MUTED)
    ax.set_xticks(list(xs)); ax.set_xticklabels([labels[k] for k in rt.MAGNITUDE_BINS], fontsize=6.5)
    ax.set(ylim=(0, 75), yticks=[0, 25, 50, 75], ylabel="Outputs corrected (%)", xlabel="Size of the error before the verifier")
    clean_axis(ax, grid="y", left=True)
    fig.tight_layout(pad=.4)
    save(fig, FIG / "si_fixrate.pdf")


if __name__ == "__main__":
    multiturn(); categories(); fixrate(); print("headroom rho, p:", headroom())
