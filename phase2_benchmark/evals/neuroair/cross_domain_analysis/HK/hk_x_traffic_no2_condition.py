import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_x_traffic_no2_condition(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    d=pd.read_sql(text("""WITH hrs AS (SELECT datetime FROM hourly_station_air_quality WHERE station_id=17 AND datetime>='2025-06-01' AND datetime<'2025-07-01' AND no2>100),
    seg AS (SELECT rs.id FROM road_segment rs, air_quality_station a WHERE a.id=17 AND ST_DWithin(rs.geometry::geography,a.coordinate::geography,300))
    SELECT t.road_segment_id, avg(t.congestion_index) v FROM hourly_road_segment_traffic t
    JOIN hrs ON t.datetime=hrs.datetime WHERE t.road_segment_id IN (SELECT id FROM seg) AND t.congestion_index IS NOT NULL
    GROUP BY 1 ORDER BY v DESC LIMIT 2"""),engine)
    gt={'sid':int(d.iloc[0]['road_segment_id']),'v':float(d.iloc[0]['v']),'_diag':('margin',round(float(d.iloc[0]['v']-d.iloc[1]['v']),2))}
    errs=[]
    v=runtime.retrieve("worst_segment_id")
    if v is None: return ValidatorResult(False,"worst_segment_id not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"worst_segment_id not numeric: {v!r}")
    if int(round(float(v)))!=int(round(float(gt["sid"]))): errs.append(f"worst_segment_id={int(round(float(v)))}, expected {int(round(float(gt['sid'])))}")
    v=runtime.retrieve("worst_segment_ci")
    if v is None: return ValidatorResult(False,"worst_segment_ci not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"worst_segment_ci not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["v"]),tolerance=0.3): errs.append(f"worst_segment_ci={round(float(v),3)}, expected ~{round(float(gt['v']),3)} (tol 0.3)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("worst_segment_id", None, "road_segment_id with highest mean congestion_index over June hours where station-17 NO2>100"),
    Variable("worst_segment_ci", None, "that mean congestion_index, 2dp"),
]
validators = {"validate_hk_x_traffic_no2_condition": validate_hk_x_traffic_no2_condition}
