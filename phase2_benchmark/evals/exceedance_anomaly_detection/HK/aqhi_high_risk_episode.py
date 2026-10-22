
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def _get_episode_date():
    """Find the date in July 2025 with the most stations recording AQHI >= 7."""
    data = pd.read_sql(
        text("""
            SELECT hsaq.datetime::date AS dt, COUNT(DISTINCT hsaq.station_id) AS station_count
            FROM hourly_station_air_quality hsaq
            WHERE hsaq.datetime >= '2025-07-01' AND hsaq.datetime < '2025-08-01'
              AND hsaq.aqhi >= 7
            GROUP BY hsaq.datetime::date
            ORDER BY station_count DESC, dt ASC
            LIMIT 1
        """),
        engine,
    )
    return str(data["dt"].iloc[0]), int(data["station_count"].iloc[0])
def validate_episode_date(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    episode_date = runtime.retrieve("episode_date")
    affected_stations = runtime.retrieve("affected_stations")

    expected_date, expected_count = _get_episode_date()

    errors = []

    if episode_date is None:
        return ValidatorResult(False, "episode_date not set", variables_not_set=True)
    if not isinstance(episode_date, str):
        errors.append("episode_date should be str")
    elif episode_date.strip() != expected_date:
        errors.append(f"episode_date='{episode_date}', expected '{expected_date}'")

    if affected_stations is None:
        return ValidatorResult(False, "affected_stations not set", variables_not_set=True)
    if not is_finite_number(affected_stations):
        errors.append("affected_stations should be numeric")
    elif int(affected_stations) != expected_count:
        errors.append(f"affected_stations={int(affected_stations)}, expected {expected_count}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: date={expected_date}, stations={expected_count}")
def validate_peak_hour(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    peak_hour = runtime.retrieve("peak_hour")
    peak_aqhi = runtime.retrieve("peak_aqhi")
    peak_station = runtime.retrieve("peak_station")

    # Re-derive the episode date
    expected_date, _ = _get_episode_date()

    # Find the peak AQHI on that date
    peak_data = pd.read_sql(
        text(f"""
            SELECT EXTRACT(HOUR FROM hsaq.datetime)::int AS hr, hsaq.aqhi, aqs.name_en
            FROM hourly_station_air_quality hsaq
            JOIN air_quality_station aqs ON hsaq.station_id = aqs.id
            WHERE hsaq.datetime::date = '{expected_date}'
              AND hsaq.aqhi IS NOT NULL
            ORDER BY hsaq.aqhi DESC, hr ASC, aqs.name_en ASC
            LIMIT 1
        """),
        engine,
    )

    expected_hour = int(peak_data["hr"].iloc[0])
    expected_aqhi = int(peak_data["aqhi"].iloc[0])
    expected_station = peak_data["name_en"].iloc[0]

    # Collect all tied stations at the peak
    tied_data = pd.read_sql(
        text(f"""
            SELECT EXTRACT(HOUR FROM hsaq.datetime)::int AS hr, aqs.name_en
            FROM hourly_station_air_quality hsaq
            JOIN air_quality_station aqs ON hsaq.station_id = aqs.id
            WHERE hsaq.datetime::date = '{expected_date}'
              AND hsaq.aqhi = {expected_aqhi}
        """),
        engine,
    )
    valid_hours = set(tied_data["hr"].tolist())
    valid_stations = set(tied_data["name_en"].str.strip().str.lower().tolist())

    errors = []

    if peak_hour is None:
        return ValidatorResult(False, "peak_hour not set", variables_not_set=True)
    if not is_finite_number(peak_hour):
        errors.append("peak_hour should be numeric")
    elif int(peak_hour) not in valid_hours:
        errors.append(f"peak_hour={int(peak_hour)}, expected one of {sorted(valid_hours)}")

    if peak_aqhi is None:
        return ValidatorResult(False, "peak_aqhi not set", variables_not_set=True)
    if not is_finite_number(peak_aqhi):
        errors.append("peak_aqhi should be numeric")
    elif int(peak_aqhi) != expected_aqhi:
        errors.append(f"peak_aqhi={int(peak_aqhi)}, expected {expected_aqhi}")

    if peak_station is None:
        return ValidatorResult(False, "peak_station not set", variables_not_set=True)
    if not isinstance(peak_station, str):
        errors.append("peak_station should be str")
    elif peak_station.strip().lower() not in valid_stations:
        errors.append(f"peak_station='{peak_station}', expected one of {sorted(valid_stations)}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: hour={expected_hour}, aqhi={expected_aqhi}, station={expected_station}")
tools = []
variables = [
    Variable("episode_date", None, "T1: Date with most stations recording AQHI>=7, format YYYY-MM-DD (str)."),
    Variable("affected_stations", None, "T1: Number of stations with AQHI>=7 on that day (int)."),
    Variable("peak_hour", None, "T2: Hour of peak AQHI on the episode date, 0-23 (int)."),
    Variable("peak_aqhi", None, "T2: Peak AQHI value (int)."),
    Variable("peak_station", None, "T2: Station name with the peak AQHI (str)."),
]
validators = {"validate_episode_date": validate_episode_date, "validate_peak_hour": validate_peak_hour}
