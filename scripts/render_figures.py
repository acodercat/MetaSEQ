"""Rebuild the paper's statistical figures, compact schematics and tables.

    uv run --project phase3_replication --with matplotlib --with pypdf \
        --with pymupdf python scripts/render_figures.py

No model calls or source-database queries. Archived agent-generated case panels
are retained as evidence. The atlas palette pass changes vector symbols only.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-only", action="store_true",
                        help="Refresh statistical plots; preserve Fig. 1, maps and tables")
    args = parser.parse_args()
    env = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    scripts = [
        "table_deployment.py", "table_results.py", "si_replication.py",
        "style_archived_atlas.py", "fig_overview.py", "fig_replication.py", "fig_failure_boundaries.py",
        "fig_evaluation.py", "plot_supp_heatmap.py", "fig_process.py", "plot_ed_fig1.py",
        "fig_experiment1.py", "fig_si_moved.py",
    ]
    if args.data_only:
        scripts = ["fig_replication.py", "fig_failure_boundaries.py", "fig_evaluation.py", "plot_supp_heatmap.py",
                   "fig_process.py", "plot_ed_fig1.py", "fig_experiment1.py", "fig_si_moved.py"]
    for name in scripts:
        subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    main()
