"""hk_moist_hypsometric_thickness — hard baseline.

Decision: Decide whether humidity can be omitted from a thickness reconstruction and whether the comparison is independent validation.
Source concept: https://www.ncei.noaa.gov/pub/data/igra/igra2-product-description-supplement.pdf
Plausible wrong paths: Using dry temperature for moist density, arithmetic endpoint averages instead of the specified log-pressure integration, using RH as a fraction without conversion, or treating derived heights as independent measurements.

Raw-data values were frozen before authoring in
.codex-review/new_cases_20261006/frozen_answers.json.
Reported answers: {'hypsometric_launches': 30, 'dry_thickness_mean_bias_m': -8.31, 'moist_thickness_mean_bias_m': -0.97, 'mean_moisture_thickness_increment_m': 7.34, 'largest_moisture_increment_launch': '2025-07-29 08:00:00', 'largest_moisture_increment_m': 8.39}

Each declared numeric precision rejects adjacent reported answers; all integer
counts use tolerance zero and finite-number guards. Runtime ground truth is
recomputed from the source files/database. No causal judgement is PV-scored.
Author-selected quadrature/cohort conventions make this an execution turn.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

def _ground_truth():
    source = pd.read_csv(DATA_DIR / "profile_sounding.csv",parse_dates=["datetime"])
    source = source[source.year.eq(2025)&source.month.eq(7)&source.hour.eq(8)&source.pressure_hpa.between(850,925)]
    rows = []
    for launch, frame in source.groupby("datetime"):
        frame = frame.sort_values("pressure_hpa",ascending=False)
        if not np.isfinite(frame[["temperature_c","relative_humidity_pct","geopotential_height_m"]]).all().all():
            continue
        if not frame.pressure_hpa.eq(925).any() or not frame.pressure_hpa.eq(850).any() or frame.pressure_hpa.duplicated().any():
            continue
        pressure = frame.pressure_hpa.to_numpy()
        celsius = frame.temperature_c.to_numpy()
        kelvin = celsius+273.15
        vapour = frame.relative_humidity_pct.to_numpy()/100*6.112*np.exp(17.67*celsius/(celsius+243.5))
        virtual = kelvin/(1-.378*vapour/pressure)
        coord = -np.log(pressure)
        dry = 287.05/9.80665*np.trapezoid(kelvin,coord)
        moist = 287.05/9.80665*np.trapezoid(virtual,coord)
        reported = float(frame.geopotential_height_m.iloc[-1]-frame.geopotential_height_m.iloc[0])
        rows.append((launch,float(dry),float(moist),reported))
    frame = pd.DataFrame(rows,columns=["launch","dry","moist","reported"]).sort_values("launch")
    contribution = frame.moist-frame.dry
    best = frame.loc[contribution.idxmax()]
    return dict(hypsometric_launches=len(frame), dry_thickness_mean_bias_m=float((frame.dry-frame.reported).mean()), moist_thickness_mean_bias_m=float((frame.moist-frame.reported).mean()), mean_moisture_thickness_increment_m=float(contribution.mean()), largest_moisture_increment_launch=f"{best.launch:%Y-%m-%d %H:%M:%S}", largest_moisture_increment_m=float(contribution.max()))


tools = []
variables = [
    Variable('hypsometric_launches', None, "Store the exact integer number of July 2025 08:00 local King's Park profiles with reported 925 and 850 hPa endpoints and finite temperature, relative humidity and geopotential height at every retained level between them. Retain all reported in-layer levels, with no interpolation or extrapolation; exclude a profile with repeated pressures."),
    Variable('dry_thickness_mean_bias_m', None, 'Store the mean dry hypsometric thickness minus supplied endpoint geopotential-height difference, in metres to 2 decimal places. Integrate temperature trapezoidally in log pressure over every retained in-layer level, not just the endpoints. Use Rd=287.05 J/(kg K), g=9.80665 m/s² and Celsius-to-kelvin offset 273.15; give each eligible launch equal weight.'),
    Variable('moist_thickness_mean_bias_m', None, 'Store the corresponding mean signed moisture-adjusted thickness error in metres to 2 decimal places. Use the IGRA virtual-temperature relation and Bolton liquid-water saturation-vapour-pressure approximation with coefficients 6.112 hPa, 17.67 and 243.5 °C; relative humidity is percent, pressure hPa, and the virtual-temperature coefficient is 0.378. Use the same levels and unrounded trapezoidal integral.'),
    Variable('mean_moisture_thickness_increment_m', None, 'Store the mean moisture-adjusted minus dry thickness across those same launches, in metres to 2 decimal places.'),
    Variable('largest_moisture_increment_launch', None, 'Store the YYYY-MM-DD HH:MM:SS local launch timestamp with greatest moisture-adjusted minus dry thickness; break exact ties by earliest launch.'),
    Variable('largest_moisture_increment_m', None, "Store that launch's moisture contribution to thickness in metres to 2 decimal places."),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "hypsometric_launches": runtime.retrieve("hypsometric_launches"),
        "dry_thickness_mean_bias_m": runtime.retrieve("dry_thickness_mean_bias_m"),
        "moist_thickness_mean_bias_m": runtime.retrieve("moist_thickness_mean_bias_m"),
        "mean_moisture_thickness_increment_m": runtime.retrieve("mean_moisture_thickness_increment_m"),
        "largest_moisture_increment_launch": runtime.retrieve("largest_moisture_increment_launch"),
        "largest_moisture_increment_m": runtime.retrieve("largest_moisture_increment_m"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    if not (is_finite_number(got["hypsometric_launches"]) and compare_numeric(got["hypsometric_launches"], expected["hypsometric_launches"], tolerance=0)):
        errors.append("hypsometric_launches="+repr(got["hypsometric_launches"])+", expected "+repr(expected["hypsometric_launches"]))
    if not (is_finite_number(got["dry_thickness_mean_bias_m"]) and reports_as(got["dry_thickness_mean_bias_m"], expected["dry_thickness_mean_bias_m"], decimals=2)):
        errors.append("dry_thickness_mean_bias_m="+repr(got["dry_thickness_mean_bias_m"])+", expected "+repr(expected["dry_thickness_mean_bias_m"]))
    if not (is_finite_number(got["moist_thickness_mean_bias_m"]) and reports_as(got["moist_thickness_mean_bias_m"], expected["moist_thickness_mean_bias_m"], decimals=2)):
        errors.append("moist_thickness_mean_bias_m="+repr(got["moist_thickness_mean_bias_m"])+", expected "+repr(expected["moist_thickness_mean_bias_m"]))
    if not (is_finite_number(got["mean_moisture_thickness_increment_m"]) and reports_as(got["mean_moisture_thickness_increment_m"], expected["mean_moisture_thickness_increment_m"], decimals=2)):
        errors.append("mean_moisture_thickness_increment_m="+repr(got["mean_moisture_thickness_increment_m"])+", expected "+repr(expected["mean_moisture_thickness_increment_m"]))
    try:
        parsed = pd.Timestamp(got["largest_moisture_increment_launch"])
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("Asia/Hong_Kong")
        valid = not pd.isna(parsed) and parsed.strftime("%Y-%m-%d %H:%M:%S") == expected["largest_moisture_increment_launch"]
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not (valid):
        errors.append("largest_moisture_increment_launch="+repr(got["largest_moisture_increment_launch"])+", expected "+repr(expected["largest_moisture_increment_launch"]))
    if not (is_finite_number(got["largest_moisture_increment_m"]) and reports_as(got["largest_moisture_increment_m"], expected["largest_moisture_increment_m"], decimals=2)):
        errors.append("largest_moisture_increment_m="+repr(got["largest_moisture_increment_m"])+", expected "+repr(expected["largest_moisture_increment_m"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
