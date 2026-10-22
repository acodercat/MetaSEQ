"""Statistics for paired binary outcomes: the pre-specified estimator (docs/preregistration.md)
and small exact tests."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

DRAWS, SEED = 10_000, 20260929      # pre-specified: task resamples and seed


def bootstrap(matrix: np.ndarray, statistic: Callable[[np.ndarray], float],
              draws: int = DRAWS, seed: int = SEED) -> tuple[float, float, float]:
    """95% percentile interval of `statistic` with the rows (tasks) resampled, and the
    two-sided bootstrap p-value at zero."""
    n = len(matrix)
    if n == 0:
        return math.nan, math.nan, math.nan
    rng = np.random.default_rng(seed)
    values = np.array([statistic(matrix[rng.integers(0, n, n)]) for _ in range(draws)])
    lo, hi = np.percentile(values, [2.5, 97.5])
    p = min(1.0, 2 * min((values <= 0).mean(), (values >= 0).mean()))
    return float(lo), float(hi), float(p)


def mean_of_first_column(m: np.ndarray) -> float:
    return float(m[:, 0].mean())


def wilson(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for a proportion."""
    if n == 0:
        return (math.nan, math.nan)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)


def binomial_two_sided(k: int, n: int) -> float:
    """Exact two-sided binomial test at p = 0.5 (doubled smaller tail, capped at 1)."""
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(k, n - k) + 1)) / 2**n
    return min(1.0, 2 * tail)


def mcnemar_exact(b: int, c: int) -> float:
    """Exact McNemar test on the discordant pairs b (control fail, treatment pass) and c."""
    return binomial_two_sided(min(b, c), b + c)
