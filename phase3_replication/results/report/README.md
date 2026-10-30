# Derived tables of experiment 2

Two reports sit here, both derived from the same stored runs and verdicts; no script in this
repository scores anything.

- `arms.csv`, `contrasts.csv`, `outcomes.csv`, `failures.csv`, `categories.csv`: the two-arm
  report (`metaseq report study`, arms A `single_agent_bare` and D
  `multi_agent_fixed_roles_verified`), read by the error analyses, the cases, the multi-turn
  rates and Fig. 5.
- `study_arms.csv`, `study_contrasts.csv`, `study_factorial.csv`, `study_cost.csv`,
  `study_outcomes.csv`, `study_bayes.md`: the six-arm study report, all eight backbones, copied
  on 2026-10-27 from the study repository's `results/report/all_backbones/` (written 2026-10-20
  by its `analysis/study.py`; the Bayesian fit by `analysis/bayes.py`; both under `analysis/`). Arms: A, B
  `single_agent_verified`, C `multi_agent_fixed_roles`, D, F `multi_agent_delegation_planned`,
  F+V `multi_agent_delegation_verified`, and G `single_agent_bare_vote` (derived from A).
  The aggregate scope is labelled `pooled over backbones`. `study_outcomes.csv` has one row
  per run (15,984) and one per backbone and task for G (888).

`scripts/replication_tables.py` reads both; `scripts/aggregate_replication.py` asserts every
number the manuscript quotes against them.
