
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def _get_rose_data():
    return pd.read_sql(
        text("""
            SELECT w.wind_direction, AVG(h.no2) AS avg_no2, COUNT(*) AS n
            FROM hourly_station_weather w
            JOIN weather_station ws ON w.station_id = ws.id
            JOIN hourly_station_air_quality h ON h.datetime = w.datetime
            JOIN air_quality_station aqs ON h.station_id = aqs.id
            WHERE ws.name_en = aqs.name_en AND ws.name_en = 'Tuen Mun'
              AND h.datetime >= '2025-10-01' AND h.datetime < '2025-11-01'
              AND w.wind_direction IS NOT NULL AND h.no2 IS NOT NULL AND w.wind_speed > 1
            GROUP BY w.wind_direction
            ORDER BY avg_no2 DESC
        """),
        engine,
    )
def validate_pollution_rose(
    response: str, runtime: IPythonRuntime, turn: Turn,
) -> ValidatorResult:
    highest_dir = runtime.retrieve("highest_no2_direction")
    highest_val = runtime.retrieve("highest_no2_value")
    lowest_dir = runtime.retrieve("lowest_no2_direction")
    lowest_val = runtime.retrieve("lowest_no2_value")
    north_val = runtime.retrieve("north_sector_no2")

    gt = _get_rose_data()
    expected_highest_dir = gt.iloc[0]["wind_direction"]
    expected_highest_val = round(float(gt.iloc[0]["avg_no2"]), 1)
    expected_lowest_dir = gt.iloc[-1]["wind_direction"]
    expected_lowest_val = round(float(gt.iloc[-1]["avg_no2"]), 1)

    north_row = gt[gt["wind_direction"].str.strip() == "N"]
    expected_north = round(float(north_row["avg_no2"].iloc[0]), 1) if not north_row.empty else 0.0

    # Handle ties
    max_no2 = gt["avg_no2"].max()
    min_no2 = gt["avg_no2"].min()
    tied_highest = gt[gt["avg_no2"] == max_no2]["wind_direction"].tolist()
    tied_lowest = gt[gt["avg_no2"] == min_no2]["wind_direction"].tolist()

    errors = []
    if highest_dir is None:
        return ValidatorResult(False, "highest_no2_direction not set", variables_not_set=True)
    if isinstance(highest_dir, str) and highest_dir.strip() not in [d.strip() for d in tied_highest]:
        errors.append(f"highest_no2_direction='{highest_dir}', expected one of {tied_highest}")

    if highest_val is None:
        return ValidatorResult(False, "highest_no2_value not set", variables_not_set=True)
    if not is_finite_number(highest_val):
        errors.append(f"highest_val should be numeric, got {type(highest_val).__name__}")
    elif abs(highest_val - expected_highest_val) > 3.0:
            errors.append(f"highest_no2_value={highest_val}, expected ≈ {expected_highest_val}")
    if lowest_dir is None:
        return ValidatorResult(False, "lowest_no2_direction not set", variables_not_set=True)
    if isinstance(lowest_dir, str) and lowest_dir.strip() not in [d.strip() for d in tied_lowest]:
        errors.append(f"lowest_no2_direction='{lowest_dir}', expected one of {tied_lowest}")

    if lowest_val is None:
        return ValidatorResult(False, "lowest_no2_value not set", variables_not_set=True)
    if not is_finite_number(lowest_val):
        errors.append(f"lowest_val should be numeric, got {type(lowest_val).__name__}")
    elif abs(lowest_val - expected_lowest_val) > 3.0:
            errors.append(f"lowest_no2_value={lowest_val}, expected ≈ {expected_lowest_val}")
    if north_val is None:
        return ValidatorResult(False, "north_sector_no2 not set", variables_not_set=True)
    if not is_finite_number(north_val):
        errors.append(f"north_val should be numeric, got {type(north_val).__name__}")
    elif abs(north_val - expected_north) > 2.0:
            errors.append(f"north_sector_no2={north_val}, expected ≈ {expected_north}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: highest={expected_highest_dir}({expected_highest_val}), lowest={expected_lowest_dir}({expected_lowest_val})")
tools = []
variables = [
    Variable("highest_no2_direction", None, "Wind direction with highest avg NO2 (str)."),
    Variable("highest_no2_value", None, "Avg NO2 from that direction (float, 1dp)."),
    Variable("lowest_no2_direction", None, "Wind direction with lowest avg NO2 (str)."),
    Variable("lowest_no2_value", None, "Avg NO2 from that direction (float, 1dp)."),
    Variable("north_sector_no2", None, "Avg NO2 when wind from north (float, 1dp)."),
]
validators = {"validate_pollution_rose": validate_pollution_rose}
