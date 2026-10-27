"""Write the experiment-2 part of the MetaSEQ Supplementary Information,
manuscript/si_replication.tex (Notes 2-4, Tables 10-20) and manuscript/tex/table_repeats.tex
(Table 23) and table_delegation.tex (Table 24): the registered 2 x 2 of decomposition and
verification (arms A, B, C, D), the voted baseline G and the exploratory delegation arms (F, F+V)
on the 111-task suite. Numbers are read from the derived tables in phase3_replication/results/report/
(through `scripts/replication_tables.py`); prompts are read from the released files.

    uv run --project phase3_replication python scripts/si_replication.py
"""

from __future__ import annotations

import json
from pathlib import Path

import replication_tables
from replication_tables import PHASE3

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript" / "si_replication.tex"
ARMS = ["A", "B", "C", "D", "F", "F+V"]
ARM_NAMES = {"A": replication_tables.A, "B": replication_tables.B, "C": replication_tables.C,
             "D": replication_tables.D, "F": replication_tables.F, "F+V": replication_tables.FV}
ARM_DESC = {"A": "single agent",
            "B": "single agent, then the verifier",
            "C": "fixed roles: coordinator, four workers, synthesis",
            "D": "fixed roles, then the verifier (MetaSEQ)",
            "F": "delegation: a lead splits the turn and hands the pieces to sub-agents",
            "F+V": "delegation, then the verifier"}
BUDGET = {"A": "50", "B": "35 + 15", "C": "42 + 8", "D": "27 + 8 + 15", "F": "10 + 40", "F+V": "10 + 25 + 15"}
CORE = ["A", "B", "C", "D"]
MODELS = replication_tables.models()            # all eight backbones, by single-agent accuracy
FIRST_THREE = replication_tables.FIRST_THREE     # the backbones the three cases were read from
MODEL_LABELS = replication_tables.LABELS
THINKING_PAIRS = replication_tables.THINKING_PAIRS


def tex(s: str) -> str:
    return (str(s).replace("\\", "\\textbackslash{}").replace("_", "\\_").replace("%", "\\%")
            .replace("&", "\\&").replace("#", "\\#").replace("$", "\\$").replace("^", "\\^{}")
            .replace("~", "\\textasciitilde{}").replace("{", "\\{").replace("}", "\\}")
            .replace("<", "$<$").replace(">", "$>$").replace("|", "$|$")
            .replace(r"\_", r"\_\allowbreak ").replace("/", r"/\allowbreak "))


def prompt_tex(text: str) -> str:
    """Keep source line boundaries while allowing long lines to wrap in the PDF."""
    return "\n".join(r"\noindent " + tex(line) + r"\par" if line.strip() else r"\smallskip"
                     for line in text.splitlines())


def table(number: int, caption: str, header: list[str], rows: list[list[str]], spec: str,
          resize: bool = False) -> str:
    # Wrap headings and model variants instead of shrinking wide tables to tiny text.
    headings = {
        "accuracy (\\%)": r"\shortstack[r]{Accuracy\\(\%)}",
        "tokens/task (k)": r"\shortstack[r]{Tokens/task\\($\times10^3$)}",
        "tokens/correct (k)": r"\shortstack[r]{Tokens/correct\\($\times10^3$)}",
        "median steps": r"\shortstack[r]{Median\\steps}",
        "turns at cap": r"\shortstack[r]{Turns\\at cap}",
        "recovered/regressed": r"\shortstack[r]{Recovered/\\regressed}",
        "control (\\%)": r"\shortstack[r]{Control\\(\%)}", "treatment (\\%)": r"\shortstack[r]{Treatment\\(\%)}",
        "B (A $\\times$ 1, verified)": r"\shortstack[r]{B\\(A + verifier)}",
        "B $-$ G [95\\% interval]": r"\shortstack[r]{B $-$ G (pp)\\{[95\% interval]}}",
        "F $-$ A": r"\shortstack[l]{F $-$ A}", "F+V $-$ F": r"\shortstack[l]{F+V $-$ F}",
        "G (A $\\times$ 3, voted)": r"\shortstack[r]{G\\(A $\times$ 3)}",
        "D $-$ G [95\\% interval]": r"\shortstack[r]{D $-$ G (pp)\\{[95\% interval]}}",
        "tokens D / G": r"\shortstack[r]{Tokens\\D / G}",
        "temperature": "Temp.", "reasoning": "Reason.", "steps per turn": r"\shortstack[l]{Steps\\per turn}",
    }
    header = [headings.get(h, h[:1].upper() + h[1:]) for h in header]
    rows = [[cell.replace(" (reasoning)", r"\newline (reasoning)") if i == 0 else cell
             for i, cell in enumerate(row)] for row in rows]
    # Fixed-width first columns allow the long model names to wrap naturally.
    specs = {
        10: r"@{}p{.05\textwidth}p{.33\textwidth}p{.38\textwidth}p{.14\textwidth}@{}",
        11: r"@{}p{.24\textwidth}lrrrrrr@{}",
        12: r"@{}p{.2\textwidth}lrrrllll@{}",
        18: r"@{}p{.2\textwidth}rrrrllr@{}",
        19: r"@{}p{.22\textwidth}p{.21\textwidth}rp{.07\textwidth}p{.18\textwidth}p{.15\textwidth}@{}",
    }
    spec = specs.get(number, spec)
    spec = spec.replace("p{", r">{\raggedright\arraybackslash}p{")
    if number == 10:
        rows = [[cell.replace(r"\_", r"\_\allowbreak ") for cell in row] for row in rows]
    if number == 19:
        rows = [[cell.replace("-", r"-\allowbreak ") if i == 1 else cell
                 for i, cell in enumerate(row)] for row in rows]
    body = " \\\\\n".join(" & ".join(r) for r in rows)
    inner = (f"\\begin{{tabular}}{{{spec}}}\n\\toprule\n{' & '.join(header)} \\\\\n\\midrule\n"
             f"{body} \\\\\n\\bottomrule\n\\end{{tabular}}")
    if number == 14:
        # Accuracy and component gains belong in separate readable blocks.
        def block(indices, titles):
            body = " \\\\\n".join(" & ".join(row[i] for i in indices) for row in rows)
            return (r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrr@{}}" + "\n\\toprule\n"
                    + " & ".join(titles) + " \\\\\n\\midrule\n" + body + " \\\\\n\\bottomrule\n\\end{tabular*}")
        inner = block([0,1,2,3,4], ["Model", "A", "A, reasoning", "D", "D, reasoning"])
        inner += "\n\\par\\medskip\n" + block([0,5,6,7,8], ["Model", r"\shortstack[r]{Reasoning\\gain (pp)}", r"\shortstack[r]{Orchestration\\gain (pp)}", r"\shortstack[r]{Joint\\gain (pp)}", r"\shortstack[r]{Reasoning $-$ orchestration\\{[95\% interval]}}"])
    return (f"\\begin{{table}}[H]\n{{\\fontsize{{9}}{{11}}\\selectfont\\sffamily\\raggedright\n"
            f"\\noindent\\textbf{{Supplementary Table~{number}.}} {caption}\\par}}\n"
            f"\\vspace{{5pt}}\n\\centering\n\\fontsize{{8.5}}{{10.5}}\\selectfont\n"
            f"\\setlength{{\\tabcolsep}}{{2.5pt}}\\renewcommand{{\\arraystretch}}{{1.15}}\n{inner}\n\\end{{table}}\n\n")


def pct(x) -> str:
    return f"{100 * float(x):.1f}"


def pfmt(p) -> str:
    return "$<10^{-4}$" if float(p) == 0 else f"{float(p):.2g}"


def main() -> None:
    acc, con = replication_tables.accuracy(), replication_tables.contrasts()
    runs = replication_tables.outcomes()
    runs6 = replication_tables.study_outcomes()
    arm6 = replication_tables.arm_accuracy(); tpc6 = replication_tables.tokens_per_correct()
    parts: list[str] = []
    try:
        bf = replication_tables.bayes_factorial()
        bayes = ("fitted as registered (bambi/PyMC, four chains of 2,000 draws, seed 20260929) on the "
                 + f"{len(runs6[runs6.arm.isin(replication_tables.CORE)]):,} runs of the four core arms, it gives, on the probability scale, "
                 + f"verification {bf.loc['verification', 'pp']:+.1f} points (95\\% interval {bf.loc['verification', 'lo']:+.1f} to {bf.loc['verification', 'hi']:+.1f}), "
                 + f"decomposition {bf.loc['decomposition', 'pp']:+.1f} ({bf.loc['decomposition', 'lo']:+.1f} to {bf.loc['decomposition', 'hi']:+.1f}) "
                 + f"and an interaction of {bf.loc['interaction', 'pp']:+.1f} ({bf.loc['interaction', 'lo']:+.1f} to {bf.loc['interaction', 'hi']:+.1f}), "
                 + "the same conclusion as the bootstrap.")
    except FileNotFoundError:
        bayes = "BAYES PENDING"

    # ---------------- Note 2 ---------------------------------------------------------------
    parts.append(r"""\pagebreak
\section*{Supplementary Note 2: Pre-specification of experiment 2, and every departure from it}

Experiment 2 reports four core arms, the voting baseline and two exploratory arms of one pre-specified study of 111 tasks, six models in eight configurations and three repeats. The study's other registered arms, which carried analysis knowledge in their prompts, were not run. This note lists what was fixed in advance, what was changed and when, and where the analysis departs from the protocol.

\textbf{What was fixed before the confirmatory runs (2026-09-29).} The four core arms as a $2\times2$ of decomposition (C, D) and verification (B, D); the hypotheses H1 (D more accurate than A), H2 (the verification main effect larger than the decomposition main effect, both reported with their interaction) and H4 (tokens per correct task of B no higher than D's); the unit of analysis (a run, paired within a backbone on task and repeat, with tasks as the resampling unit); the primary model, a Bayesian mixed-effects logistic regression of a run's correctness on decomposition, verification and their interaction with task, backbone and task $\times$ backbone random intercepts; the task-resampled paired bootstrap (mean paired difference, 10,000 task resamples, seed 20260929) as the frequentist check of each contrast, Holm-corrected over the four core contrasts D $-$ A, B $-$ A, C $-$ A and D $-$ B; the self-consistency baseline G (the single agent run three times with its outputs voted, scored by the same validators; Supplementary Table~18); the turns the verifier fixed and broke as a secondary outcome (Supplementary Table~20); the all-turns scoring rule; and the exclusion rules. These were applied as written; every run was scored by its validator when it finished, and those verdicts are the results, except on the three tasks whose comparison bands were revised after scoring (below). The primary model, BAYES_SENTENCE

\textbf{Registration.} The protocol is dated 2026-09-29 and was committed to the study repository on 2026-10-01; the first confirmatory run started on 2026-10-10 (Supplementary Table~19). Five of the eight backbones were added after the first three had been analysed, which departs from the protocol's statement that none would be added after results were seen; each was run in full under the unchanged hypotheses, estimator and scoring rule, and reported (below).

\textbf{Departures in the analysis.} (i) The arms that carry analysis knowledge in their prompts (the published role prompts, and the rules twins of A to D), registered to test whether part of the published gain lies in that knowledge (H3), were not run; H3 is not tested here, and experiment 1, which ran the published prompts, is the only comparison of the two. (ii) The delegation arms F and F+V, added before the confirmatory grid (below), are reported as exploratory, without Holm correction and without a confirmatory claim (Supplementary Table~24). (iii) The protocol's single scoring pass after the last run, with a second pass to reproduce every verdict, was not performed; every run was scored by its validator when it finished, and those verdicts are the results. The only rescoring is the one under the widened bands described below.

\textbf{What was revised before the confirmatory grid, with its reason.} (i) \emph{Step budget}, 20 to 30 to 50 per turn (2026-10-06). A pilot under the pre-specified 20 steps showed D on one backbone ending 460 of its 489 turns at the step cap, against 23 for A, so that a measured deficit of the multi-agent topology would have been a deficit of steps; the verifier's and synthesis worker's reserves were scaled with the budget, keeping their shares. (ii) \emph{Task suite}, 92 to 104 to 111 tasks (2026-10-03 to 10-08). A convention audit against the standards the tasks invoke found eight defects (five answer-changing); they were corrected at the source and the suite re-ported, with new tasks added in the same period; the final suite was frozen on 2026-10-08. (iii) \emph{Backbones}. The pre-specified list named six models; those available through the laboratory's relay at the time of the grid were DeepSeek-V4-Flash and Qwen3.8-Flash, and GPT-6 Luna joined before any of its runs under the rule that every backbone started is run in full and reported. (iv) \emph{Delegation arms}. A second form of decomposition, in which a lead agent splits each turn and hands the pieces to sub-agents (F), was added on 2026-10-06, and its verified twin (F+V) on 2026-10-08, with the lead's note and the sub-agents' budgets fixed after a pilot in which F left outputs unset in two fifths of its turns; both were then run in full on every backbone. (v) \emph{Execution harness}. GPT-6 Luna, run without reasoning, rarely emitted the fenced code block the pre-specified harness required; every arm was therefore run for every backbone through a single native tool call per step. Five further backbones (Qwen3.8-27B with reasoning off and on, DeepSeek-V4-Flash with reasoning on, DeepSeek-V4-Pro and Claude Sonnet 5.5) were run after the first three had completed and been analysed (the departure noted under Registration), under the same protocol and the rule that every backbone started is run in full and reported; the two reasoning-mode runs test whether the gain stacks with a model's own extended reasoning. Results obtained under the superseded budget, suite or harness are not part of the analysis and are not reported.

\textbf{What was changed after scoring (2026-10-12).} For three tasks the declared reporting precision made a convention decisive that neither the task text nor the variable definitions state. On \texttt{beijing\_wind\_sector\_pm25} the two-decimal southerly mean turned on whether the hour ending at 00:00 on 1 March belongs to February (47.8964 against 47.8925); on \texttt{hk\_ozone\_burden\_year\_on\_year} the 2025 mean turned on one boundary row of the year (55.0473 against 55.0447); on \texttt{hk\_sunshine\_ozone\_scale\_reversal} a three-decimal regression slope turned on whether the hourly series is placed on a continuous grid before the rolling mean (1.3144 against 1.3147). The comparison bands were widened to $\pm 0.01$, $\pm 0.01$ and $\pm 0.002$; every documented wrong route is still refused; answer keys, task text and variable definitions are unchanged; every run of the first three backbones was rescored under the final bands, and the verdicts under the original bands are archived. Supplementary Table~13 reports the headline figures under both.
""")

    # ---------------- Note 3: task list ------------------------------------------------------
    rows = []
    for p in sorted((PHASE3 / "suites" / "air_quality" / "tasks").glob("*/*.json")):
        j = json.loads(p.read_text())
        turns = sum(len(c["turns"]) for c in j["conversations"])
        rows.append([tex(j["name"]), "HK" if j["name"].startswith("hk_") else "Beijing",
                     tex(j["category"].replace("_", " ")), str(turns)])
    body = " \\\\\n".join(" & ".join(r) for r in rows)
    # ---------------- Note 4: three cases ------------------------------------------------------
    cases = replication_tables.case_counts()
    def counts(task):
        a, d = cases.loc[(task, replication_tables.A)], cases.loc[(task, replication_tables.D)]
        per = "; ".join(f"{MODEL_LABELS[m]} {int(a[m])}/{int(d[m])}" for m in FIRST_THREE)
        return f"Single agent {int(a.passed)} of {int(a.runs)} runs, MetaSEQ {int(d.passed)} of {int(d.runs)} ({per})"
    c1, c2, c3 = (counts(t) for t, _ in replication_tables.CASES)
    t1 = cases.loc[("hk_ozone_peak_season_aqo", replication_tables.A), "turn1_passed"]
    t1d = cases.loc[("hk_ozone_peak_season_aqo", replication_tables.D), "turn1_passed"]
    parts.append(r"""\section*{Supplementary Note 3: Three tasks on which the arms diverge}

The three tasks below are the largest consistent contrasts between the single agent (A) and MetaSEQ (D) in experiment 2 (nine runs per arm: the three backbones run first, DeepSeek-V4-Flash, GPT-6 Luna and Qwen3.8-Flash, $\times$ three repeats; per-backbone passes given as A/D). They were chosen after the results were known and illustrate mechanisms; they are not inferential. Transcript excerpts are abridged.

\textbf{Case 1, \texttt{beijing\_olympics\_meteorological\_adjustment} (cross-domain analysis).} Compare Beijing PM$_{2.5}$ over 4--20 February 2022 with the same dates in 2021: the raw difference and the window coefficient from an OLS regression allowing for log ventilation, with the number of days. The two data streams carry different day conventions: the hourly air-quality record is hour-ending (the row stamped 00:00 closes the previous day), the ERA5 meteorology is instantaneous (a calendar day is hours 0--23). """ + c1 + r""". Every single-agent failure built the two daily series on inconsistently aligned days, giving a raw difference of $-44.0$ to $-43.9$ and an adjusted coefficient of $-27.9$ to $-28.3$ against $-43.95$ and $-27.95$. In MetaSEQ the data-acquisition worker resolved each convention before any analysis:

\begin{quote}\raggedright\fontsize{9}{11}\selectfont\ttfamily
For air quality (df), a day is hours 1--23 plus hour 0 of the next date. For meteorology (met\_df), a day is hours 0--23.\\
All 34 days (17 per window) are in the positive cohort, including both Feb 4 and Feb 20 in each year.
\end{quote}

The analysis worker then computed on the staged cohort ($-43.95$, $-27.95$, 34 days). In two of the three DeepSeek-V4-Flash runs the verifier recomputed and changed nothing.

\textbf{Case 2, \texttt{hk\_ozone\_peak\_season\_aqo} (regulatory standards), turn 1.} Tap Mun's 2025 peak-season ozone under the objective added in April 2025: the daily maximum 8-hour mean (at least 6 of 8 hours), averaged over each six-month window from month $M-2$ to $M+3$ for $M$ in 2025, the peak season being the highest of the twelve. The method is stated in the suite's system prompt. Single agent: """ + f"{int(t1)} of 9 first turns" + r"""; MetaSEQ: """ + f"{int(t1d)} of 9" + r""" (task level, all turns: """ + c2[0].lower() + c2[1:] + r"""). The nine single-agent failures took three forms. DeepSeek-V4-Flash assigned the 8-hour means to the calendar day of their stamp instead of the hour-ending day (121.3 against 120.6). GPT-6 Luna computed the right value and stored the window as 2025-12 to 2026-05. Qwen3.8-Flash fetched data from 31 December 2024 onward, so the windows reaching into November and December 2024 were truncated and it selected November--April:

\begin{quote}\raggedright\fontsize{9}{11}\selectfont\ttfamily
Note: data only starts 2024-12-31, so windows reaching into Nov/Dec 2024 and Jan 2026 are partial.\\
tap\_mun\_peak\_season\_first\_month = '2024-11'; tap\_mun\_peak\_season\_last\_month = '2025-04'
\end{quote}

In MetaSEQ (DeepSeek-V4-Flash, repeat 1) the analysis worker also truncated the windows to 2025 and the synthesis worker stored 120.1 over 2024-11 to 2025-04; the verifier re-fetched the hourly record from November 2024 to March 2026, recomputed the twelve windows and reassigned the outputs:

\begin{quote}\raggedright\fontsize{9}{11}\selectfont\ttfamily
For M=1, need Nov 2024 to Apr 2025. For M=12, need Oct 2025 to Mar 2026. So we need data from Nov 2024 through Mar 2026.\\
VERIFY tap\_mun\_peak\_season\_o3\_2025: stored=120.1 | independent=120.6 | final=120.6\\
VERIFY tap\_mun\_peak\_season\_first\_month: stored=2024-11 | independent=2024-12 | final=2024-12
\end{quote}

\textbf{Case 3, \texttt{hk\_weekend\_ozone\_ox\_conservation} (temporal pattern analysis), turn 2.} Weekend-minus-weekday afternoon NO$_2$ and odd oxygen (O$_x$ = O$_3$ + NO$_2$, summed in moles and expressed as NO$_2$-equivalent mass) for the general stations, the roadside stations and Tap Mun, and whether the desk may write that cutting NO$_x$ would worsen Hong Kong's ozone. """ + c3 + r""". In every MetaSEQ failure the six numbers were correct (general stations: NO$_2$ $-5.91$, O$_x$ $-0.20$~$\mu$g\,m$^{-3}$) and the boolean was wrong. The analysis worker read the weekend ozone rise as support for the claim, and the verifier, having recomputed the numbers, confirmed it:

\begin{quote}\raggedright\fontsize{9}{11}\selectfont\ttfamily
This is the classic weekend effect: with lower NOx, ozone titration by NO is reduced, so ozone goes up. This supports the claim that cutting NOx would worsen ozone. [\ldots] line\_can\_be\_written = True
\end{quote}

The single agent, holding the same numbers in one context, drew the opposite conclusion:

\begin{quote}\raggedright\fontsize{9}{11}\selectfont\ttfamily
However, odd oxygen (the conserved quantity) is essentially flat or slightly lower on weekends, meaning the ozone rise is largely a redistribution of the NO2--O3 balance rather than more total oxidant being produced.
\end{quote}

The judgement turns on a conservation argument that the single agent carried from the numbers to the conclusion, and that the worker answering the boolean, scoped to its own subtask, did not apply; it has the same form as the Moran's~I regression of experiment 1.
""")

    # ---------------- Note 5: task list --------------------------------------------------------
    parts.append(r"""\section*{Supplementary Note 4: The 111 tasks of experiment 2}

One row per task: identifier (as released), city, category and number of turns. The task text, variable definitions and validators are in the code release.

{\scriptsize
\begin{longtable}{@{}p{6.4cm}lp{4.2cm}c@{}}
\toprule
task & city & category & turns \\
\midrule
\endhead
""" + body + r""" \\
\bottomrule
\end{longtable}}
""")

    # ---------------- Tables ------------------------------------------------------------------
    t = 10
    parts.append(table(t, "The arms of experiment 2, their code names in the release, and the partition of the 50 code-execution steps per turn (B: solver, verifier; C: workers, synthesis; D: workers, synthesis, verifier; F: lead, sub-agents; F+V: lead, sub-agents, verifier; the verifier also receives whatever the turn left unused). A, B, C and D are the registered $2\\times2$; F and F+V are exploratory. G, the voting baseline, is derived from A's three repeats and runs nothing.",
                       ["arm", "configuration", "code name", "steps per turn"],
                       [[a, ARM_DESC[a], tex(ARM_NAMES[a]), BUDGET[a]] for a in ARMS]
                       + [["G", "A's three repeats, outputs voted", tex(replication_tables.G), "---"]], "@{}llll@{}"))
    t += 1
    rows = []
    for model in MODELS:
        for a in ARMS:
            sel = runs6[(runs6.model == model) & (runs6.arm == ARM_NAMES[a])]
            rows.append([MODEL_LABELS[model] if a == "A" else "", a,
                         f"{arm6.loc[model, ARM_NAMES[a]]:.1f}",
                         f"{int(sel.ok.sum())}/{len(sel)}", f"{sel.total_tokens.mean() / 1e3:,.0f}",
                         f"{tpc6.loc[model, ARM_NAMES[a]] / 1e3:,.0f}",
                         f"{sel.steps.median():.0f}", f"{int(sel.step_limit_turns.sum())}"])
    parts.append(table(t, "Experiment 2 by backbone and arm: validated accuracy (runs passed over runs scored), runs passed, mean tokens per task and per correct task (thousands), median code-execution steps per run, and turns in which an answering stage ended at its step cap.",
                       ["backbone", "arm", "accuracy (\\%)", "passed", "tokens/task (k)", "tokens/correct (k)",
                        "median steps", "turns at cap"], rows, "@{}llrrrrrr@{}"))
    t += 1
    rows = []
    HNAME = {"H1": "D $-$ A", "H2a": "B $-$ A", "H2b": "C $-$ A", "H2c": "D $-$ B"}
    for scope in MODELS + ["pooled"]:
        cc = replication_tables.core_contrasts(scope)
        for i, (h, r) in enumerate(cc.iterrows()):
            rows.append([(r"\textbf{Pooled}" if scope == "pooled" else MODEL_LABELS[scope]) if i == 0 else "", HNAME[h],
                         f"{100 * r.control_acc:.1f}", f"{100 * r.treatment_acc:.1f}",
                         f"{(0.0 if abs(r.delta_pp) < .05 else r.delta_pp):+.1f}", f"[{r.lo_pp:+.1f}, {r.hi_pp:+.1f}]", pfmt(r.p), pfmt(r.holm_p),
                         f"{int(r.recovered)}/{int(r.regressed)}"])
    st = replication_tables.sign_test()
    parts.append(table(t, "The four registered contrasts per backbone and pooled: accuracy of the control and the treatment arm, mean paired difference (percentage points), 95\\% percentile interval over 10,000 resamples of tasks (seed 20260929), two-sided bootstrap $p$, the same $p$ Holm-corrected over the four contrasts within the scope, and task-repeats recovered/regressed. D $-$ A is positive on all " + str(st['all']['n']) + " backbones (exact sign test $p = " + f"{st['all']['p']:.3f}" + "$) and on all " + str(st['distinct']['n']) + " distinct models when a model run with and without reasoning is counted once ($p = " + f"{st['distinct']['p']:.3f}" + "$).",
                       ["backbone", "contrast", "control (\\%)", "treatment (\\%)", "$\\Delta$ (pp)", "95\\% interval", "$p$", "Holm $p$",
                        "recovered/regressed"], rows, "@{}llrrrlllr@{}"))
    t += 1
    before = replication_tables.preband()       # the archived verdicts under the original bands
    # the same three backbones under the final bands, through the same estimator
    import sys as _sys
    _sys.path.insert(0, str(PHASE3))
    from analysis.report import contrast as _contrast
    from evaluation.experiment import Contrast as _Contrast
    sub = runs[runs.model.isin(before["models"])].reset_index(drop=True)
    after = _contrast(sub, _Contrast(name="H1", treatment=ARM_NAMES["D"], control=ARM_NAMES["A"]))
    final = {"A": 100 * after["control_acc"], "D": 100 * after["treatment_acc"]}
    rows = [[a, f"{before[a]:.1f}", f"{final[a]:.1f}", f"{final[a] - before[a]:+.1f}"] for a in ("A", "D")]
    g = before["gain"]
    rows.append(["D $-$ A", f"{g[0]:+.1f} [{g[1]:+.1f}, {g[2]:+.1f}]",
                 f"{after['delta_pp']:+.1f} [{after['lo_pp']:+.1f}, {after['hi_pp']:+.1f}]", ""])
    parts.append(table(t, "The three comparison bands widened after the first three backbones had been scored (Supplementary Note~2): pooled accuracy of A and D on those three backbones and their difference under the original and the final bands. The five backbones added later were scored under the final bands only.",
                       ["quantity", "original bands", "final bands", "change"], rows, "@{}llll@{}"))
    t += 1
    tp = replication_tables.thinking_pairs()
    rows = [[MODEL_LABELS[m], f"{r.A:.1f}", f"{r.A_reasoning:.1f}", f"{r.D:.1f}", f"{r.D_reasoning:.1f}",
             f"{r.gain_reasoning:+.1f}", f"{r.gain_orchestration:+.1f}", f"{r.gain_both:+.1f}",
             f"{r.diff_pp:+.1f} [{r.diff_lo:+.1f}, {r.diff_hi:+.1f}]"] for m, r in tp.iterrows()]
    parts.append(table(t, "Reasoning mode and orchestration on the two models run both ways: validated accuracy of the single agent and of MetaSEQ with reasoning off and on, the gain from each alone and from both, and the paired task-resampled difference between reasoning alone and orchestration alone (95\\% interval).",
                       ["model", "A", "A, reasoning", "D", "D, reasoning", "reasoning alone", "orchestration alone", "both", "reasoning $-$ orchestration"], rows, "@{}lrrrrrrrl@{}", resize=True))
    t += 1
    fb = replication_tables.fixed_broken_by_class()
    order = ["unset", "gross >=50%", "mid 2-50%", "near miss <2%", "other/unparsed"]
    labels = {"unset": "Required output missing", "gross >=50%": "Off by $\\geq$50\\%", "mid 2-50%": "Off by 2--50\\%",
              "near miss <2%": "Off by $<$2\\%", "other/unparsed": "Other or unparsed mismatch"}
    rows = [[labels[k], str(int(fb.loc[k, "fixed"])), str(int(fb.loc[k, "broken"]))] for k in order if k in fb.index]
    rows.append([r"\textbf{All}", str(int(fb.fixed.sum())), str(int(fb.broken.sum()))])
    parts.append(table(t, "Error class of the failing arm in the discordant cells of experiment 2. Fixed: cells the single agent failed and MetaSEQ passed, classed by the single agent's first failed turn; broken: cells MetaSEQ failed and the single agent passed, classed by MetaSEQ's. Classes from the validator message: a required output missing; the largest relative numeric error explicitly reported in the message at least 50\\%, between 2 and 50\\%, or below 2\\%; or other/unparsed mismatches (including Boolean, label, timestamp, type and nonfinite-value errors). A missing required output takes precedence; zero-reference comparisons remain unclassified. These descriptive bins do not identify causes or establish correctness of unreported outputs.",
                       ["error class of the failing arm", "fixed (A wrong, D right)", "broken (A right, D wrong)"], rows, "@{}lrr@{}"))
    t += 1
    rows = []
    for cat in sorted(runs.category.unique()):
        sel = runs[runs.category == cat]
        a = sel[sel.arm == ARM_NAMES["A"]].groupby("task").passed.mean().mean()
        d = sel[sel.arm == ARM_NAMES["D"]].groupby("task").passed.mean().mean()
        rows.append([tex(cat.replace("_", " ")), str(sel.task.nunique()), pct(a), pct(d), f"{100 * (d - a):+.1f}"])
    parts.append(table(t, "Task pass rate (\\%) by category for A and D, all backbones (descriptive; several categories hold few tasks and no per-category inference is made).",
                       ["category", "tasks", "A", "D", "D $-$ A"], rows, "@{}lrrrr@{}"))
    t += 1
    prompts = PHASE3 / "agents" / "prompts" / "fixed_roles" / "stripped"
    files = [("Coordinator", prompts / "coordinator.md"),
             ("Shared-runtime discipline", prompts / "discipline.md"),
             ("Data acquisition worker", prompts / "roles" / "data_acquisition.md"),
             ("Knowledge retrieval worker", prompts / "roles" / "knowledge_retrieval.md"),
             ("Pollution analysis worker", prompts / "roles" / "pollution_analysis.md"),
             ("Multivariate, meteorological and geospatial worker", prompts / "roles" / "multivariate_meteo.md"),
             ("Synthesis worker", prompts / "roles" / "synthesis_report.md"),
             ("Verifier", prompts / "roles" / "verification.md")]
    blocks = []
    for label, path in files:
        text = path.read_text().strip()
        blocks.append(f"\\noindent\\textbf{{{label}}}\\par\n"
                      f"{{\\fontsize{{8}}{{10}}\\selectfont\\noindent\\path{{{path.relative_to(PHASE3).as_posix()}}}\\par}}\n\n"
                      f"\\begin{{quote}}\\raggedright\\fontsize{{8}}{{10}}\\selectfont\\ttfamily\n{prompt_tex(text)}\n\\end{{quote}}\n")
    parts.append(f"""\\noindent\\textbf{{Supplementary Table~{t}.}} The prompts of arm D in experiment 2, verbatim from the release. The worker prompts are the deployed role prompts with the analysis rules removed (the deployed versions, which state for instance that a total is a sum and a correlation is Pearson's $r$, are released beside them). Arm A receives only the suite's system prompt and the task text, which all arms share and which are released with the tasks.

{''.join(blocks)}
""")

    t += 1
    vb = replication_tables.vote_baseline().set_index("model")
    vv = replication_tables.vote_vs_verified()
    rows = []
    for m in MODELS + ["pooled"]:
        r, v = vb.loc[m], vv.loc[m]
        rows.append([MODEL_LABELS.get(m, r"\textbf{Pooled}"), f"{r.A:.1f}", f"{r.G:.1f}", f"{v.B:.1f}", f"{r.D:.1f}",
                     f"{(0.0 if abs(v.delta_pp) < .05 else v.delta_pp):+.1f} [{v.lo_pp:+.1f}, {v.hi_pp:+.1f}]",
                     f"{r.delta_pp:+.1f} [{r.lo_pp:+.1f}, {r.hi_pp:+.1f}]", f"{r.tokens_ratio:.2f}"])
    pos_b = int(vv.loc["pooled", "backbones_positive"]); pos = int(vb.loc["pooled", "backbones_positive"])
    parts.append(table(t, "The protocol's three-run voting baseline G: for each backbone and task, the single agent's three repeats with every output set to the value most of them stored (numbers compared at six significant figures; no majority: the median of numbers, else the first repeat), scored by the same validators (\\texttt{analysis/vote.py}). Accuracy of A, G, B and D; the mean paired differences B $-$ G and D $-$ G with their 95\\% intervals from 10,000 task resamples (seed 20260929); and D's mean tokens per task as a multiple of G's (the three repeats' sum). B exceeds G on " + str(pos_b) + " of the eight backbones and D on " + str(pos) + ".",
                       ["backbone", "A", "G (A $\\times$ 3, voted)", "B", "D", "B $-$ G [95\\% interval]", "D $-$ G [95\\% interval]", "tokens D / G"], rows, "@{}lrrrrllr@{}"))
    t += 1
    bs = replication_tables.backbone_settings()
    rows = [[MODEL_LABELS[r.model], tex(r.api_model), f"{r.temperature:g}", r.reasoning, r.access,
             f"{r.first} to {r.last}" if r.first != r.last else r.first] for r in bs.itertuples()]
    parts.append(table(t, "The backbones of experiment 2 as recorded in every run: the model identifier sent to the API, the sampling temperature (Claude at the Messages API's default), the reasoning setting, how the model was reached, and the dates of the backbone's runs. Five runs of one backbone whose requests the relay rejected were served by the provider's own endpoint (Methods).",
                       ["backbone", "API model", "temperature", "reasoning", "access", "run dates"], rows, "@{}llrlll@{}"))
    t += 1
    vt = replication_tables.verifier_turns()
    rows = []
    for m in MODELS + ["pooled"]:
        r = vt.loc[m]
        rows.append([MODEL_LABELS.get(m, r"\textbf{Pooled}"), str(int(r[(replication_tables.B, "verified")]))]
                    + [str(int(r[(arm, k)])) for arm in (replication_tables.B, replication_tables.D, replication_tables.FV)
                       for k in ("fixed", "broken")])
    parts.append(table(t, "Turns the verifier fixed and broke in the three verified arms, per backbone and in total (a registered secondary outcome; Supplementary Note~2). Every verified turn stores the required outputs as the answering stage left them and after the verifier recomputed them; the first snapshot was scored with the task's validator when the run finished and paired with the final verdict. Fixed: failed before the verifier, passed after; broken: the reverse. Every cell verified 510 turns per arm.",
                       ["backbone", "turns", "B fixed", "B broken", "D fixed", "D broken", "F+V fixed", "F+V broken"], rows, "@{}lrrrrrrr@{}"))

    text = "\n".join(parts).replace("BAYES_SENTENCE", bayes)
    OUT.write_text(text)
    print("written", OUT, f"tables 10-{t}")

    # Supplementary Table 23 sits after the hand-written Table 22 in si.tex, so it has its own file.
    br = replication_tables.by_repeat()
    rows = []
    for m in MODELS + ["pooled"]:
        r = br.loc[m]
        cells = [f"{r[(arm, k)]:.1f}" for arm in (replication_tables.A, replication_tables.D) for k in (1, 2, 3)]
        tally = "/".join(str(int(r[("D_vs_A", k)])) for k in ("higher", "equal", "lower"))
        rows.append([MODEL_LABELS.get(m, r"\textbf{Pooled}"), *cells, tally])
    rep = ROOT / "manuscript" / "tex" / "table_repeats.tex"
    rep.write_text(table(23, "Experiment 2 by backbone and repeat: share of the 111 runs passed (\\%) by the single agent (A) and MetaSEQ (D) in each of the three repeats, and the number of repeats in which D passed more, as many or fewer runs than A. The pooled row averages the eight backbones; its last column sums theirs.",
                         ["backbone", r"\shortstack[r]{A\\repeat 1}", r"\shortstack[r]{A\\repeat 2}", r"\shortstack[r]{A\\repeat 3}",
                          r"\shortstack[r]{D\\repeat 1}", r"\shortstack[r]{D\\repeat 2}", r"\shortstack[r]{D\\repeat 3}",
                          r"\shortstack[r]{D higher/\\equal/lower}"], rows,
                         r"@{}p{.24\textwidth}rrrrrrr@{}"))
    print("written", rep, "table 23")

    # Supplementary Table 24: the exploratory delegation contrasts per backbone, after Table 23.
    rows = []
    for scope in MODELS + ["pooled"]:
        dc = replication_tables.delegation_contrasts(scope)
        for i, k in enumerate(("F-A", "FV-F", "FV-B", "FV-D")):
            r = dc.loc[k]
            rows.append([(r"\textbf{Pooled}" if scope == "pooled" else MODEL_LABELS[scope]) if i == 0 else "",
                         k.replace("FV", "F+V").replace("-", " $-$ "), f"{100 * r.control_acc:.1f}", f"{100 * r.treatment_acc:.1f}",
                         f"{(0.0 if abs(r.delta_pp) < .05 else r.delta_pp):+.1f}", f"[{r.lo_pp:+.1f}, {r.hi_pp:+.1f}]", pfmt(r.p),
                         f"{int(r.recovered)}/{int(r.regressed)}"])
    dele = ROOT / "manuscript" / "tex" / "table_delegation.tex"
    dele.write_text(table(24, "The exploratory delegation arms, per backbone and pooled: F (a lead agent splits each turn and hands the pieces to sub-agents, no verifier) against A, and F+V (the same, then the verifier) against F, B and D. Accuracy of the control and the treatment arm, mean paired difference (percentage points), 95\\% percentile interval over 10,000 task resamples (seed 20260929), two-sided bootstrap $p$ (uncorrected; these contrasts were not registered) and task-repeats recovered/regressed.",
                          ["backbone", "contrast", "control (\\%)", "treatment (\\%)", "$\\Delta$ (pp)", "95\\% interval", "$p$", "recovered/regressed"], rows,
                          r"@{}p{.2\textwidth}lrrrllr@{}"))
    print("written", dele, "table 24")


if __name__ == "__main__":
    main()
