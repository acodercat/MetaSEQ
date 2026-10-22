# Experiment 1: single agent against the deployed MetaSEQ configuration

This directory is the environment of experiment 1 in the paper: 50 Hong Kong
air-quality tasks, seven backbones, each run once as a single agent and once under the
deployed multi-agent configuration (700 runs). Every answer is graded by a validator
that recomputes the ground truth from the monitoring database; no LLM or human judgement
enters the score.

Pooled over the seven backbones the task pass rate rose from 74.6% to 85.1%
(55 tasks recovered, 18 regressed; exact McNemar *p* = 1.7 × 10⁻⁵). The narrative is in
`../PV_findings.md`.

## Layout

| Path | Contents |
|---|---|
| `benchmarks_metaseq.json` | The 50 tasks (59 turns) in eight categories, Hong Kong only |
| `evals/<category>/HK/` | One `.json` specification and one `.py` validator per task |
| `domains/HK/` | Database access and the shared runtime setup for Hong Kong |
| `datasets/HK_population_1km.csv` | WorldPop 2020 1-km grid, used by the exposure tasks |
| `adapters/` | The single agent (`CaveAgentFactory`) and the multi-agent topology (`multiagent_adapter.py`: coordinator, specialist workers, synthesis and verifier over one runtime) |
| `core/`, `runner.py`, `scripts/run.py` | Runner, scoring and result writing |
| `experiments/metaseq/<backbone>/{single,multi}/run1/HK/` | The 700 archived runs: responses, executed code, runtime variables and validator verdicts |
| `experiments/metaseq/summary/` | Per-backbone, per-category and per-cell tables and `summary.md`, written by `scripts/aggregate_metaseq.py` |

Backbones: `gpt55`, `deepseek-v4-pro`, `deepseek-v4-flash`, `qwen3.5-397b`,
`qwen3.6-35b`, `qwen3.6-27b`, `qwen-2.5-72b`.

## Regenerating the numbers

No model or database call is made; this reads only the archived runs.

```bash
uv run --project ../phase3_replication python -m scripts.aggregate_metaseq
```

It writes `experiments/metaseq/summary/` and asserts full 7 × 2 × 50 coverage and the
published counts under both scoring rules: all turns must pass (the primary rule), and,
as a sensitivity analysis, only the final turn. `--no-expected` skips the count
assertions if the archive changes.

## Running the experiment again

This needs the Hong Kong monitoring database and model credentials. Copy
`.env.example` to `.env` (database URL) and `models.toml.example` to `models.toml`
(endpoints and keys); both are gitignored.

```bash
uv run python -m scripts.run --domain HK --model gpt55 --topology single --exp metaseq/gpt55/single/run1
uv run python -m scripts.run --domain HK --model gpt55 --topology multi  --exp metaseq/gpt55/multi/run1
```

Runs are written to `experiments/{exp}/HK/{category}/{task}/{model}_{timestamp}.json` and
are resumable: completed tasks are skipped unless `--no-skip` is given.
