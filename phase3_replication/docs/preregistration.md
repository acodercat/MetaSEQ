# Pre-registration: where the reliability of multi-agent air-quality analysis comes from

Written 2026-09-29 22:10 (Asia/Hong_Kong), before any run of the arms it registers
other than the smoke runs listed under "Data already in hand". Nothing below is to be
changed after the registered runs start; departures, if any, are to be recorded in
`docs/deviations.md` with their reason and date.

State registered with this document:

- code: MetaSEQ-lab working tree, protocol fingerprints `hk 01c8ca64dff6a05d`,
  `beijing d1cfdbe8a4ccf729` (`evaluation/protocol.py`: agent code, prompts, runner,
  model transport, environment); cave-agent 0.8.0 pinned in `uv.lock`;
- tasks: suite `air_quality`, 92 tasks (Hong Kong 44, Beijing 48), 187 files,
  manifest sha256 `6efa3869fae7fc4d…` (`results/reliability/suite_manifest.json`);
- model: `deepseek-v4-flash` as configured in `models.toml` (temperature 0.3, reasoning
  off); the configuration fingerprint is recorded in every run;
- experiment: `configs/experiments/reliability.toml`; arms: `configs/arms.toml`;
  prompts: `agents/prompts/fixed_roles/{published,stripped}` with `diff.md`.

## 1. Question

The group's earlier published system (npj Clean Air 2026) reported that its full multi-agent pipeline solves more
programmatically verified air-quality tasks than a single agent under a matched 20-step
budget. Its multi-agent arm bundled three things the single agent did not have:
decomposition into domain workers, an independent verifier, and analysis knowledge
written into the worker prompts; each configuration was run once. This study separates
those factors on a public, reproducible benchmark with repeated runs.

## 2. Hypotheses (confirmatory, fixed in advance)

| | Hypothesis | Test |
|---|---|---|
| H1 | The full orchestration (D) solves more tasks than the single agent (A) with no analysis knowledge on either side. | D − A > 0 |
| H2 | The verifier accounts for more of that gain than decomposition does. | main effect of verification > main effect of decomposition; both reported with the interaction |
| H3 | Part of the published gain lies in the analysis knowledge the role prompts carried. | (E − A) − (D − A) > 0, i.e. E − D > 0; and the knowledge factor on Flash (rules arms vs their twins) |
| H4 | At the accuracy it reaches, the single agent with the verifier (B) is at least as token-efficient as the full orchestration (D). | tokens per correct task, B ≤ D; D − B reported with its interval |
| H5 | Gains are larger where the single agent is weaker. | descriptive, across backbones (only when ≥ 4 backbones have run) |

Origin of the hypotheses (disclosed): H1–H4 were formed from exploratory runs of other
architectures on the same 92 tasks with the analysis rules on (`results/single_vs_multi`)
and from a re-run of that paper's 50-task comparison. The arms below have not been run on
these tasks other than the smoke runs listed in §8. Confirmatory evidence therefore
comes first from the pre-specified tests on Flash and then from backbones never run here.

## 3. Arms

All arms: the suite's system prompt and the task's own text; `max_steps = 20` per turn;
temperature and model identical; security checker and output limit identical. "Rules" =
`agents/prompts/rules.md` given to every agent that computes.

| Arm | Decomposition | Verifier | Knowledge | Steps |
|---|---|---|---|---|
| A `single_agent_bare` | no | no | none | 20 |
| B `single_agent_verified` | no | yes | none | 14 + verifier gets 20 − used |
| C `multi_agent_fixed_roles` | yes | no | none | 20 (synthesis reserve 3) |
| D `multi_agent_fixed_roles_verified` | yes | yes | none | 20 (verifier reserve 6, synthesis 3) |
| `single_agent` | no | no | rules | 20 |
| `single_agent_verified_rules` | no | yes | rules | as B |
| `multi_agent_fixed_roles_rules` | yes | no | rules | as C |
| `multi_agent_fixed_roles_verified_rules` | yes | yes | rules | as D |
| E `multi_agent_fixed_roles_published` | yes | yes | the published role prompts verbatim | as D |

The orchestration is that system's released harness ported mechanism by mechanism
(coordinator plan, default plan, budget rule, type-only manifest, instruction assembly;
tests compare the port with the harness). Two adaptations, made for this suite and
applied to every fixed-role arm: required outputs are the declared variables registered so
far, and every worker sees the conversation so far (the harness's tasks were single-turn).
The verifier is one function shared by B and D. What was removed from the prompts and
why is fixed in `agents/prompts/fixed_roles/README.md` and `diff.md`.

Backbones: DeepSeek-V4-Flash now, all nine arms. Planned next, the four core arms only,
fixed here before any of them runs: GPT-5.5, DeepSeek-V4-Pro, Qwen3.5-397B-A17B,
Qwen3.6-35B-A3B, Qwen2.5-72B-Instruct. A backbone that cannot be run (access, cost) is
dropped with the reason recorded; none is added after results are seen.

Repeats: 3 per (arm, task, backbone). No stopping rule; the grid is run in full.

Precision expected (from the earlier runs on these tasks): for one backbone, the
task-clustered 95% interval of a paired difference between two arms is about ±6–7
percentage points wide on each side; pooled over five backbones about ±3; the
interaction about ±5. Effects below that are reported as not resolved, not as absent.

## 4. Outcome measures

Primary: task-level accuracy under the all-turns rule (a task passes only if every turn's
validator passes; a turn that cannot be judged makes the task unscored, never failed).

Secondary: (i) consistency, the share of tasks with the same pass/fail outcome in all 3
repeats, and majority-of-3 accuracy; (ii) tokens per run and tokens per correct task;
(iii) verifier effect: turns failing before the verifier and passing after ("fixed") and
the reverse ("broken"), from `programmatic_verification_before.json`; (iv) failure causes
(outputs not set / wrong type / out of steps / wrong value) and, for Flash, a manual
annotation of failed turns by reasoning type (regulatory convention, spatial geometry,
cross-source integration, attribution, delivery) by two annotators with agreement
reported; (v) coordinator fallbacks and step-cap hits; (vi) accuracy by task category
and by city (descriptive; no per-category inference).

## 5. Analysis

Unit of analysis: one run (arm × task × repeat × backbone). Primary model:
`correct ~ decomposition * verification + (1 | task) + (1 | backbone) + (1 | task:backbone)`,
Bayesian mixed-effects logistic regression (bambi/PyMC, weakly informative priors),
fitted on the four core arms; with one backbone the backbone terms are dropped.
Reported: posterior means and 95% intervals of both main effects and the interaction on
the probability scale (marginal), and the pre-specified pairwise contrasts H1 (D − A),
H2a (B − A), H2b (C − A), H2c (D − B), H3 (E − D and rules twins), H4 (tokens per correct,
D vs B). Frequentist checks: task-clustered paired bootstrap (10,000 resamples, seed
20260929) for each contrast, Holm-corrected across the four core contrasts; exact
McNemar on run pairs reported descriptively. H5: Spearman correlation between a
backbone's single-agent accuracy and its D − A gain, exploratory.

Self-consistency baseline (G, no new runs): for each task and backbone, each output
variable of arm A is set to the majority value across its 3 repeats (numbers compared
after rounding to 6 significant figures; no majority → the median for numbers, the
first repeat otherwise) and the assembled snapshot is scored with the same validators;
reported as a compute-matched single-agent point (3× tokens) on the accuracy–token plane.

Exclusions: a turn with status `raised` (validator defect) or `infra_error` after
retries is excluded from every arm for that task/repeat; runs with `error` are re-run on
resume before scoring; nothing else is excluded.

Ground truth: all runs are scored together at one time after the last run; the scorecards
and the database state (max timestamp and row count per table) are archived; a second
scoring pass must reproduce every verdict (0 changes) before analysis.

## 6. What would count against the hypotheses

H1 fails if the D − A interval includes 0. H2 fails if decomposition's main effect is at
least as large as verification's. H3 fails if E − D's interval includes 0 and the rules
twins show no knowledge effect. H4 fails if B's tokens per correct task exceed D's.
All four outcomes are reportable; the design does not depend on their direction.

## 7. Limitations known in advance

Hypotheses formed on these tasks (§2); the analysis rules were written from failures on
a different suite (phase2_hk) but the tasks here have been run with them before; the
Hong Kong database is live (frozen by the scoring protocol in §5, not by a snapshot,
unless one can be exported); one backbone until the others run; the verifier prompt is
the released one, so "verification" here means that specific stage.

## 8. Data already in hand at registration

`results/reliability`: 200 runs of A (made 2026-09-29 before the orchestration was
replaced; the single agent's code and prompts unchanged, checked file by file), and the
smoke runs of B, C, D on three tasks × 3 repeats (27 runs, 2026-09-29). They are kept as
ordinary runs of the grid; no other arm has been run on these tasks.
