import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_hard_nearest_other_no2_gap(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    sql = text("""
        WITH general AS (
            SELECT id, coordinate
            FROM air_quality_station
            WHERE station_type = 'GENERAL'
        ), nearest AS (
            SELECT g1.id AS base_id,
                   g2.id AS near_id,
                   ST_Distance(g1.coordinate::geography, g2.coordinate::geography) AS dist_m,
                   ROW_NUMBER() OVER (PARTITION BY g1.id ORDER BY ST_Distance(g1.coordinate::geography, g2.coordinate::geography), g2.id) AS rn
            FROM general g1
            JOIN general g2 ON g2.id <> g1.id
            WHERE g1.id <> 8
        ), means AS (
            SELECT station_id, AVG(no2) AS mean_no2
            FROM hourly_station_air_quality
            WHERE datetime >= '2025-06-01 00:00:00'
              AND datetime <  '2025-07-01 00:00:00'
              AND no2 IS NOT NULL
            GROUP BY station_id
        ), gaps AS (
            SELECT n.base_id, n.near_id, mb.mean_no2 - mn.mean_no2 AS gap
            FROM nearest n
            JOIN means mb ON mb.station_id = n.base_id
            JOIN means mn ON mn.station_id = n.near_id
            WHERE n.rn = 1
        )
        SELECT base_id, near_id, gap
        FROM gaps
        ORDER BY gap DESC, base_id ASC
        LIMIT 1
    """)
    df = pd.read_sql(sql, engine)
    gt = {"base_station_id": int(df.loc[0, "base_id"]), "nearest_station_id": int(df.loc[0, "near_id"]), "max_no2_gap": round(float(df.loc[0, "gap"]), 6)}
    errs=[]
    v=runtime.retrieve("base_station_id")
    if v is None: return ValidatorResult(False,"base_station_id not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"base_station_id not numeric: {v!r}")
    if int(round(float(v)))!=int(round(float(gt["base_station_id"]))): errs.append(f"base_station_id={int(round(float(v)))}, expected {int(round(float(gt['base_station_id'])))}")
    v=runtime.retrieve("nearest_station_id")
    if v is None: return ValidatorResult(False,"nearest_station_id not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"nearest_station_id not numeric: {v!r}")
    if int(round(float(v)))!=int(round(float(gt["nearest_station_id"]))): errs.append(f"nearest_station_id={int(round(float(v)))}, expected {int(round(float(gt['nearest_station_id'])))}")
    v=runtime.retrieve("max_no2_gap")
    if v is None: return ValidatorResult(False,"max_no2_gap not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"max_no2_gap not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["max_no2_gap"]),tolerance=1e-06): errs.append(f"max_no2_gap={round(float(v),3)}, expected ~{round(float(gt['max_no2_gap']),3)} (tol 1e-06)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("base_station_id", None, "GENERAL non-8 station with the largest mean-NO2 minus nearest-other-GENERAL mean-NO2 gap."),
    Variable("nearest_station_id", None, "Nearest OTHER GENERAL station id used for the winning base station."),
    Variable("max_no2_gap", None, "Winning NO2 mean gap, rounded to 6 decimals."),
]
validators = {"validate_hk_hard_nearest_other_no2_gap": validate_hk_hard_nearest_other_no2_gap}
