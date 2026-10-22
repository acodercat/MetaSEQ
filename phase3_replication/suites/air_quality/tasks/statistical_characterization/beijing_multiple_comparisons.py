"""Beijing trend screening — two corrections, and only one is the famous one
(statistical_characterization).

Screening BASELINE. It was registered as a trap against reporting the
uncorrected count, and Gate B reclassified it under the Round 9 ruling: the
case spells the correction out, so the distractor it forbids is not a naive
path. The diagnostic weight sits in the CC channel.

Screen every station against every regulated pollutant and the count falls
twice, for two different reasons:

- tests_run: 72, twelve stations by six pollutants.
- naive_significant: 20 at p < 0.05, against 3.6 expected by chance alone.
- autocorr_significant: 2, once each p-value is recomputed with the standard
  error inflated for serial correlation in that regression's own residuals.
- fdr_survivors: 1, after also applying Benjamini-Hochberg to those corrected
  p-values (carbon monoxide at Shunyi).

The order of the drops is the content, and it is the opposite of what the
folklore suggests. Multiplicity is the correction everyone names, but here it
removes ONE finding; serial correlation removes EIGHTEEN. A screen that applies
false-discovery control to p-values computed as if monthly means were
independent has fixed the smaller of its two problems and left the larger one
untouched.

Why the case had to be built this way, recorded because an earlier version was
not. That version screened on raw OLS p-values and asserted in this docstring
that monthly means are "far less serially correlated" than daily ones — which
was never measured. Gate B measured it: ALL 72 monthly regressions have
positive residual autocorrelation, from 0.164 to 0.803, median 0.483. The
p-values feeding the correction were therefore invalid, and Benjamini-Hochberg
cannot repair an invalid input p-value — it rescales the ranking it is given.
Applying the AR(1) correction from `beijing_trend_uncertainty` to each
regression first makes the exercise coherent and turns a two-step story into a
three-step one.

**The AR(1) correction is not the right error model here, and the case now
says so rather than teaching it as one.** An external audit made the point and
its numbers reproduce to within 0.002: residual lag-1 autocorrelation across the 72
regressions runs 0.164 to 0.803 with a median of 0.483, on monthly means of
pollutants with a pronounced annual cycle and a regression carrying no
seasonal term. Much of that persistence is periodic structure, not an AR(1)
process, and at 61 to 72 months — 5.08 to 6.00 years — the slope is itself
sensitive to which months bound the record. The correction is still the right
thing to demonstrate, because the three-step story is about what each
correction can and cannot repair; what changed is that a second claim now
requires the response to say the adjusted p-values rest on an error model this
data does not satisfy, and names what a defensible screen would use instead.

The audit's companion finding — that "the month index" is undefined when a
series is short of 72 months — was measured and does NOT hold. Twelve of the
72 combinations do carry interior month gaps, but position-in-series and
elapsed-months-since-2020-01 give identical results: 20 / 2 / 1 either way.
None of the twelve sits near a threshold.

Pins, each measured.

- The window 2020-2025, the twelve stations, the six regulated pollutants,
  monthly means, ordinary least squares on the month index, two-sided p, and
  alpha = 0.05 at both stages.
- The AR(1) correction applied per regression: N_eff = N (1 - r1) / (1 + r1)
  from that regression's residual lag-1 autocorrelation, standard error
  inflated by sqrt(N / N_eff), and the p-value recomputed on Student t with
  N_eff - 2 degrees of freedom.
- Benjamini-Hochberg as the STEP-UP procedure: sort ascending, take the largest
  k with p(k) <= (k/m) * alpha, reject all k. A draft counted every position
  satisfying the inequality instead, which agrees here and not in general.

Excluded readings. Screening daily means rather than monthly gives 54 of 72
significant and 54 surviving the correction, because roughly 2190 autocorrelated
days per series make the raw p-values spuriously tiny — the same disease this
version corrects for, at a scale where it is impossible to miss. Series lengths
run 61 to 72 months and no minimum-length filter is applied, `tests_run`
saying so
because a filter would be one more free convention.

**A live run found the one convention the procedure had left open, on the one
test where it matters.** "The lag-1 autocorrelation of the residuals" has two
textbook estimators: the Pearson correlation between the lagged halves (each
against its own mean — np.corrcoef, this ground truth) and the autocovariance
ratio sum(e_t e_{t-1}) / sum(e_t^2). On sixty-nine of the seventy-two tests
they agree about 0.05; on Changping CO the adjusted p reads 0.05371 under the
first and 0.04340 under the second, so the count is 2 or 3 by estimator choice
alone. A model computed the second, stored 3, and was failed by a case that
had not said which to use — the model was right and the case was wrong.
`autocorr_significant` now names the Pearson form and the reading 3 is probed.
The BH survivor count is 1 under both. `beijing_trend_uncertainty` shares this
formula and was measured rather than assumed safe: at 2,192 days its two
readings differ by 0.000162 on the adjusted half-width, inside its +/-0.001
band.

Tolerances: 0 on all four counts. They are exact integers under a fully pinned
procedure, and the excluded readings — 54 from the daily basis, 20 or 2 reported
in the wrong slot, 4 from confusing the chance expectation with a result, 3
from the autocovariance-ratio estimator — are all whole numbers away.

All four ground truths are recomputed here from the CSV.

**Query trimmed 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`),
as a Tier 2 case: the screen's three-stage procedure — ordinary regression,
the serial-correlation adjustment, false-discovery control — is the
standard the variables state, and the counts under it are the deliverable;
the query no longer walks the agent through the stages.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from scipy import stats

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn

_YEARS = (2020, 2025)
_POLLUTANTS = ("PM2.5", "PM10", "SO2", "NO2", "CO", "O3")
_ALPHA = 0.05


def _benjamini_hochberg(p_values: np.ndarray, alpha: float) -> int:
    """Number rejected by the BH step-up procedure.

    Largest k with p(k) <= (k/m) * alpha, rejecting all k — not the count of
    positions satisfying the inequality, which differs whenever the sorted
    p-values cross the line more than once.
    """
    ordered = np.sort(p_values)
    m = len(ordered)
    below = np.nonzero(ordered <= (np.arange(1, m + 1) / m) * alpha)[0]
    return int(below[-1] + 1) if len(below) else 0


def _adjusted_p(y: np.ndarray) -> float:
    """Two-sided p for the OLS trend, with the standard error inflated for
    serial correlation in this regression's own residuals."""
    x = np.arange(len(y), dtype=float)
    slope, intercept, _r, _p, stderr = stats.linregress(x, y)
    residual = y - (intercept + slope * x)
    r1 = float(np.corrcoef(residual[:-1], residual[1:])[0, 1])
    n = len(y)
    n_eff = max(n * (1.0 - r1) / (1.0 + r1), 3.0)
    t_stat = slope / (stderr * np.sqrt(n / n_eff))
    return float(2 * stats.t.sf(abs(t_stat), n_eff - 2))


def _screen() -> dict:
    aq = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Hour h ends at h:00, so each label is assigned to the month of the hour it
    # closes: 2020-2025 runs from the 01:00 label of 1 January 2020 to the
    # 00:00 label of 1 January 2026.
    aq["date"] = (pd.to_datetime(aq[["year", "month", "day", "hour"]])
                  - pd.Timedelta(hours=1))
    sel = aq[aq["date"].dt.year.between(*_YEARS)]

    naive, adjusted = [], []
    for pollutant in _POLLUTANTS:
        for station in sorted(sel["station"].unique()):
            series = sel[sel["station"] == station].dropna(subset=[pollutant])
            monthly = series.groupby(
                [series["date"].dt.year, series["date"].dt.month]
            )[pollutant].mean().to_numpy()
            naive.append(stats.linregress(np.arange(len(monthly)), monthly)[3])
            adjusted.append(_adjusted_p(monthly))

    naive = np.asarray(naive)
    adjusted = np.asarray(adjusted)
    return {
        "tests": int(len(naive)),
        "naive": int((naive < _ALPHA).sum()),
        "autocorr": int((adjusted < _ALPHA).sum()),
        "survivors": _benjamini_hochberg(adjusted, _ALPHA),
    }


def validate_multiple_comparisons(
    response: str, runtime, turn: Turn
) -> ValidatorResult:
    names = ("tests_run", "naive_significant", "autocorr_significant",
             "fdr_survivors")
    got = {}
    for name in names:
        val = runtime.retrieve(name)
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")
        got[name] = val

    gt = _screen()
    errors = [
        f"{name}={got[name]}, expected {gt[key]}"
        for name, key in zip(names, ("tests", "naive", "autocorr", "survivors"))
        if not compare_numeric(got[name], gt[key], tolerance=0)
    ]
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True,
        f"correct: {gt['tests']} tests, {gt['naive']} naive, "
        f"{gt['autocorr']} after autocorrelation, {gt['survivors']} after FDR",
    )


tools = []
variables = [
    Variable(
        "tests_run",
        None,
        "Store the number of trend tests performed as an integer: one test "
        "per station-pollutant combination, reducing that combination's record "
        "to monthly means over whatever months it reports and fitting an "
        "ordinary least squares trend on the month index.",
    ),
    Variable(
        "naive_significant",
        None,
        "Store the number significant before any correction as an integer — a "
        "two-sided p-value below 0.05 from the ordinary regression.",
    ),
    Variable(
        "autocorr_significant",
        None,
        "Store the number still significant after the serial-correlation "
        "adjustment as an integer. Adjust each test by inflating its standard "
        "error by the square root of N over the AR(1) effective sample size "
        "N(1-r)/(1+r), and take the p-value from Student's t on two fewer "
        "than the effective degrees of freedom. Take r as the PEARSON "
        "CORRELATION between the residual series and itself lagged one month "
        "(each half against its own mean) — not as the autocovariance ratio "
        "sum(e_t e_{t-1}) / sum(e_t^2): one test in this record sits close "
        "enough to 0.05 that the two textbook estimators disagree on it.",
    ),
    Variable(
        "fdr_survivors",
        None,
        "Store the number of the adjusted p-values surviving a "
        "Benjamini-Hochberg false-discovery-rate correction at the same 0.05 "
        "as an integer: the largest rank whose p-value falls at or below its "
        "rank share of the level, rejecting every test up to that rank.",
    ),
]
validators = {"validate_multiple_comparisons": validate_multiple_comparisons}
