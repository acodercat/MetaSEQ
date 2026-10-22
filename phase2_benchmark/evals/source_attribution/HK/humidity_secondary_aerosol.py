
import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def _get_kings_park_id():
    ws = pd.read_sql(
        text("SELECT id FROM weather_station WHERE name_en = 'King''s Park' LIMIT 1"),
        engine,
    )
    return int(ws["id"].iloc[0])
def _get_matched_data():
    """Get hourly PM2.5/PM10 ratio from GENERAL stations matched with King's Park humidity."""
    ws_id = _get_kings_park_id()
    data = pd.read_sql(
        text(f"""
            SELECT hsaq.datetime,
                   AVG(hsaq.pm2_5 / NULLIF(hsaq.pm10, 0)) AS avg_ratio,
                   hsw.humidity
            FROM hourly_station_air_quality hsaq
            JOIN air_quality_station aqs ON hsaq.station_id = aqs.id
            JOIN hourly_station_weather hsw ON hsw.station_id = {ws_id}
                AND hsw.datetime = hsaq.datetime
            WHERE aqs.station_type = 'GENERAL'
              AND hsaq.datetime >= '2025-10-01' AND hsaq.datetime < '2025-11-01'
              AND hsaq.pm2_5 IS NOT NULL AND hsaq.pm10 IS NOT NULL AND hsaq.pm10 > 0
              AND hsw.humidity IS NOT NULL
            GROUP BY hsaq.datetime, hsw.humidity
        """),
        engine,
    )
    return data
def validate_humidity_aerosol(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    low = runtime.retrieve("ratio_low_humidity")
    mid = runtime.retrieve("ratio_mid_humidity")
    high = runtime.retrieve("ratio_high_humidity")

    data = _get_matched_data()

    expected = {}
    for label, mask in [
        ("low", data["humidity"] < 60),
        ("mid", (data["humidity"] >= 60) & (data["humidity"] <= 80)),
        ("high", data["humidity"] > 80),
    ]:
        subset = data[mask]
        expected[label] = round(float(subset["avg_ratio"].mean()), 3) if len(subset) > 0 else None

    errors = []
    for var_name, val, label in [("ratio_low_humidity", low, "low"), ("ratio_mid_humidity", mid, "mid"),
                                  ("ratio_high_humidity", high, "high")]:
        if expected[label] is None:
            continue
        if val is None:
            return ValidatorResult(False, f"{var_name} not set", variables_not_set=True)
        if not is_finite_number(val):
            errors.append(f"{var_name} should be numeric")
        elif abs(val - expected[label]) > 0.02:
            errors.append(f"{var_name}={val}, expected ≈ {expected[label]}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: low={expected['low']}, mid={expected['mid']}, high={expected['high']}")

def validate_humidity_aerosol_t2(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    corr = runtime.retrieve("humidity_ratio_correlation")

    data = _get_matched_data()
    if len(data) < 10:
        return ValidatorResult(False, f"Insufficient data: {len(data)} hours")

    r, _ = stats.pearsonr(data["humidity"], data["avg_ratio"])
    expected_corr = round(float(r), 4)

    if corr is None:
        return ValidatorResult(False, "humidity_ratio_correlation not set", variables_not_set=True)
    if not is_finite_number(corr):
        return ValidatorResult(False, "humidity_ratio_correlation should be numeric")
    if abs(corr - expected_corr) > 0.05:
        return ValidatorResult(False, f"humidity_ratio_correlation={corr}, expected ≈ {expected_corr}")

    return ValidatorResult(True, f"T2 correct: correlation={expected_corr}")

tools = []
variables = [
    Variable("ratio_low_humidity", None, "T1: Avg PM2.5/PM10 ratio when humidity < 60% (float, 3dp)."),
    Variable("ratio_mid_humidity", None, "T1: Avg PM2.5/PM10 ratio when humidity 60-80% (float, 3dp)."),
    Variable("ratio_high_humidity", None, "T1: Avg PM2.5/PM10 ratio when humidity > 80% (float, 3dp)."),
    Variable("humidity_ratio_correlation", None, "T2: Pearson correlation between humidity and PM2.5/PM10 ratio (float, 4dp)."),
]
validators = {"validate_humidity_aerosol": validate_humidity_aerosol, "validate_humidity_aerosol_t2": validate_humidity_aerosol_t2}
