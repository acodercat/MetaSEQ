"""beijing_aerosol_beer_lambert_mean — medium baseline.

Decision: Decide whether an annual optical-depth summary can stand in for a mean direct-beam radiation diagnostic.
Primary source: https://aeronet.gsfc.nasa.gov/new_web/PDF/afi.pdf
BASELINE: The observed vectorized path computes the requested mean directly; no demonstrated PV diagnostic trap is claimed. The explicit averaging comparison is assessed separately in CC.
Excluded readings: Applying Beer–Lambert to annual mean AOD gives 0.6302 instead of mean transmittance 0.6895; a linear 1-AOD estimate gives 0.5382. Both differ from the sample-wise physical mean. Minimum transmittance is 0.00978; its timestamp is unique and matched exactly. Numeric report precision rejects both naive means and adjacent reports.

Raw-file outputs frozen before authoring:
.codex-review/diverse_cases_20261006/frozen_answers.json
Reported answers: {'aerosol_transmission_samples': 2920, 'mean_aerosol_transmission': 0.6895, 'strongest_attenuation_timestamp': '2025-03-01 23:00:00', 'minimum_aerosol_transmission': 0.00978}

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
from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

def _ground_truth():
    f=pd.read_csv(DATA_DIR / 'aerosol_cams.csv',parse_dates=['datetime'])
    f=f[f.datetime.ge('2025-01-01')&f.datetime.lt('2026-01-01')&np.isfinite(f.total_aod550)&f.total_aod550.ge(0)].copy()
    f['transmittance']=np.exp(-f.total_aod550)
    best=f.sort_values(['transmittance','datetime']).iloc[0]
    return dict(aerosol_transmission_samples=len(f),mean_aerosol_transmission=float(f.transmittance.mean()),strongest_attenuation_timestamp=str(best.datetime),minimum_aerosol_transmission=float(best.transmittance))


tools = []
variables = [
    Variable('aerosol_transmission_samples', None, 'Store the exact integer number of reported CAMS samples in local calendar 2025 with finite nonnegative total aerosol optical depth at 550 nm. Each reported sample has equal weight; do not interpolate gaps.'),
    Variable('mean_aerosol_transmission', None, 'Store the arithmetic mean dimensionless aerosol-only direct-beam transmittance for the prescribed vertical path, to 4 decimal places. Use the reported total 550-nm aerosol optical depth and Beer–Lambert–Bouguer law. The path has optical air mass one; omit gaseous, Rayleigh and cloud extinction.'),
    Variable('strongest_attenuation_timestamp', None, 'Store the local YYYY-MM-DD HH:MM:SS string for the reported sample with the smallest aerosol-only direct-beam transmittance in that cohort; break exact ties by earliest timestamp.'),
    Variable('minimum_aerosol_transmission', None, 'Store that selected sample’s dimensionless aerosol-only transmittance to 5 decimal places.'),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "aerosol_transmission_samples": runtime.retrieve("aerosol_transmission_samples"),
        "mean_aerosol_transmission": runtime.retrieve("mean_aerosol_transmission"),
        "strongest_attenuation_timestamp": runtime.retrieve("strongest_attenuation_timestamp"),
        "minimum_aerosol_transmission": runtime.retrieve("minimum_aerosol_transmission"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    if not (is_finite_number(got["aerosol_transmission_samples"]) and compare_numeric(got["aerosol_transmission_samples"], expected["aerosol_transmission_samples"], tolerance=0)):
        errors.append("aerosol_transmission_samples="+repr(got["aerosol_transmission_samples"])+", expected "+repr(expected["aerosol_transmission_samples"]))
    if not (is_finite_number(got["mean_aerosol_transmission"]) and reports_as(got["mean_aerosol_transmission"], expected["mean_aerosol_transmission"], decimals=4)):
        errors.append("mean_aerosol_transmission="+repr(got["mean_aerosol_transmission"])+", expected "+repr(expected["mean_aerosol_transmission"]))
    try:
        parsed = pd.Timestamp(got["strongest_attenuation_timestamp"])
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("Asia/Shanghai").tz_localize(None)
        valid = isinstance(got["strongest_attenuation_timestamp"], str) and not pd.isna(parsed) and parsed == pd.Timestamp(expected["strongest_attenuation_timestamp"])
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not (valid):
        errors.append("strongest_attenuation_timestamp="+repr(got["strongest_attenuation_timestamp"])+", expected "+repr(expected["strongest_attenuation_timestamp"]))
    if not (is_finite_number(got["minimum_aerosol_transmission"]) and reports_as(got["minimum_aerosol_transmission"], expected["minimum_aerosol_transmission"], decimals=5)):
        errors.append("minimum_aerosol_transmission="+repr(got["minimum_aerosol_transmission"])+", expected "+repr(expected["minimum_aerosol_transmission"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
