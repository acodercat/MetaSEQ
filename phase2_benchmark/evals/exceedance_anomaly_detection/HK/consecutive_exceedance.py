
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_consecutive(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    station_name = runtime.retrieve("station_name")
    hours = runtime.retrieve("consecutive_hours")
    start_dt = runtime.retrieve("event_start")

    # Get all exceedance hours per station in Oct 2025
    data = pd.read_sql(
        text("""
            SELECT aqs.name_en, hsaq.datetime
            FROM hourly_station_air_quality hsaq
            JOIN air_quality_station aqs ON hsaq.station_id = aqs.id
            WHERE hsaq.datetime >= '2025-10-01' AND hsaq.datetime < '2025-11-01'
              AND hsaq.pm2_5 > 50
            ORDER BY aqs.name_en, hsaq.datetime
        """),
        engine,
    )

    # Find longest consecutive run per station
    best_station, best_hours, best_start = "", 0, None

    for name, group in data.groupby("name_en"):
        times = sorted(group["datetime"].tolist())
        if not times:
            continue
        run_start = times[0]
        run_len = 1
        for i in range(1, len(times)):
            if (times[i] - times[i-1]).total_seconds() == 3600:
                run_len += 1
            else:
                if run_len > best_hours:
                    best_hours = run_len
                    best_station = name
                    best_start = run_start
                run_start = times[i]
                run_len = 1
        if run_len > best_hours:
            best_hours = run_len
            best_station = name
            best_start = run_start

    expected_start_str = best_start.strftime("%Y-%m-%d %H:%M:%S") if best_start else ""

    errors = []

    if station_name is None:
        return ValidatorResult(False, "station_name not set", variables_not_set=True)
    if not isinstance(station_name, str):
        errors.append(f"station_name should be str")
    elif station_name.strip().lower() != best_station.strip().lower():
        errors.append(f"station_name='{station_name}', expected '{best_station}'")

    if hours is None:
        return ValidatorResult(False, "consecutive_hours not set", variables_not_set=True)
    if not is_finite_number(hours):
        errors.append(f"consecutive_hours should be numeric")
    elif int(hours) != best_hours:
        errors.append(f"consecutive_hours={int(hours)}, expected {best_hours}")

    if start_dt is None:
        return ValidatorResult(False, "event_start not set", variables_not_set=True)
    if not isinstance(start_dt, str):
        errors.append(f"event_start should be str")
    elif start_dt.strip() != expected_start_str:
        errors.append(f"event_start='{start_dt}', expected '{expected_start_str}'")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: {best_station}, {best_hours}h from {expected_start_str}")

tools = []
variables = [
    Variable("station_name", None, "Station with longest consecutive PM2.5>50 event (str)."),
    Variable("consecutive_hours", None, "Number of consecutive hours (int)."),
    Variable("event_start", None, "Start datetime of the event, format 'YYYY-MM-DD HH:MM:SS' (str)."),
]
validators = {"validate_consecutive": validate_consecutive}
