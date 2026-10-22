import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_hard_same_hour_area_correlations(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    sql = text("""
        WITH hourly AS (
            SELECT aq.datetime,
                   AVG(aq.no2) FILTER (WHERE s.station_type = 'GENERAL' AND s.area_type = 'URBAN') AS gen_no2,
                   AVG(aq.no2) FILTER (WHERE s.station_type = 'ROADSIDE' AND s.area_type = 'URBAN') AS road_no2,
                   AVG(aq.pm10) FILTER (WHERE s.station_type = 'GENERAL' AND s.area_type = 'URBAN') AS gen_pm10,
                   AVG(aq.pm10) FILTER (WHERE s.station_type = 'ROADSIDE' AND s.area_type = 'URBAN') AS road_pm10
            FROM hourly_station_air_quality aq
            JOIN air_quality_station s ON s.id = aq.station_id
            WHERE aq.datetime >= '2025-06-01 00:00:00'
              AND aq.datetime <  '2025-07-01 00:00:00'
              AND s.area_type = 'URBAN'
            GROUP BY aq.datetime
        )
        SELECT COUNT(*) FILTER (WHERE gen_no2 IS NOT NULL AND road_no2 IS NOT NULL) AS n_no2,
               corr(gen_no2, road_no2) FILTER (WHERE gen_no2 IS NOT NULL AND road_no2 IS NOT NULL) AS r_no2,
               COUNT(*) FILTER (WHERE gen_pm10 IS NOT NULL AND road_pm10 IS NOT NULL) AS n_pm10,
               corr(gen_pm10, road_pm10) FILTER (WHERE gen_pm10 IS NOT NULL AND road_pm10 IS NOT NULL) AS r_pm10
        FROM hourly
    """)
    df = pd.read_sql(sql, engine)
    gt = {"no2_pair_count": int(df.loc[0, "n_no2"]), "no2_corr": round(float(df.loc[0, "r_no2"]), 6), "pm10_pair_count": int(df.loc[0, "n_pm10"]), "pm10_corr": round(float(df.loc[0, "r_pm10"]), 6)}
    errs=[]
    v=runtime.retrieve("no2_pair_count")
    if v is None: return ValidatorResult(False,"no2_pair_count not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"no2_pair_count not numeric: {v!r}")
    if int(round(float(v)))!=int(round(float(gt["no2_pair_count"]))): errs.append(f"no2_pair_count={int(round(float(v)))}, expected {int(round(float(gt['no2_pair_count'])))}")
    v=runtime.retrieve("no2_corr")
    if v is None: return ValidatorResult(False,"no2_corr not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"no2_corr not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["no2_corr"]),tolerance=1e-06): errs.append(f"no2_corr={round(float(v),3)}, expected ~{round(float(gt['no2_corr']),3)} (tol 1e-06)")
    v=runtime.retrieve("pm10_pair_count")
    if v is None: return ValidatorResult(False,"pm10_pair_count not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"pm10_pair_count not numeric: {v!r}")
    if int(round(float(v)))!=int(round(float(gt["pm10_pair_count"]))): errs.append(f"pm10_pair_count={int(round(float(v)))}, expected {int(round(float(gt['pm10_pair_count'])))}")
    v=runtime.retrieve("pm10_corr")
    if v is None: return ValidatorResult(False,"pm10_corr not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"pm10_corr not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["pm10_corr"]),tolerance=1e-06): errs.append(f"pm10_corr={round(float(v),3)}, expected ~{round(float(gt['pm10_corr']),3)} (tol 1e-06)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("no2_pair_count", None, "Number of datetimes with both GENERAL URBAN and ROADSIDE URBAN mean NO2 available."),
    Variable("no2_corr", None, "Pearson correlation of same-hour GENERAL URBAN and ROADSIDE URBAN mean NO2, rounded to 6 decimals."),
    Variable("pm10_pair_count", None, "Number of datetimes with both GENERAL URBAN and ROADSIDE URBAN mean PM10 available."),
    Variable("pm10_corr", None, "Pearson correlation of same-hour GENERAL URBAN and ROADSIDE URBAN mean PM10, rounded to 6 decimals."),
]
validators = {"validate_hk_hard_same_hour_area_correlations": validate_hk_hard_same_hour_area_correlations}
