"""Fig. 3 (experiment 1), in the same form as Fig. 4a. (a) Task pass rate per backbone and pooled,
single agent and MetaSEQ, Wilson 95% intervals, the gain above each pair and MetaSEQ's token
multiple below its label. (b) Outcome of the 350 paired backbone-task cells.
Writes manuscript/figures/experiment1.pdf.

    uv run --project phase3_replication --with matplotlib python scripts/fig_experiment1.py
"""
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from data_figure_style import setup, save, panel, WIDTH, MM, INK, MUTED, GRID, SINGLE, SINGLE_LIGHT, MULTI, VOTE

setup()
ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "phase2_benchmark/experiments/metaseq/summary"
OUT = ROOT / "manuscript/figures/experiment1.pdf"
WRAP = {"GPT-5.5": "GPT-5.5", "DeepSeek-V4-Pro": "DeepSeek-\nV4-Pro", "DeepSeek-V4-Flash": "DeepSeek-\nV4-Flash",
        "Qwen3.5-397B-A17B": "Qwen3.5-\n397B-A17B", "Qwen3.6-35B-A3B": "Qwen3.6-\n35B-A3B", "Qwen3.6-27B": "Qwen3.6-\n27B",
        "Qwen2.5-72B-Instruct": "Qwen2.5-72B-\nInstruct", "Pooled": "Pooled"}


def wilson(k, n, z=1.959964):
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return 100 * (c - h), 100 * (c + h)


def rows():
    with open(SUMMARY / "per_backbone.csv") as f:
        bb = sorted(csv.DictReader(f), key=lambda r: int(r["single"]))
    out = [dict(label=r["public_name"], ks=int(r["single"]), km=int(r["multi"]), n=50,
                ts=float(r["avg_tokens_single"]), tm=float(r["avg_tokens_multi"])) for r in bb]
    out.append(dict(label="Pooled", ks=sum(r["ks"] for r in out), km=sum(r["km"] for r in out), n=50 * len(out),
                    ts=sum(r["ts"] for r in out) / len(out), tm=sum(r["tm"] for r in out) / len(out)))
    return out


def bars(ax):
    data = rows()
    xs = list(range(len(data))); xs[-1] += .3
    w = .34
    for x, r in zip(xs, data):
        for dx, k, colour in ((-w / 2, r["ks"], SINGLE_LIGHT), (w / 2, r["km"], MULTI)):
            mu = 100 * k / r["n"]; lo, hi = wilson(k, r["n"])
            ax.bar(x + dx, mu, width=w * .9, color=colour, zorder=2)
            ax.errorbar(x + dx, mu, yerr=[[mu - lo], [hi - mu]], fmt="none", ecolor=INK,
                        elinewidth=.55, capsize=1.4, capthick=.55, zorder=3)
        gain = 100 * (r["km"] - r["ks"]) / r["n"]
        top = max(wilson(r["ks"], r["n"])[1], wilson(r["km"], r["n"])[1]) + 2.2
        ax.plot([x - w / 2, x - w / 2, x + w / 2, x + w / 2], [top - 1.1, top, top, top - 1.1], color=MUTED, lw=.5)
        pooled = r["label"] == "Pooled"
        ax.text(x, top + .5, f"{gain:+.1f}" if pooled else f"{gain:+.0f}", ha="center", va="bottom",
                fontsize=6, color=MULTI, weight="bold" if pooled else "normal")
        ax.text(x, -.165, f"{r['tm'] / r['ts']:.1f}×", transform=ax.get_xaxis_transform(), ha="center",
                va="top", fontsize=6, color=MUTED, weight="bold" if pooled else "normal")
    ax.text(xs[0] - .6, -.165, "Tokens D/A", transform=ax.get_xaxis_transform(), ha="right", va="top",
            fontsize=6, color=MUTED)
    ax.set_xticks(xs); ax.set_xticklabels([WRAP[r["label"]] for r in data], fontsize=6, linespacing=1.15)
    ax.get_xticklabels()[-1].set_weight("bold")
    ax.axvline((xs[-2] + xs[-1]) / 2, color=GRID, lw=.6)
    ax.set(ylim=(0, 108), yticks=[0, 20, 40, 60, 80, 100], xlim=(xs[0] - .6, xs[-1] + .5), ylabel="Task pass rate (%)")
    ax.tick_params(axis="x", length=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.yaxis.grid(True, color=GRID, lw=.5); ax.set_axisbelow(True)
    ax.legend(handles=[Patch(color=SINGLE_LIGHT, label="Single agent"), Patch(color=MULTI, label="MetaSEQ")],
              loc="lower left", bbox_to_anchor=(0, 1.02), ncol=2, columnspacing=1.4, handlelength=1.1, borderaxespad=0)
    ax.text(1.0, 1.035, "Brackets: gain (percentage points)", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6, color=MULTI)


def outcomes(ax):
    with open(SUMMARY / "per_cell.csv") as f:
        cells = list(csv.DictReader(f))
    pairs = {}
    for c in cells:
        pairs.setdefault((c["model"], c["task"]), {})[c["topology"]] = int(c["all_turns"])
    n = {"both": 0, "multi": 0, "single": 0, "neither": 0}
    for p in pairs.values():
        n["both" if p["single"] and p["multi"] else "multi" if p["multi"] else "single" if p["single"] else "neither"] += 1
    total = sum(n.values())
    segs = [("Both correct", n["both"], "#E4E6E9", INK), ("MetaSEQ only", n["multi"], MULTI, "white"),
            ("Single agent only", n["single"], VOTE, "white"), ("Both wrong", n["neither"], SINGLE, "white")]
    left = 0
    for name, k, colour, tc in segs:
        ax.barh(0, k, left=left, height=.5, color=colour, edgecolor="white", lw=.6)
        if k / total > .06:
            ax.text(left + k / 2, 0, str(k), ha="center", va="center", fontsize=6.3, color=tc)
        else:   # too narrow for a label inside: lead it out above the bar
            ax.annotate(str(k), (left + k / 2, .25), (left + k / 2, .7), ha="center", va="bottom", fontsize=6.3,
                        color=INK, arrowprops=dict(arrowstyle="-", lw=.5, color=INK, shrinkA=0, shrinkB=0))
        left += k
    ax.set(xlim=(0, total), ylim=(-1.4, 1.15)); ax.axis("off")
    ax.legend(handles=[Patch(color=c, label=f"{nm} ({100 * k / total:.0f}%)") for nm, k, c, _ in segs],
              loc="upper center", bbox_to_anchor=(.5, .25), ncol=4, columnspacing=1.2, handlelength=1.1, fontsize=6.3)


def main():
    fig = plt.figure(figsize=(WIDTH, 96 * MM))   # 96 mm: Fig. 3 and Table 1 share a float page
    axb = fig.add_axes([.105, .40, .875, .48])
    bars(axb)
    panel(fig, "a", .012, .975, "Task pass rate by backbone")
    axc = fig.add_axes([.105, .02, .875, .17])
    outcomes(axc)
    panel(fig, "b", .012, .215, "Outcome of the 350 paired backbone–task cells")
    save(fig, OUT)


if __name__ == "__main__":
    main()
