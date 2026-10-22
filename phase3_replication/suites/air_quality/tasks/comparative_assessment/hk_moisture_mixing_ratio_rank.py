"""hk_moisture_mixing_ratio_rank — medium trap.

Decision: Schedule lower-tropospheric water-vapour measurements using mass abundance rather than a temperature-dependent saturation fraction.
Primary source: https://glossary.ametsoc.org/wiki/humidity-mixing-ratio/
Naive path / excluded reading: Ranking monthly mean RH selects June, whereas largest mean water-vapour mixing ratio selects July. These are not the same estimand. The named water-vapour mixing ratio has a dry-air mass reference; using specific humidity or converting mean temperature and RH first also changes its value.

Raw-file outputs frozen before authoring:
.codex-review/diverse_cases_20261006/frozen_answers.json
Reported answers: {'moisture_peak_month': '2025-07', 'peak_mean_mixing_ratio_gkg': 18.41, 'peak_moisture_launches': 30, 'annual_moisture_launches': 361, 'peak_month_temperature_c': 24.07}

Tolerance: reports_as at each declared precision accepts the correctly rounded
and unrounded physical result, rejects adjacent reports and the documented
wrong method. Counts are finite with tolerance zero; identity timestamps/months
match the selected local event exactly after timezone normalization. No tolerance
applies to those identities; deterministic tie rules select one event.
Named physical quantities determine the target; no formula is revealed.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

def _ground_truth():
    f=pd.read_csv(DATA_DIR / 'profile_sounding.csv')
    f=f[f.year.eq(2025)&f.hour.eq(8)&f.pressure_hpa.eq(925)&np.isfinite(f[['temperature_c','relative_humidity_pct']]).all(axis=1)&f.relative_humidity_pct.between(0,100)].copy()
    vapour=f.relative_humidity_pct/100*6.112*np.exp(17.67*f.temperature_c/(f.temperature_c+243.5))
    f['mixing_ratio']=.622*vapour/(f.pressure_hpa-vapour)*1000
    months=f.groupby('month').agg(mean_ratio=('mixing_ratio','mean'),n=('mixing_ratio','count'),mean_temperature=('temperature_c','mean')).reset_index().sort_values(['mean_ratio','month'],ascending=[False,True]);b=months.iloc[0]
    return dict(moisture_peak_month=f'2025-{int(b.month):02d}',peak_mean_mixing_ratio_gkg=float(b.mean_ratio),peak_moisture_launches=int(b.n),annual_moisture_launches=len(f),peak_month_temperature_c=float(b.mean_temperature))


tools = []
variables = [
    Variable('moisture_peak_month', None, "Store a YYYY-MM string for the calendar-2025 month with the largest arithmetic mean water-vapour mixing ratio at the reported 925 hPa level of King's Park 08:00 local launches. Each reported launch has equal weight within its month. Use finite temperature and relative humidity in [0,100] percent, no level interpolation or missing-launch filling; break exact mean ties by earliest month."),
    Variable('peak_mean_mixing_ratio_gkg', None, 'Store that month’s mean water-vapour mixing ratio in g per kg of dry air, to 2 decimal places. Use the Bolton liquid-water saturation-pressure approximation with coefficients 6.112 hPa, 17.67 and 243.5 °C, and water-vapour/dry-air molecular-mass ratio 0.622; retain unrounded level values.'),
    Variable('peak_moisture_launches', None, 'Store the exact integer count of eligible reported launches contributing to the selected monthly mean.'),
    Variable('annual_moisture_launches', None, 'Store the exact integer number of eligible reported 925-hPa morning launches across all twelve months of 2025.'),
    Variable('peak_month_temperature_c', None, 'Store the arithmetic mean reported 925-hPa temperature on the selected month’s same eligible launches, in °C to 2 decimal places.'),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "moisture_peak_month": runtime.retrieve("moisture_peak_month"),
        "peak_mean_mixing_ratio_gkg": runtime.retrieve("peak_mean_mixing_ratio_gkg"),
        "peak_moisture_launches": runtime.retrieve("peak_moisture_launches"),
        "annual_moisture_launches": runtime.retrieve("annual_moisture_launches"),
        "peak_month_temperature_c": runtime.retrieve("peak_month_temperature_c"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    try:
        parsed = pd.Timestamp(got["moisture_peak_month"])
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("Asia/Hong_Kong")
        valid = not pd.isna(parsed) and parsed.strftime("%Y-%m") == expected["moisture_peak_month"]
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not (valid):
        errors.append("moisture_peak_month="+repr(got["moisture_peak_month"])+", expected "+repr(expected["moisture_peak_month"]))
    if not (is_finite_number(got["peak_mean_mixing_ratio_gkg"]) and reports_as(got["peak_mean_mixing_ratio_gkg"], expected["peak_mean_mixing_ratio_gkg"], decimals=2)):
        errors.append("peak_mean_mixing_ratio_gkg="+repr(got["peak_mean_mixing_ratio_gkg"])+", expected "+repr(expected["peak_mean_mixing_ratio_gkg"]))
    if not (is_finite_number(got["peak_moisture_launches"]) and compare_numeric(got["peak_moisture_launches"], expected["peak_moisture_launches"], tolerance=0)):
        errors.append("peak_moisture_launches="+repr(got["peak_moisture_launches"])+", expected "+repr(expected["peak_moisture_launches"]))
    if not (is_finite_number(got["annual_moisture_launches"]) and compare_numeric(got["annual_moisture_launches"], expected["annual_moisture_launches"], tolerance=0)):
        errors.append("annual_moisture_launches="+repr(got["annual_moisture_launches"])+", expected "+repr(expected["annual_moisture_launches"]))
    if not (is_finite_number(got["peak_month_temperature_c"]) and reports_as(got["peak_month_temperature_c"], expected["peak_month_temperature_c"], decimals=2)):
        errors.append("peak_month_temperature_c="+repr(got["peak_month_temperature_c"])+", expected "+repr(expected["peak_month_temperature_c"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
