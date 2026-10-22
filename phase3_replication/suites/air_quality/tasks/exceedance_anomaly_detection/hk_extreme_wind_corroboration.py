"""Two windstorms of different sizes, and a record gust nothing else saw
(exceedance_anomaly_detection).

BASELINE, medium, rebuilt 2026-09-02 on the surface rule
(`docs/query_surface_audit.md`). The first turn asks for the year's strongest
gust and whether the rest of the network bears it out; the second asks for
the year's lowest pressure and which date had more of the network blowing hard.
What the case tests is whether the agent, holding a record gust and a record
pressure fall that point at different days, characterises how the two events
differ rather than deciding which one counts — and whether it leaves the
gust's status open where the record does.

**Gate B round 6 blocked the first version of this case and was right.** It
asked which of the two dates was "the year's severe windstorm" and required
the pressure date, on the reasoning that the gust date's reading stood alone.
Both halves were wrong. The Hong Kong Observatory documents the evening of 25
July 2025 as severe squally convective weather with more than 2,900
cloud-to-ground strikes and a violent gust near Sai Kung, and the database
corroborates it: Sai Kung reads 111 km/h at the stamp 19:00, and at 20:00
Peng Chau, Tai Mei Tuk, Cheung Chau Beach and Sai Kung read 94, 89, 81 and
80. A response identifying BOTH events was scientifically better than the
one the case demanded, and would have failed.

**What the two dates actually are, and the measure that separates them.**

    2025-07-20   MSLP falls to 975.1 hPa      27 of 51 stations gust to 80 km/h
    2025-07-25   gust of 319.0 km/h           6 of 51 stations gust to 80 km/h

Typhoon Wipha on the 20th is a territory-wide system: a large share of the
network is blowing hard at once, and every barometer in the affected area
falls together. The 25th is a localised convective windstorm: a handful of
stations, a few kilometres across, with pressure near normal — the thirteen
reporting barometers span 999.4 to 1001.7 hPa that hour. Neither is a
non-event. The scale is the difference.

**The 319 is uncorroborated, and that is all the record says.** Ngong Ping
reports 319.0 km/h at the stamp 21:00 with a mean wind of 15.0 km/h that
hour; the strongest reading anywhere else in the same hour is 106 — Cheung
Chau Beach, a third of the Ngong Ping figure — within an hour either side
111, on the whole day 111 — no other station reached even
half of it. It is far above anything else in the year (of the 260,027 gusts
recorded in 2025, nine reach 200 km/h and exactly one reaches 250). Those
are reasons to doubt it. But a convective downdraught a few kilometres wide
is a real possibility on a night the Observatory describes exactly that way,
and nothing in the record — no maintenance log, no quality flag, no second
instrument at Ngong Ping — distinguishes an instrument fault from a genuine
local extreme. The scored verdict is "not corroborated"; the claim requires
the response to hold the rest open rather than settle it.

**The gust-factor test does not work here, and that was measured.** A gust
implausibly large against its own station's mean wind looks like the obvious
screen. The year's highest such ratios are all in near-calm air — 141.176 at
Tai Po Kau on a 0.17 km/h mean, then 88, then a run at 70 — 4,554 records
carry a gust with a mean wind of exactly zero, and 1,095 readings exceed the
suspect reading's own ratio of 21.3. No threshold on that ratio separates
anything.

**The pressure is mean sea-level pressure, not station pressure.** HKO's
source product is reduced to sea level, which the data confirm: the thirteen
reporting stations' 2025 means span only 1012.562 to 1013.413 hPa despite
differing elevations. The variable names it, because the cross-station
comparability the case rests on depends on that reduction.

**What is scored, and what survives every route.** The earlier version scored
the corroborating gust and the two station counts at a threshold of 80 km/h,
with the query naming the threshold and the hour; the count was the
author's construction. The rebuilt turns score the two extremes — strict
maxima, no construction to choose — and two verdicts that `_routes()`
recomputes under several constructions and refuses to score if any differs:

    corroborated?   another station reaching half, or two thirds, of the
                    reading in the same hour, within an hour, or on the day:
                    never (106 / 111 / 111 against 319)     -> not corroborated
    more of the     stations whose day's peak gust reached 60, 80 or 100
    network?        km/h, days cut hour-ending or on the stamp:
                    28/27/24 on the 20th against 17/6/3     -> the pressure date

    NOT scored: the corroborating reading, the station counts.

Counts scoped to 2025 rather than to the whole record, because the record
grows and a live total drifts — an earlier draft quoted 422,469 gusts and it
had already moved.

**How this differs from `hk_radiation_sensor_failure`.** That case screens
for zeros and asks which of two suspicious days is decidable from one
station's own channels. This one classifies two real events by spatial scale
and leaves an instrument question open. Gate B round 6 ruled the distinctness
sound.

Ground truth is recomputed from the database at validation time.


**Gate B round 21 (2026-09-03) found "bigger windstorm" undefined**, and it is:
the pressure date is plainly broader — 28 stations against 17 at a 60 km/h
day-peak, a station-peak median of 128 against 61.5 km/h — while the gust date
plainly owns the fiercer single reading, 319 km/h against 121. A respondent who
answers on peak intensity is using an ordinary meaning of "bigger" and was
failing PV for it, with the scale distinction only explained afterwards in the
claims. The query and the variable now ask which date had more of the network
blowing hard at once, which is the comparison the routes actually sweep, and
the claims keep the point that this is the distinction that matters.

The same round found the docstring's peer figure stale: the strongest reading
beside the 319 in its own hour is 106 km/h, not 94 — 94 is the 20:00 stamp's
figure, an hour earlier — and the 20:00 list named Lau Fau Shan where the
record has Tai Mei Tuk. Both are corrected above. The corroboration verdict is
unchanged: 106 is a third of 319, and the route asks for half.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, is_finite_number, reports_as
from domains.hk.db import read_frame

_SPAN = {"lo": "2025-01-01", "hi": "2026-01-01"}


def _extremes() -> Dict[str, object]:
    gust = read_frame(text("""
        select station_id, datetime, wind_gust from hourly_station_weather
        where datetime > :lo and datetime <= :hi and wind_gust is not null
        order by wind_gust desc limit 1
    """), _SPAN).iloc[0]
    pressure = read_frame(text("""
        select datetime, pressure from hourly_station_weather
        where datetime > :lo and datetime <= :hi and pressure is not null
        order by pressure asc limit 1
    """), _SPAN).iloc[0]
    return {"gust_station": gust["station_id"], "gust": float(gust["wind_gust"]), "gust_stamp": pd.Timestamp(gust["datetime"]),
            "pressure": float(pressure["pressure"]),
            "pressure_stamp": pd.Timestamp(pressure["datetime"])}


def _day_of(stamp: pd.Timestamp, shift_hours: int) -> pd.Timestamp:
    return (stamp - pd.Timedelta(hours=shift_hours)).normalize()


def _scale_routes(pressure_stamp: pd.Timestamp, gust_stamp: pd.Timestamp) -> Dict[str, str]:
    """Which date had more of the network blowing hard, under three thresholds
    and two day cuts."""
    out = {}
    for shift in (1, 0):
        days = {"the pressure date": _day_of(pressure_stamp, shift),
                "the gust date": _day_of(gust_stamp, shift)}
        for threshold in (60, 80, 100):
            counts = {}
            for name, day in days.items():
                reached = read_frame(text("""
                    select count(*) as n from (
                        select station_id, max(wind_gust) as peak
                        from hourly_station_weather
                        where datetime > :lo and datetime <= :hi
                        group by 1) per_station
                    where peak >= :threshold
                """), {"lo": (day + pd.Timedelta(hours=shift)).isoformat(),
                                      "hi": (day + pd.Timedelta(hours=24 + shift)).isoformat(),
                                      "threshold": threshold})
                counts[name] = int(reached["n"].iloc[0])
            label = f"{threshold} km/h, {'hour-ending' if shift else 'stamp'} days"
            if days["the pressure date"] == days["the gust date"]:
                out[label] = "the same event"
            else:
                out[label] = max(counts, key=counts.get)
    return out


def _invariant(routes: Dict[str, str], name: str) -> str:
    values = set(routes.values())
    if len(values) != 1:
        raise RuntimeError(f"{name} is not invariant across constructions: "
                           + "; ".join(f"{k}={v}" for k, v in routes.items()))
    return values.pop()


def _figures() -> Dict[str, object]:
    ext = _extremes()
    return {
        "max_gust_kmh": ext["gust"],
        "max_gust_date": str(_day_of(ext["gust_stamp"], 1).date()),
        "max_peer_gust_kmh": float(read_frame(text("""
            select max(wind_gust) as gust from hourly_station_weather
            where datetime = :stamp and station_id <> :station
        """), {"stamp": ext["gust_stamp"].isoformat(),
                 "station": ext["gust_station"]})["gust"].iloc[0]),
        "min_pressure_hpa": ext["pressure"],
        "min_pressure_date": str(_day_of(ext["pressure_stamp"], 1).date()),
        "date_with_more_of_the_network_blowing_hard": _invariant(
            _scale_routes(ext["pressure_stamp"], ext["gust_stamp"]),
            "date_with_more_of_the_network_blowing_hard"),
    }


def _normalise(value) -> str:
    return str(value).strip().lower()


def _check(got: Dict[str, object], numbers: tuple, date_field: str,
           verdict_field: str | None) -> ValidatorResult:
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    for name in numbers:
        if not is_finite_number(got[name]):
            return ValidatorResult(False, f"{name}={got[name]!r} is not a number")
    gt = _figures()
    wrong = [f"{name}={got[name]}, expected ~{gt[name]:.1f}" for name in numbers
             if not reports_as(got[name], gt[name], decimals=1)]
    if str(got[date_field]).strip() != gt[date_field]:
        wrong.append(f"{date_field}={got[date_field]!r}, expected {gt[date_field]!r}")
    if verdict_field is not None and _normalise(got[verdict_field]) != _normalise(gt[verdict_field]):
        wrong.append(f"{verdict_field}={got[verdict_field]!r}, expected {gt[verdict_field]!r}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


def validate_record_gust(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "max_gust_kmh": runtime.retrieve("max_gust_kmh"),
        "max_gust_date": runtime.retrieve("max_gust_date"),
        "max_peer_gust_kmh": runtime.retrieve("max_peer_gust_kmh"),
    }, ("max_gust_kmh", "max_peer_gust_kmh"), "max_gust_date", None)


def validate_event_scale(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "min_pressure_hpa": runtime.retrieve("min_pressure_hpa"),
        "min_pressure_date": runtime.retrieve("min_pressure_date"),
        "date_with_more_of_the_network_blowing_hard":
            runtime.retrieve("date_with_more_of_the_network_blowing_hard"),
    }, ("min_pressure_hpa",), "min_pressure_date",
        "date_with_more_of_the_network_blowing_hard")


tools = []
variables = [
    Variable("max_gust_kmh", None,
             "Store the strongest hourly wind gust any Hong Kong weather station "
             "reported in 2025, as a float in km/h to 1 decimal place."),
    Variable("max_gust_date", None,
             "Store the calendar date of that reading, as a string 'YYYY-MM-DD' in "
             "Hong Kong local time."),
    Variable("max_peer_gust_kmh", None,
             "Store the largest gust at a different station at the exact timestamp "
             "of the record gust, as a float in km/h to 1 decimal place."),
    Variable("min_pressure_hpa", None,
             "Store the lowest hourly mean-sea-level pressure reported anywhere in "
             "Hong Kong in 2025, as a float in hPa to 1 decimal place."),
    Variable("min_pressure_date", None,
             "Store the calendar date of that reading, as a string 'YYYY-MM-DD' in "
             "Hong Kong local time."),
    Variable("date_with_more_of_the_network_blowing_hard", None,
             "Store which of the two dates had more of the weather network "
             "reporting strong wind at the same time, as one of exactly these "
             "strings: 'the pressure date', 'the gust date', 'the same event'."),
]
validators = {
    "validate_record_gust": validate_record_gust,
    "validate_event_scale": validate_event_scale,
}
