# MetaSEQ

MetaSEQ is a multi-agent large language model (LLM) system for air-quality analysis,
deployed in Hong Kong. A coordinator divides each query among specialist agents that
share one persistent Python runtime, so every number in an answer comes from executed
code over live monitoring data. A verifier recomputes the required outputs before the
answer is final.

This repository holds the system, the three evaluations reported in the paper, and the
scripts that turn their archived results into every figure and table. The scripts write
their output to `manuscript/figures/` and `manuscript/tex/`.

## The paper's evidence

| Evaluation | Directory | What it tests |
|---|---|---|
| Deployment | `phase1_evaluation/` | 117 real Hong Kong queries, six backbones, scored by three LLM judges; judge-free process metrics from the execution logs |
| Experiment 1 | `phase2_benchmark/` | 50 validator-graded Hong Kong tasks, seven backbones, one run per cell (700 runs): single agent against the deployed configuration |
| Experiment 2 | `phase3_replication/` | 111 validator-graded tasks in Hong Kong (58) and Beijing (53), eight backbones, three repeats; a pre-specified 2 × 2 of decomposition and verification (A single agent, B with the verifier, C fixed roles, D MetaSEQ), a voted baseline G and two exploratory delegation arms (15,984 runs), with the analysis rules removed from the prompts |

Headline results, every one asserted by a script (see below):

| | Single agent | MetaSEQ | Gain |
|---|---|---|---|
| Experiment 1, pooled over seven backbones | 74.6% | 85.1% | +10.6 points, exact McNemar *p* = 1.7 × 10⁻⁵ |
| Experiment 2, pooled over eight backbones | 77.1% | 84.1% | +7.0 points, 95% interval 4.7–9.6 |
| Experiment 2, single agent with the verifier (B) | 77.1% | 84.2% | +7.1 points, 4.8–9.6 |

In experiment 2 the verification main effect is +5.4 points (3.9–7.1) and the decomposition
main effect +1.6 (0.1–3.2); given the verifier, the roles add nothing (D − B −0.0, −1.4 to 1.2)
at 1.5 times the tokens per correct answer. The protocol's three-run voting baseline reached
81.1%, 3.1 points below the single agent with the verifier.

The deployment judge scores and execution logs are the Hong Kong half of the evaluation
in Neuro-Air (Ma et al., *npj Clean Air* 2, 59, 2026), extended here from four to six
backbones.

## Repository layout

| Path | Contents |
|---|---|
| `phase1_evaluation/` | Deployment evaluation: per-query judge scores (`eval_results/hk/`), pairwise trajectory judgements (`eval_results/compare/`), process metrics (`eval_results/objective_hk/`); the agent execution logs they were computed from are available from the corresponding author on request |
| `phase2_benchmark/` | Experiment 1: the 50 tasks (`benchmarks_metaseq.json`, `evals/`), the single and multi-agent runners, the archived runs (`experiments/metaseq/<backbone>/{single,multi}/run1/`) and their summary (`experiments/metaseq/summary/`) |
| `phase3_replication/` | Experiment 2: suite, arms, harness, scoring, statistics and the derived report tables (two-arm and six-arm; `results/report/README.md`); its own `README.md` and `docs/` (pre-registration and deviations) |
| `scripts/` | Everything that turns archived results into the paper's figures and tables, and the checks on every quoted number |
| `manuscript/figures/archive_sources/` | The archived data-layer atlas from which SI Fig. 9 is drawn |
| `PV_findings.md` | Narrative of experiment 1 with per-backbone and per-category results |

## Reproducing the figures and tables

No script below calls a model or the live database.

```bash
# every figure and generated table, from archived results
uv run --project phase3_replication --with matplotlib --with pypdf --with pymupdf --with scipy \
    python scripts/render_figures.py

# check every number the paper quotes
uv run --project phase3_replication python scripts/aggregate_replication.py   # experiment 2 and Fig. 5
uv run --project phase3_replication python scripts/table_deployment.py        # deployment evaluation
cd phase2_benchmark && uv run --project ../phase3_replication python -m scripts.aggregate_metaseq && cd ..   # experiment 1
```

Add `--data-only` to `render_figures.py` to refresh the statistical plots while keeping
the map atlas and the tables as they are.

| Output | Generator |
|---|---|
| Fig. 2, deployment case | Archived agent output, not regenerated |
| Fig. 3, experiment 1 | `scripts/fig_experiment1.py` |
| Fig. 4, experiment 2 | `scripts/fig_replication.py` |
| Table 2, experiment 2 by arm | `scripts/table_arms.py` |
| Fig. 5, gain by task and remaining errors; SI Fig. 9, robustness; SI Table 21 | `scripts/fig_failure_boundaries.py`, with `scripts/failure_evidence.py` |
| Table 1 | `scripts/table_results.py` |
| SI Fig. 4 and SI Table 5, deployment judge scores | `scripts/fig_evaluation.py`, `scripts/table_deployment.py` |
| SI Fig. 5, per-criterion judge profiles | `scripts/plot_supp_heatmap.py` |
| SI Fig. 6, process reliability | `scripts/fig_process.py` |
| SI Fig. 7, pairwise preference | `scripts/plot_ed_fig1.py` |
| SI Fig. 8, data-layer atlas | `scripts/gis/supp_maps.py` (needs the database); recoloured by `scripts/style_archived_atlas.py` |
| SI Figs. 10–12 | `scripts/fig_si_moved.py` |
| SI Notes 2–4, SI Tables 10–20 and 23–26 | `scripts/si_replication.py` |
| SI Table 18, voted baseline G | `phase3_replication/analysis/vote.py`, read through `scripts/replication_tables.py` |

All figures share one palette, defined in `scripts/data_figure_style.py`: grey for the
single agent, blue for MetaSEQ, orange for the voted baseline. Fig. 2 and Supplementary
Figs. 1–3 are archived panels from deployed answers and are not regenerated.

Fig. 3, Fig. 4, the experiment-2 Supplementary Tables (`scripts/si_replication.py`) and
`scripts/aggregate_replication.py` read the experiment-2 run records, which are not in this
repository (see below). Everything else, including the deployment evaluation, experiment 1,
Figs. 1 and 2 and Table 1, regenerates from the repository alone.

## Data and credentials

- The experiment-2 run records of all six arms (about 3.8 GB) are deposited on Zenodo, not
  tracked. Only the derived report tables and alias records are in
  `phase3_replication/results/`; the six-arm tables (`study_*.csv`) come from the study
  repository that ran the full grid (`results/report/README.md`).
- Credentials never enter tracked files. Database URLs and API keys live in
  `phase2_benchmark/.env`, `phase2_benchmark/models.toml` and
  `phase3_replication/models.toml`, all gitignored; see the `.example` files.
- Rerunning experiments, the atlas and the Hong Kong validators needs the monitoring
  database. The Beijing half of experiment 2 reproduces from the files alone.

## Conventions

- Numbers are generated, never typed. Change a result by re-running the script that
  produces it, then the check that asserts it.
- `PV_findings.md`, the paper and the archived runs describe the same experiments;
  a number changed in one place is checked in the others.

## Citation

If you use MetaSEQ, its task suite or these results, please cite the paper (manuscript in
preparation; the reference will be updated on publication). `CITATION.cff` holds the same
information.

```bibtex
@article{ran2026metaseq,
  author = {Ran, Maohao and Ma, Chendong and Song, Jun and Gao, Meng},
  title  = {Orchestrating language-model agents improves the reliability of environmental data analysis},
  year   = {2026},
  note   = {Manuscript in preparation}
}
```

MetaSEQ extends Neuro-Air:

```bibtex
@article{ma2026neuroair,
  author  = {Ma, Chendong and Ran, Maohao and Song, Jun and Gao, Meng},
  title   = {Multi-agent {AI} for end-to-end air quality analysis and decision support},
  journal = {npj Clean Air},
  volume  = {2},
  number  = {1},
  pages   = {59},
  year    = {2026},
  doi     = {10.1038/s44407-026-00102-4}
}
```

