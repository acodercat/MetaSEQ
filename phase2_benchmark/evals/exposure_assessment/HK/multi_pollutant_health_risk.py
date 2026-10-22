
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_multi_pollutant(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    res_name = runtime.retrieve("residential_area_name")
    station_name = runtime.retrieve("station_name")
    total_ar = runtime.retrieve("total_ar")

    ground_truth = pd.read_sql(
        text("""
            WITH largest_res AS (
                SELECT id, name, geometry FROM sensitive_area
                WHERE category = 'RESIDENTIAL_AREA' AND area IS NOT NULL
                ORDER BY area DESC LIMIT 1
            ),
            nearest_station AS (
                SELECT aqs.id AS station_id, aqs.name_en, lr.name AS res_name
                FROM largest_res lr CROSS JOIN air_quality_station aqs
                ORDER BY ST_Distance(ST_Centroid(lr.geometry)::geography, aqs.coordinate)
                LIMIT 1
            )
            SELECT ns.res_name, ns.name_en AS station_name,
                   ROUND((COALESCE(hsaq.no2_ar, 0) + COALESCE(hsaq.o3_ar, 0)
                        + COALESCE(hsaq.so2_ar, 0) + COALESCE(hsaq.pm_ar, 0))::numeric, 2) AS total_ar
            FROM nearest_station ns
            JOIN hourly_station_air_quality hsaq ON ns.station_id = hsaq.station_id
            WHERE hsaq.datetime = '2025-10-05 14:00:00'
        """),
        engine,
    )

    if ground_truth.empty:
        return ValidatorResult(False, "No ground-truth data found")

    expected_res = ground_truth["res_name"].iloc[0]
    expected_station = ground_truth["station_name"].iloc[0]
    expected_ar = float(ground_truth["total_ar"].iloc[0])

    errors = []

    if res_name is None:
        return ValidatorResult(False, "residential_area_name not set", variables_not_set=True)
    if not isinstance(res_name, str):
        errors.append(f"residential_area_name should be str, got {type(res_name).__name__}")
    elif res_name.strip().lower() != str(expected_res).strip().lower():
        errors.append(f"residential_area_name='{res_name}', expected '{expected_res}'")

    if station_name is None:
        return ValidatorResult(False, "station_name not set", variables_not_set=True)
    if not isinstance(station_name, str):
        errors.append(f"station_name should be str, got {type(station_name).__name__}")
    elif station_name.strip().lower() != expected_station.strip().lower():
        errors.append(f"station_name='{station_name}', expected '{expected_station}'")

    if total_ar is None:
        return ValidatorResult(False, "total_ar not set", variables_not_set=True)
    if not is_finite_number(total_ar):
        errors.append(f"total_ar should be numeric, got {type(total_ar).__name__}")
    elif abs(total_ar - expected_ar) > 0.05:
        errors.append(f"total_ar={total_ar}, expected ≈ {expected_ar} (±0.05)")

    if errors:
        return ValidatorResult(False, "; ".join(errors))

    return ValidatorResult(True, f"Correct: {res_name} → {station_name}, AR={total_ar}")

tools = []
variables = [
    Variable("residential_area_name", None, "Store the name of the largest residential area sensitive area (str)."),
    Variable("station_name", None, "Store the name of the nearest AQ station (str)."),
    Variable("total_ar", None, "Store the total Added Health Risk rounded to 2 decimal places (float)."),
]
validators = {
    "validate_multi_pollutant": validate_multi_pollutant,
}
