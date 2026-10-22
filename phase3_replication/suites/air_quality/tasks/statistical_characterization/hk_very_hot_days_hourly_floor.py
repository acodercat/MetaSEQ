"""An hourly record can only put a floor under a threshold count — and the
Observatory's 53 very hot days of 2025 come out as 33
(statistical_characterization).

BASELINE. A "very hot day" is a defined statistic: the Hong Kong Observatory
counts a day whose maximum temperature at its headquarters station reaches
33.0 degrees or more. For 2025 the Observatory published 53 — the third
highest on record — with 4 in October, a record for the month, and an annual
mean of 24.3 degrees (HKO, The Year's Weather 2025). This database carries
the headquarters station ("HK Observatory" in `weather_station`) at hourly
resolution, 8,757 hours in 2025, with an annual mean of 24.368 — the same
station, the same year. Counting days whose HIGHEST HOURLY VALUE reaches 33.0
gives 33, and 2 in October.

**Why 33 and not 53.** The published maximum is the highest instantaneous
reading of the day, taken from the station's one-minute data; each row of
this record is the HOURLY MEAN of the station's ten-minute readings (the
stored values are sixths — 19.17, 86.50, 78.33), stamped at the end of the
hour. A mean cannot exceed the readings it averages, so a day's highest
hourly value sits at or below its true maximum — on a day whose real peak
is 33.2 the record can show 32.8 — and the count of days reaching 33.0 is
a lower bound on the statistic, not a measurement of it. The record makes
the size of the effect visible: 25 days of 2025 have an HKO hourly maximum
in [32.5, 33.0), and 33 + 25 = 58 brackets the published 53.

**The nesting is exact, and it is what fixed the weather stamp.** Against
HKO's published daily maxima and minima at the Observatory for 2025, the
record's daily maximum is at or below the published one on 365 of 365 days
and its daily minimum at or above on 365 of 365 — under the hour-ending
day. Read as its own hour, the stamp puts the record ABOVE the published
maximum on 21 days (by up to 0.58 degrees) and below the published minimum
on 4, which no sub-sample of one trace can do. Gate B round 18 found the 21
and read it as proof that the two records were not one trace; the 0 under
the other reading is what established that `hourly_station_weather` is
hour-ending, and the domain prompt now says so for both tables.

**Other quantities, each with a number** (none is the statistic; the
Observatory's definition names the station and the threshold, so these are
answers to different questions rather than tempting paths — the reason
this is a baseline). The domain's
TERRITORY FIGURES convention — mean across reporting stations, then the
threshold — gives 8 days: thirty-nine stations report temperature, among
them Tai Mo Shan at 955 m, Ngong Ping at 593 m, Tate's Cairn at 572 m and The
Peak at 406 m (the station annual means fit a lapse of -0.70 degrees per
100 m), and averaging before thresholding removes the extremes on top of
that. "Any station at 33 or above" gives 100. Restricting the territory mean
to stations below 100 m gives 21. Lowering the threshold to 32.5 to "match"
the Observatory gives 58. None of these is the statistic; the first is the
domain convention applied to a quantity that is not a territory figure.

**Turn 1** asks the count and scores 33 — the number this record supports
under the Observatory's definition (the count is the same whichever day
the midnight stamp is given to). **Turn 2** relays the desk: the
Observatory says 53, we say 33, which is right and can we publish 33? It
scored, in a design the 2026-09-02 rebuild replaced, the two facts that
settle it — the 25 near-miss days, and the
station's annual mean (24.37, matching the published 24.3, so the station
and the year are the right ones and the gap is not a data error) — and the
claims carry the judgement: 33 is a floor set by hourly averaging; the
published figure stands; the threshold is not to be lowered to reproduce it.

**What generalises.** Every count of hours or days at or above a
threshold made from an hourly-mean table — very hot days here, gusts
above a warning level, visibility below a criterion — is a floor for the
same reason, and a count at or BELOW one is a ceiling (the mirror case). The case is placed here
rather than in a weather category because that is the statistical fact it
teaches, and the ozone AQO is where the corpus will meet it next.

**Pins, and where each one goes** (`case_design_standard.md` §3.1). Turn 1's
variable names the Observatory's definition by reference and nothing else:
knowing, or finding, that the statistic is defined at the headquarters
station and not across the network is the exam, and every naive path above
is a different answer to that question. Turn 2's query states the definition
in the desk's words, because by then the question is about sampling, not
definition. Days are the domain's hour-ending days; a day's maximum is the
highest hourly value stored for it.

**Readings measured and excluded** (turn 1 count / turn 2 near-miss days /
annual mean):

    territory-mean days at 33            8
    any-station days at 33             100
    stations below 100 m, mean          21
    threshold lowered to 32.5           58
    near-miss band read as [32, 33)     42
    near-miss band read as [32, 32.5)   17
    territory-mean annual temperature   23.25
    below-100 m annual temperature      23.71

Counts are exact. (The annual mean was scored with `reports_as` at two
decimals in the design the 2026-09-02 rebuild replaced; it is still computed
as context and read by nothing.)

**Overlap, stated.** `hk_hot_nights_hourly_ceiling` is this case's mirror —
the same record and mechanism on a minimum-based statistic, where the bias
runs the other way (61 hourly-record hot nights against the Observatory's
54) — and the two are meant to be read together. `hk_weather_variable_coverage`
is about which stations carry which variables; `hk_cyclone_approach_and_passage`
uses the gust and pressure extremes of one storm. Neither of those asks what
an hourly record can and cannot say about a threshold statistic.

All ground truths are recomputed from the database at validation time. The
published 53 is not scored — it is not in the record — and appears only in
the desk's note.

**Turn 2 rebuilt 2026-09-01 on the surface rule.** The desk's objection stays;
the near-miss band and the annual-mean check are no longer dictated. PV
scores which figure to publish (the Observatory's) and what our count is (a
floor). `_reconciliation_verdicts()` re-derives the floor from the record —
the hourly count must not exceed the published 53 — rather than asserting
it. The near-miss count and the annual mean stay in this docstring as the
evidence the claims expect a response to find for itself.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult
from domains.hk.db import read_frame

_STATION = "HK Observatory"
_THRESHOLD = 33.0
_NEAR_MISS_LOW = 32.5


def _hko_daily() -> pd.DataFrame:
    return read_frame(text("""
        select date(h.datetime - interval '1 hour') as day, max(h.temperature) as tmax,
               avg(h.temperature) as tmean, count(h.temperature) as n
        from hourly_station_weather h
        join weather_station s on s.id = h.station_id
        where s.name_en = :station and h.temperature is not null
          and h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
        group by 1
    """), {"station": _STATION})


def _figures() -> Dict[str, object]:
    daily = _hko_daily()
    hourly_mean = float((daily["tmean"] * daily["n"]).sum() / daily["n"].sum())
    return {
        "very_hot_days_2025": int((daily["tmax"] >= _THRESHOLD).sum()),
        "near_miss_days_2025": int(((daily["tmax"] >= _NEAR_MISS_LOW)
                                    & (daily["tmax"] < _THRESHOLD)).sum()),
        "hko_annual_mean_temperature_2025": hourly_mean,
    }


def _is_int(val) -> bool:
    """`bool` is an `int` subclass; True must not pass as a count of one."""
    return isinstance(val, int) and not isinstance(val, bool)


def validate_count(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = runtime.retrieve("very_hot_days_2025")
    if got is None:
        return ValidatorResult(False, "very_hot_days_2025 not set", variables_not_set=True)
    if not _is_int(got):
        return ValidatorResult(False, f"very_hot_days_2025={got!r} is not an integer")
    gt = _figures()["very_hot_days_2025"]
    if got != gt:
        return ValidatorResult(False, f"very_hot_days_2025={got}, expected {gt}")
    return ValidatorResult(True, f"correct: {gt} days")



_DAY = ("A day is the calendar day the stored hours BELONG to on the "
        "domain's hour-ending convention")


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


def _reconciliation_verdicts() -> Dict[str, object]:
    """Ours is a floor: an hourly mean cannot exceed the readings in it, so the
    record's daily maxima sit at or below the true ones; checked against the
    published 53."""
    figures = _figures()
    if figures["very_hot_days_2025"] > 53:
        raise RuntimeError("the record exceeds the published count; the floor argument fails")
    return {"figure_to_publish": "the Observatory's figure", "our_count_is": "a floor"}


def validate_reconciliation(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "figure_to_publish": runtime.retrieve("figure_to_publish"),
        "our_count_is": runtime.retrieve("our_count_is"),
    }
    return _verdict_check(got, _reconciliation_verdicts())

tools = []
variables = [
    Variable(
        "very_hot_days_2025",
        None,
        "Store the number of very hot days in 2025, as the Hong Kong "
        "Observatory defines a very hot day, that this record's hourly "
        "temperatures support, as an integer. " + _DAY + " and its maximum is the "
        "highest hourly value stored for it.",
    ),
    Variable("figure_to_publish", None,
             "Store which very-hot-day count the desk should publish, as one of "
             "exactly these strings: 'the Observatory's figure', 'our figure', "
             "'neither'."),
    Variable("our_count_is", None,
             "Store what the count from this record is, relative to the true "
             "statistic, as one of exactly these strings: 'a floor', 'a "
             "ceiling', 'an estimate'."),
]


def validate_evidence_and_conclusion(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "very_hot_days_2025": runtime.retrieve("very_hot_days_2025"),
        "figure_to_publish": runtime.retrieve("figure_to_publish"),
        "our_count_is": runtime.retrieve("our_count_is"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, f"{missing} not set", variables_not_set=True)
    result_0 = validate_count(response, runtime, turn)
    if not result_0.success:
        return result_0
    result_1 = validate_reconciliation(response, runtime, turn)
    if not result_1.success:
        return result_1
    return ValidatorResult(True, result_0.message + "; " + result_1.message)

validators = {
    "validate_count": validate_count,
    "validate_reconciliation": validate_reconciliation,
    "validate_evidence_and_conclusion": validate_evidence_and_conclusion,
}
