"""Difficulty upgrade — hk_sunshine_ozone_scale_reversal (2026-10-06).

Daily, season-adjusted and climatological ozone-radiation scales.
Professional consequence: Assess a sunshine term before fitting or interpreting a forecast.
Plausible wrong reading: A climatological sign is not the daily slope; contemporaneous regression and month controls do not establish causal photochemical sensitivity or operational forecast skill.

Source concept: https://acp.copernicus.org/articles/18/6223/2018/
The paper supports the concept, not these dataset-specific answers. This case
uses its stated data, time conventions and statistical target; no causal or
surface-emission claim is inferred from a column or conditional association.

Independent raw-data results frozen before authoring the advanced helper:
{
  "pooled_sunshine_slope": 0.872267401759657,
  "month_adjusted_sunshine_slope": 1.3147455746878232,
  "monthly_climatology_correlation": -0.572710324642772,
  "sunshine_paired_days": 2184
}

The three regression figures are scored within 0.002 of the unrounded figure
(compare_numeric), which accepts their declared three-decimal report; the
count uses tolerance zero. The band replaced the three-decimal reports_as
after the reliability_tool study (2026-10-12): under it the month-adjusted
slope turned on whether the hourly series is reindexed to a continuous grid
before the 8-hour rolling mean (1.3144 without, 1.3147 with), a step the
variables do not state, and 16 turns across three models, otherwise correct,
failed on it alone. Assigning windows to the stamp date instead of the
hour-ending day reads 0.8784, 1.3175 and -0.565, which the band still
refuses on every figure. All sample definitions and
units are visible. Author-selected analysis recipes are marked execution in
the scenario, and are not counted as autonomous method discovery.

The earlier module/validator remains for its original outputs; the current
scenario calls the extended validator requiring those and the added evidence.
The pre-upgrade content is archived in .codex-review/difficulty_20261006/before.
"""

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number
from domains.hk.db import read_frame

_SPAN = {"lo": "2020-01-01", "hi": "2026-01-01"}
_MIN_HOURS = 6
SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
           6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}


def _radiation() -> pd.DataFrame:
    rad = pd.read_csv(DATA_DIR / "radiation_hko.csv")
    rad["day"] = pd.to_datetime(rad["date"])
    rad = rad[(rad["day"] >= _SPAN["lo"]) & (rad["day"] < _SPAN["hi"])]
    return rad[["day", "global_solar_radiation_mj_m2"]].rename(
        columns={"global_solar_radiation_mj_m2": "rad"})


def _ozone_routes() -> List[Tuple[str, pd.Series]]:
    """Three measures of the territory's daily ozone, indexed by hour-ending day."""
    hourly = read_frame(text("""
        select datetime, avg(o3) as o3
        from hourly_station_air_quality
        where o3 is not null and datetime > :lo and datetime <= :hi
        group by datetime order by datetime
    """), _SPAN).set_index("datetime")["o3"].asfreq("h")
    start = hourly.index - pd.Timedelta(hours=1)
    peak = hourly.groupby(start.normalize()).max()
    mean = hourly.groupby(start.normalize()).mean()
    rolling = hourly.rolling(8, min_periods=_MIN_HOURS).mean()
    ending = pd.Series(rolling.values, index=rolling.index - pd.Timedelta(hours=1))
    mda8 = ending.groupby(ending.index.normalize()).max()
    return [("hourly peak", peak), ("MDA8", mda8), ("daily mean", mean)]


def _paired(ozone: pd.Series) -> pd.DataFrame:
    paired = _radiation().merge(ozone.rename("o3"), left_on="day", right_index=True).dropna()
    paired["month"] = paired["day"].dt.month
    paired["season"] = paired["month"].map(SEASONS)
    return paired


def _conclusions(name: str, paired: pd.DataFrame) -> Dict[str, object]:
    pooled = paired["rad"].corr(paired["o3"])
    demeaned = paired[["rad", "o3"]] - paired.groupby("month")[["rad", "o3"]].transform("mean")
    within = float(np.polyfit(demeaned["rad"], demeaned["o3"], 1)[0])
    if (pooled > 0) != (within > 0):
        raise RuntimeError(f"{name}: pooled and within-month signs disagree "
                           f"({pooled:.3f} against {within:.3f})")
    climatology = []
    for level in ("month", "season"):
        means = paired.groupby(level)[["rad", "o3"]].mean()
        climatology.append({
            "sunniest_has_most_ozone": means["rad"].idxmax() == means["o3"].idxmax(),
            "negative": means["rad"].corr(means["o3"]) < 0,
        })
    if len({(c["sunniest_has_most_ozone"], c["negative"]) for c in climatology}) != 1:
        raise RuntimeError(f"{name}: monthly and seasonal climatology disagree {climatology}")
    by_month = paired.groupby("month").apply(
        lambda g: g["rad"].corr(g["o3"]), include_groups=False)
    return {
        "months_with_more_ozone_on_sunnier_days": int((by_month > 0).sum()),
        "sunniest_season_has_the_most_ozone": bool(climatology[0]["sunniest_has_most_ozone"]),
        "within_month_slope": within,
        "monthly_climatology_r": float(
            paired.groupby("month")[["rad", "o3"]].mean().corr().loc["rad", "o3"]),
    }


# What PV scores, and so what must hold under every ozone summary. The other
# keys `_conclusions()` returns — the within-month slope and the monthly
# climatology correlation — are measured context for the docstring and the
# claims, and they are NOT invariant (the slope runs 0.909 to 1.574 across the
# three summaries), which is exactly why they are not scored.
_SCORED = ("months_with_more_ozone_on_sunnier_days", "sunniest_season_has_the_most_ozone")


def _figures() -> Dict[str, object]:
    table = [(name, _conclusions(name, _paired(ozone))) for name, ozone in _ozone_routes()]
    out: Dict[str, object] = {}
    for key in _SCORED:
        values = {row[key] for _, row in table}
        if len(values) != 1:
            raise RuntimeError(f"{key} is not invariant across constructions: "
                               + "; ".join(f"{n}={row[key]!r}" for n, row in table))
        out[key] = values.pop()
    out["context"] = {name: {k: v for k, v in row.items() if k not in _SCORED}
                      for name, row in table}
    return out


def _normalise(value) -> str:
    return str(value).strip().lower()


def validate_sunshine_term(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "months_with_more_ozone_on_sunnier_days":
            runtime.retrieve("months_with_more_ozone_on_sunnier_days"),
        "sunniest_season_has_the_most_ozone": runtime.retrieve("sunniest_season_has_the_most_ozone"),
    }
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    for name, val in got.items():
        expected = gt[name]
        if isinstance(expected, bool):
            ok = (isinstance(val, bool) and val == expected) or (
                isinstance(val, str) and _normalise(val) in {str(expected).lower(),
                                                              "yes" if expected else "no"})
        else:
            ok = _normalise(val) == _normalise(expected)
        if not ok:
            errors.append(f"{name}={val!r}, expected {expected!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


tools = []
variables = [
    Variable("months_with_more_ozone_on_sunnier_days", None,
             "Store how many of the twelve calendar months carry more of the "
             "territory's ozone on their own sunnier days, over 2020 through "
             "2025, as an integer from 0 to 12. Take all of a calendar month's "
             "days across the six years together (every June, say) and count "
             "the month if its daily ozone rises with its daily sunshine, that "
             "is, if the ordinary (Pearson) correlation between the two over "
             "those days is positive. Sunshine is King's Park's daily global "
             "solar radiation, every day the record reports, including the few "
             "it flags as incomplete; the day's ozone is the territory's, on "
             "whichever daily measure the team would forecast."),
    Variable("sunniest_season_has_the_most_ozone", None,
             "Store True if the season with the most solar radiation is also the "
             "season with the most ozone over the same period, else False."),
    Variable('pooled_sunshine_slope', None, 'Store the OLS slope with an intercept of territory daily maximum eight-hour O3 on daily global solar radiation, in (µg/m³)/(MJ/m²) to 3 decimal places. Use territory hourly means, trailing eight-clock-hour windows with at least six valid hours and all 24 ending hours, assigned to hour-ending days; pair with reported daily HKO radiation in 2020-2025.'),
    Variable('month_adjusted_sunshine_slope', None, 'Store the radiation coefficient in the same daily model with an intercept and 12 month-of-year fixed effects shared across years, to 3 decimal places in the same units. Keep exactly the same paired days; these are month-of-year effects, not year-month effects.'),
    Variable('monthly_climatology_correlation', None, 'Store the Pearson correlation between the 12 month-of-year means of radiation and daily maximum-eight-hour ozone formed from those paired days, to 3 decimal places; weight those 12 climatological months equally.'),
    Variable('sunshine_paired_days', None, 'Store the exact integer count of paired daily radiation and maximum-eight-hour ozone observations in 2020-2025.'),
]

# Difficulty upgrade 2026-10-06: older docstring magnitudes describe the
# earlier scoring surface. Added metrics below are recomputed from source data.
# They are checked within 0.002 (see the docstring); counts are exact. The
# independent raw-data maps were frozen before these helpers.

def _advanced_metrics():
    ozone = dict(_ozone_routes())["MDA8"]
    frame = _paired(ozone)
    x, y = frame["rad"], frame["o3"]
    residual = frame[["rad", "o3"]]-frame.groupby("month")[["rad", "o3"]].transform("mean")
    climatology = frame.groupby("month")[["rad", "o3"]].mean()
    return {"pooled_sunshine_slope": float(np.polyfit(x, y, 1)[0]),
            "month_adjusted_sunshine_slope": float(np.polyfit(residual["rad"], residual["o3"], 1)[0]),
            "monthly_climatology_correlation": float(climatology["rad"].corr(climatology["o3"])),
            "sunshine_paired_days": len(frame)}






def validate_harder_turn_1(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "months_with_more_ozone_on_sunnier_days": runtime.retrieve("months_with_more_ozone_on_sunnier_days"),
        "sunniest_season_has_the_most_ozone": runtime.retrieve("sunniest_season_has_the_most_ozone"),
        "pooled_sunshine_slope": runtime.retrieve("pooled_sunshine_slope"),
        "month_adjusted_sunshine_slope": runtime.retrieve("month_adjusted_sunshine_slope"),
        "monthly_climatology_correlation": runtime.retrieve("monthly_climatology_correlation"),
        "sunshine_paired_days": runtime.retrieve("sunshine_paired_days"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_sunshine_term(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["pooled_sunshine_slope"]) or not compare_numeric(got["pooled_sunshine_slope"], gt["pooled_sunshine_slope"], tolerance=0.002):
        errors.append(f"pooled_sunshine_slope={got["pooled_sunshine_slope"]!r}, expected {gt["pooled_sunshine_slope"]!r}")
    if not is_finite_number(got["month_adjusted_sunshine_slope"]) or not compare_numeric(got["month_adjusted_sunshine_slope"], gt["month_adjusted_sunshine_slope"], tolerance=0.002):
        errors.append(f"month_adjusted_sunshine_slope={got["month_adjusted_sunshine_slope"]!r}, expected {gt["month_adjusted_sunshine_slope"]!r}")
    if not is_finite_number(got["monthly_climatology_correlation"]) or not compare_numeric(got["monthly_climatology_correlation"], gt["monthly_climatology_correlation"], tolerance=0.002):
        errors.append(f"monthly_climatology_correlation={got["monthly_climatology_correlation"]!r}, expected {gt["monthly_climatology_correlation"]!r}")
    if not is_finite_number(got["sunshine_paired_days"]) or not compare_numeric(got["sunshine_paired_days"], gt["sunshine_paired_days"], tolerance=0):
        errors.append(f"sunshine_paired_days={got["sunshine_paired_days"]!r}, expected {gt["sunshine_paired_days"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


validators = {
    "validate_sunshine_term": validate_sunshine_term,
    "validate_harder_turn_1": validate_harder_turn_1,
}
