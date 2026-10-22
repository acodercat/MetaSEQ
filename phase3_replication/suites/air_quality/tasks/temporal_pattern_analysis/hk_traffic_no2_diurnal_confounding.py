"""Difficulty upgrade — hk_traffic_no2_diurnal_confounding (2026-10-06).

Temporal aggregation versus within-clock and month-clock association.
Professional consequence: Assess whether a congestion reduction can be assigned a NO2 benefit from this comparison.
Plausible wrong reading: Copying a correlation across 24 clock means into hourly or adjusted association is a different calculation; adjustment for temporal categories does not identify a traffic intervention.

Source concept: https://acp.copernicus.org/articles/18/6223/2018/
The paper supports the concept, not these dataset-specific answers. This case
uses its stated data, time conventions and statistical target; no causal or
surface-emission claim is inferred from a column or conditional association.

Independent raw-data results frozen before authoring the advanced helper:
{
  "hourly_congestion_no2_r": 0.4862595151043646,
  "clock_adjusted_congestion_no2_r": 0.10592358687408215,
  "month_clock_adjusted_congestion_no2_r": 0.2032127201408093
}

Numerical answers use the decimal places declared on their variables and
reports_as; counts use tolerance zero and finite-number guards. This excludes
adjacent reported answers, not just gross errors. All sample definitions and
units are visible. Author-selected analysis recipes are marked execution in
the scenario, and are not counted as autonomous method discovery.

The earlier module/validator remains for its original outputs; the current
scenario calls the extended validator requiring those and the added evidence.
The pre-upgrade content is archived in .codex-review/difficulty_20261006/before.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

_SPAN = ("2025-07-01", "2026-01-01")

# Aggregated server-side. The finite guard is what `paired_hours` states: two
# segment-hours carry a zero speed and an infinite index, and one infinity
# turns an hourly mean and then the whole correlation into a non-number.
_CONGESTION = text("""
    select datetime, avg(congestion_index) as congestion
    from hourly_road_segment_traffic
    where datetime > :lo and datetime <= :hi
      and congestion_index < 'Infinity'
    group by 1
""")

_ROADSIDE_NO2 = text("""
    select h.datetime, avg(h.no2) as no2
    from hourly_station_air_quality h
    join air_quality_station s on s.id = h.station_id
    where s.station_type = 'ROADSIDE'
      and h.datetime > :lo and h.datetime <= :hi
      and h.no2 is not null
    group by 1
""")


def _paired() -> pd.DataFrame:
    """One row per hour that has both a congestion figure and a roadside NO2."""
    span = {"lo": _SPAN[0], "hi": _SPAN[1]}
    congestion = read_frame(_CONGESTION, span)
    no2 = read_frame(_ROADSIDE_NO2, span)
    paired = congestion.merge(no2, on="datetime")
    paired["hour"] = paired["datetime"].dt.hour
    return paired


def _figures() -> Dict[str, object]:
    """The three scored quantities."""
    paired = _paired()
    shape = paired.groupby("hour")[["congestion", "no2"]].mean()
    anomaly = paired[["congestion", "no2"]].sub(
        paired.groupby("hour")[["congestion", "no2"]].transform("mean"))
    return {
        "diurnal_congestion_no2_r": float(shape["congestion"].corr(shape["no2"])),
        "paired_hours": int(len(paired)),
        "residual_congestion_no2_r": float(
            anomaly["congestion"].corr(anomaly["no2"])),
    }


def _unusable(name: str, val) -> ValidatorResult:
    """The failure for a variable that is missing or not a number, else None.

    `runtime.retrieve` stays in the validators: `tests/test_turn_stores.py`
    reads the names out of the validator source to check them against the
    turn's `stores`, and hiding the call here would take that check away.
    """
    if val is None:
        return ValidatorResult(False, f"{name} not set", variables_not_set=True)
    if not is_finite_number(val):
        return ValidatorResult(False, f"{name}={val!r} is not a number")
    return None


def validate_diurnal_correlation(response: str, runtime, turn: Turn) -> ValidatorResult:
    diurnal = runtime.retrieve("diurnal_congestion_no2_r")
    hours = runtime.retrieve("paired_hours")

    failure = _unusable("diurnal_congestion_no2_r", diurnal)
    if failure is not None:
        return failure
    if hours is None:
        return ValidatorResult(False, "paired_hours not set", variables_not_set=True)
    if not isinstance(hours, int) or isinstance(hours, bool):
        return ValidatorResult(False, f"paired_hours={hours!r} is not an integer")

    gt = _figures()
    wrong = []
    if not reports_as(diurnal, gt["diurnal_congestion_no2_r"], decimals=3):
        wrong.append(f"diurnal_congestion_no2_r={diurnal}, "
                     f"expected ~{gt['diurnal_congestion_no2_r']:.3f}")
    # Exact: the hour count is what makes a different infinity repair or a
    # different window endpoint visible instead of absorbed.
    if hours != gt["paired_hours"]:
        wrong.append(f"paired_hours={hours}, expected {gt['paired_hours']}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: r={diurnal} over {hours} paired hours")




def _normalise_verdict(value) -> str:
    return str(value).strip().lower().replace("_", " ").replace("\u2019", "'")


def _verdict_check(got, gt) -> ValidatorResult:
    """Score enumerated conclusions, booleans and exact strings or integers."""
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    errors = []
    for name, val in got.items():
        expected = gt[name]
        if isinstance(expected, bool):
            ok = (isinstance(val, bool) and val == expected) or (
                isinstance(val, str) and _normalise_verdict(val) in {str(expected).lower(),
                                                                      "yes" if expected else "no"})
        elif isinstance(expected, int):
            ok = isinstance(val, int) and not isinstance(val, bool) and val == expected
        else:
            ok = _normalise_verdict(val) == _normalise_verdict(expected)
        if not ok:
            errors.append(f"{name}={val!r}, expected {expected!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


def _licence_verdicts() -> Dict[str, object]:
    """The day-shape correlation is two clocks; checked by residualising on the
    hour of day alone and on hour x weekday, so the verdict does not depend on
    which cycle an analyst removes."""
    paired = _paired()
    weekday = (paired["datetime"] - pd.Timedelta(hours=1)).dt.dayofweek >= 5
    hour = (paired["datetime"] - pd.Timedelta(hours=1)).dt.hour
    shapes = paired.groupby(hour)[["congestion", "no2"]].mean()
    day_shape_r = float(shapes["congestion"].corr(shapes["no2"]))
    verdicts = set()
    for keys in ([hour], [hour, weekday]):
        resid = paired[["congestion", "no2"]] - paired.groupby(keys)[["congestion", "no2"]].transform("mean")
        residual_r = float(resid["congestion"].corr(resid["no2"]))
        verdicts.add((day_shape_r > 0.7, residual_r < 0.3))
    if len(verdicts) != 1:
        raise RuntimeError("the licence verdict is not invariant to the cycle removed")
    strong_shape, weak_residual = verdicts.pop()
    confounded = bool(strong_shape and weak_residual)
    return {
        # Derived from the same measurement, not asserted: the sentence the
        # colleague wants — that congestion explains most of the variation in
        # roadside NO2 — cannot be licensed by a day-shape correlation that is
        # confounded by the clock. A record whose residual relationship was
        # strong would license it, and would score the other way.
        "license_the_sentence": not confounded,
        "the_day_shape_is_confounded_by_the_clock": confounded,
    }


def validate_licence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "license_the_sentence": runtime.retrieve("license_the_sentence"),
        "the_day_shape_is_confounded_by_the_clock":
            runtime.retrieve("the_day_shape_is_confounded_by_the_clock"),
    }
    return _verdict_check(got, _licence_verdicts())

tools = []
variables = [
    Variable(
        "diurnal_congestion_no2_r",
        None,
        "Store the Pearson correlation between the twenty-four hour-of-day mean "
        "congestion values and the twenty-four hour-of-day mean roadside NO2 "
        "values, as a float to 3 decimal places, over the hours that carry "
        "both figures. Count only segment readings whose congestion index is "
        "a finite number — two segment-hours in this record divide by a speed "
        "of zero.",
    ),
    Variable(
        "paired_hours",
        None,
        "Store how many hours of the window carry both a congestion figure and "
        "a roadside NO2 figure, as an integer. An hour's roadside NO2 is the "
        "mean over the roadside stations reporting it. Count only segment "
        "readings whose congestion index is a finite number — two segment-hours "
        "in this record divide by a speed of zero.",
    ),
    Variable("license_the_sentence", None,
             "Store True if the colleague may write that congestion explains "
             "most of the variation in roadside nitrogen dioxide, else False."),
    Variable("the_day_shape_is_confounded_by_the_clock", None,
             "Store True if the day-shape relationship is confounded by the "
             "time of day both series follow, so that it cannot be read as the "
             "share of nitrogen dioxide congestion accounts for, else False. "
             "Take it as confounded if the day-shape correlation is strong, "
             "above 0.7, while what survives comparing each hour with its own "
             "time of day is weak, below 0.3."),
    Variable('hourly_congestion_no2_r', None, 'Store the Pearson correlation across the paired territory-road congestion and roadside NO2 hours of July-December 2025, to 3 decimal places, before clock adjustment. Use the same paired hours as the existing diurnal-mean correlation.'),
    Variable('clock_adjusted_congestion_no2_r', None, 'Store the partial Pearson correlation on those paired hours controlling for the 24 clock-hour categories, to 3 decimal places; retain the original hourly observation weights.'),
    Variable('month_clock_adjusted_congestion_no2_r', None, 'Store the partial Pearson correlation on the same hours controlling for separate month-of-year by clock-hour cells over July-December 2025, to 3 decimal places. Month is the observation month of the hour-ending record.'),
]


def validate_evidence_and_conclusion_full_review(response: str, runtime, turn: Turn) -> ValidatorResult:
    values = {
        'diurnal_congestion_no2_r': runtime.retrieve("diurnal_congestion_no2_r"),
        'paired_hours': runtime.retrieve("paired_hours"),
        'license_the_sentence': runtime.retrieve("license_the_sentence"),
        'the_day_shape_is_confounded_by_the_clock': runtime.retrieve("the_day_shape_is_confounded_by_the_clock"),
    }
    missing = [name for name, value in values.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    result = validate_diurnal_correlation(response, runtime, turn)
    if not result.success:
        return result
    result = validate_licence(response, runtime, turn)
    if not result.success:
        return result
    return ValidatorResult(True, "computed evidence and conclusion accepted")


# Difficulty upgrade 2026-10-06: older docstring magnitudes describe the
# earlier scoring surface. Added metrics below are recomputed from source data.
# Their single declared decimal report is checked by reports_as; counts are
# exact. The independent raw-data maps were frozen before these helpers.

def _advanced_metrics():
    frame = _paired()
    cols = ["congestion", "no2"]
    numeric = frame[cols]
    clock = numeric-frame.groupby("hour")[cols].transform("mean")
    month = (frame["datetime"]-pd.Timedelta(hours=1)).dt.month
    monthclock = numeric-frame.groupby([month, frame["hour"]])[cols].transform("mean")
    return {"hourly_congestion_no2_r": float(numeric["congestion"].corr(numeric["no2"])),
            "clock_adjusted_congestion_no2_r": float(clock["congestion"].corr(clock["no2"])),
            "month_clock_adjusted_congestion_no2_r": float(monthclock["congestion"].corr(monthclock["no2"]))}





def validate_harder_turn_1(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "diurnal_congestion_no2_r": runtime.retrieve("diurnal_congestion_no2_r"),
        "paired_hours": runtime.retrieve("paired_hours"),
        "license_the_sentence": runtime.retrieve("license_the_sentence"),
        "the_day_shape_is_confounded_by_the_clock": runtime.retrieve("the_day_shape_is_confounded_by_the_clock"),
        "hourly_congestion_no2_r": runtime.retrieve("hourly_congestion_no2_r"),
        "clock_adjusted_congestion_no2_r": runtime.retrieve("clock_adjusted_congestion_no2_r"),
        "month_clock_adjusted_congestion_no2_r": runtime.retrieve("month_clock_adjusted_congestion_no2_r"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_evidence_and_conclusion_full_review(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["hourly_congestion_no2_r"]) or not reports_as(got["hourly_congestion_no2_r"], gt["hourly_congestion_no2_r"], decimals=3):
        errors.append(f"hourly_congestion_no2_r={got["hourly_congestion_no2_r"]!r}, expected {gt["hourly_congestion_no2_r"]!r}")
    if not is_finite_number(got["clock_adjusted_congestion_no2_r"]) or not reports_as(got["clock_adjusted_congestion_no2_r"], gt["clock_adjusted_congestion_no2_r"], decimals=3):
        errors.append(f"clock_adjusted_congestion_no2_r={got["clock_adjusted_congestion_no2_r"]!r}, expected {gt["clock_adjusted_congestion_no2_r"]!r}")
    if not is_finite_number(got["month_clock_adjusted_congestion_no2_r"]) or not reports_as(got["month_clock_adjusted_congestion_no2_r"], gt["month_clock_adjusted_congestion_no2_r"], decimals=3):
        errors.append(f"month_clock_adjusted_congestion_no2_r={got["month_clock_adjusted_congestion_no2_r"]!r}, expected {gt["month_clock_adjusted_congestion_no2_r"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


validators = {
    "validate_diurnal_correlation": validate_diurnal_correlation,
    "validate_licence": validate_licence,
    "validate_harder_turn_1": validate_harder_turn_1,
    'validate_evidence_and_conclusion_full_review': validate_evidence_and_conclusion_full_review,
}
