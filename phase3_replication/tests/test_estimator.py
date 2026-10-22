"""The pre-specified estimator: pairing, the task bootstrap, and the report's contrast."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis.report import contrast
from analysis.stats import bootstrap, mean_of_first_column
from evaluation.experiment import Contrast

X = Contrast(name="x", treatment="t", control="c")


def _outcomes(passes: dict[str, list[list[int]]], missing: tuple = (),
              model: str = "m") -> pd.DataFrame:
    """passes[arm][task][repeat] -> one scored row each; `missing` rows are unscored."""
    rows = []
    for arm, tasks in passes.items():
        for t, repeats in enumerate(tasks):
            for r, passed in enumerate(repeats, 1):
                unscored = (arm, t, r) in missing
                rows.append({"arm": arm, "model": model, "task": f"t{t}", "repeat": r,
                             "status": "unscored" if unscored else "scored",
                             "passed": None if unscored else bool(passed),
                             "total_tokens": 100})
    return pd.DataFrame(rows)


def test_bootstrap_of_a_constant_difference_is_that_difference_with_p_zero():
    lo, hi, p = bootstrap(np.full((5, 1), 0.2), mean_of_first_column, draws=200)
    assert (lo, hi, p) == pytest.approx((0.2, 0.2, 0.0))
    assert bootstrap(np.zeros((5, 1)), mean_of_first_column, draws=200)[2] == 1.0


def test_bootstrap_p_is_two_sided():
    diffs = np.array([[1.0], [-1.0], [0.5], [-0.5], [0.1]])
    lo, hi, p = bootstrap(diffs, mean_of_first_column, draws=2000)
    assert lo < 0 < hi and 0.5 < p <= 1.0


def test_contrast_pairs_scored_runs_and_counts_run_level_changes():
    outcomes = _outcomes({"t": [[1, 1, 1], [0, 1, 0]], "c": [[0, 1, 1], [1, 1, 0]]},
                         missing={("c", 1, 3)})
    row = contrast(outcomes, X)
    assert row["pairs"] == 5 and row["tasks"] == 2
    # task 0: +1/3; task 1 (repeats 1-2 paired): -1/2
    assert row["delta_pp"] == pytest.approx(100 * (1 / 3 - 1 / 2) / 2)
    # Accuracies weight tasks as the difference does, so they subtract to it.
    assert (row["control_acc"], row["treatment_acc"]) == pytest.approx((5 / 6, 3 / 4))
    assert (row["recovered"], row["regressed"]) == (1, 1)


def test_runs_pair_within_a_model_and_a_task_averages_its_models():
    flash = _outcomes({"t": [[1, 1, 1]], "c": [[0, 0, 0]]}, model="flash")
    qwen = _outcomes({"t": [[1, 1, 1]], "c": [[1, 1, 1]]}, model="qwen")
    lonely = _outcomes({"t": [[1, 1, 1]]}, model="third")       # no control: never paired
    row = contrast(pd.concat([flash, qwen, lonely]), X)
    assert (row["tasks"], row["pairs"]) == (1, 6)
    assert row["delta_pp"] == pytest.approx(100 * (1 + 0) / 2)
