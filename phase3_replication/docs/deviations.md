# Departures from the pre-specified protocol: arms A and D

The protocol (`docs/preregistration.md`, 2026-09-29) specified a larger study of the same tasks,
backbones and repeats; its other arms are reported separately, and the full dated log of the
study is released with them. This log records every departure that bears on the comparison of
the single agent (A, `single_agent_bare`) with the MetaSEQ topology (D, `multi_agent_fixed_roles_verified`). Section
numbers in brackets are those of the full log.

## What was applied as written

The hypothesis that D is more accurate than A; the unit of analysis (a run, paired within a
backbone on task and repeat, with tasks as the resampling unit); the task-resampled paired
bootstrap (mean paired difference, 10,000 task resamples, seed 20260929) as the frequentist
check of each contrast; the self-consistency baseline G (§5: the single agent's three repeats
voted, scored by the same validators; `analysis/vote.py`); the all-turns scoring rule; and the
exclusion rules.

## Registration

The protocol is dated 2026-09-29 and was committed to the study's repository on 2026-10-01; the
first confirmatory run started on 2026-10-10. The five backbones added after the first three
were run under its rule that every backbone started is run in full and reported.

## Departures in the analysis

- **Primary model.** The protocol's primary model (§5) is a Bayesian mixed-effects logistic
  regression over the four core arms (`correct ~ decomposition * verification`, task, backbone
  and task × backbone random intercepts, bambi/PyMC). This paper compares A and D only, so its
  headline estimate is the protocol's bootstrap check (on the probability scale, matching the
  figures), and the primary model is fitted restricted to the two arms (`correct ~ topology`,
  same random intercepts) with statsmodels' variational `BinomialBayesMixedGLM`, as experiment 1
  did, instead of the named sampler. Reported in Supplementary Note 2 (`replication_tables.mixed_model`).
- **Holm correction.** The protocol's Holm correction across its four contrasts was not applied
  to D − A; its bootstrap p is below 10⁻³ and no correction over four contrasts changes the
  conclusion.
- **Verifier audit (post hoc, 2026-10-17).** The protocol lists the turns fixed and broken by the
  verifier as a secondary outcome (§4 (iii)); the task-level pass rate before the verifier, its
  comparison with A and the interpretation are post hoc. Every D turn's record stores the
  required outputs as the synthesis worker left them (`coordination.before_verification`); these
  were scored with the task's validator (`analysis/before_verifier.py`, stored as the pseudo-arm
  `multi_agent_fixed_roles_verified_before`) and paired with the stored final verdicts. The verifier
  corrected 342 turns and broke 122 of 4,080; task pass rate 77.2% before it, 84.1% after
  (+6.9 pp, 95% interval 5.3–8.7), net positive on every backbone and in both cities. No run was
  repeated. Reported in Results and Supplementary Table 20.
- **Scoring pass.** The protocol's single scoring pass after the last run, with a second pass
  reproducing every verdict (§5), was not performed. Every run was scored by its validator when it
  finished and those verdicts are the results; the only rescoring is the one under the widened
  bands (below).
- **Backbones added after results were seen.** §3 says no backbone is added after results are
  seen. Five of the eight were added after the first three had been analysed (2026-10-14 and
  10-15, below); each was run in full under the unchanged hypothesis, estimator and scoring rule.

## Revised before the confirmatory runs

- **Task suite (2026-09-30 to 2026-10-08) [§1, §10, §11, §16].** A convention audit of the
  registered 92 tasks (no model calls) found eight defects against the standards the tasks
  invoke, five of which could change an answer or a verdict, among them: the Hong Kong system
  prompt contradicted itself on which day the 00:00 row belongs to; four Beijing answer keys took
  24-hour means over the label day rather than HJ 663's natural day; two tasks admitted a plain
  reading their keys rejected. They
  were fixed at the benchmark source (2026-10-03), with further tasks whose text did not determine
  the answer, and the suite was re-ported as tasks were added (104 tasks on 2026-10-07, 111 on
  2026-10-08: Hong Kong 58, Beijing 53). The suite has been frozen since 2026-10-08. Tasks whose key
  is right but whose answer needs a published rule the agent is not told were not changed.
- **Step budget (2026-10-06) [§14, §15].** Under the pre-specified 20 steps per turn, D on
  qwen3.8-flash ended 460 of its 489 turns with an answering stage at the step cap, against 23 for
  A, so a deficit of the multi-agent topology would have measured a deficit of steps. The budget
  was raised to 30 and, before that round completed, to 50, with the verifier's and synthesis
  worker's reserves scaled in proportion (verifier 30 %, synthesis 15 %): A 50; D 27 + 8 + 15.
- **What D's agents were told (2026-10-06, 2026-10-08) [§15, §17].** Before the 50-step round:
  the required outputs listed to D's workers and verifier no longer include the environment's own
  data; the verifier is shown the current turn's outputs only; every worker is told that its
  role's rules take precedence over the suite prompt's single-analyst guidance; the verifier's
  staged-values heading points it at the required outputs it was given.
- **Backbones (2026-10-01, 2026-10-09) [§9, §18].** The pre-specified list named six models; those
  available through the laboratory's relay were DeepSeek-V4-Flash and qwen3.8-flash, and GPT-6
  Luna joined before any of its runs, under the rule that every backbone started is run in full and
  reported.
- **Execution harness (2026-10-09) [§18].** GPT-6 Luna, run without reasoning, rarely wrote the
  fenced code block the pre-specified harness required. Every arm on every backbone was therefore
  run through one native `python` tool call per step, under one harness. The suite prompt's three
  protocol paragraphs are given in the tool's words; nothing else changed.

Results obtained under the superseded budget, suite or harness are not part of the analysis and
are not reported.

## Changed after scoring (2026-10-12) [§19]

For three tasks the declared reporting precision made a convention decisive that neither the
task text nor the variable definitions state:

| task | declared precision | the convention that decided the verdict |
|---|---|---|
| `beijing_wind_sector_pm25` | 2 decimals | whether the hour ending at 00:00 on 1 March belongs to February (47.8964 against 47.8925) |
| `hk_ozone_burden_year_on_year` | 2 decimals | one boundary row of the year (55.0473 against 55.0447) |
| `hk_sunshine_ozone_scale_reversal` | 3 decimals | whether the hourly series is put on a continuous grid before the rolling mean (1.3144 against 1.3147) |

Their comparison bands were widened to ±0.01, ±0.01 and ±0.002. Each band still refuses every
wrong route the task's documentation names; queries, variables and answer keys are unchanged, so
no run was rerun and the protocol fingerprint did not move. Every run was rescored under the
final bands. The verdicts under the original bands are kept (`results/original_bands/`).

Effect on A and D, pooled over the three backbones (recomputed from those verdicts by
`scripts/aggregate_replication.py`):

| | original bands | final bands |
|---|---|---|
| A | 72.1 % | 73.7 % |
| D | 77.9 % | 79.3 % |
| D − A | +5.8 [2.1, 9.7] | +5.6 [1.8, 9.6] |

## The release (2026-10-12)

This tree was reduced to the two arms. The code paths of the other arms were removed and the
stored runs of A and D were copied unchanged; `results/protocol_aliases.json`
records the checks that justified carrying the runs over (every request the model receives,
byte-identical before and after; every Beijing verdict reproduced on rescoring).

## Backbones added after the release (2026-10-14)

The Qwen3.8-27B runs of A and D (thinking off and on, 1,332 runs), made in the larger study's
tree under the same protocol, were added to this store; `results/protocol_aliases.json` records
why they count as made under this tree's protocol. Their verdicts are the ones made when each
run finished, under the validators of the final bands. The
fixed-role arm and its topology were renamed in the same release
(`multi_agent_fixed_roles_verified`, `fixed_roles`); no prompt text changed.

The runs of A and D on DeepSeek-V4 Flash with thinking, deepseek-v4-pro-0813 and
claude-sonnet-5-5 (1,998 runs) were added on 2026-10-15, likewise. Claude is served over
Anthropic's Messages API; the gateway that speaks it was taken unchanged from the larger
study's tree, which made these runs (`llm/tool_gateway.py`, `llm/registry.py`), and
`results/protocol_aliases.json` records that every request under A and D stayed
byte-identical.
