
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_distance_pollution(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    avg_under_5km = runtime.retrieve("avg_diff_under_5km")
    avg_over_15km = runtime.retrieve("avg_diff_over_15km")

    # Step 1: Daily average PM2.5 per station
    pm25_data = pd.read_sql(
        text("""
            SELECT aqs.id, AVG(hsaq.pm2_5) AS avg_pm25
            FROM air_quality_station aqs
            JOIN hourly_station_air_quality hsaq ON aqs.id = hsaq.station_id
            WHERE hsaq.datetime::date = '2025-10-05'
              AND hsaq.pm2_5 IS NOT NULL
            GROUP BY aqs.id
        """),
        engine,
    )

    # Step 2: All-pairs distances (a < b to avoid duplicates)
    distances = pd.read_sql(
        text("""
            SELECT a.id AS id_a, b.id AS id_b,
                   ST_Distance(a.coordinate, b.coordinate) AS dist_m
            FROM air_quality_station a, air_quality_station b
            WHERE a.id < b.id
        """),
        engine,
    )

    # Step 3: Compute PM2.5 differences and group by distance
    pm25_map = pm25_data.set_index("id")["avg_pm25"].to_dict()

    diffs_under_5 = []
    diffs_over_15 = []

    for _, row in distances.iterrows():
        id_a, id_b = int(row["id_a"]), int(row["id_b"])
        if id_a not in pm25_map or id_b not in pm25_map:
            continue

        pm_diff = abs(pm25_map[id_a] - pm25_map[id_b])
        dist_km = row["dist_m"] / 1000.0

        if dist_km < 5:
            diffs_under_5.append(pm_diff)
        elif dist_km > 15:
            diffs_over_15.append(pm_diff)

    expected_under = round(float(np.mean(diffs_under_5)), 1) if diffs_under_5 else None
    expected_over = round(float(np.mean(diffs_over_15)), 1) if diffs_over_15 else None

    errors = []

    if avg_under_5km is None:
        return ValidatorResult(False, "avg_diff_under_5km not set", variables_not_set=True)
    if expected_under is None:
        errors.append("No station pairs found within 5km in ground truth")
    elif not is_finite_number(avg_under_5km):
        errors.append(f"avg_diff_under_5km should be numeric, got {type(avg_under_5km).__name__}")
    elif abs(avg_under_5km - expected_under) > 0.5:
        errors.append(f"avg_diff_under_5km={avg_under_5km}, expected ≈ {expected_under}")

    if avg_over_15km is None:
        return ValidatorResult(False, "avg_diff_over_15km not set", variables_not_set=True)
    if expected_over is None:
        errors.append("No station pairs found beyond 15km in ground truth")
    elif not is_finite_number(avg_over_15km):
        errors.append(f"avg_diff_over_15km should be numeric, got {type(avg_over_15km).__name__}")
    elif abs(avg_over_15km - expected_over) > 0.5:
        errors.append(f"avg_diff_over_15km={avg_over_15km}, expected ≈ {expected_over}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))

    return ValidatorResult(True, f"Correct: <5km avg diff={avg_under_5km}, >15km avg diff={avg_over_15km}")

tools = []
variables = [
    Variable("avg_diff_under_5km", None, "Store the average absolute PM2.5 difference for pairs <5km apart, rounded to 1 decimal place (float)."),
    Variable("avg_diff_over_15km", None, "Store the average absolute PM2.5 difference for pairs >15km apart, rounded to 1 decimal place (float)."),
]
validators = {
    "validate_distance_pollution": validate_distance_pollution,
}
