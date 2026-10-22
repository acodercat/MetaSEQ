import math

import pytest

from analysis.stats import mcnemar_exact, wilson


def test_mcnemar_reproduces_the_phase2_headline():
    # PV_findings.md: pooled discordant pairs 55/18 -> exact p = 1.69e-05.
    assert mcnemar_exact(55, 18) == pytest.approx(1.69e-05, rel=0.01)


def test_mcnemar_edge_cases():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(8, 0) == pytest.approx(2 / 2**8)


def test_wilson_matches_the_phase2_interval():
    lo, hi = wilson(261, 350)   # 74.6% (Wilson 69.8-78.8)
    assert (round(100 * lo, 1), round(100 * hi, 1)) == (69.8, 78.8)
    assert all(math.isnan(x) for x in wilson(0, 0))
