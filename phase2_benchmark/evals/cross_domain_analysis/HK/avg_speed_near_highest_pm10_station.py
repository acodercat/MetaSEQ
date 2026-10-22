
import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_avg_speed_near_highest_pm10_station(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    """Check agent finds avg traffic speed near the station with highest PM10 at 14:00."""
    speed_val = runtime.retrieve("avg_speed_near_pm10")

    ground_truth = pd.read_sql(
        text(
            "WITH max_pm10_station AS ( "
            "    SELECT aqs.id, aqs.coordinate "
            "    FROM hourly_station_air_quality hsaq "
            "    JOIN air_quality_station aqs ON hsaq.station_id = aqs.id "
            "    WHERE hsaq.datetime = '2025-10-05 14:00:00' "
            "    ORDER BY hsaq.pm10 DESC LIMIT 1 "
            ") "
            "SELECT ROUND(AVG(t.speed)::numeric, 1) AS avg_speed "
            "FROM hourly_road_segment_traffic t "
            "JOIN road_segment rs ON t.road_segment_id = rs.id "
            "CROSS JOIN max_pm10_station ms "
            "WHERE t.datetime = '2025-10-05 14:00:00' "
            "AND ST_DWithin(rs.geometry::geography, ms.coordinate, 500)"
        ),
        engine,
    )
    if ground_truth.empty or pd.isna(ground_truth["avg_speed"].iloc[0]):
        return ValidatorResult(False, "No ground-truth data for speed near max PM10 station")

    expected_speed = float(ground_truth["avg_speed"].iloc[0])

    if speed_val is None:
        return ValidatorResult(False, "avg_speed_near_pm10 not set")
    if not is_finite_number(speed_val):
        return ValidatorResult(False, f"avg_speed_near_pm10 should be numeric, got {type(speed_val).__name__}")
    if abs(speed_val - expected_speed) / max(abs(expected_speed), 1) > 0.01:
        return ValidatorResult(False, f"avg_speed_near_pm10: {speed_val}, expected ≈ {expected_speed}")

    return ValidatorResult(True, f"Correct avg speed: {speed_val}")

tools = []
variables = [
    Variable("avg_speed_near_pm10", None,
        "Store the average traffic speed within 500m of the station with highest PM10 at 2025-10-05 14:00 (float)."),
]
validators = {
    "validate_avg_speed_near_highest_pm10_station": validate_avg_speed_near_highest_pm10_station,
}
