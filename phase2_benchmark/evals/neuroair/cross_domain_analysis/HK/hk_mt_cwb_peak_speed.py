import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_mt_cwb_peak_speed(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    r=pd.read_sql(text("SELECT datetime, no2 FROM hourly_station_air_quality WHERE station_id=17 AND datetime>='2025-06-01' AND datetime<'2025-07-01' AND no2 IS NOT NULL ORDER BY no2 DESC LIMIT 1"),engine).iloc[0]
    dt=str(r['datetime']); no2=float(r['no2'])
    sp=pd.read_sql(text(f"SELECT avg(tr.speed) v FROM road_segment rs JOIN hourly_road_segment_traffic tr ON tr.road_segment_id=rs.id, air_quality_station a WHERE a.id=17 AND ST_DWithin(rs.geometry::geography,a.coordinate::geography,300) AND tr.datetime='{dt}' AND tr.speed IS NOT NULL"),engine).iloc[0]['v']
    gt={'no2':no2,'sp':float(sp) if sp is not None else -1.0}
    errs=[]
    v=runtime.retrieve("cwb_peak_no2")
    if v is None: return ValidatorResult(False,"cwb_peak_no2 not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"cwb_peak_no2 not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["no2"]),tolerance=1.0): errs.append(f"cwb_peak_no2={round(float(v),3)}, expected ~{round(float(gt['no2']),3)} (tol 1.0)")
    v=runtime.retrieve("cwb_peak_speed")
    if v is None: return ValidatorResult(False,"cwb_peak_speed not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"cwb_peak_speed not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["sp"]),tolerance=3.0): errs.append(f"cwb_peak_speed={round(float(v),3)}, expected ~{round(float(gt['sp']),3)} (tol 3.0)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("cwb_peak_no2", None, "highest single-hour NO2 at station 17 in June, 1dp"),
    Variable("cwb_peak_speed", None, "mean traffic speed of <=300m road segments at that peak-NO2 timestamp, 2dp"),
]
validators = {"validate_hk_mt_cwb_peak_speed": validate_hk_mt_cwb_peak_speed}
