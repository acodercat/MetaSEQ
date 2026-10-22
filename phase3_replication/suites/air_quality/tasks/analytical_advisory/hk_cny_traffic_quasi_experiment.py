"""Hong Kong holiday comparison under a fixed nearby-week design (execution).

The baseline uses the same weekday/hour at -14, -7, +7 and +14 days: local
calendar matching limits seasonal drift without claiming to remove weather or
other holiday changes. This is a retrospective contrast, not a causal design.
The old unrestricted baseline had no unique sign: using only +14 days reverses
the roadside increment. It is no longer scored as a universal boolean.

Independent raw-data answers frozen before this implementation:
.codex-review/new_rules_fix_20261008/frozen_answers.json
NO2 increment -8.855599, shared fall 67.928012%, 72 event/288 baseline hours;
70 complete covariate hours; roadside ozone +12.158275 over 72 event hours.
Missing covariate hours matter: using separate cohorts is a rejected reading.
Numerical results use reports_as at declared precision; counts are exact.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

_OFFSETS = (-14, -7, 7, 14)
_EVENT_HOURS = pd.date_range("2026-02-17 01:00", "2026-02-20 00:00", freq="h")


def _matched(frame):
    """One event observation and four complete same-weekday/hour controls."""
    frame = frame.replace([np.inf, -np.inf], np.nan)
    parts = [frame.reindex(_EVENT_HOURS)]
    for days in _OFFSETS:
        peer = frame.reindex(_EVENT_HOURS + pd.Timedelta(days=days))
        peer.index = _EVENT_HOURS
        parts.append(peer)
    complete = pd.concat(parts, axis=1).notna().all(axis=1)
    event = parts[0].loc[complete]
    reference = sum(part.loc[complete] for part in parts[1:]) / 4
    return event, reference


def _figures():
    air = read_frame(text("""
        SELECT h.datetime, s.station_type::text AS kind,
               avg(h.no2) AS no2, avg(h.o3) AS o3
        FROM hourly_station_air_quality h
        JOIN air_quality_station s ON s.id=h.station_id
        WHERE h.datetime > '2026-02-03' AND h.datetime <= '2026-03-06'
        GROUP BY h.datetime,s.station_type
    """))
    air["datetime"] = pd.to_datetime(air["datetime"])
    event, reference = _matched(air.pivot(index="datetime", columns="kind", values="no2"))
    delta = (event - reference).mean()
    result = {
        "roadside_increment_change": float(delta["ROADSIDE"] - delta["GENERAL"]),
        "shared_no2_drop_pct": float(100 * delta["GENERAL"] / delta["ROADSIDE"]),
        "matched_event_hours": len(event),
        "baseline_no2_hours": 4 * len(event),
    }
    traffic = read_frame(text("""
        SELECT datetime, avg(congestion_index) AS congestion, avg(speed) AS speed
        FROM hourly_road_segment_traffic
        WHERE datetime > '2026-02-03' AND datetime <= '2026-03-06'
          AND congestion_index NOT IN ('Infinity'::float8,'-Infinity'::float8,'NaN'::float8)
          AND speed NOT IN ('Infinity'::float8,'-Infinity'::float8,'NaN'::float8)
        GROUP BY datetime
    """))
    wind = read_frame(text("""
        SELECT h.datetime,h.wind_speed AS wind
        FROM hourly_station_weather h JOIN weather_station s ON s.id=h.station_id
        WHERE s.name_en='King''s Park'
          AND h.datetime > '2026-02-03' AND h.datetime <= '2026-03-06'
    """))
    covariates = traffic.merge(wind, on="datetime").set_index("datetime")
    covariates.index = pd.to_datetime(covariates.index)
    event, reference = _matched(covariates)
    delta = (event - reference).mean()
    result.update(congestion_index_change=float(delta["congestion"]),
                  traffic_speed_change_kmh=float(delta["speed"]),
                  kings_park_wind_change_kmh=float(delta["wind"]),
                  matched_covariate_hours=len(event))
    ozone = air[air["kind"] == "ROADSIDE"].set_index("datetime")[["o3"]]
    event, reference = _matched(ozone)
    result.update(roadside_ozone_change=float((event-reference)["o3"].mean()),
                  matched_ozone_hours=len(event),
                  treated_days=int((event.index-pd.Timedelta(hours=1)).normalize().nunique()))
    return result


_DECIMALS = {"roadside_increment_change": 3, "shared_no2_drop_pct": 2,
             "congestion_index_change": 3, "traffic_speed_change_kmh": 3,
             "kings_park_wind_change_kmh": 3, "roadside_ozone_change": 3}


def _check(runtime, names):
    got = {name: runtime.retrieve(name) for name in names}
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    expected = _figures()
    errors = []
    for name, value in got.items():
        valid = is_finite_number(value) and (
            reports_as(value, expected[name], decimals=_DECIMALS[name])
            if name in _DECIMALS else compare_numeric(value, expected[name], tolerance=0))
        if not valid:
            errors.append(f"{name}={value!r}, expected {expected[name]}")
    return ValidatorResult(not errors, "; ".join(errors) if errors else "correct matched comparison")


def validate_event_contrast(response: str, runtime, turn: Turn):
    return _check(runtime, ("roadside_increment_change", "shared_no2_drop_pct",
                            "matched_event_hours", "baseline_no2_hours"))


def validate_confounds(response: str, runtime, turn: Turn):
    return _check(runtime, ("congestion_index_change", "traffic_speed_change_kmh",
                            "kings_park_wind_change_kmh", "matched_covariate_hours"))


def validate_three_pollutants(response: str, runtime, turn: Turn):
    return _check(runtime, ("roadside_ozone_change", "matched_ozone_hours", "treated_days"))


_BASELINE = (
    "The event is the 72 hour-ending stamps after 2026-02-17 00:00 through "
    "2026-02-20 00:00 inclusive. Match each to exactly four controls at the same "
    "clock hour, 14 and 7 days before and 7 and 14 days after. Retain an event "
    "hour only if the event and all four controls report every quantity in the "
    "turn's common cohort. Average the four controls equally within each event "
    "hour, then average eligible event hours equally. No filling or extra filters. "
)
tools = []
variables = [
    Variable("roadside_increment_change", None,
             "Store holiday-minus-baseline change in roadside-minus-general NO2, "
             "in µg/m³ to 3 decimal places. " + _BASELINE +
             "For this turn, form each class's hourly NO2 as the mean of its "
             "reporting stations and require both classes at every matched stamp."),
    Variable("shared_no2_drop_pct", None,
             "Store 100 times the general-station NO2 fall divided by the roadside "
             "NO2 fall on the same matched cohort, to 2 decimal places. Form each "
             "fall as baseline mean minus event mean, retaining unrounded values."),
    Variable("matched_event_hours", None, "Store the exact integer count of eligible NO2 event hours."),
    Variable("baseline_no2_hours", None, "Store the exact integer count of distinct control hours supporting those NO2 pairs."),
    Variable("congestion_index_change", None,
             "Store event-minus-baseline territory congestion-index change to 3 "
             "decimal places under the same four-control design. For this turn "
             "use a common cohort with congestion, traffic speed and King's Park "
             "wind at all five stamps. At each stamp average road segments with "
             "both finite congestion index and finite speed, giving each segment "
             "equal weight. The congestion index is free-flow speed divided by actual speed."),
    Variable("traffic_speed_change_kmh", None, "Store the corresponding traffic-speed change in km/h to 3 decimal places, on that same covariate cohort."),
    Variable("kings_park_wind_change_kmh", None, "Store the corresponding King's Park hourly wind-speed change in km/h to 3 decimal places, on that same covariate cohort."),
    Variable("matched_covariate_hours", None, "Store the exact integer number of eligible event hours in the joint congestion/speed/wind cohort."),
    Variable("roadside_ozone_change", None,
             "Store event-minus-baseline roadside O3 in µg/m³ to 3 decimal places "
             "under the same four-control design. Use the mean over reporting "
             "roadside stations at each stamp, retaining event hours with finite "
             "roadside O3 at the event and all four controls, independently of the NO2 cohort."),
    Variable("matched_ozone_hours", None, "Store the exact integer count of eligible roadside-ozone event hours."),
    Variable("treated_days", None, "Store the exact integer number of hour-ending event dates represented by that ozone cohort."),
]
validators = {"validate_event_contrast": validate_event_contrast,
              "validate_confounds": validate_confounds,
              "validate_three_pollutants": validate_three_pollutants}
