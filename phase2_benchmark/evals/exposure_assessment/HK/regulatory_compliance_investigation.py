
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
DATE = "2025-12-30"
def _get_worst_station():
    return pd.read_sql(
        text(f"""
            SELECT aqs.id, aqs.name_en, AVG(hsaq.pm2_5) AS avg_pm25
            FROM hourly_station_air_quality hsaq
            JOIN air_quality_station aqs ON hsaq.station_id = aqs.id
            WHERE hsaq.datetime::date = '{DATE}' AND hsaq.pm2_5 IS NOT NULL
            GROUP BY aqs.id, aqs.name_en
            HAVING AVG(hsaq.pm2_5) > 15
            ORDER BY avg_pm25 DESC
        """),
        engine,
    )
def validate_t1(response, runtime, turn) -> ValidatorResult:
    count = runtime.retrieve("exceedance_station_count")
    worst_name = runtime.retrieve("worst_station_name")
    worst_pm25 = runtime.retrieve("worst_station_pm25")

    gt = _get_worst_station()
    expected_count = len(gt)
    expected_name = gt.iloc[0]["name_en"]
    expected_pm25 = round(float(gt.iloc[0]["avg_pm25"]), 1)

    errors = []
    if count is None:
        return ValidatorResult(False, "exceedance_station_count not set", variables_not_set=True)
    if not is_finite_number(count):
        errors.append("exceedance_station_count should be numeric")
    elif int(count) != expected_count:
        errors.append(f"exceedance_station_count={int(count)}, expected {expected_count}")
    if worst_name is None:
        return ValidatorResult(False, "worst_station_name not set", variables_not_set=True)
    if not isinstance(worst_name, str):
        errors.append("worst_station_name should be str")
    elif worst_name.strip().lower() != expected_name.strip().lower():
        errors.append(f"worst_station_name='{worst_name}', expected '{expected_name}'")
    if worst_pm25 is None:
        return ValidatorResult(False, "worst_station_pm25 not set", variables_not_set=True)
    if not is_finite_number(worst_pm25):
        errors.append("worst_station_pm25 should be numeric")
    elif abs(worst_pm25 - expected_pm25) > 0.5:
        errors.append(f"worst_station_pm25={worst_pm25}, expected ≈ {expected_pm25}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"T1 correct: {expected_count} stations, worst={worst_name}({worst_pm25})")
def validate_t2(response, runtime, turn) -> ValidatorResult:
    res_cnt = runtime.retrieve("residential_count")
    edu_cnt = runtime.retrieve("educational_count")

    gt = _get_worst_station()
    station_id = int(gt.iloc[0]["id"])

    counts_gt = pd.read_sql(
        text(f"""
            SELECT
                (SELECT COUNT(*) FROM sensitive_area sa
                 WHERE sa.category = 'RESIDENTIAL_AREA'
                   AND ST_DWithin(ST_Centroid(sa.geometry)::geography,
                       (SELECT coordinate FROM air_quality_station WHERE id = {station_id}), 2000)) AS res_cnt,
                (SELECT COUNT(*) FROM sensitive_area sa
                 WHERE sa.category = 'EDUCATIONAL_INSTITUTION'
                   AND ST_DWithin(ST_Centroid(sa.geometry)::geography,
                       (SELECT coordinate FROM air_quality_station WHERE id = {station_id}), 2000)) AS edu_cnt
        """),
        engine,
    )
    expected_res = int(counts_gt["res_cnt"].iloc[0])
    expected_edu = int(counts_gt["edu_cnt"].iloc[0])

    errors = []
    for var, val, exp in [("residential_count", res_cnt, expected_res), ("educational_count", edu_cnt, expected_edu)]:
        if val is None:
            return ValidatorResult(False, f"{var} not set", variables_not_set=True)
        if not is_finite_number(val):
            errors.append(f"{var} should be numeric")
        elif abs(int(val) - exp) > 5:
            errors.append(f"{var}={int(val)}, expected ≈ {exp} (±5)")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"T2 correct: res={res_cnt}, edu={edu_cnt}")
def validate_t3(response, runtime, turn) -> ValidatorResult:
    pct = runtime.retrieve("residential_in_residential_zone_pct")

    gt = _get_worst_station()
    station_id = int(gt.iloc[0]["id"])

    # Residential areas within 2km
    res_areas = pd.read_sql(
        text(f"""
            SELECT sa.id, ST_Centroid(sa.geometry) AS centroid
            FROM sensitive_area sa
            WHERE sa.category = 'RESIDENTIAL_AREA'
              AND ST_DWithin(ST_Centroid(sa.geometry)::geography,
                  (SELECT coordinate FROM air_quality_station WHERE id = {station_id}), 2000)
        """),
        engine,
    )
    total_res = len(res_areas)

    if total_res == 0:
        expected_pct = 0.0
    else:
        # Count how many are in Residential land use zones
        res_ids = ", ".join(str(i) for i in res_areas["id"].tolist())
        in_zone = pd.read_sql(
            text(f"""
                SELECT COUNT(DISTINCT sa.id) AS cnt
                FROM sensitive_area sa, land_use_zone l
                WHERE sa.id IN ({res_ids})
                  AND l.land_category = 'Residential'
                  AND ST_Contains(l.geometry, ST_Centroid(sa.geometry))
            """),
            engine,
        )
        in_zone_cnt = int(in_zone["cnt"].iloc[0])
        expected_pct = round((in_zone_cnt / total_res) * 100, 1)

    if pct is None:
        return ValidatorResult(False, "residential_in_residential_zone_pct not set", variables_not_set=True)
    if not is_finite_number(pct):
        return ValidatorResult(False, "residential_in_residential_zone_pct should be numeric")
    if abs(pct - expected_pct) > 2.0:
        return ValidatorResult(False, f"residential_in_residential_zone_pct={pct}, expected ≈ {expected_pct} (±2)")
    return ValidatorResult(True, f"T3 correct: {pct}% residential areas in Residential zones")
tools = []
variables = [
    Variable("exceedance_station_count", None, "T1: Number of stations exceeding WHO guideline (int)."),
    Variable("worst_station_name", None, "T1: Station with highest daily avg PM2.5 (str)."),
    Variable("worst_station_pm25", None, "T1: That station's daily avg PM2.5 rounded to 1dp (float)."),
    Variable("residential_count", None, "T2: residential area count within 2km (int)."),
    Variable("educational_count", None, "T2: educational institution count within 2km (int)."),
    Variable("residential_in_residential_zone_pct", None, "T3: Percentage in Residential land use zones, 1dp (float)."),
]
validators = {"validate_t1": validate_t1, "validate_t2": validate_t2, "validate_t3": validate_t3}
