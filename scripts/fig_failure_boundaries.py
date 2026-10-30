"""Failure boundaries, subgroup sensitivity and the linked evidence table."""
import html
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch, Rectangle
import numpy as np

import failure_evidence as fe
import replication_tables as rt
from error_messages import ORDER
from data_figure_style import (setup, save, panel, clean_axis, WIDTH, MM,
                               INK, MUTED, GRID, SINGLE, MULTI, VOTE, PALE)

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "manuscript/figures"
TEX = ROOT / "manuscript/tex"
setup()


def task_gains(ax):
    """Per-task gain D - A over the 24 paired runs of each task (8 backbones x 3 repeats), ranked."""
    o = rt.outcomes(); o["ok"] = o.passed.astype(float)
    t = o.groupby(["task", "arm"]).ok.mean().unstack()
    d = (100 * (t[rt.D] - t[rt.A])).sort_values(ascending=False)
    x = np.arange(len(d))
    colours = [MULTI if v > 0 else VOTE if v < 0 else GRID for v in d]
    ax.bar(x, d.to_numpy(), width=.82, color=colours, zorder=2)
    ax.axhline(0, color=MUTED, lw=.6)
    ax.axhline(d.mean(), color=INK, lw=.7, ls=(0, (3, 2)))
    pos, neg, tie = int((d > 0).sum()), int((d < 0).sum()), int((d == 0).sum())
    ax.text(pos - 1, d.mean() + 2, f"mean {d.mean():+.1f}", ha="right", va="bottom", fontsize=6, color=INK)
    for xx, txt, col in ((pos / 2, f"{pos} tasks higher under MetaSEQ", MULTI),
                         (pos + tie / 2, f"{tie} equal", MUTED),
                         (pos + tie + neg / 2, f"{neg} lower", VOTE)):
        ax.text(xx, 1.04, txt, transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=6, color=col)
    for edge in (pos - .5, pos + tie - .5):
        ax.axvline(edge, color=GRID, lw=.6, zorder=1)
    # the three tasks of Supplementary Note 3
    for (task, _), label in zip(rt.CASES, ("Meteorological adjustment", "Ozone season", "O\u2093 conservation")):
        i = d.index.get_loc(task); v = d.iloc[i]
        ax.annotate(label, (i, v), xytext=(i + 6, v + 14) if v >= 0 else (i - 8, v), textcoords="data",
                    fontsize=5.8, color=INK, ha="left" if v >= 0 else "right", va="center",
                    arrowprops=dict(arrowstyle="-", color=INK, lw=.5, shrinkA=0, shrinkB=1))
    ax.set(xlim=(-1, len(d)), ylim=(d.min() - 4, d.max() + 4), xticks=[], ylabel="D − A (points)")
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.yaxis.grid(True, color=GRID, lw=.5); ax.set_axisbelow(True)
    ax.set_xlabel("The 111 tasks, ranked by gain", labelpad=3)


def failures(counts, representative, states, cases):
    """Fig. 5: (a) per-task gain; (b) error classes recovered and introduced; (c) shared wrong outputs."""
    fig = plt.figure(figsize=(WIDTH, 205 * MM))
    panel(fig, "a", .025, .99, "Gain by task")
    task_gains(fig.add_axes([.105, .815, .875, .15]))
    # ---- b: recovered / introduced by error class ------------------------------------------
    panel(fig, "b", .025, .755, "Errors recovered and introduced")
    ax = fig.add_axes([.245, .585, .33, .14])
    labels = ["Required output missing", "Reported error \u226550%", "Reported error 2\u201350%",
              "Reported error <2%", "Other / unparsed"]
    for y, key in enumerate(ORDER):
        for offset, direction, color in [(-.19, "fixed", MULTI), (.19, "broken", VOTE)]:
            n = counts.loc[key, direction]
            ax.barh(y + offset, n, .32, color=color, zorder=3)
            ax.text(n + 2.5, y + offset, str(n), va="center", fontsize=6.7, color=INK)
    ax.set(xlim=(0, 143), xticks=[0, 50, 100], ylim=(4.6, -.6),
           yticks=range(5), yticklabels=labels, xlabel="Discordant task\u2013repeat pairs")
    ax.tick_params(axis="y", labelsize=6.6)
    clean_axis(ax)
    ax.legend(handles=[Patch(fc=MULTI, label="Recovered by MetaSEQ"), Patch(fc=VOTE, label="Introduced by MetaSEQ")],
              loc="lower left", bbox_to_anchor=(-.01, 1.03), ncol=2,
              handlelength=1.1, columnspacing=1.0, fontsize=6.5, borderaxespad=0)

    # ---- d: the two main effects by how well the single agent did on the task ---------------
    panel(fig, "d", .605, .755, "Effects by single-agent accuracy")
    ax = fig.add_axes([.69, .585, .285, .14])
    bb = rt.effects_by_baseline()
    bins = [b for b in bb.index if b != "all"]
    x = np.arange(len(bins))
    for offset, effect, color, label in ((-.13, "verification", MULTI, "Verification"), (.13, "decomposition", VOTE, "Decomposition")):
        est = bb.loc[bins, f"{effect}_pp"].to_numpy()
        lo, hi = bb.loc[bins, f"{effect}_lo"].to_numpy(), bb.loc[bins, f"{effect}_hi"].to_numpy()
        ax.errorbar(x + offset, est, yerr=[est - lo, hi - est], fmt="o", color=color, ms=3.4, lw=.9, capsize=0, zorder=3, label=label)
        for xx, v in zip(x + offset, est):
            ax.text(xx + (.1 if offset > 0 else -.1), v, f"{v:+.1f}", fontsize=5.6, color=color, va="center",
                    ha="left" if offset > 0 else "right", zorder=4)
    ax.axhline(0, color=MUTED, lw=.6, ls=(0, (3, 2)))
    ax.set(xlim=(-.55, len(bins) - .45), xticks=x, ylim=(-5, 15), yticks=[-5, 0, 5, 10, 15], ylabel="Effect (points)")
    ax.set_xticklabels([f"{b.replace('<=', '≤').replace('-', '–')}\n(n = {int(bb.loc[b, 'tasks'])})" for b in bins], fontsize=6.3)
    ax.set_xlabel("Single agents passing the task on repeat 1", labelpad=2)
    clean_axis(ax, grid="y", left=True)
    ax.legend(loc="upper right", ncol=1, handlelength=1.1, fontsize=6.3, borderaxespad=.2, handletextpad=.4, frameon=False)

    # ---- c: shared wrong outputs across model families ------------------------------------
    panel(fig, "c", .025, .528, "Shared wrong outputs across model families")
    ax = fig.add_axes([.305, .10, .665, .338])
    # each cell holds the three repeats side by side: passed, failed otherwise, shared wrong value
    colors = {0: "#F3F4F6", 1: MUTED, 2: VOTE}
    for y in range(len(representative)):
        for x in range(16):
            for n in range(3):
                ax.add_patch(Rectangle((x - .5 + n / 3, y - .5), 1 / 3, 1, facecolor=colors[states[y, x, n]],
                                       edgecolor="white", lw=.3, zorder=2))
    ax.set(xlim=(-.5, 15.5), ylim=(len(representative) - .5, -.5), yticks=range(len(representative)),
           yticklabels=[f"{r.task_id}  {fe.TASK_LABELS[r.task]}" for r in representative.itertuples()],
           xticks=range(16), xticklabels=["A", "D"] * 8)
    ax.xaxis.tick_top()
    ax.tick_params(length=0, pad=3, labelsize=6.5)
    for i, label in enumerate(ax.get_xticklabels()):
        label.set_color(SINGLE if i % 2 == 0 else MULTI)
        label.set_weight("bold")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(-.5, 16), minor=True)
    ax.set_yticks(np.arange(-.5, len(representative)), minor=True)
    ax.grid(which="minor", color="white", lw=1.2, zorder=3)
    ax.tick_params(which="minor", length=0)
    for x in (5.5, 11.5, 13.5):
        ax.axvline(x, color="white", lw=3)
    names = ["27B", "27B\nreasoning", "3.8-Flash", "V4-Flash", "V4-Flash\nreasoning", "Pro", "GPT-6\nLuna", "Sonnet\n5.5"]
    for j, name in enumerate(names):
        ax.text((j + .5) / 8, 1.05, name, transform=ax.transAxes, ha="center", va="bottom",
                fontsize=6.1, color=INK, linespacing=1.1)
    for left, right, name in [(0, 6, "Qwen"), (6, 12, "DeepSeek"), (12, 14, "OpenAI"), (14, 16, "Anthropic")]:
        ax.text((left + right) / 32, 1.21, name, transform=ax.transAxes, ha="center", va="bottom",
                fontsize=7, weight="bold")
        ax.plot([left / 16 + .006, right / 16 - .006], [1.195, 1.195], transform=ax.transAxes,
                color=MUTED, lw=.6, clip_on=False)
    fig.legend(handles=[Patch(fc=colors[0], ec=GRID, lw=.4, label="Turn passed"),
                        Patch(fc=colors[2], label="Shared wrong value returned"),
                        Patch(fc=colors[1], label="Failed otherwise")],
               loc="lower left", bbox_to_anchor=(.30, .028), ncol=3,
               title="Each cell: the three repeats of the turn that stores the output",
               title_fontsize=6.5, fontsize=6.5, handlelength=1.2, columnspacing=1.4)
    fig.text(.305, .010, "One output per task; all 30 qualifying outputs and source records in Supplementary Table 21.",
             fontsize=5.9, color=MUTED)
    save(fig, FIG / "failure_boundaries.pdf")


def robustness(frame):
    fig = plt.figure(figsize=(WIDTH, 95 * MM))
    ax = fig.add_axes([.37, .17, .36, .76])
    y = np.array([0, 1.65, 2.65, 4.3, 5.3, 6.3, 7.95, 8.95, 9.95])
    for i, r in enumerate(frame.itertuples()):
        ax.plot([r.lo, r.hi], [y[i], y[i]], color=MULTI, lw=1.2)
        ax.plot(r.delta, y[i], "D" if i == 0 else "o", color=MULTI, ms=4.8)
        ax.text(1.04, y[i], f"{r.delta:+.1f}  [{r.lo:+.1f}, {r.hi:+.1f}]",
                transform=ax.get_yaxis_transform(), va="center", fontsize=7,
                weight="bold" if i == 0 else "normal")
        ax.text(-.10, y[i], str(r.tasks), transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=7, color=MUTED)
    ax.axhspan(-.5, .5, color=PALE, zorder=0)
    ax.axvline(0, color=MUTED, lw=.8, ls=(0, (3, 3)))
    ax.set(xlim=(-5, 17), xticks=[-5, 0, 5, 10, 15], ylim=(10.65, -.65), yticks=[],
           xlabel="D − A (percentage points)")
    clean_axis(ax)
    # Put row labels in a separate figure column so n and labels never collide.
    for yy, r in zip(y, frame.itertuples()):
        fy = .17 + .76*(10.65-yy)/(10.65+.65)
        fig.text(.025, fy, r.label, va="center", fontsize=7,
                 weight="bold" if r.group == "Reference" else "normal")
    for yy in (.85, 3.5, 7.15):
        ax.axhline(yy, color=GRID, lw=.6)
    fig.text(.334, .955, "Tasks", ha="right", fontsize=6.5, color=MUTED)
    fig.text(.745, .955, "D \u2212 A [95% interval]", fontsize=6.5, color=MUTED)
    save(fig, FIG / "robustness.pdf")


def tex_escape(text):
    return str(text).replace("_", r"\_\allowbreak ").replace("%", r"\%")


def ascii_label(text):
    for a, b in [("₂", "2"), ("₃", "3"), ("₅", "5"), ("–", "--")]:
        text = text.replace(a, b)
    return text


def evidence_table(shared, records):
    TEX.mkdir(exist_ok=True)
    header = r"""\clearpage
\begingroup\singlespacing
{\fontsize{9}{11}\selectfont\sffamily\raggedright
\noindent\textbf{Supplementary Table~21. Shared wrong numeric outputs across model families.}
Each row is one task--output pair selected after inspection of the results:
at least eight parsed wrong outputs, a modal wrong value accounting for at least half,
and that value returned by at least three configurations from at least two families.
Values are grouped after rounding to four decimal places. T01--T18 match Fig.~5c;
E01--E30 identify rows in the accompanying source-data CSVs.
Reference values are those recorded in validator messages, printed to six significant figures;
they were not recomputed from a fresh database snapshot for this analysis.
A and D count occurrences of the shared wrong value, not all failures.
Q = Qwen, D = DeepSeek, O = OpenAI; the number in parentheses counts configurations.
All matching run paths, messages, turns and unrounded reference values are written by
\path{scripts/failure_evidence.py} from the deposited runs.
\par}
\begingroup
\sffamily
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.2}
\fontsize{8}{10}\selectfont
\begin{longtable}{@{}>{\raggedright\arraybackslash}p{.43\textwidth}
>{\raggedleft\arraybackslash}p{.105\textwidth}
>{\raggedleft\arraybackslash}p{.105\textwidth}
>{\raggedright\arraybackslash}p{.14\textwidth}rr@{}}
\toprule
Task / output & Reference & Shared\newline value & Families\newline (configs) & A & D \\
\midrule
\endfirsthead
\multicolumn{6}{@{}l}{\textbf{Supplementary Table 21 (continued)}}\\[3pt]
\toprule
Task / output & Reference & Shared\newline value & Families\newline (configs) & A & D \\
\midrule
\endhead
\midrule
\multicolumn{6}{r@{}}{\footnotesize Continued on next page}\\
\endfoot
\bottomrule
\endlastfoot
"""
    rows = []
    previous = None
    short = {"qwen": "Q", "deepseek": "D", "openai": "O", "anthropic": "A"}
    for r in shared.itertuples():
        if previous is not None and previous != r.task_id:
            rows.append(r"\addlinespace[4pt]")
        reference = ", ".join(f"{v:.6g}" for v in r.reference_values)
        first = (r"\textbf{" + r.evidence_id + " / " + r.task_id + " " +
                 tex_escape(ascii_label(fe.TASK_LABELS[r.task])) + r"}\newline " +
                 r"{\fontsize{7}{9}\selectfont\texttt{" + tex_escape(r.variable) + "}}")
        families = "/".join(short[v] for v in r.families.split(","))
        rows.append(f"{first} & {reference} & {r.wrong_value:.6g} & {families} ({r.n_configurations}) & {r.A_count} & {r.D_count} " + r"\\")
        if r.evidence_id == "E16":
            rows.append(r"\pagebreak")
        previous = r.task_id
    footer = r"""
\end{longtable}
\endgroup
{\fontsize{8}{10}\selectfont\raggedright
\textbf{Interpretation.} Selection establishes coincidence of recorded wrong outputs,
not a shared causal mechanism. For T01, inspected transcripts document pooling hourly
exceedances across stations before applying the annual allowance; the benchmark validator
instead applies the allowance to each station-year. Other rows remain output-level
observations without a causal-route assignment. Tasks were selected using the same
outcomes displayed here; their lower accuracy is descriptive, not an independent test.
There were no tied modal values among these selected outputs.
\par}
\endgroup
"""
    (TEX / "table_shared_errors.tex").write_text(header + "\n".join(rows) + footer)
    # A searchable, linked companion keeps long evidence paths out of the printed table.
    page = ['<!doctype html><meta charset="utf-8"><title>Shared-error evidence</title>',
            '<style>body{font:15px/1.6 system-ui;margin:40px;color:#253746}table{border-collapse:collapse;width:100%}th,td{padding:10px;border-bottom:1px solid #dce5e2;text-align:left;vertical-align:top}th{background:#edf4f1}code{overflow-wrap:anywhere}details{margin:10px 0}a{color:#238779}</style>',
            '<h1>Shared wrong outputs · evidence records</h1><p>Exploratory output coincidence; reference values from archived validator messages. No fresh ground-truth recomputation.</p>',
            '<table><tr><th>Evidence / task / output</th><th>Reference → wrong</th><th>Families</th><th>A / D</th><th>Source records</th></tr>']
    for r in shared.itertuples():
        subset = records[records.evidence_id == r.evidence_id]
        sources = []
        for v in subset.itertuples():
            label = f"{'A' if v.arm == rt.A else 'D'} · {v.model} · r{v.repeat} · turn {v.turn}"
            sources.append(f'<li><a href="../../../{html.escape(v.path)}">{html.escape(label)}</a><br><code>{html.escape(v.message)}</code></li>')
        page.append(f'<tr id="{r.evidence_id}"><td><b>{r.evidence_id} | {r.task_id}</b><br>{html.escape(r.task)}<br><code>{html.escape(r.variable)}</code></td>'
                    f'<td>{html.escape(str(r.reference_values))} → {r.wrong_value:g}</td><td>{r.families}<br>{r.n_configurations} configurations</td>'
                    f'<td>{r.A_count} / {r.D_count}</td><td><details><summary>{len(subset)} records</summary><ul>{"".join(sources)}</ul></details>{html.escape(r.evidence_status)}</td></tr>')
    page.append('</table>')
    (fe.OUT / "evidence.html").write_text("\n".join(page))


def main():
    counts, shared, representative, records, matrix, states, robust, cases = fe.build()
    failures(counts, representative, states, cases)
    robustness(robust)
    evidence_table(shared, records)


if __name__ == "__main__":
    main()
