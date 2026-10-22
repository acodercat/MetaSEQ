
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_quadrants(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    ne_count = runtime.retrieve("ne_count")
    nw_count = runtime.retrieve("nw_count")
    se_count = runtime.retrieve("se_count")
    sw_count = runtime.retrieve("sw_count")

    ground_truth = pd.read_sql(
        text("""
            WITH ref AS (
                SELECT ST_Y(coordinate::geometry) AS lat,
                       ST_X(coordinate::geometry) AS lon
                FROM air_quality_station
                WHERE name_en = 'Central'
                LIMIT 1
            )
            SELECT
                SUM(CASE WHEN ST_Y(a.coordinate::geometry) > ref.lat
                          AND ST_X(a.coordinate::geometry) > ref.lon THEN 1 ELSE 0 END) AS ne,
                SUM(CASE WHEN ST_Y(a.coordinate::geometry) > ref.lat
                          AND ST_X(a.coordinate::geometry) < ref.lon THEN 1 ELSE 0 END) AS nw,
                SUM(CASE WHEN ST_Y(a.coordinate::geometry) < ref.lat
                          AND ST_X(a.coordinate::geometry) > ref.lon THEN 1 ELSE 0 END) AS se,
                SUM(CASE WHEN ST_Y(a.coordinate::geometry) < ref.lat
                          AND ST_X(a.coordinate::geometry) < ref.lon THEN 1 ELSE 0 END) AS sw
            FROM air_quality_station a, ref
            WHERE a.name_en != 'Central'
        """),
        engine,
    )
    if ground_truth.empty:
        return ValidatorResult(False, "No ground-truth data found")

    expected = {
        "ne_count": int(ground_truth["ne"].iloc[0]),
        "nw_count": int(ground_truth["nw"].iloc[0]),
        "se_count": int(ground_truth["se"].iloc[0]),
        "sw_count": int(ground_truth["sw"].iloc[0]),
    }

    errors = []
    for var_name, actual_val in [("ne_count", ne_count), ("nw_count", nw_count),
                                  ("se_count", se_count), ("sw_count", sw_count)]:
        if actual_val is None:
            return ValidatorResult(False, f"{var_name} not set", variables_not_set=True)
        if not is_finite_number(actual_val):
            errors.append(f"{var_name} should be numeric, got {type(actual_val).__name__}")
        elif int(actual_val) != expected[var_name]:
            errors.append(f"{var_name}={int(actual_val)}, expected {expected[var_name]}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))

    return ValidatorResult(True, f"Correct quadrants: NE={expected['ne_count']}, NW={expected['nw_count']}, SE={expected['se_count']}, SW={expected['sw_count']}")

tools = []
variables = [
    Variable("ne_count", None, "Store the number of stations in the NE quadrant (int)."),
    Variable("nw_count", None, "Store the number of stations in the NW quadrant (int)."),
    Variable("se_count", None, "Store the number of stations in the SE quadrant (int)."),
    Variable("sw_count", None, "Store the number of stations in the SW quadrant (int)."),
]
validators = {
    "validate_quadrants": validate_quadrants,
}
