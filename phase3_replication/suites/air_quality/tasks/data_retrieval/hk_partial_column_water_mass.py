"""hk_partial_column_water_mass — hard baseline.

Decision: Compare an 850–500 hPa water inventory with the supplied surface–500 hPa inventory, and distinguish both from accumulated rainfall.
Primary sources: https://www.ncei.noaa.gov/pub/data/igra/derived/igra2-derived-format.txt
https://repository.library.noaa.gov/view/noaa/72271/noaa_72271_DS1.pdf
Naive path / excluded reading: Integrating the dry-air mixing ratio unchanged gives 46.04 mm rather than 45.40 mm; omitting hPa-to-Pa gives 0.45 mm; substituting the same launch's IGRA surface–500 hPa product gives 75.37 mm. Neither inventory includes the atmosphere above 500 hPa.

Raw-file outputs frozen before authoring:
.codex-review/diverse_cases_20261006/frozen_answers.json
Reported answers: {'partial_water_launches': 361, 'largest_partial_water_launch': '2025-08-03 08:00:00', 'partial_water_mm': 45.4, 'selected_column_water_mm': 75.37, 'selected_water_profile_levels': 5}

Tolerance: reports_as at each declared precision accepts the correctly rounded
and unrounded physical result, rejects adjacent reports and the documented
wrong method. Counts are finite with tolerance zero; identity timestamps/months
match the selected local event exactly after timezone normalization. No tolerance
applies to those identities; deterministic tie rules select one event.
Prescribed approximation/cohort makes this an execution turn.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

def _ground_truth():
    f=pd.read_csv(DATA_DIR / 'profile_sounding.csv',parse_dates=['datetime'])
    f=f[f.year.eq(2025)&f.hour.eq(8)&f.pressure_hpa.between(500,850)]
    rows=[]
    for launch,group in f.groupby('datetime'):
        group=group.sort_values('pressure_hpa')
        if not {500,850}.issubset(set(group.pressure_hpa)) or group.pressure_hpa.duplicated().any():continue
        if not np.isfinite(group[['temperature_c','relative_humidity_pct']]).all().all() or not group.relative_humidity_pct.between(0,100).all():continue
        pressure=group.pressure_hpa.to_numpy();temp=group.temperature_c.to_numpy();rh=group.relative_humidity_pct.to_numpy()
        e=.01*rh*6.112*np.exp(17.67*temp/(temp+243.5));specific=.622*e/(pressure-.378*e)
        mass=float(np.trapezoid(specific,pressure*100)/9.80665)
        rows.append((launch,mass,len(group)))
    rank=pd.DataFrame(rows,columns=['launch','mass','levels']).sort_values(['mass','launch'],ascending=[False,True]);b=rank.iloc[0]
    index=pd.read_csv(DATA_DIR / 'sounding_indices.csv',parse_dates=['datetime']).set_index('datetime')
    return dict(partial_water_launches=len(rank),largest_partial_water_launch=str(b.launch),partial_water_mm=float(b.mass),selected_column_water_mm=float(index.loc[b.launch,'precipitable_water_mm']),selected_water_profile_levels=int(b.levels))


tools = []
variables = [
    Variable('partial_water_launches', None, "Store the exact integer count of King's Park 2025 08:00 local profiles with unique reported 850 and 500 hPa endpoints and finite temperature and relative humidity in [0,100] percent at every reported in-layer level. Retain all levels; exclude repeated pressures, with no level interpolation, extrapolation or missing-launch filling."),
    Variable('largest_partial_water_launch', None, 'Store the local YYYY-MM-DD HH:MM:SS string for the eligible launch with greatest 850–500 hPa precipitable-water amount; break exact ties by earliest launch.'),
    Variable('partial_water_mm', None, 'Store that layer’s liquid-water-equivalent amount in mm to 2 decimal places. Use the exact ideal-gas water-vapour mass fraction and integrate it trapezoidally in pressure across all retained levels with g=9.80665 m/s². Use Bolton liquid-water saturation-pressure coefficients 6.112 hPa, 17.67 and 243.5 °C, and water-vapour/dry-air molecular-mass ratio 0.622; use unrounded humidity values.'),
    Variable('selected_column_water_mm', None, 'Store the supplied IGRA precipitable water between the surface and 500 hPa for the same launch, in mm to 2 decimal places; retain the supplied product rather than recomputing it. Do not select a second launch by its maximum.'),
    Variable('selected_water_profile_levels', None, 'Store the exact integer number of reported levels used in the selected launch’s partial-layer integral, including its endpoints.'),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "partial_water_launches": runtime.retrieve("partial_water_launches"),
        "largest_partial_water_launch": runtime.retrieve("largest_partial_water_launch"),
        "partial_water_mm": runtime.retrieve("partial_water_mm"),
        "selected_column_water_mm": runtime.retrieve("selected_column_water_mm"),
        "selected_water_profile_levels": runtime.retrieve("selected_water_profile_levels"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    if not (is_finite_number(got["partial_water_launches"]) and compare_numeric(got["partial_water_launches"], expected["partial_water_launches"], tolerance=0)):
        errors.append("partial_water_launches="+repr(got["partial_water_launches"])+", expected "+repr(expected["partial_water_launches"]))
    try:
        parsed = pd.Timestamp(got["largest_partial_water_launch"])
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("Asia/Hong_Kong").tz_localize(None)
        valid = isinstance(got["largest_partial_water_launch"], str) and not pd.isna(parsed) and parsed == pd.Timestamp(expected["largest_partial_water_launch"])
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not (valid):
        errors.append("largest_partial_water_launch="+repr(got["largest_partial_water_launch"])+", expected "+repr(expected["largest_partial_water_launch"]))
    if not (is_finite_number(got["partial_water_mm"]) and reports_as(got["partial_water_mm"], expected["partial_water_mm"], decimals=2)):
        errors.append("partial_water_mm="+repr(got["partial_water_mm"])+", expected "+repr(expected["partial_water_mm"]))
    if not (is_finite_number(got["selected_column_water_mm"]) and reports_as(got["selected_column_water_mm"], expected["selected_column_water_mm"], decimals=2)):
        errors.append("selected_column_water_mm="+repr(got["selected_column_water_mm"])+", expected "+repr(expected["selected_column_water_mm"]))
    if not (is_finite_number(got["selected_water_profile_levels"]) and compare_numeric(got["selected_water_profile_levels"], expected["selected_water_profile_levels"], tolerance=0)):
        errors.append("selected_water_profile_levels="+repr(got["selected_water_profile_levels"])+", expected "+repr(expected["selected_water_profile_levels"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
