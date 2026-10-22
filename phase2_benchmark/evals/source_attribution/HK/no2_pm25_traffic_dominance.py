
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_traffic_dominance(
    response: str, runtime: IPythonRuntime, turn: Turn,
) -> ValidatorResult:
    no2_ratio = runtime.retrieve("no2_roadside_general_ratio")
    pm25_ratio = runtime.retrieve("pm25_roadside_general_ratio")
    more_dominated = runtime.retrieve("more_traffic_dominated")

    gt = pd.read_sql(
        text("""
            SELECT aqs.station_type,
                   AVG(h.no2) AS avg_no2, AVG(h.pm2_5) AS avg_pm25
            FROM hourly_station_air_quality h
            JOIN air_quality_station aqs ON h.station_id = aqs.id
            WHERE h.datetime >= '2025-10-01' AND h.datetime < '2025-11-01'
              AND h.no2 IS NOT NULL AND h.pm2_5 IS NOT NULL
            GROUP BY aqs.station_type
        """),
        engine,
    )
    r_row = gt[gt["station_type"] == "ROADSIDE"].iloc[0]
    g_row = gt[gt["station_type"] == "GENERAL"].iloc[0]

    expected_no2_ratio = round(r_row["avg_no2"] / g_row["avg_no2"], 2)
    expected_pm25_ratio = round(r_row["avg_pm25"] / g_row["avg_pm25"], 2)
    expected_dominated = "NO2" if expected_no2_ratio > expected_pm25_ratio else "PM2.5"

    errors = []
    if no2_ratio is None:
        return ValidatorResult(False, "no2_roadside_general_ratio not set", variables_not_set=True)
    if not is_finite_number(no2_ratio):
        errors.append(f"no2_ratio should be numeric, got {type(no2_ratio).__name__}")
    elif abs(no2_ratio - expected_no2_ratio) > 0.1:
            errors.append(f"no2_roadside_general_ratio={no2_ratio}, expected ≈ {expected_no2_ratio}")
    if pm25_ratio is None:
        return ValidatorResult(False, "pm25_roadside_general_ratio not set", variables_not_set=True)
    if not is_finite_number(pm25_ratio):
        errors.append(f"pm25_ratio should be numeric, got {type(pm25_ratio).__name__}")
    elif abs(pm25_ratio - expected_pm25_ratio) > 0.1:
            errors.append(f"pm25_roadside_general_ratio={pm25_ratio}, expected ≈ {expected_pm25_ratio}")
    if more_dominated is None:
        return ValidatorResult(False, "more_traffic_dominated not set", variables_not_set=True)
    if isinstance(more_dominated, str):
        agent_clean = more_dominated.strip().upper().replace(".", "").replace("_", "").replace(" ", "")
        expected_clean = expected_dominated.replace(".", "").replace("_", "")
        if agent_clean != expected_clean:
            errors.append(f"more_traffic_dominated='{more_dominated}', expected '{expected_dominated}'")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: NO2 ratio={expected_no2_ratio}, PM2.5 ratio={expected_pm25_ratio}")
def validate_rush_offpeak_ratio(
    response: str, runtime: IPythonRuntime, turn: Turn,
) -> ValidatorResult:
    rush_ratio = runtime.retrieve("rush_no2_pm25_ratio")
    offpeak_ratio = runtime.retrieve("offpeak_no2_pm25_ratio")

    gt = pd.read_sql(
        text("""
            SELECT
                CASE WHEN EXTRACT(HOUR FROM h.datetime) IN (8,9,17,18,19) THEN 'rush'
                     ELSE 'offpeak' END AS period,
                AVG(h.no2 / h.pm2_5) AS no2_pm25_ratio
            FROM hourly_station_air_quality h
            JOIN air_quality_station aqs ON h.station_id = aqs.id
            WHERE h.datetime >= '2025-10-01' AND h.datetime < '2025-11-01'
              AND aqs.station_type = 'ROADSIDE'
              AND h.no2 IS NOT NULL AND h.pm2_5 IS NOT NULL AND h.pm2_5 > 0
              AND EXTRACT(HOUR FROM h.datetime) IN (0,1,2,3,4,5,8,9,10,11,12,13,14,15,17,18,19)
            GROUP BY period
        """),
        engine,
    )
    expected_rush = round(float(gt[gt["period"] == "rush"]["no2_pm25_ratio"].iloc[0]), 2)
    expected_offpeak = round(float(gt[gt["period"] == "offpeak"]["no2_pm25_ratio"].iloc[0]), 2)

    errors = []
    if rush_ratio is None:
        return ValidatorResult(False, "rush_no2_pm25_ratio not set", variables_not_set=True)
    if not is_finite_number(rush_ratio):
        errors.append(f"rush_ratio should be numeric, got {type(rush_ratio).__name__}")
    elif abs(rush_ratio - expected_rush) > 0.15:
            errors.append(f"rush_no2_pm25_ratio={rush_ratio}, expected ≈ {expected_rush}")
    if offpeak_ratio is None:
        return ValidatorResult(False, "offpeak_no2_pm25_ratio not set", variables_not_set=True)
    if not is_finite_number(offpeak_ratio):
        errors.append(f"offpeak_ratio should be numeric, got {type(offpeak_ratio).__name__}")
    elif abs(offpeak_ratio - expected_offpeak) > 0.15:
            errors.append(f"offpeak_no2_pm25_ratio={offpeak_ratio}, expected ≈ {expected_offpeak}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: rush={expected_rush}, offpeak={expected_offpeak}")
tools = []
variables = [
    Variable("no2_roadside_general_ratio", None, "T1: Ratio of roadside avg NO2 to general avg NO2 (float, 2dp)."),
    Variable("pm25_roadside_general_ratio", None, "T1: Ratio of roadside avg PM2.5 to general avg PM2.5 (float, 2dp)."),
    Variable("more_traffic_dominated", None, "T1: Which pollutant has larger roadside enhancement (str)."),
    Variable("rush_no2_pm25_ratio", None, "T2: Average NO2/PM2.5 ratio during rush hours at roadside stations (float, 2dp)."),
    Variable("offpeak_no2_pm25_ratio", None, "T2: Average NO2/PM2.5 ratio during off-peak hours at roadside stations (float, 2dp)."),
]
validators = {
    "validate_traffic_dominance": validate_traffic_dominance,
    "validate_rush_offpeak_ratio": validate_rush_offpeak_ratio,
}
