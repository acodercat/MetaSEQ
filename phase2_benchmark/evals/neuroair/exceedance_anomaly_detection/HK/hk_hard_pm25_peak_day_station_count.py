import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_hard_pm25_peak_day_station_count(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    sql = text("""
        WITH daily AS (
            SELECT aq.station_id, s.station_type, aq.datetime::date AS d, MAX(aq.pm2_5) AS daily_max
            FROM hourly_station_air_quality aq
            JOIN air_quality_station s ON s.id = aq.station_id
            WHERE aq.datetime >= '2025-06-01 00:00:00'
              AND aq.datetime <  '2025-07-01 00:00:00'
              AND aq.pm2_5 IS NOT NULL
            GROUP BY aq.station_id, s.station_type, aq.datetime::date
        ), station_counts AS (
            SELECT station_id, station_type, SUM(CASE WHEN daily_max >= 35.0 THEN 1 ELSE 0 END) AS peak_days
            FROM daily
            GROUP BY station_id, station_type
        ), type_avgs AS (
            SELECT station_type, AVG(peak_days::float) AS avg_peak_days
            FROM station_counts
            GROUP BY station_type
        )
        SELECT (SELECT avg_peak_days FROM type_avgs WHERE station_type = 'ROADSIDE') AS r,
               (SELECT avg_peak_days FROM type_avgs WHERE station_type = 'GENERAL') AS g,
               (SELECT avg_peak_days FROM type_avgs WHERE station_type = 'ROADSIDE') - (SELECT avg_peak_days FROM type_avgs WHERE station_type = 'GENERAL') AS diff
    """)
    df = pd.read_sql(sql, engine)
    gt = {"roadside_avg_peak_days": round(float(df.loc[0, "r"]), 6), "general_avg_peak_days": round(float(df.loc[0, "g"]), 6), "roadside_minus_general": round(float(df.loc[0, "diff"]), 6)}
    errs=[]
    v=runtime.retrieve("roadside_avg_peak_days")
    if v is None: return ValidatorResult(False,"roadside_avg_peak_days not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"roadside_avg_peak_days not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["roadside_avg_peak_days"]),tolerance=1e-06): errs.append(f"roadside_avg_peak_days={round(float(v),3)}, expected ~{round(float(gt['roadside_avg_peak_days']),3)} (tol 1e-06)")
    v=runtime.retrieve("general_avg_peak_days")
    if v is None: return ValidatorResult(False,"general_avg_peak_days not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"general_avg_peak_days not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["general_avg_peak_days"]),tolerance=1e-06): errs.append(f"general_avg_peak_days={round(float(v),3)}, expected ~{round(float(gt['general_avg_peak_days']),3)} (tol 1e-06)")
    v=runtime.retrieve("roadside_minus_general")
    if v is None: return ValidatorResult(False,"roadside_minus_general not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"roadside_minus_general not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["roadside_minus_general"]),tolerance=1e-06): errs.append(f"roadside_minus_general={round(float(v),3)}, expected ~{round(float(gt['roadside_minus_general']),3)} (tol 1e-06)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("roadside_avg_peak_days", None, "Average across ROADSIDE stations of the number of June dates whose daily max PM2.5 >= 35.0."),
    Variable("general_avg_peak_days", None, "Average across GENERAL stations of the number of June dates whose daily max PM2.5 >= 35.0."),
    Variable("roadside_minus_general", None, "roadside_avg_peak_days minus general_avg_peak_days, rounded to 6 decimals."),
]
validators = {"validate_hk_hard_pm25_peak_day_station_count": validate_hk_hard_pm25_peak_day_station_count}
