"""Beijing's PM2.5 trend and the interval that is too narrow
(statistical_characterization).

**The 2026-10-06 difficulty upgrade was reverted on 2026-10-07.** It had added
the annual slope, both Newey-West interval endpoints at two bandwidths and the
day count, and pinned the estimator on the variables: "Bartlett weights and
bandwidth 30 days, z=1.96, and no finite-sample covariance correction". P1 held
— every degree of freedom was named — but nothing was left for the agent to
choose, and no atmospheric knowledge was required: the turn became an
econometric implementation exercise scored at three decimals.

What that bought, measured: of the four PV failures in that round this was one,
and its failure was a day-boundary reading worth one unit in the last place
(slope -1.867 against -1.8664, hac30_upper -0.092 against -0.0913). The corpus
already tests the day convention deliberately elsewhere, so the four endpoints
added execution burden and a second place for the same convention error, not
discrimination. Meanwhile the turn's one claim, `precision_not_conclusion`,
scored 0.00 against the same model — the science was being missed where it was
asked for, and the added arithmetic did not touch it.

So the turn is back to the estimand without the estimator: fit the trend,
report the residual autocorrelation, and say whether the conclusion survives
Newey-West bandwidths through 120 days. How to form a HAC interval is the
agent's to decide, and nothing scored depends on which convention it picks —
only on whether the separation from zero survives the range.

"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from scipy import stats

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, reports_as, is_finite_number
from tasks import Turn

_YEARS = (2020, 2025)
_DAYS_PER_YEAR = 365.25


FALLING = "falling"
RISING = "rising"
NO_TREND = "no clear trend"


def _daily() -> pd.Series:
    aq = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Label h is the hour ending at h:00, so a day is its labels 1-23 and label
    # 0 of the next date, and 2020-2025 runs from 2020-01-01 01:00 through
    # 2026-01-01 00:00.
    aq["ts"] = pd.to_datetime(aq[["year", "month", "day", "hour"]])
    aq["date"] = (aq["ts"] - pd.Timedelta(hours=1)).dt.normalize()
    obs = aq[aq["date"].dt.year.between(*_YEARS)].dropna(subset=["PM2.5"])
    hourly = obs.groupby(["date", "ts"])["PM2.5"].mean()
    return hourly.groupby(level=0).mean().sort_index()


def _newey_west_halfwidth(t: np.ndarray, residual: np.ndarray, lag: int) -> float:
    u = (t - t.mean()) * residual
    s = float((u ** 2).sum())
    for k in range(1, lag + 1):
        s += 2.0 * (1.0 - k / (lag + 1)) * float((u[:-k] * u[k:]).sum())
    return 1.96 * np.sqrt(s) / float(((t - t.mean()) ** 2).sum())


def _trend() -> dict:
    """The slope's direction and two verdicts, across the ways an analyst could
    defensibly set the interval: the AR(1) effective-sample-size correction
    (half-width 1.50), Newey-West at lags 10, 30, 45, 60, 90 and 120 (1.36,
    1.78, 1.93, 2.01, 2.02, 1.98), a regression on monthly means (1.75), a
    monthly block bootstrap (1.65), and the Theil-Sen interval (-1.38 to
    -0.53). The textbook interval is 0.73 and every route is wider, so
    `textbook_interval_too_narrow` is invariant.

    **Whether the decline separates from zero is NOT invariant, and that is now
    the finding rather than an embarrassment.** The slope is -1.87 per year;
    the bandwidths at 45 days and beyond put half-widths of 1.93 to 2.02
    against it, so they cover zero, while the shorter ones do not — and the
    case's own lag-30 route clears the bar by five per cent. Until Gate B round
    21 this helper excluded the long bandwidths with the argument that the
    residual correlation "has decayed well inside ten days (r1 = 0.62)", which
    the reviewer rejected as post hoc, and rightly: bandwidth is an ordinary
    analyst choice, the residual autocorrelation is still positive at lags 10,
    20, 30 and 45 (0.108, 0.050, 0.068, 0.056) and returns to +0.14 at 365 days because six
    years of daily PM2.5 carry an annual cycle this linear fit does not remove.
    A route was being excluded exactly where it flipped the conclusion.

    So the scored verdict is the sensitivity itself. `separation_from_zero_is_robust`
    is False, and reaching it takes what the query asks for — allowances for
    persistence across the named range, a few days to 120, not one of them."""
    daily = _daily()
    y, t = daily.to_numpy(), np.arange(len(daily), dtype=float)
    slope, intercept, _r, _p, stderr = stats.linregress(t, y)
    residual = y - (intercept + slope * t)
    n = len(y)
    r1 = float(np.corrcoef(residual[:-1], residual[1:])[0, 1])
    n_eff = n * (1.0 - r1) / (1.0 + r1)
    per_year = slope * _DAYS_PER_YEAR
    naive = 1.96 * stderr * _DAYS_PER_YEAR
    corrected = {
        "AR(1) effective sample size": float(stats.t.ppf(0.975, n_eff - 2) * stderr * np.sqrt(n / n_eff) * _DAYS_PER_YEAR),
    }
    for lag in (10, 30, 45, 60, 90, 120):
        corrected[f"Newey-West, lag {lag}"] = _newey_west_halfwidth(t, residual, lag) * _DAYS_PER_YEAR
    monthly = daily.resample("MS").mean()
    tm = np.arange(len(monthly), dtype=float)
    ms, _mi, _r, _p, mse = stats.linregress(tm, monthly.to_numpy())
    corrected["monthly means"] = float(stats.t.ppf(0.975, len(tm) - 2) * mse * 12)
    rng = np.random.default_rng(0)
    blocks = [g.to_numpy() for _, g in daily.groupby([daily.index.year, daily.index.month])]
    resampled = []
    for _ in range(300):
        series = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        resampled.append(np.polyfit(np.arange(len(series)), series, 1)[0] * _DAYS_PER_YEAR)
    corrected["monthly block bootstrap"] = float(1.96 * np.std(resampled))
    theil = stats.theilslopes(y, t)
    slopes = {"ordinary least squares": per_year, "monthly means": ms * 12, "Theil-Sen": theil[0] * _DAYS_PER_YEAR}
    directions = {FALLING if v < 0 else RISING for v in slopes.values()}
    if len(directions) != 1:
        raise RuntimeError(f"the trend direction is not invariant: {slopes}")
    survives = {name: bool(abs(per_year) > hw) for name, hw in corrected.items()}
    survives["Theil-Sen interval"] = bool(theil[3] < 0)
    # Deliberately NOT asserted invariant: the disagreement among these is the
    # scored finding. `separation_from_zero_is_robust` is the conjunction.
    too_narrow = {name: bool(naive < hw) for name, hw in corrected.items()}
    if len(set(too_narrow.values())) != 1:
        raise RuntimeError(f"whether the textbook interval is too narrow is not invariant: {too_narrow}")
    return {
        "residual_autocorrelation": float(r1),
        "trend_direction": directions.pop(),
        "textbook_interval_too_narrow": too_narrow["AR(1) effective sample size"],
        "separation_from_zero_is_robust": all(survives.values()),
        "survives": survives,
        "trend": float(per_year), "naive": float(naive), "corrected": corrected,
    }


def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_trend_uncertainty(response: str, runtime, turn: Turn) -> ValidatorResult:
    direction = runtime.retrieve("trend_direction")
    narrow = runtime.retrieve("textbook_interval_too_narrow")
    survives = runtime.retrieve("separation_from_zero_is_robust")
    autocorrelation = runtime.retrieve("residual_autocorrelation")
    missing = [n for n, v in (("trend_direction", direction), ("textbook_interval_too_narrow", narrow),
                              ("separation_from_zero_is_robust", survives),
                              ("residual_autocorrelation", autocorrelation)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _trend()
    errors = []
    if not is_finite_number(autocorrelation):
        errors.append(f"residual_autocorrelation={autocorrelation!r} is not a number")
    # The requested two-decimal report is 0.62. Alternate daily constructions
    # report the same figure; a tolerance must not admit 0.60, 0.61 or 0.63.
    elif not reports_as(autocorrelation, gt["residual_autocorrelation"], decimals=2):
        errors.append(f"residual_autocorrelation={autocorrelation}, "
                      f"expected ~{gt['residual_autocorrelation']:.2f}")
    if str(direction).strip().lower() != gt["trend_direction"]:
        errors.append(f"trend_direction={direction!r}, expected {gt['trend_direction']!r}")
    for name, val in (("textbook_interval_too_narrow", narrow), ("separation_from_zero_is_robust", survives)):
        if not _bool_ok(val, gt[name]):
            errors.append(f"{name}={val!r}, expected {gt[name]}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    surviving = sum(gt["survives"].values())
    return ValidatorResult(True, f"correct: {gt['trend_direction']} ({gt['trend']:+.2f} ug/m3 per year); the "
                                 f"textbook interval (+/-{gt['naive']:.2f}) is too narrow, and separation from "
                                 f"zero holds under {surviving} of {len(gt['survives'])} intervals, not all")


tools = []
variables = [
    Variable("residual_autocorrelation", None,
             "Store the lag-one autocorrelation of the residuals about that "
             "ordinary least-squares straight-line trend against calendar date, without "
             "seasonal terms — how strongly one day's departure from it predicts the "
             "next day's — as a float, 2 decimal places."),
    Variable("trend_direction", None,
             "Store the direction of Beijing's daily PM2.5 over 2020 through "
             f"2025, as one of exactly these strings: '{FALLING}', '{RISING}', "
             f"'{NO_TREND}'."),
    Variable("textbook_interval_too_narrow", None,
             "Store True if the textbook confidence interval on that trend — "
             "the one that treats the daily values as independent — is too "
             "narrow for this series, else False."),
    Variable("separation_from_zero_is_robust", None,
             "Store True if the trend stays distinguishable from zero, at 95 %, "
             "under every allowance for the day-to-day persistence of the "
             "series from short-memory ones out to persistence lasting about "
             "four months — Newey-West bandwidths anywhere up to 120 days "
             "included — else False."),
]
validators = {"validate_trend_uncertainty": validate_trend_uncertainty}
