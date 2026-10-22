
import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_vis_pm25_correlation(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    vis_pm25_corr = runtime.retrieve("vis_pm25_corr")

    # Get hourly visibility at Chek Lap Kok and PM2.5 at Tung Chung, matched on datetime
    merged = pd.read_sql(
        text("""
            SELECT hsw.visibility, hsaq.pm2_5
            FROM hourly_station_weather hsw
            JOIN weather_station ws ON hsw.station_id = ws.id
            JOIN hourly_station_air_quality hsaq ON hsaq.datetime = hsw.datetime
            JOIN air_quality_station aqs ON hsaq.station_id = aqs.id
            WHERE ws.name_en = 'Chek Lap Kok'
              AND aqs.name_en = 'Tung Chung'
              AND hsw.datetime >= '2025-10-01' AND hsw.datetime < '2025-11-01'
              AND hsw.visibility IS NOT NULL
              AND hsaq.pm2_5 IS NOT NULL
        """),
        engine,
    )

    if len(merged) < 10:
        return ValidatorResult(False, f"Insufficient matched data: only {len(merged)} hours")

    expected_corr, _ = stats.pearsonr(merged["visibility"], merged["pm2_5"])
    expected_corr = round(float(expected_corr), 4)

    if vis_pm25_corr is None:
        return ValidatorResult(False, "vis_pm25_corr not set", variables_not_set=True)
    if not is_finite_number(vis_pm25_corr):
        return ValidatorResult(False, "vis_pm25_corr should be numeric")
    if abs(vis_pm25_corr - expected_corr) > 0.03:
        return ValidatorResult(False, f"vis_pm25_corr={vis_pm25_corr}, expected ≈ {expected_corr}")

    return ValidatorResult(True, f"Correct: correlation={expected_corr}")
def validate_vis_pm25_extremes(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    low_vis_date = runtime.retrieve("low_vis_date")
    low_vis_value = runtime.retrieve("low_vis_value")
    low_vis_pm25 = runtime.retrieve("low_vis_pm25")
    high_vis_date = runtime.retrieve("high_vis_date")
    high_vis_value = runtime.retrieve("high_vis_value")
    high_vis_pm25 = runtime.retrieve("high_vis_pm25")

    # Get daily average visibility at Chek Lap Kok
    daily_vis = pd.read_sql(
        text("""
            SELECT hsw.datetime::date AS day, AVG(hsw.visibility) AS avg_vis
            FROM hourly_station_weather hsw
            JOIN weather_station ws ON hsw.station_id = ws.id
            WHERE ws.name_en = 'Chek Lap Kok'
              AND hsw.datetime >= '2025-10-01' AND hsw.datetime < '2025-11-01'
              AND hsw.visibility IS NOT NULL
            GROUP BY day
            ORDER BY day
        """),
        engine,
    )

    # Get daily average PM2.5 at Tung Chung
    daily_pm25 = pd.read_sql(
        text("""
            SELECT hsaq.datetime::date AS day, AVG(hsaq.pm2_5) AS avg_pm25
            FROM hourly_station_air_quality hsaq
            JOIN air_quality_station aqs ON hsaq.station_id = aqs.id
            WHERE aqs.name_en = 'Tung Chung'
              AND hsaq.datetime >= '2025-10-01' AND hsaq.datetime < '2025-11-01'
              AND hsaq.pm2_5 IS NOT NULL
            GROUP BY day
            ORDER BY day
        """),
        engine,
    )

    merged = pd.merge(daily_vis, daily_pm25, on="day", how="inner")

    low_vis_row = merged.loc[merged["avg_vis"].idxmin()]
    high_vis_row = merged.loc[merged["avg_vis"].idxmax()]

    expected_low_date = str(low_vis_row["day"])
    expected_low_vis = round(float(low_vis_row["avg_vis"]), 1)
    expected_low_pm25 = round(float(low_vis_row["avg_pm25"]), 1)
    expected_high_date = str(high_vis_row["day"])
    expected_high_vis = round(float(high_vis_row["avg_vis"]), 1)
    expected_high_pm25 = round(float(high_vis_row["avg_pm25"]), 1)

    errors = []

    # Validate dates
    for var_name, val, expected in [
        ("low_vis_date", low_vis_date, expected_low_date),
        ("high_vis_date", high_vis_date, expected_high_date),
    ]:
        if val is None:
            return ValidatorResult(False, f"{var_name} not set", variables_not_set=True)
        if not isinstance(val, str):
            errors.append(f"{var_name} should be a string")
        elif val.strip() != expected:
            errors.append(f"{var_name}='{val}', expected '{expected}'")

    # Validate visibility values (tolerance ±500 meters)
    for var_name, val, expected in [
        ("low_vis_value", low_vis_value, expected_low_vis),
        ("high_vis_value", high_vis_value, expected_high_vis),
    ]:
        if val is None:
            return ValidatorResult(False, f"{var_name} not set", variables_not_set=True)
        if not is_finite_number(val):
            errors.append(f"{var_name} should be numeric")
        elif abs(val - expected) > 500:
            errors.append(f"{var_name}={val}, expected ≈ {expected}")

    # Validate PM2.5 values (tolerance ±0.5)
    for var_name, val, expected in [
        ("low_vis_pm25", low_vis_pm25, expected_low_pm25),
        ("high_vis_pm25", high_vis_pm25, expected_high_pm25),
    ]:
        if val is None:
            return ValidatorResult(False, f"{var_name} not set", variables_not_set=True)
        if not is_finite_number(val):
            errors.append(f"{var_name} should be numeric")
        elif abs(val - expected) > 0.5:
            errors.append(f"{var_name}={val}, expected ≈ {expected}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True,
        f"T2 correct: low_date={expected_low_date}(vis={expected_low_vis}, pm25={expected_low_pm25}), "
        f"high_date={expected_high_date}(vis={expected_high_vis}, pm25={expected_high_pm25})",
    )
tools = []
variables = [
    Variable("vis_pm25_corr", None, "T1: Pearson correlation between hourly visibility and PM2.5 (float, 4dp)."),
    Variable("low_vis_date", None, "T2: Date with lowest average visibility (str, YYYY-MM-DD)."),
    Variable("low_vis_value", None, "T2: Average visibility on lowest day (float, 1dp)."),
    Variable("low_vis_pm25", None, "T2: Average PM2.5 at Tung Chung on lowest visibility day (float, 1dp)."),
    Variable("high_vis_date", None, "T2: Date with highest average visibility (str, YYYY-MM-DD)."),
    Variable("high_vis_value", None, "T2: Average visibility on highest day (float, 1dp)."),
    Variable("high_vis_pm25", None, "T2: Average PM2.5 at Tung Chung on highest visibility day (float, 1dp)."),
]
validators = {
    "validate_vis_pm25_correlation": validate_vis_pm25_correlation,
    "validate_vis_pm25_extremes": validate_vis_pm25_extremes,
}
