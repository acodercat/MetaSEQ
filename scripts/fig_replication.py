"""Fig. 4, experiment 2. (a) Task pass rate of the single agent (A), the voted three-run baseline
(G) and MetaSEQ (D) on every backbone and pooled, with 95% intervals from 10,000 task resamples
(seed 20260929), the gain D - A above each group and D's token multiple of A below its label.
(b) Turn pass rate after a failed and after a passed turn, and on third turns. (c) Reasoning mode
off and on, single agent and MetaSEQ, on the two models run both ways.

    uv run --project phase3_replication --with matplotlib python scripts/fig_replication.py
"""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import replication_tables as rt
from data_figure_style import (setup, save, panel, clean_axis, WIDTH, MM, INK, MUTED,
                               GRID, SINGLE, SINGLE_LIGHT, MULTI, MULTI_LIGHT, VOTE)
setup()
OUT = Path(__file__).resolve().parents[1] / "manuscript/figures/replication.pdf"
SHORT = {"qwen3.8-27b": "Qwen3.8-\n27B", "qwen3.8-flash": "Qwen3.8-\nFlash", "gpt-6-luna": "GPT-6\nLuna",
         "deepseek-v4-flash": "DeepSeek-\nV4-Flash", "qwen3.8-27b-thinking": "Qwen3.8-27B\n(reasoning)",
         "deepseek-v4-flash-thinking": "DeepSeek-V4-\nFlash (reasoning)", "deepseek-v4-pro-0813": "DeepSeek-\nV4-Pro",
         "claude-sonnet-5-5": "Claude\nSonnet 5.5", "pooled": "Pooled"}
G_COLOR = "#F2C29B"          # light orange for the voted baseline bar, so blue stays the focus


def task_ci(per_task: np.ndarray, draws: np.ndarray) -> tuple[float, float]:
    bs = per_task[draws].mean(axis=1)
    return 100 * np.percentile(bs, 2.5), 100 * np.percentile(bs, 97.5)


def accuracy_panel(ax):
    o = rt.outcomes(); o["ok"] = o.passed.astype(float)
    tasks = sorted(o.task.unique())
    a = o[o.arm == rt.A].groupby(["model", "task"]).ok.mean().unstack(0).reindex(tasks)
    d = o[o.arm == rt.D].groupby(["model", "task"]).ok.mean().unstack(0).reindex(tasks)
    import json
    g = {}
    for path in (rt.PHASE3 / "results").glob(f"*/*/*/{rt.G}/*/r1/programmatic_verification.json"):
        card = json.loads(path.read_text())
        g[(path.parts[-3], path.parts[-5])] = float(all(t.get("success") for c in card["conversations"] for t in c["turns"]))
    models = rt.models()
    gm = __import__("pandas").DataFrame({m: {t: g[(m, t)] for t in tasks} for m in models}).reindex(tasks)
    a, d = a[models], d[models]
    a["pooled"], d["pooled"], gm["pooled"] = a.mean(axis=1), d.mean(axis=1), gm.mean(axis=1)
    con = rt.contrasts().set_index("scope")
    acc = rt.accuracy().set_index("model")
    draws = np.random.default_rng(20260929).integers(0, len(tasks), (10_000, len(tasks)))
    cols = models + ["pooled"]
    xs = np.arange(len(cols), dtype=float); xs[-1] += .3
    w = .2
    # MetaSEQ before its verifier: the pre-verifier cards, three repeats averaged per task like D
    bv = {}
    for path in (rt.PHASE3 / "results").glob(f"*/*/*/{rt.D_BEFORE}/*/r*/programmatic_verification.json"):
        card = json.loads(path.read_text())
        bv.setdefault((path.parts[-3], path.parts[-5]), []).append(
            float(all(t.get("success") for c in card["conversations"] for t in c["turns"])))
    bm = __import__("pandas").DataFrame({m: {t: sum(bv[(m, t)]) / len(bv[(m, t)]) for t in tasks} for m in models}).reindex(tasks)
    bm["pooled"] = bm.mean(axis=1)
    for x, m in zip(xs, cols):
        for dx, frame, colour in ((-1.5 * w, a, SINGLE_LIGHT), (-.5 * w, bm, MULTI_LIGHT), (.5 * w, gm, G_COLOR), (1.5 * w, d, MULTI)):
            vals = frame[m].to_numpy()
            mu = 100 * vals.mean(); lo, hi = task_ci(vals, draws)
            ax.bar(x + dx, mu, width=w * .9, color=colour, zorder=2)
            ax.errorbar(x + dx, mu, yerr=[[mu - lo], [hi - mu]], fmt="none", ecolor=INK,
                        elinewidth=.55, capsize=1.4, capthick=.55, zorder=3)
        gain = con.loc[m, "delta_pp"]
        top = 100 * max(np.percentile(a[m].to_numpy()[draws].mean(axis=1), 97.5),
                        np.percentile(d[m].to_numpy()[draws].mean(axis=1), 97.5)) + 2.2
        ax.plot([x - 1.5 * w, x - 1.5 * w, x + 1.5 * w, x + 1.5 * w], [top - 1.1, top, top, top - 1.1], color=MUTED, lw=.5)
        ax.text(x, top + .5, f"{gain:+.1f}", ha="center", va="bottom", fontsize=6,
                color=MULTI, weight="bold" if m == "pooled" else "normal")
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{k + 1}\n{SHORT[m]}" if m != "pooled" else "\nPooled" for k, m in enumerate(cols)],
                       fontsize=6, linespacing=1.15)
    tok_y = -.215   # axes fraction, below the index and two-line model labels
    for x, m in zip(xs, cols):
        ax.text(x, tok_y, f"{acc.loc[m, 'tokens_D'] / acc.loc[m, 'tokens_A']:.1f}×",
                transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=6, color=MUTED,
                weight="bold" if m == "pooled" else "normal")
    ax.text(xs[0] - .55, tok_y, "Tokens D/A", transform=ax.get_xaxis_transform(), ha="right", va="top",
            fontsize=6, color=MUTED)
    for t, m in zip(ax.get_xticklabels(), cols):
        if m == "pooled":
            t.set_weight("bold")
    ax.axvline((xs[-2] + xs[-1]) / 2, color=GRID, lw=.6)
    ax.set(ylim=(0, 108), yticks=[0, 20, 40, 60, 80, 100], xlim=(xs[0] - .55, xs[-1] + .5),
           ylabel="Task pass rate (%)")
    ax.tick_params(axis="x", length=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.yaxis.grid(True, color=GRID, lw=.5); ax.set_axisbelow(True)
    ax.legend(handles=[Patch(color=SINGLE_LIGHT, label="Single agent (A)"),
                       Patch(color=MULTI_LIGHT, label="MetaSEQ before its verifier"),
                       Patch(color=G_COLOR, label="Single agent, three runs voted (G)"),
                       Patch(color=MULTI, label="MetaSEQ (D)")],
              loc="lower left", bbox_to_anchor=(0, 1.02), ncol=4, columnspacing=1.2, handlelength=1.1,
              borderaxespad=0, fontsize=6.5)
    ax.text(1.0, 1.035, "Brackets: D − A (percentage points)", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6, color=MULTI)


def cost_panel(ax):
    """MetaSEQ against the compute-matched baseline G, per backbone: D - G (points, 95% task-resampled
    interval) against D's tokens as a multiple of G's (G = three single-agent runs, tokens summed)."""
    vb = rt.vote_baseline().set_index("model")
    order = sorted(rt.models(), key=lambda m: vb.loc[m, "tokens_ratio"])
    ax.axhline(0, color=MUTED, lw=.7, ls=(0, (3, 2)))
    ax.axvline(1, color=MUTED, lw=.5, ls=(0, (1, 2)))
    ax.text(1.005, 19.5, "equal tokens", fontsize=5.6, color=MUTED, va="top")
    for m in order:
        r = vb.loc[m]
        ax.plot([r.tokens_ratio] * 2, [r.lo_pp, r.hi_pp], color=MULTI_LIGHT, lw=1.1, zorder=2)
        ax.plot(r.tokens_ratio, r.delta_pp, "o", ms=4.6, color=MULTI, zorder=3)
    p = vb.loc["pooled"]
    ax.plot([p.tokens_ratio] * 2, [p.lo_pp, p.hi_pp], color=INK, lw=1.2, zorder=4)
    ax.plot(p.tokens_ratio, p.delta_pp, "D", ms=5, color=INK, zorder=5)
    # number each point by its position in panel a (1 = leftmost backbone), so no names collide
    idx = {m: k + 1 for k, m in enumerate(rt.models())}
    for m in order:
        r = vb.loc[m]
        off = (0, -7.5) if m == "deepseek-v4-pro-0813" else (4.5, 0)
        ax.annotate(str(idx[m]), (r.tokens_ratio, r.delta_pp), xytext=off, textcoords="offset points",
                    fontsize=6, color=INK, va="center", ha="left" if off[0] else "center")
    ax.annotate("Pooled", (p.tokens_ratio, p.hi_pp), xytext=(0, 3), textcoords="offset points",
                fontsize=6, color=INK, weight="bold", va="bottom", ha="center")
    ax.set(xlim=(.7, 1.72), ylim=(-10, 20), xticks=[.8, 1.0, 1.2, 1.4, 1.6], yticks=[-10, -5, 0, 5, 10, 15, 20],
           xlabel="Tokens per task, D / G", ylabel="D − G (percentage points)")
    clean_axis(ax, grid="y", left=True)
    ax.text(.995, .97, "MetaSEQ ahead", transform=ax.transAxes, ha="right", va="top", fontsize=6, color=MULTI)
    ax.text(.995, .03, "Repetition ahead", transform=ax.transAxes, ha="right", va="bottom", fontsize=6, color=VOTE)


def multiturn_panel(ax):
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


def reasoning_panel(ax):
    tp = rt.thinking_pairs()
    for i, (model, r) in enumerate(tp.iterrows()):
        xs = np.array([0, 1]) + i * 3.2
        for off, on, colour, fill, ls in [("A", "A_reasoning", SINGLE, "white", (0, (3, 2))),
                                          ("D", "D_reasoning", MULTI, MULTI, "-")]:
            vs = [r[off], r[on]]
            ax.plot(xs, vs, marker="o", ms=4, mfc=fill, color=colour, lw=.9, ls=ls)
            for x, v in zip(xs, vs):
                on_a = off == "A" and x == xs[1]
                ax.annotate(f"{v:.1f}", (x, v), xytext=(6, -2) if on_a else (0, 5 if off == "D" else -9),
                            textcoords="offset points", ha="left" if on_a else "center", fontsize=6)
        ax.text(float(xs.mean()), 102.5, rt.LABELS[model],
                ha="center", va="top", fontsize=6.3)
    ax.set(xlim=(-.5, 4.7), ylim=(50, 103), xticks=[0, 1, 3.2, 4.2], xticklabels=["Off", "On", "Off", "On"],
           yticks=[50, 75, 100], xlabel="Reasoning mode", ylabel="Task pass rate (%)")
    clean_axis(ax, grid="y", left=True)


def main():
    fig = plt.figure(figsize=(WIDTH, 158 * MM))
    axa = fig.add_axes([.105, .535, .875, .37])
    accuracy_panel(axa)
    panel(fig, "a", .012, .975, "Task pass rate by backbone")
    axb = fig.add_axes([.105, .085, .43, .27])
    cost_panel(axb)
    panel(fig, "b", .012, .385, "MetaSEQ against three voted single-agent runs")
    axc = fig.add_axes([.665, .085, .315, .27])
    reasoning_panel(axc)
    panel(fig, "c", .585, .385, "Reasoning and orchestration")
    save(fig, OUT)


if __name__ == "__main__":
    main()
