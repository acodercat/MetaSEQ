# phase3_replication: experiment 2 of the MetaSEQ paper

The experiment environment of the paper's experiment 2: the single agent (arm A,
`single_agent_bare`) against the MetaSEQ multi-agent topology (arm D,
`multi_agent_fixed_roles_verified`: coordinator, four analytical workers, synthesis worker,
verifier) on the 111-task `air_quality` suite (Hong Kong 58, Beijing 53), three repeats each,
on eight backbones (5,328 runs): DeepSeek-V4-Flash, qwen3.8-flash and GPT-6 Luna, run first,
then Qwen3.8-27B with thinking off and on, DeepSeek-V4-Flash with thinking, deepseek-v4-pro-0813
and claude-sonnet-5-5 (`docs/deviations.md`). The paper reports all eight. Every answer is scored by a programmatic validator that recomputes ground truth from the source data
(the Hong Kong monitoring database, the Beijing data files).

The runs were made within a larger pre-specified study of the same tasks, backbones and
repeats (`docs/preregistration.md`, verbatim; the departures that bear on A and D are in
`docs/deviations.md`); its other arms are reported separately and are not part of this tree.

## The two arms

| arm | what runs each turn | steps per turn |
|---|---|---|
| `single_agent_bare` | one agent: the suite's system prompt and the task's own text | 50 |
| `multi_agent_fixed_roles_verified` | a coordinator plans over four domain workers sharing one runtime; a synthesis worker assigns the outputs; the verifier recomputes every output from the raw data and reassigns what differs | 27 + 8 + 15 |

Both arms run without analysis rules: the role prompts are the deployed prompts with the
analysis knowledge removed (`agents/prompts/fixed_roles/stripped`; the deployed texts are kept
beside them in `published/`, and `diff.md` lists every change). Each agent runs its code
through one native `python` tool call per step (`agents/harness/`).

## Quick start

```bash
uv sync
cp .env.example .env                  # METASEQ_HK_DATABASE_URL (read-only role)
cp models.toml.example models.toml    # model endpoints and keys

uv run metaseq suites                 # air_quality: 111 tasks, 170 turns (hk, beijing)
uv run metaseq arms                   # the two arms (configs/arms.toml)
uv run metaseq check                  # import and check every task module

uv run metaseq run study --dry-run   # what a run would do, nothing run
uv run metaseq run study --model gpt-6-luna --shard 0/8
uv run metaseq score study           # re-judge stored runs; no model calls
uv run metaseq report study           # all eight backbones: results/report/ (tracked)
uv run python -m analysis.vote study  # G, the pre-registered voted single-agent baseline (no model calls)
uv run python -m analysis.before_verifier study   # D's outputs before its verifier, re-scored (post hoc; HK needs the database)
uv run pytest                         # offline: scripted model, toy suite
```

The stored runs are deposited on Zenodo; unpacked under `results/`, `metaseq run study --dry-run`
reports `5328 runs selected, 0 to run`, `metaseq score study` reproduces every verdict and
`metaseq report study` regenerates the tables in `results/report/`, which are tracked. The Beijing half
needs only the files under `data/`; the Hong Kong half needs the database.

## Layout

```
agents/            the system under test
  arm.py           Arm: topology, step budget, the verifier's and synthesis reserves
  system.py        MetaSEQAgent: runs the arm's topology turn by turn
  topologies/      single.py, fixed_roles.py (the MetaSEQ topology)
  verification.py  the verifier stage
  workspace.py     a Python runtime plus lab-side access to it
  harness/         one native `python` tool call per step: the agent loop, its tool,
                   transcripts, and the suite prompt's protocol paragraphs in its words
  failure.py       why a run ended without an answer, and whether it was the model's
  stage.py         one agent run by one role
  instructions.py  which prompt pieces each agent receives
  security.py      what agent code may not import or read
  prompts/fixed_roles/  the role prompts: stripped/ (used), published/ (deployed, for reference)
evaluation/        runner, protocol fingerprint, scoring, result store, experiment loop
analysis/          outcomes, failure causes, the pre-specified estimator, report, vote.py (baseline G),
                   before_verifier.py (the verifier audit)
tasks/             task model, suite loading, porting (`metaseq port`)
domains/           hk (database engine, files, tools), beijing (files, MDA8 helper)
llm/               models.toml registry, transport settings, the tool gateway (OpenAI-compatible,
                   OpenAI Responses and Anthropic Messages APIs)
cli.py settings.py validation.py errors.py
configs/           arms.toml, experiments/study.toml
suites/air_quality/  suite.toml, environments/<domain>.json, tasks/<category>/<task>.{json,py}
data/              hk/ (tracked), beijing/ (CSVs copied from AirBench, gitignored; see
                   the *.sources.json beside them)
docs/              preregistration.md (the protocol of the larger study, verbatim), deviations.md
                   (every departure that bears on arms A and D)
tests/             offline tests (scripted model + toy suite)
```

Results follow AirBench's layout, with the lab's `arm` level and numbered repeats:

```
results/<domain>/<category>/<task>/<arm>/<model>/r<k>/
    run.json                          the trajectory: per turn query, response, cost,
                                      stages, runtime_variables; no verdict
    programmatic_verification.json    per turn: validator, status, success, message
    transcripts/<conversation>.jsonl  one message per line
results/<domain>/<category>/<task>/single_agent_bare_vote/<model>/r1/programmatic_verification.json
                                      the voted baseline G: a verdict with no run.json beside it
results/<domain>/<category>/<task>/multi_agent_fixed_roles_verified_before/<model>/r<k>/programmatic_verification.json
                                      D's pre-verifier outputs scored: a verdict with no run.json beside it
results/report/      summary.md and the csv tables behind it, arms A and D (tracked)
results/protocol_aliases.json   see "Protocol" below (tracked)
results/model_aliases.json      the same model served by another endpoint (tracked)
results/original_bands/   A and D on the first three backbones under the three comparison bands
                          before they were widened (docs/deviations.md); with the runs on Zenodo
```

## Design rules

- **The suite owns the environment.** A task runs under the prompt it was written
  for; the lab's own prompts are added by arm, never edited into the suite.
- **Scoring reads the snapshot**, never the live runtime. A turn that cannot be
  judged (query changed, validator crashed, database unavailable) is reported as
  missing, never as a failure; an output stored as a type JSON cannot hold fails
  its turn.
- **Tasks are the unit.** A task passes only if every turn passes; contrasts pair
  runs within a backbone on (task, repeat) and report a 95% interval that resamples
  tasks, so repeats of one task are never counted as independent.
- **Protocol.** Every run records a fingerprint of the agent code, prompts and
  environment it was made under; resume reruns a run whose fingerprint, arm or
  model configuration differs. When code changes only in form, a checked migration
  writes `protocol_aliases.json` instead of rerunning. Each entry records what changed and
  the checks that showed the model is sent exactly what it was sent before: the reduction of
  this tree to the two arms, the arm rename of 2026-10-14 (which rewrote the arm name inside
  `run.json`), and the later backbones and the Anthropic Messages API.

## Known issues

- `air_quality` was ported from AirBench's working tree with uncommitted changes
  (`suite.toml: dirty = true`). Commit AirBench and re-port to pin it.
