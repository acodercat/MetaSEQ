"""The index column stops at ten; the band does not (regulatory_standards).

DIAGNOSTIC TRAP.

**The naive path and what it produces.** Hong Kong's published Air Quality
Health Index tops out at a band EPD writes as "10+", and this database stores
the index as an integer that therefore **caps at 10** — no row in the record
carries a higher number. A station reading 10 may have been exactly 10, which
EPD calls Very High, or above 10, which it calls Serious. Only `aqhi_level`
separates them. Counting stations at 10 or above to find the Serious ones
returns **15**; the answer is **10**.

The two groups are not separable from anything else in the row either. At the
scored hour the ten Serious stations carry ozone from 236.7 to 362.9 ug/m3 and
the five Very High ones from 107.4 to 304.5 — overlapping ranges, so the band
cannot be recovered from the concentration. Across the whole record 982 rows
sit at 10, splitting 360 Serious against 622 Very High.

The error survives P1 because "the Serious band" names one thing and the
numeric column is a lossy encoding of it, not a second defensible reading. The
query asks how many stations were in the highest band and does not say which
column answers that — working out that one of them cannot is the exam.

**The episode.** Screening 2020-2025 for the hour whose network median ozone is
highest, counting only hours in which at least fifteen stations report, returns
**2022-09-16 15:00** at **272.35 ug/m3**, with **14 of 18** stations at or above
200. A government notice of that afternoon describing a high ozone episode was
cited to the author when this case was proposed
(`https://www.info.gov.hk/gia/general/202209/16/P2022091600436.htm`); it is
recorded as provenance for why the date is worth a case and is NOT relied on by
anything scored, because the author did not retrieve it. Everything the
validators check comes from the database.
The hour's mean risk contributions are ozone 13.414 against nitrogen dioxide
3.912, particulates 2.297 and sulphur dioxide 0.116, so the index that hour is
carried by its ozone term — which is why the case asks about spatial extent and
the dominant term rather than asking anyone to demonstrate photochemistry.

**Convention sweep — three axes, twelve combinations, all computed.**
Only the peak value
moves. Every combination selects the same hour and returns the same 14 and 10:
the minimum-reporting-station floor at 12, 15 or 18 changes nothing because all
eighteen stations report that hour and the runner-up hours are the same
afternoon, and the window endpoint changes nothing because no station-hour
falls at 2026-01-01 00:00. The `stat` axis moves only the peak value — the
network median reads 272.35 and the network mean 254.67 — which is why
that value is no longer scored.

**Tolerances.** The hour is matched exactly as a
timestamp — the runner-up is 14:00 the same day at 268.05, an hour away and
4.30 ug/m3 down, so a near miss exists and the exactness is deliberate rather
than incidental. The two counts are integers matched exactly, which is what
rejects the naive 15.

**What the case does not claim.** It does not ask anyone to establish that the
episode was photochemical, only that the index that hour was carried by its
ozone term, which the stored risk contributions show directly. And it does not
say EPD's published index is wrong: the point is that this database's numeric
column is a capped rendering of a published band, so the band is the field to
read when the band is the question.

Ground truth is recomputed from the database at validation time.

**Turn 1 rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier query named the median, the fifteen-station floor and the 200
ug/m3 count; the peak VALUE (272.35 median against 254.67 mean) is what had
forced the statistic into the query, and it is no longer scored. The hour
is: `_figures()` recomputes it under the median and the mean with the
floor at fifteen stations and at one, and refuses to score if they differ.
The 200 count stays on its variable as the named measure of extent.

**Split 2026-09-02 (query length, and a reveal).** Turn 2 used to say the
index "runs from low up to a highest band that EPD announces separately from
the ones below it" — which is the numeric column's 10+ encoding, the trap
this case exists for, stated on the surface. Turn 2 now asks only how many
stations sat in the highest band; a third turn asks for the bulletin
characterisation and scores which pollutant the index was carrying
(ozone: 13.4 against 3.9 / 2.3 / 0.1 on the mean added-risk terms), with
the three claims moved to it.


**Gate B round 21 (2026-09-03): "strongest territory-wide episode" was not one
question.** The reviewer ranked every hour of the period by mean, median, upper
quartiles and deciles, minimum, maximum, and by the count of stations at or
above 150, 180 and 200 ug/m3. Mean and median agree on 2022-09-16 15:00, which
is what `_figures()` asserted; but the hour with the MOST stations at or above
200 is 2022-09-12 16:00, with 15 of 17 reporting, and 14 September has two more
hours at 15. Maximising how many stations are simultaneously very high is at
least as natural a reading of "territory-wide strength" as maximising the
average, and it moves both scored quantities.

The fix is to name the statistic as the deliverable rather than to widen the
route set: the variable now says the hour whose ozone AVERAGED ACROSS THE
REPORTING STATIONS is highest. That is what quantity is wanted, not how to
compute it, and the reviewer's alternative — scoring the mean-peak hour and the
count-peak hour separately — would make the case about ranking conventions
instead of about how an ozone episode is encoded in a public index.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, is_finite_number
from domains.hk.db import read_frame

_SPAN = ("2020-01-01", "2026-01-01")
_MIN_REPORTING = 15
_HIGH_O3 = 200.0


def _peak_hour(statistic: str, floor: int) -> pd.Timestamp:
    """The hour whose territory ozone figure is highest, at one construction."""
    agg = ("percentile_cont(0.5) within group (order by o3)" if statistic == "median"
           else "avg(o3)")
    row = read_frame(text(f"""
        select datetime, {agg} as territory
        from hourly_station_air_quality
        where datetime > :lo and datetime <= :hi and o3 is not null
        group by 1
        having count(o3) >= :floor
        order by 2 desc
        limit 1
    """), {"lo": _SPAN[0], "hi": _SPAN[1], "floor": floor}).iloc[0]
    return pd.Timestamp(row["datetime"])


def _figures() -> Dict[str, object]:
    """The three scored quantities; the peak hour is asserted invariant."""
    hours = {f"{stat}, at least {floor} stations": _peak_hour(stat, floor)
             for stat in ("median", "mean") for floor in (_MIN_REPORTING, 1)}
    if len(set(hours.values())) != 1:
        raise RuntimeError(f"the peak hour is not invariant across constructions: {hours}")
    peak = next(iter(hours.values()))
    hour = read_frame(text("""
        select count(*) filter (where o3 >= :high)              as high_o3,
               count(*) filter (where aqhi_level::text = 'SERIOUS') as serious
        from hourly_station_air_quality
        where datetime = :at
    """), {"at": peak.to_pydatetime(), "high": _HIGH_O3}).iloc[0]
    terms = read_frame(text("""
        select avg(o3_ar) as ozone, avg(no2_ar) as no2, avg(pm_ar) as particulates, avg(so2_ar) as so2
        from hourly_station_air_quality where datetime = :at
    """), {"at": peak.to_pydatetime()}).iloc[0]
    carried = {"ozone": "ozone", "no2": "nitrogen dioxide", "particulates": "particulates", "so2": "sulphur dioxide"}[terms.idxmax()]
    return {
        "peak_episode_hour": str(peak),
        "stations_o3_at_least_200": int(hour["high_o3"]),
        "stations_in_serious_band": int(hour["serious"]),
        "index_carried_by": carried,
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


def _not_an_integer(name: str, val) -> ValidatorResult:
    """A count must be an int; `bool` is excluded as an `int` subclass."""
    if val is None:
        return ValidatorResult(False, f"{name} not set", variables_not_set=True)
    if not isinstance(val, int) or isinstance(val, bool):
        return ValidatorResult(False, f"{name}={val!r} is not an integer")
    return None


def validate_episode_peak(response: str, runtime, turn: Turn) -> ValidatorResult:
    hour = runtime.retrieve("peak_episode_hour")
    high = runtime.retrieve("stations_o3_at_least_200")
    if hour is None:
        return ValidatorResult(False, "peak_episode_hour not set",
                               variables_not_set=True)
    failure = _not_an_integer("stations_o3_at_least_200", high)
    if failure is not None:
        return failure
    gt = _figures()
    wrong = []
    # Matched exactly: the near miss is the preceding hour of the same
    # afternoon, 4.30 ug/m3 down, so the hour is a real discriminator.
    if str(hour).strip() != gt["peak_episode_hour"]:
        wrong.append(f"peak_episode_hour={hour!r}, "
                     f"expected {gt['peak_episode_hour']!r}")
    if high != gt["stations_o3_at_least_200"]:
        wrong.append(f"stations_o3_at_least_200={high}, "
                     f"expected {gt['stations_o3_at_least_200']}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {gt['peak_episode_hour']}, "
              f"{high} stations at or above 200")


def validate_serious_band(response: str, runtime, turn: Turn) -> ValidatorResult:
    serious = runtime.retrieve("stations_in_serious_band")
    failure = _not_an_integer("stations_in_serious_band", serious)
    if failure is not None:
        return failure

    gt = _figures()
    # Exact, and this is the trap: the numeric index caps at 10, so counting
    # stations at 10 or above returns 15 where the band returns 10.
    if serious != gt["stations_in_serious_band"]:
        return ValidatorResult(
            False, f"stations_in_serious_band={serious}, "
                   f"expected {gt['stations_in_serious_band']}")
    return ValidatorResult(True, f"correct: {serious} stations in the band")


def validate_bulletin(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("index_carried_by")
    if val is None:
        return ValidatorResult(False, "index_carried_by not set", variables_not_set=True)
    gt = _figures()
    if str(val).strip().lower() != gt["index_carried_by"]:
        return ValidatorResult(False, f"index_carried_by={val!r}, expected {gt['index_carried_by']!r}")
    return ValidatorResult(True, f"correct: the index was carrying {gt['index_carried_by']}")


tools = []
variables = [
    Variable(
        "peak_episode_hour",
        None,
        "Store the hour at which the episode peaked — the hour whose ozone "
        "averaged across the reporting stations is the highest of the period — "
        "as a string 'YYYY-MM-DD HH:MM:SS' in Hong Kong local time.",
    ),
    Variable(
        "stations_o3_at_least_200",
        None,
        "Store how many stations report ozone of 200 ug/m3 or more in that "
        "hour, as an integer.",
    ),
    Variable(
        "stations_in_serious_band",
        None,
        "Store how many stations sit in the highest Air Quality Health Index "
        "band in that hour, as an integer.",
    ),
]
validators = {
    "validate_episode_peak": validate_episode_peak,
    "validate_serious_band": validate_serious_band,
    "validate_bulletin": validate_bulletin,
}
variables += [
    Variable("index_carried_by", None,
             "Store which pollutant the index was carrying in that hour — the "
             "one whose added-risk term was the largest across the stations — "
             "as one of exactly these strings: 'ozone', 'nitrogen dioxide', "
             "'particulates', 'sulphur dioxide'."),
]
