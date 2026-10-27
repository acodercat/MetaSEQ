"""Fig. 4, experiment 2: the registered 2 x 2 of decomposition and verification, with the voted
baseline and the exploratory delegation arms. (a) Task pass rate of the four core arms and G on
every backbone and pooled, 95% intervals from 10,000 task resamples (seed 20260929). (b) The
pooled effects: verification and decomposition main effects, their interaction, D - B, and the
delegation contrasts (exploratory). (c) Pooled accuracy against tokens per correct task for every
arm; arrows join each configuration to the same one with the verifier. (d) Reasoning mode off and
on, single agent and MetaSEQ, on the two models run both ways.

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
# one palette: grey for the single agent, blue for the fixed roles; the verified arm of each is the full
# colour, the unverified one the light tint; orange for the voted baseline; delegation arms are squares
COLOUR = {rt.A: SINGLE_LIGHT, rt.B: SINGLE, rt.C: MULTI_LIGHT, rt.D: MULTI, rt.G: VOTE,
          rt.F: MULTI_LIGHT, rt.FV: MULTI}
NAME = {rt.A: "A  single agent", rt.B: "B  single agent + verifier", rt.C: "C  fixed roles",
        rt.D: "D  fixed roles + verifier (MetaSEQ)", rt.G: "G  single agent, three runs voted",
        rt.F: "F  delegation", rt.FV: "F+V  delegation + verifier"}


def task_ci(per_task: np.ndarray, draws: np.ndarray) -> tuple[float, float]:
    bs = per_task[draws].mean(axis=1)
    return 100 * np.percentile(bs, 2.5), 100 * np.percentile(bs, 97.5)


def accuracy_panel(ax):
    arms = [rt.A, rt.B, rt.C, rt.D, rt.G]
    means = {arm: rt.arm_task_means(arm) for arm in arms}
    models = rt.models(); cols = models + ["pooled"]
    n = len(means[rt.A])
    draws = np.random.default_rng(20260929).integers(0, n, (10_000, n))
    xs = np.arange(len(cols), dtype=float); xs[-1] += .3
    w = .16
    pm = rt.per_model_effects(); fx = rt.factorial()
    for x, m in zip(xs, cols):
        tops = []
        for k, arm in enumerate(arms):
            vals = means[arm][m].to_numpy()
            mu = 100 * vals.mean(); lo, hi = task_ci(vals, draws)
            ax.bar(x + (k - 2) * w, mu, width=w * .88, color=COLOUR[arm], zorder=2)
            ax.errorbar(x + (k - 2) * w, mu, yerr=[[mu - lo], [hi - mu]], fmt="none", ecolor=INK,
                        elinewidth=.5, capsize=1.2, capthick=.5, zorder=3)
            tops.append(hi)
        if m == "pooled":
            ver, dec = fx.loc["verification", "estimate_pp"], fx.loc["decomposition", "estimate_pp"]
        else:
            ver, dec = pm.loc[m, "verification_pp"], pm.loc[m, "decomposition_pp"]
        top = max(tops) + 1.5
        ver, dec = (0.0 if abs(v) < .05 else v for v in (ver, dec))   # no "-0.0"
        ax.text(x, top, f"verification {ver:+.1f}\ndecomposition {dec:+.1f}", ha="center", va="bottom",
                fontsize=5.4, color=INK, linespacing=1.1, weight="bold" if m == "pooled" else "normal")
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{k + 1}\n{SHORT[m]}" if m != "pooled" else "\nPooled" for k, m in enumerate(cols)],
                       fontsize=6, linespacing=1.15)
    for t, m in zip(ax.get_xticklabels(), cols):
        if m == "pooled":
            t.set_weight("bold")
    ax.axvline((xs[-2] + xs[-1]) / 2, color=GRID, lw=.6)
    ax.set(ylim=(0, 116), yticks=[0, 20, 40, 60, 80, 100], xlim=(xs[0] - .5, xs[-1] + .5),
           ylabel="Task pass rate (%)")
    ax.tick_params(axis="x", length=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.yaxis.grid(True, color=GRID, lw=.5); ax.set_axisbelow(True)
    ax.legend(handles=[Patch(color=COLOUR[a], label=NAME[a]) for a in arms],
              loc="lower left", bbox_to_anchor=(0, 1.02), ncol=5, columnspacing=1.0, handlelength=1.1,
              borderaxespad=0, fontsize=5.9)


def effects_panel(ax):
    """Pooled effects as a forest plot: the registered 2 x 2 and D - B, then the exploratory delegation
    contrasts below a rule."""
    fx, cc, dc = rt.factorial(), rt.core_contrasts(), rt.delegation_contrasts()
    rows = [("Verification", fx.loc["verification"], True), ("Decomposition", fx.loc["decomposition"], True),
            ("Interaction", fx.loc["interaction"], True), ("D − B", cc.loc["H2c"], True),
            None,
            ("F − A", dc.loc["F-A"], False), ("F+V − F", dc.loc["FV-F"], False),
            ("F+V − B", dc.loc["FV-B"], False), ("F+V − D", dc.loc["FV-D"], False)]
    y = 0
    ys, labels = [], []
    for row in rows:
        if row is None:
            ax.axhline(y, color=GRID, lw=.6); y += 1; continue
        label, r, core = row
        est, lo, hi = (r["estimate_pp"], r["lo_pp"], r["hi_pp"]) if "estimate_pp" in r else (r.delta_pp, r.lo_pp, r.hi_pp)
        ax.plot([lo, hi], [y, y], color=INK if core else MUTED, lw=1.0, zorder=2)
        ax.plot(est, y, "o", ms=4.2, color=INK if core else "white", mec=INK if core else MUTED, mew=.8, zorder=3)
        ax.text(10.6, y, f"{est:+.1f} [{lo:+.1f}, {hi:+.1f}]", fontsize=5.8, va="center", ha="left",
                color=INK if core else MUTED)
        ys.append(y); labels.append(label); y += 1
    ax.axvline(0, color=MUTED, lw=.6, ls=(0, (3, 2)))
    ax.set(xlim=(-9, 17.5), ylim=(y - .4, -.7), xticks=[-8, -4, 0, 4, 8], yticks=ys, yticklabels=labels,
           xlabel="Effect on task pass rate (percentage points)")
    ax.text(10.6, 4, "exploratory", fontsize=5.6, color=MUTED, va="center", ha="left", style="italic")
    clean_axis(ax, grid="x", left=False)
    ax.tick_params(axis="y", length=0, labelsize=6.2)


def cost_panel(ax):
    """Pooled accuracy against tokens per correct task, every arm; arrows from each configuration to the
    same one with the verifier."""
    acc = rt.arm_accuracy().loc["pooled"]; tok = rt.tokens_per_correct().loc["pooled"] / 1e3
    marker = {rt.A: "o", rt.B: "o", rt.C: "o", rt.D: "o", rt.F: "s", rt.FV: "s", rt.G: "D"}
    for a, b in ((rt.A, rt.B), (rt.C, rt.D), (rt.F, rt.FV)):
        ax.annotate("", (tok[b], acc[b]), (tok[a], acc[a]),
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=.7, shrinkA=4, shrinkB=4, mutation_scale=7), zorder=1)
    offsets = {rt.A: (-4, -7), rt.B: (6, -3), rt.C: (6, -4), rt.D: (6, -3), rt.F: (6, -5), rt.FV: (6, 1), rt.G: (6, -4)}
    for arm in [rt.A, rt.B, rt.C, rt.D, rt.F, rt.FV, rt.G]:
        ax.plot(tok[arm], acc[arm], marker[arm], ms=5, color=COLOUR[arm], mec=INK, mew=.4, zorder=3)
        ax.annotate(rt.ARM_LABELS[arm], (tok[arm], acc[arm]), xytext=offsets[arm], textcoords="offset points",
                    fontsize=6.2, color=INK, va="center", ha="left" if offsets[arm][0] > 0 else "right")
    ax.set(xlim=(120, 580), ylim=(75.5, 86.5), xticks=[200, 300, 400, 500], yticks=[76, 78, 80, 82, 84, 86],
           xlabel="Tokens per correct task (thousands)", ylabel="Task pass rate (%)")
    clean_axis(ax, grid="y", left=True)
    ax.text(.03, .96, "arrow: the verifier added", transform=ax.transAxes, ha="left", va="top", fontsize=5.8, color=MUTED)


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
        ax.text(float(xs.mean()), 102.5, rt.LABELS[model], ha="center", va="top", fontsize=6.3)
    ax.set(xlim=(-.5, 4.7), ylim=(50, 103), xticks=[0, 1, 3.2, 4.2], xticklabels=["Off", "On", "Off", "On"],
           yticks=[50, 75, 100], xlabel="Reasoning mode", ylabel="Task pass rate (%)")
    clean_axis(ax, grid="y", left=True)
    ax.legend(handles=[Line2D([], [], color=SINGLE, ls=(0, (3, 2)), marker="o", mfc="white", ms=4, label="A"),
                       Line2D([], [], color=MULTI, marker="o", ms=4, label="D")],
              loc="lower right", fontsize=6, frameon=False, handlelength=1.6)


def main():
    fig = plt.figure(figsize=(WIDTH, 162 * MM))
    axa = fig.add_axes([.07, .56, .915, .35])
    accuracy_panel(axa)
    panel(fig, "a", .008, .985, "Task pass rate by backbone")
    axb = fig.add_axes([.12, .085, .255, .33])
    effects_panel(axb)
    panel(fig, "b", .008, .455, "Pooled effects")
    axc = fig.add_axes([.475, .085, .22, .33])
    cost_panel(axc)
    panel(fig, "c", .415, .455, "Accuracy against cost")
    axd = fig.add_axes([.775, .085, .21, .33])
    reasoning_panel(axd)
    panel(fig, "d", .72, .455, "Reasoning mode")
    save(fig, OUT)


if __name__ == "__main__":
    main()
