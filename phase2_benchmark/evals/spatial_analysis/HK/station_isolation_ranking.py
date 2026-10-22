
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_isolation_ranking(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    ground_truth = pd.read_sql(
        text("""
            SELECT a.name_en, MIN(ST_Distance(a.coordinate, b.coordinate)) AS nn_dist
            FROM air_quality_station a, air_quality_station b
            WHERE a.id != b.id
            GROUP BY a.id, a.name_en
            ORDER BY nn_dist DESC
            LIMIT 3
        """),
        engine,
    )
    if len(ground_truth) < 3:
        return ValidatorResult(False, "Fewer than 3 stations found")

    errors = []
    for rank in range(3):
        idx = rank + 1
        name_var = f"isolated_{idx}_name"
        dist_var = f"isolated_{idx}_distance"
        name_val = runtime.retrieve(name_var)
        dist_val = runtime.retrieve(dist_var)
        expected_name = ground_truth["name_en"].iloc[rank]
        expected_dist = float(ground_truth["nn_dist"].iloc[rank])

        if name_val is None:
            return ValidatorResult(False, f"{name_var} not set", variables_not_set=True)
        if not isinstance(name_val, str):
            errors.append(f"{name_var} should be str, got {type(name_val).__name__}")
        elif name_val.strip().lower() != expected_name.strip().lower():
            errors.append(f"{name_var}='{name_val}', expected '{expected_name}'")

        if dist_val is None:
            return ValidatorResult(False, f"{dist_var} not set", variables_not_set=True)
        if not is_finite_number(dist_val):
            errors.append(f"{dist_var} should be numeric, got {type(dist_val).__name__}")
        elif abs(dist_val - expected_dist) / max(expected_dist, 1) > 0.05:
            errors.append(f"{dist_var}={dist_val}, expected ≈ {expected_dist:.0f}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))

    return ValidatorResult(True, "Correct isolation ranking for top 3 stations")

tools = []
variables = [
    Variable("isolated_1_name", None, "Store the name of the most isolated station (str)."),
    Variable("isolated_1_distance", None, "Store the nearest-neighbor distance of the most isolated station in meters (float)."),
    Variable("isolated_2_name", None, "Store the name of the 2nd most isolated station (str)."),
    Variable("isolated_2_distance", None, "Store the nearest-neighbor distance of the 2nd most isolated station in meters (float)."),
    Variable("isolated_3_name", None, "Store the name of the 3rd most isolated station (str)."),
    Variable("isolated_3_distance", None, "Store the nearest-neighbor distance of the 3rd most isolated station in meters (float)."),
]
validators = {
    "validate_isolation_ranking": validate_isolation_ranking,
}
