
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_ox_ratio(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    roadside_ox = runtime.retrieve("roadside_ox_ratio")
    general_ox = runtime.retrieve("general_ox_ratio")
    highest_station = runtime.retrieve("highest_ox_station")
    highest_ratio = runtime.retrieve("highest_ox_ratio")

    gt = pd.read_sql(
        text("""
            SELECT aqs.name_en, aqs.station_type,
                   AVG(hsaq.o3 / NULLIF(hsaq.o3 + hsaq.no2, 0)) AS avg_ox_ratio
            FROM hourly_station_air_quality hsaq
            JOIN air_quality_station aqs ON hsaq.station_id = aqs.id
            WHERE hsaq.datetime::date = '2025-10-05'
              AND hsaq.o3 IS NOT NULL AND hsaq.no2 IS NOT NULL
              AND (hsaq.o3 + hsaq.no2) > 0
            GROUP BY aqs.id, aqs.name_en, aqs.station_type
            ORDER BY avg_ox_ratio DESC
        """),
        engine,
    )

    roadside = gt[gt["station_type"] == "ROADSIDE"]
    general = gt[gt["station_type"] == "GENERAL"]

    expected_roadside = round(float(roadside["avg_ox_ratio"].mean()), 3)
    expected_general = round(float(general["avg_ox_ratio"].mean()), 3)
    expected_highest_name = gt.iloc[0]["name_en"]
    expected_highest_ratio = round(float(gt.iloc[0]["avg_ox_ratio"]), 3)

    errors = []

    if roadside_ox is None:
        return ValidatorResult(False, "roadside_ox_ratio not set", variables_not_set=True)
    if not is_finite_number(roadside_ox):
        errors.append("roadside_ox_ratio should be numeric")
    elif abs(roadside_ox - expected_roadside) > 0.01:
        errors.append(f"roadside_ox_ratio={roadside_ox}, expected ≈ {expected_roadside}")

    if general_ox is None:
        return ValidatorResult(False, "general_ox_ratio not set", variables_not_set=True)
    if not is_finite_number(general_ox):
        errors.append("general_ox_ratio should be numeric")
    elif abs(general_ox - expected_general) > 0.01:
        errors.append(f"general_ox_ratio={general_ox}, expected ≈ {expected_general}")

    if highest_station is None:
        return ValidatorResult(False, "highest_ox_station not set", variables_not_set=True)
    if not isinstance(highest_station, str):
        errors.append("highest_ox_station should be str")
    elif highest_station.strip().lower() != expected_highest_name.strip().lower():
        errors.append(f"highest_ox_station='{highest_station}', expected '{expected_highest_name}'")

    if highest_ratio is None:
        return ValidatorResult(False, "highest_ox_ratio not set", variables_not_set=True)
    if not is_finite_number(highest_ratio):
        errors.append("highest_ox_ratio should be numeric")
    elif abs(highest_ratio - expected_highest_ratio) > 0.01:
        errors.append(f"highest_ox_ratio={highest_ratio}, expected ≈ {expected_highest_ratio}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: roadside={expected_roadside}, general={expected_general}, highest={expected_highest_name}({expected_highest_ratio})")

def validate_ox_ratio_t2(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    morning_ox = runtime.retrieve("morning_ox")
    midday_ox = runtime.retrieve("midday_ox")
    evening_ox = runtime.retrieve("evening_ox")

    # Re-derive the station with highest Ox ratio
    gt = pd.read_sql(
        text("""
            SELECT aqs.id, aqs.name_en,
                   AVG(hsaq.o3 / NULLIF(hsaq.o3 + hsaq.no2, 0)) AS avg_ox_ratio
            FROM hourly_station_air_quality hsaq
            JOIN air_quality_station aqs ON hsaq.station_id = aqs.id
            WHERE hsaq.datetime::date = '2025-10-05'
              AND hsaq.o3 IS NOT NULL AND hsaq.no2 IS NOT NULL
              AND (hsaq.o3 + hsaq.no2) > 0
            GROUP BY aqs.id, aqs.name_en
            ORDER BY avg_ox_ratio DESC LIMIT 1
        """),
        engine,
    )
    station_id = int(gt["id"].iloc[0])

    expected = {}
    for label, start_hr, end_hr in [("morning", 6, 9), ("midday", 11, 14), ("evening", 17, 20)]:
        period_gt = pd.read_sql(
            text(f"""
                SELECT AVG(o3 / NULLIF(o3 + no2, 0)) AS avg_ratio
                FROM hourly_station_air_quality
                WHERE station_id = {station_id}
                  AND datetime::date = '2025-10-05'
                  AND o3 IS NOT NULL AND no2 IS NOT NULL AND (o3 + no2) > 0
                  AND EXTRACT(HOUR FROM datetime) >= {start_hr}
                  AND EXTRACT(HOUR FROM datetime) <= {end_hr}
            """),
            engine,
        )
        expected[label] = round(float(period_gt["avg_ratio"].iloc[0]), 3)

    errors = []
    for var_name, val, label in [("morning_ox", morning_ox, "morning"), ("midday_ox", midday_ox, "midday"), ("evening_ox", evening_ox, "evening")]:
        if val is None:
            return ValidatorResult(False, f"{var_name} not set", variables_not_set=True)
        if not is_finite_number(val):
            errors.append(f"{var_name} should be numeric")
        elif abs(val - expected[label]) > 0.01:
            errors.append(f"{var_name}={val}, expected ≈ {expected[label]}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"T2 correct: morning={expected['morning']}, midday={expected['midday']}, evening={expected['evening']}")

tools = []
variables = [
    Variable("roadside_ox_ratio", None, "T1: Mean photochemical oxidant partitioning ratio for roadside stations (float, 3dp)."),
    Variable("general_ox_ratio", None, "T1: Mean photochemical oxidant partitioning ratio for general stations (float, 3dp)."),
    Variable("highest_ox_station", None, "T1: Station with highest photochemical oxidant partitioning ratio (str)."),
    Variable("highest_ox_ratio", None, "T1: Highest photochemical oxidant partitioning ratio (float, 3dp)."),
    Variable("morning_ox", None, "T2: photochemical oxidant partitioning ratio for 06:00-09:00 at highest-ratio station (float, 3dp)."),
    Variable("midday_ox", None, "T2: photochemical oxidant partitioning ratio for 11:00-14:00 at highest-ratio station (float, 3dp)."),
    Variable("evening_ox", None, "T2: photochemical oxidant partitioning ratio for 17:00-20:00 at highest-ratio station (float, 3dp)."),
]
validators = {"validate_ox_ratio": validate_ox_ratio, "validate_ox_ratio_t2": validate_ox_ratio_t2}
