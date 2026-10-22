
import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_nearest_station_to_severe_congestion(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    """Check agent finds nearest station to any severe congestion (status 3) at 18:00 and its NO2."""
    station_id = runtime.retrieve("severe_congestion_station_id")
    no2_val = runtime.retrieve("severe_congestion_station_no2")

    ground_truth = pd.read_sql(
        text(
            "WITH severe_roads AS ( "
            "    SELECT rs.geometry "
            "    FROM hourly_road_segment_traffic t "
            "    JOIN road_segment rs ON t.road_segment_id = rs.id "
            "    WHERE t.datetime = '2025-10-05 18:00:00' AND t.congestion_status = 3 "
            "), "
            "nearest_station AS ( "
            "    SELECT aqs.id AS station_id "
            "    FROM air_quality_station aqs "
            "    CROSS JOIN severe_roads sr "
            "    ORDER BY ST_Distance(aqs.coordinate, sr.geometry::geography) ASC LIMIT 1 "
            ") "
            "SELECT ns.station_id, hsaq.no2 "
            "FROM hourly_station_air_quality hsaq "
            "JOIN nearest_station ns ON hsaq.station_id = ns.station_id "
            "WHERE hsaq.datetime = '2025-10-05 18:00:00'"
        ),
        engine,
    )
    if ground_truth.empty:
        return ValidatorResult(False, "No ground-truth data for severe congestion and stations")

    expected_id = int(ground_truth["station_id"].iloc[0])
    expected_no2 = float(ground_truth["no2"].iloc[0])

    errors = []

    if station_id is None:
        errors.append("severe_congestion_station_id not set")
    elif int(station_id) != expected_id:
        errors.append(f"severe_congestion_station_id: {station_id}, expected {expected_id}")

    if no2_val is None:
        errors.append("severe_congestion_station_no2 not set")
    elif not is_finite_number(no2_val):
        errors.append(f"severe_congestion_station_no2 should be numeric, got {type(no2_val).__name__}")
    elif abs(no2_val - expected_no2) > 0.5:
        errors.append(f"severe_congestion_station_no2: {no2_val}, expected ≈ {expected_no2}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))

    return ValidatorResult(True, f"Correct station {station_id} with NO2={no2_val}")

tools = []
variables = [
    Variable("severe_congestion_station_id", None,
        "Store the ID of the nearest air quality station to any severely congested road (most severe level) at 2025-10-05 18:00 (int)."),
    Variable("severe_congestion_station_no2", None,
        "Store the NO2 reading at the nearest station to severe congestion at 2025-10-05 18:00 (float)."),
]
validators = {
    "validate_nearest_station_to_severe_congestion": validate_nearest_station_to_severe_congestion,
}
