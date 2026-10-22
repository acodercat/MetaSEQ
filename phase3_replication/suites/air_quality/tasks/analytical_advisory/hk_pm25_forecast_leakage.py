"""A climatology that has seen the year it forecasts (analytical_advisory).

BASELINE, rebuilt 2026-09-02 on the surface rule
(`docs/query_surface_audit.md`). The first turn asks a team's question —
what bar must a day-ahead PM2.5 forecast beat? — and scores which of the two
standard reference forecasts sets it and where it sits; the second relays a
colleague's proposal to refit the climatology with the verification year in
it, and scores whether the refit scores better (it does) and whether that
counts as skill (it cannot).

**The finding.** Hong Kong's general-station daily PM2.5 over 2025, each day
the mean of the hourly territory means, scored against the two reference
forecasts of forecast verification over all 365 days:

    persistence — yesterday's observed value        MAE 3.9396 ug/m3
    calendar-day climatology, record through 2024   MAE 5.4839
    the same climatology refitted with 2025 in it   MAE 4.5665

Persistence beats climatology, which is the honest headline and the reason a
day-ahead PM2.5 forecast has to clear a low but real bar before it is worth
having. The third figure is the one the second turn is about: refitting on
the verification year improves the climatology by 0.9174 ug/m3, closing 60 %
of its gap to persistence, and every bit of that improvement is the forecast
remembering the answer. With 365 days against five years of training the
leakage is a 1-in-6 contamination of each calendar day's mean, which is why
the effect is this large.

**What is scored, and what survives every route.** The earlier turns scored
the three errors to three decimals, and to make that unique the query had to
say how a day is formed, how a calendar day is keyed and where the training
window opens — three live runs found three window defects, all in the case
whose subject is which years a forecast may see. The rebuilt turns score
conclusions, and `_routes()` recomputes them under the constructions an
analyst could defensibly choose — a day as the mean of hourly territory
means or of pooled station-hours; a calendar day keyed by month-and-day or
by day-of-year; the training window opening at the record's start or at
2021 — and refuses to score if any conclusion differs:

    recipe    key        train from   persistence   clean   leaked
    network   month-day  record       3.9396        5.4839  4.5665
    network   day-of-yr  record       3.9396        5.4442  4.5334
    network   month-day  2021         3.9396        5.5465  4.4372
    pooled    month-day  record       3.9333        5.4671  4.5526
    pooled    day-of-yr  2021         3.9333        5.4752  4.3802

    the harder bar is persistence          every route
    the bar's MAE to one decimal           3.9 on every route
    the refit scores better than the fit   every route
    the improvement is skill               False — by construction

    NOT scored: the climatology's error (5.44 to 5.55 across routes), the
    leaked error (4.38 to 4.57), the day count.

`recipe` matters because station coverage varies within a day; `key`
because 29 February exists in the training record but not in 2025, so
day-of-year shifts 253 of the 365 test days onto a neighbour's mean;
`train from` because the record begins 2020-01-09 and its first year
contributes 358 days. None of them moves a scored conclusion.

**The judgement that is scored as a constant.** "Is the improvement skill?"
is not computed from the record: a reference forecast scored against a year
it was fitted on is not a forecast of that year, whatever the number says,
and the validator holds the answer as False for that reason. The claims
carry the argument the response has to make.

**What this case does not claim.** It does not establish that a climatology
is useless or that persistence is a good forecast; both are reference
baselines, and the gap between them says only that day-to-day persistence
carries more information at one day's range than the seasonal cycle does.
The leakage result is about verification practice, not about either
forecast.

Ground truth is recomputed from the database at validation time, under five
constructions at once.

**Gate C on the rebuilt turn (2026-09-02, `gate_c_t1c`):** flash computed
both errors correctly (3.9 and 5.5) and stored climatology as "the harder
reference", reasoning that "the larger error belongs to climatology, making
it the harder reference to beat". The word had carried no definition; the
variable now says the harder bar is the lower error. The Beijing sibling's
variable says the same.
"""

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, is_finite_number
from domains.hk.db import read_frame

_TEST_YEAR = ("2025-01-01", "2026-01-01")
_RECORD_START = "2020-01-01"      # the data itself begins 2020-01-09
PERSISTENCE = "persistence"
CLIMATOLOGY = "climatology"


def _daily(pooled: bool) -> pd.Series:
    """General-station daily PM2.5, hour-ending days.

    `pooled=False` is the domain prompt's TERRITORY FIGURES recipe — hourly
    territory means, then the day's mean; `pooled=True` averages the day's
    station-hours directly. They differ because coverage varies within a day.
    """
    if pooled:
        frame = read_frame(text("""
            select date(a.datetime - interval '1 hour') as day, avg(a.pm2_5) as pm25
            from hourly_station_air_quality a
            join air_quality_station s on s.id = a.station_id
            where s.station_type = 'GENERAL'
              and a.datetime > :lo and a.datetime <= :hi and a.pm2_5 is not null
            group by 1
        """), {"lo": _RECORD_START, "hi": _TEST_YEAR[1]})
        daily = frame.set_index(pd.to_datetime(frame["day"]))["pm25"]
    else:
        hourly = read_frame(text("""
            select a.datetime, avg(a.pm2_5) as pm25
            from hourly_station_air_quality a
            join air_quality_station s on s.id = a.station_id
            where s.station_type = 'GENERAL'
              and a.datetime > :lo and a.datetime <= :hi and a.pm2_5 is not null
            group by 1
        """), {"lo": _RECORD_START, "hi": _TEST_YEAR[1]})
        hourly["day"] = (hourly["datetime"] - pd.Timedelta(hours=1)).dt.normalize()
        daily = hourly.groupby("day")["pm25"].mean()
        daily.index = pd.DatetimeIndex(daily.index)
    return daily.sort_index()


def _errors(daily: pd.Series, key: str, train_from: str) -> Dict[str, float]:
    test = daily[(daily.index >= _TEST_YEAR[0]) & (daily.index < _TEST_YEAR[1])]
    label = (lambda idx: idx.strftime("%m-%d")) if key == "month-day" else (lambda idx: idx.dayofyear)

    def climatology(through: str) -> np.ndarray:
        train = daily[(daily.index >= train_from) & (daily.index < through)]
        by_day = train.groupby(label(train.index)).mean()
        return by_day.reindex(label(test.index)).to_numpy(dtype=float)

    def mae(forecast) -> float:
        return float(np.nanmean(np.abs(np.asarray(forecast, dtype=float) - test.to_numpy())))

    return {
        "persistence": mae(daily.shift(1).reindex(test.index).to_numpy()),
        "clean": mae(climatology(_TEST_YEAR[0])),
        "leaked": mae(climatology(_TEST_YEAR[1])),
    }


def _routes() -> List[Tuple[str, Dict[str, float]]]:
    network, pooled = _daily(pooled=False), _daily(pooled=True)
    return [
        ("network, month-day, from the record", _errors(network, "month-day", _RECORD_START)),
        ("network, day-of-year, from the record", _errors(network, "day-of-year", _RECORD_START)),
        ("network, month-day, from 2021", _errors(network, "month-day", "2021-01-01")),
        ("pooled, month-day, from the record", _errors(pooled, "month-day", _RECORD_START)),
        ("pooled, day-of-year, from 2021", _errors(pooled, "day-of-year", "2021-01-01")),
    ]


def _conclusions(errors: Dict[str, float]) -> Dict[str, object]:
    harder = PERSISTENCE if errors["persistence"] < errors["clean"] else CLIMATOLOGY
    return {
        "harder_reference": harder,
        "bar_mae": round(min(errors["persistence"], errors["clean"]), 1),
        "refit_scores_better": bool(errors["leaked"] < errors["clean"]),
    }


def _figures() -> Dict[str, object]:
    table = [(name, _conclusions(errors)) for name, errors in _routes()]
    out: Dict[str, object] = {}
    for key in table[0][1]:
        values = {row[key] for _, row in table}
        if len(values) != 1:
            raise RuntimeError(f"{key} is not invariant across constructions: "
                               + "; ".join(f"{n}={row[key]!r}" for n, row in table))
        out[key] = values.pop()
    # A judgement, not a computation: a reference scored on the year it was
    # fitted to is not a forecast of that year (see the docstring).
    out["refit_improvement_is_skill"] = False
    return out


def _normalise(value) -> str:
    return str(value).strip().lower()


def _check(got: Dict[str, object]) -> ValidatorResult:
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
        elif isinstance(expected, float):
            ok = is_finite_number(val) and round(float(val), 1) == expected
        else:
            ok = _normalise(val) == _normalise(expected)
        if not ok:
            errors.append(f"{name}={val!r}, expected {expected!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


def validate_reference_bar(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "harder_reference": runtime.retrieve("harder_reference"),
        "bar_mae": runtime.retrieve("bar_mae"),
    })


def validate_refit(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "refit_scores_better": runtime.retrieve("refit_scores_better"),
        "refit_improvement_is_skill": runtime.retrieve("refit_improvement_is_skill"),
    })


tools = []
variables = [
    Variable("harder_reference", None,
             "Store which of the two standard reference forecasts sets the "
             "harder bar for a day-ahead forecast of the general stations' "
             "daily PM2.5 over 2025, as one of exactly these strings: "
             f"'{PERSISTENCE}' (yesterday's observed value carried forward), "
             f"'{CLIMATOLOGY}' (the calendar day's mean over the earlier years "
             "of the record). The bar is the reference's mean absolute error "
             "over the days of 2025, and the harder bar is the LOWER error — "
             "the reference a forecast has to beat before it adds anything."),
    Variable("bar_mae", None,
             "Store that harder reference's mean absolute error over 2025, as a "
             "float in ug/m3 to 1 decimal place."),
    Variable("refit_scores_better", None,
             "Store True if the calendar-day climatology refitted with 2025 in "
             "its record scores a lower mean absolute error over 2025 than the "
             "one fitted without it, else False."),
    Variable("refit_improvement_is_skill", None,
             "Store True if the change in score from that refit is evidence of "
             "forecast skill, else False."),
]


def validate_evidence_and_conclusion_full_review(response: str, runtime, turn: Turn) -> ValidatorResult:
    values = {
        'harder_reference': runtime.retrieve("harder_reference"),
        'bar_mae': runtime.retrieve("bar_mae"),
        'refit_scores_better': runtime.retrieve("refit_scores_better"),
        'refit_improvement_is_skill': runtime.retrieve("refit_improvement_is_skill"),
    }
    missing = [name for name, value in values.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    result = validate_reference_bar(response, runtime, turn)
    if not result.success:
        return result
    result = validate_refit(response, runtime, turn)
    if not result.success:
        return result
    return ValidatorResult(True, "computed evidence and conclusion accepted")

validators = {
    "validate_reference_bar": validate_reference_bar,
    "validate_refit": validate_refit,
    'validate_evidence_and_conclusion_full_review': validate_evidence_and_conclusion_full_review,
}
