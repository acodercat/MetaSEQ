"""hk_bulk_richardson_screen — hard trap.

Decision: Select a stable morning layer for higher-resolution wind and turbulence follow-up rather than inferring turbulence solely from a temperature inversion.
Primary source: https://glossary.ametsoc.org/wiki/bulk-richardson-number/
Naive path / excluded reading: Using only the difference in scalar endpoint speeds gives Ri=0.5897 and shear=0.01676 s^-1 for the same selected launch, instead of 0.3105 and 0.02310 s^-1. The wrong method selects the same date, so numeric outputs are essential. Reference-temperature and dry approximations are prescribed; the vector-wind misconception remains unhinted.

Raw-file outputs frozen before authoring:
.codex-review/diverse_cases_20261006/frozen_answers.json
Reported answers: {'stable_shear_launches': 356, 'minimum_bulk_ri_launch': '2025-12-12 08:00:00', 'minimum_dry_bulk_ri': 0.3105, 'selected_layer_shear_per_s': 0.0231, 'layer_theta_increase_k': 3.6}

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
    f=f[f.year.eq(2025)&f.hour.eq(8)&f.pressure_hpa.isin([925,850])]
    rows=[]
    fields=['potential_temperature_k','geopotential_height_m','wind_speed_ms','wind_dir_deg']
    for launch,block in f.groupby('datetime'):
        if len(block)!=2 or block.pressure_hpa.nunique()!=2 or not np.isfinite(block[fields]).all().all():continue
        low=block[block.pressure_hpa.eq(925)].iloc[0];high=block[block.pressure_hpa.eq(850)].iloc[0]
        dz=high.geopotential_height_m-low.geopotential_height_m;dt=high.potential_temperature_k-low.potential_temperature_k
        if dz<=0 or dt<=0:continue
        radians=np.deg2rad([low.wind_dir_deg,high.wind_dir_deg]);speeds=np.array([low.wind_speed_ms,high.wind_speed_ms])
        u=-speeds*np.sin(radians);v=-speeds*np.cos(radians);shear_squared=float(np.diff(u)[0]**2+np.diff(v)[0]**2)
        if shear_squared<=0:continue
        ri=9.80665*dt*dz/(((low.potential_temperature_k+high.potential_temperature_k)/2)*shear_squared)
        rows.append((launch,float(ri),float(np.sqrt(shear_squared)/dz),float(dt)))
    rank=pd.DataFrame(rows,columns=['launch','ri','shear','increase']).sort_values(['ri','launch']);b=rank.iloc[0]
    return dict(stable_shear_launches=len(rank),minimum_bulk_ri_launch=str(b.launch),minimum_dry_bulk_ri=float(b.ri),selected_layer_shear_per_s=float(b.shear),layer_theta_increase_k=float(b.increase))


tools = []
variables = [
    Variable('stable_shear_launches', None, "Store the exact integer count of reported 08:00 local King's Park launches in 2025 with unique reported 925 and 850 hPa endpoints, finite endpoint potential temperature, height, wind speed and direction, positive height separation, dry statically stable stratification and nonzero layer wind shear. No endpoint interpolation or extrapolation."),
    Variable('minimum_bulk_ri_launch', None, 'Store the local YYYY-MM-DD HH:MM:SS string of the eligible launch with the smallest dry bulk Richardson number; break exact ties by earliest launch.'),
    Variable('minimum_dry_bulk_ri', None, 'Store that launch’s dimensionless dry finite-layer bulk Richardson number to 4 decimal places, using the reported dry potential temperatures, their arithmetic endpoint mean as reference temperature, reported geopotential-height separation and g=9.80665 m/s². This is the stratified-shear definition, not the CAPE-based storm-type index; omit virtual-temperature correction for this dry diagnostic.'),
    Variable('selected_layer_shear_per_s', None, 'Store the selected layer’s bulk horizontal wind-shear magnitude in s⁻¹ to 5 decimal places, using its reported endpoint winds and geopotential-height separation.'),
    Variable('layer_theta_increase_k', None, 'Store upper (850 hPa) minus lower (925 hPa) reported dry potential temperature in K to 1 decimal place for the selected launch.'),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "stable_shear_launches": runtime.retrieve("stable_shear_launches"),
        "minimum_bulk_ri_launch": runtime.retrieve("minimum_bulk_ri_launch"),
        "minimum_dry_bulk_ri": runtime.retrieve("minimum_dry_bulk_ri"),
        "selected_layer_shear_per_s": runtime.retrieve("selected_layer_shear_per_s"),
        "layer_theta_increase_k": runtime.retrieve("layer_theta_increase_k"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    if not (is_finite_number(got["stable_shear_launches"]) and compare_numeric(got["stable_shear_launches"], expected["stable_shear_launches"], tolerance=0)):
        errors.append("stable_shear_launches="+repr(got["stable_shear_launches"])+", expected "+repr(expected["stable_shear_launches"]))
    try:
        parsed = pd.Timestamp(got["minimum_bulk_ri_launch"])
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("Asia/Hong_Kong").tz_localize(None)
        valid = isinstance(got["minimum_bulk_ri_launch"], str) and not pd.isna(parsed) and parsed == pd.Timestamp(expected["minimum_bulk_ri_launch"])
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not (valid):
        errors.append("minimum_bulk_ri_launch="+repr(got["minimum_bulk_ri_launch"])+", expected "+repr(expected["minimum_bulk_ri_launch"]))
    if not (is_finite_number(got["minimum_dry_bulk_ri"]) and reports_as(got["minimum_dry_bulk_ri"], expected["minimum_dry_bulk_ri"], decimals=4)):
        errors.append("minimum_dry_bulk_ri="+repr(got["minimum_dry_bulk_ri"])+", expected "+repr(expected["minimum_dry_bulk_ri"]))
    if not (is_finite_number(got["selected_layer_shear_per_s"]) and reports_as(got["selected_layer_shear_per_s"], expected["selected_layer_shear_per_s"], decimals=5)):
        errors.append("selected_layer_shear_per_s="+repr(got["selected_layer_shear_per_s"])+", expected "+repr(expected["selected_layer_shear_per_s"]))
    if not (is_finite_number(got["layer_theta_increase_k"]) and reports_as(got["layer_theta_increase_k"], expected["layer_theta_increase_k"], decimals=1)):
        errors.append("layer_theta_increase_k="+repr(got["layer_theta_increase_k"])+", expected "+repr(expected["layer_theta_increase_k"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
