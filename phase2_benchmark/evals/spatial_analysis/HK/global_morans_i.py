
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_morans_i(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    morans_i = runtime.retrieve("morans_i")
    spatial_pattern = runtime.retrieve("spatial_pattern")

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

    # Step 2: All-pairs distances
    distances = pd.read_sql(
        text("""
            SELECT a.id AS id_a, b.id AS id_b,
                   ST_Distance(a.coordinate, b.coordinate) AS dist_m
            FROM air_quality_station a, air_quality_station b
            WHERE a.id != b.id
        """),
        engine,
    )

    # Step 3: Compute Global Moran's I with inverse distance weights
    pm25_map = pm25_data.set_index("id")["avg_pm25"].to_dict()
    station_ids = list(pm25_map.keys())
    n = len(station_ids)
    x_bar = np.mean(list(pm25_map.values()))

    # Build weight lookup
    dist_lookup = {}
    for _, row in distances.iterrows():
        dist_lookup[(int(row["id_a"]), int(row["id_b"]))] = row["dist_m"]

    # Compute Moran's I
    w_total = 0.0
    numerator = 0.0
    denominator = 0.0

    for i in station_ids:
        denominator += (pm25_map[i] - x_bar) ** 2

    for i in station_ids:
        for j in station_ids:
            if i == j:
                continue
            d = dist_lookup.get((i, j), None)
            if d is None or d == 0:
                continue
            w = 1.0 / d
            w_total += w
            numerator += w * (pm25_map[i] - x_bar) * (pm25_map[j] - x_bar)

    if denominator == 0 or w_total == 0:
        return ValidatorResult(False, "Cannot compute Moran's I: zero variance or zero weights")

    expected_i = round((n / w_total) * (numerator / denominator), 4)

    # Determine expected pattern
    if expected_i > 0.1:
        expected_pattern = "clustered"
    elif expected_i < -0.1:
        expected_pattern = "dispersed"
    else:
        expected_pattern = "random"

    # Validate
    errors = []

    if morans_i is None:
        return ValidatorResult(False, "morans_i not set", variables_not_set=True)
    if not is_finite_number(morans_i):
        errors.append(f"morans_i should be numeric, got {type(morans_i).__name__}")
    elif abs(morans_i - expected_i) > 0.02:
        errors.append(f"morans_i={morans_i}, expected ≈ {expected_i} (±0.02)")

    if spatial_pattern is None:
        return ValidatorResult(False, "spatial_pattern not set", variables_not_set=True)
    if not isinstance(spatial_pattern, str):
        errors.append(f"spatial_pattern should be str, got {type(spatial_pattern).__name__}")
    elif spatial_pattern.strip().lower() != expected_pattern:
        errors.append(f"spatial_pattern='{spatial_pattern}', expected '{expected_pattern}'")

    if errors:
        return ValidatorResult(False, "; ".join(errors))

    return ValidatorResult(True, f"Correct: Moran's I={morans_i}, pattern={spatial_pattern}")

tools = []
variables = [
    Variable("morans_i", None, "Store the Global Moran's I value rounded to 4 decimal places (float)."),
    Variable("spatial_pattern", None, "Store the spatial pattern: 'clustered', 'dispersed', or 'random' (str)."),
]
validators = {
    "validate_morans_i": validate_morans_i,
}
