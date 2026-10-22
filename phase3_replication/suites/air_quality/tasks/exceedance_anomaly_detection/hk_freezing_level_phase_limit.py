"""hk_freezing_level_phase_limit — hard baseline.

Decision: Identify a profile needing vertical cold-phase follow-up without converting a freezing-level diagnostic into a surface-weather observation.
Primary source: https://www.weather.gov/ama/winterpreciptypes
Naive path / excluded reading: Confusing height above station with mean-sea-level height gives 2452.0 m instead of 2518.0 m. Using a single zero level misses the selected profile’s three distinct crossings.

Raw-file outputs frozen before authoring:
.codex-review/diverse_cases_20261006/frozen_answers.json
Reported answers: {'freezing_valid_launches': 361, 'lowest_freezing_launch': '2025-01-09 08:00:00', 'lowest_freezing_height_msl_m': 2518.0, 'freezing_selected_profile_levels': 30, 'selected_launch_zero_crossings': 3}

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
    f=f[f.year.eq(2025)&f.hour.eq(8)&f.pressure_hpa.ge(300)]
    rows=[]
    for launch,group in f.groupby('datetime'):
        group=group.sort_values('geopotential_height_m')
        if not group.pressure_hpa.eq(300).any() or group.geopotential_height_m.duplicated().any():continue
        if not np.isfinite(group[['temperature_c','geopotential_height_m']]).all().all():continue
        levels=set(float(x) for x in group.loc[group.temperature_c.eq(0),'geopotential_height_m'])
        temp=group.temperature_c.to_numpy();z=group.geopotential_height_m.to_numpy()
        for i in np.flatnonzero(temp[:-1]*temp[1:]<0):
            levels.add(float(np.interp(0,sorted([temp[i],temp[i+1]]),[z[i],z[i+1]] if temp[i]<temp[i+1] else [z[i+1],z[i]])))
        if levels:rows.append((launch,min(levels),len(group),len(levels)))
    rank=pd.DataFrame(rows,columns=['launch','height','levels','crossings']).sort_values(['height','launch']);b=rank.iloc[0]
    return dict(freezing_valid_launches=len(rank),lowest_freezing_launch=str(b.launch),lowest_freezing_height_msl_m=float(b.height),freezing_selected_profile_levels=int(b.levels),selected_launch_zero_crossings=int(b.crossings))


tools = []
variables = [
    Variable('freezing_valid_launches', None, "Store the exact integer number of King's Park 2025 08:00 local profiles reporting 300 hPa, with finite temperature and geopotential height at every reported level from the lowest supplied level up to and including 300 hPa, no repeated heights, and at least one zero-degree-C level within that range. No extrapolation beyond the reported profile."),
    Variable('lowest_freezing_launch', None, 'Store the local YYYY-MM-DD HH:MM:SS string of the eligible launch with lowest dry-bulb zero-degree level; break exact ties by earliest launch.'),
    Variable('lowest_freezing_height_msl_m', None, 'Store that launch’s lowest dry-bulb 0 °C level as geopotential height in metres above mean sea level, to 1 decimal place. Use temperature linearly interpolated in supplied geopotential height between consecutive retained levels; an exactly zero reported temperature counts at its own height. Retain all supplied levels in range.'),
    Variable('freezing_selected_profile_levels', None, 'Store the exact integer number of reported levels retained from the lowest supplied level through 300 hPa on the selected launch.'),
    Variable('selected_launch_zero_crossings', None, 'Store the exact integer number of distinct zero-degree-C heights on that same launch under the stated interpolation; do not double-count an exact zero at a shared segment endpoint.'),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "freezing_valid_launches": runtime.retrieve("freezing_valid_launches"),
        "lowest_freezing_launch": runtime.retrieve("lowest_freezing_launch"),
        "lowest_freezing_height_msl_m": runtime.retrieve("lowest_freezing_height_msl_m"),
        "freezing_selected_profile_levels": runtime.retrieve("freezing_selected_profile_levels"),
        "selected_launch_zero_crossings": runtime.retrieve("selected_launch_zero_crossings"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    if not (is_finite_number(got["freezing_valid_launches"]) and compare_numeric(got["freezing_valid_launches"], expected["freezing_valid_launches"], tolerance=0)):
        errors.append("freezing_valid_launches="+repr(got["freezing_valid_launches"])+", expected "+repr(expected["freezing_valid_launches"]))
    try:
        parsed = pd.Timestamp(got["lowest_freezing_launch"])
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("Asia/Hong_Kong").tz_localize(None)
        valid = isinstance(got["lowest_freezing_launch"], str) and not pd.isna(parsed) and parsed == pd.Timestamp(expected["lowest_freezing_launch"])
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not (valid):
        errors.append("lowest_freezing_launch="+repr(got["lowest_freezing_launch"])+", expected "+repr(expected["lowest_freezing_launch"]))
    if not (is_finite_number(got["lowest_freezing_height_msl_m"]) and reports_as(got["lowest_freezing_height_msl_m"], expected["lowest_freezing_height_msl_m"], decimals=1)):
        errors.append("lowest_freezing_height_msl_m="+repr(got["lowest_freezing_height_msl_m"])+", expected "+repr(expected["lowest_freezing_height_msl_m"]))
    if not (is_finite_number(got["freezing_selected_profile_levels"]) and compare_numeric(got["freezing_selected_profile_levels"], expected["freezing_selected_profile_levels"], tolerance=0)):
        errors.append("freezing_selected_profile_levels="+repr(got["freezing_selected_profile_levels"])+", expected "+repr(expected["freezing_selected_profile_levels"]))
    if not (is_finite_number(got["selected_launch_zero_crossings"]) and compare_numeric(got["selected_launch_zero_crossings"], expected["selected_launch_zero_crossings"], tolerance=0)):
        errors.append("selected_launch_zero_crossings="+repr(got["selected_launch_zero_crossings"])+", expected "+repr(expected["selected_launch_zero_crossings"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
