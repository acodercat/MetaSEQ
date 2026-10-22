import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_mt_hottest_general_o3(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    d=pd.read_sql(text("""WITH nn AS (SELECT a.id aq, a.name_en, (SELECT w.id FROM weather_station w ORDER BY a.coordinate<->w.coordinate LIMIT 1) wid FROM air_quality_station a WHERE a.station_type='GENERAL')
    SELECT nn.aq, nn.name_en, avg(h.temperature) t FROM nn JOIN hourly_station_weather h ON h.station_id=nn.wid WHERE datetime>='2025-06-01' AND datetime<'2025-07-01' AND h.temperature IS NOT NULL GROUP BY 1,2 ORDER BY t DESC"""),engine)
    sid=int(d.iloc[0]['aq']); nm=str(d.iloc[0]['name_en'])
    o3=float(pd.read_sql(text(f"SELECT avg(o3) v FROM hourly_station_air_quality WHERE station_id={sid} AND datetime>='2025-06-01' AND datetime<'2025-07-01' AND o3 IS NOT NULL"),engine).iloc[0]['v'])
    gt={'name':nm,'o3':o3,'_diag':('tmargin',round(float(d.iloc[0]['t']-d.iloc[1]['t']),2))}
    errs=[]
    v=runtime.retrieve("hottest_gen_station")
    if v is None: return ValidatorResult(False,"hottest_gen_station not set",variables_not_set=True)
    if str(v).strip().lower()!=str(gt["name"]).strip().lower(): errs.append(f"hottest_gen_station={v!r}, expected {gt['name']!r}")
    v=runtime.retrieve("hottest_gen_o3")
    if v is None: return ValidatorResult(False,"hottest_gen_o3 not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"hottest_gen_o3 not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["o3"]),tolerance=1.0): errs.append(f"hottest_gen_o3={round(float(v),3)}, expected ~{round(float(gt['o3']),3)} (tol 1.0)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("hottest_gen_station", None, "general station whose nearest weather station has the highest June mean temperature"),
    Variable("hottest_gen_o3", None, "that station's own June mean O3, 1dp"),
]
validators = {"validate_hk_mt_hottest_general_o3": validate_hk_mt_hottest_general_o3}
