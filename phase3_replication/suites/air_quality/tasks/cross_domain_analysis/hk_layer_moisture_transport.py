"""Screen a moisture-transport monitoring episode using a signed partial-layer flux.
Sources: https://codes.ecmwf.int/grib/param-db/?id=162071
https://codes.ecmwf.int/grib/param-db/162072
https://www.ncei.noaa.gov/pub/data/igra/derived/igra2-derived-format.txt
Three-level hydrostatic approximation with Bolton liquid-water humidity, not full-column IVT.
Wrong paths: scalar-speed integral 916.84 versus northward 793.87 kg m^-1 s^-1;
using wind-to convention flips sign; omitting pressure conversion gives 7.94;
maximum water inventory instead selects 2025-08-03. Scalar and northward maxima
share a launch, so the date alone cannot diagnose scalar substitution.

Independent raw-data answers frozen before this helper was authored:
.codex-review/proxy_cases_20261008/frozen_answers.json
The prescribed cohort and physical approximation make this baseline/execution.
Float acceptance is reports_as at declared precision; counts and identities are exact.
Alternative-path and adjacent-report probes live in scripts/verdict_baseline.py.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, is_finite_number, reports_as

def _ground_truth():
    frame = pd.read_csv(DATA_DIR / "profile_sounding.csv", parse_dates=["datetime"])
    frame = frame[frame.year.eq(2025) & frame.hour.eq(8) & frame.pressure_hpa.isin([700, 850, 925])]
    rows = []
    for stamp, group in frame.groupby("datetime"):
        group = group.sort_values("pressure_hpa")
        if len(group) != 3 or set(group.pressure_hpa) != {700, 850, 925}:
            continue
        if not np.isfinite(group[["temperature_c", "relative_humidity_pct", "wind_speed_ms"]]).all().all():
            continue
        speed = group.wind_speed_ms.to_numpy()
        direction = group.wind_dir_deg.to_numpy()
        if (speed < 0).any() or not group.relative_humidity_pct.between(0, 100).all():
            continue
        direction = np.where(speed == 0, 0, direction)
        if not (np.isfinite(direction) & (direction >= 0) & (direction <= 360)).all():
            continue
        pressure = group.pressure_hpa.to_numpy()
        temp = group.temperature_c.to_numpy()
        e = 6.112 * np.exp(17.67 * temp / (temp + 243.5)) * group.relative_humidity_pct.to_numpy() / 100
        q = .622 * e / (pressure - .378 * e)
        north = -speed * np.cos(np.deg2rad(direction))
        east = -speed * np.sin(np.deg2rad(direction))
        flux = np.trapezoid(np.stack([q, q * north, q * east]), pressure * 100, axis=1) / 9.80665
        rows.append((stamp, *flux))
    profiles = pd.DataFrame(rows, columns=["stamp", "water", "north", "east"])
    best = profiles.sort_values(["north", "stamp"], ascending=[False, True]).iloc[0]
    return dict(moisture_transport_launch=str(best.stamp), northward_layer_transport=float(best.north),
                eastward_layer_transport=float(best.east), layer_water_kg_m2=float(best.water),
                moisture_transport_profiles=len(profiles), southward_profiles=int(profiles.north.lt(0).sum()))


tools = []
variables = [
    Variable('moisture_transport_profiles', None, "Store the exact count of King's Park 2025 08:00 local launches with exactly one reported level at each of 925, 850 and 700 hPa. Use only these three levels, without filling/interpolation. All must have finite temperature, RH in [0,100]%, and nonnegative finite wind speed; a positive speed requires finite meteorological wind-from direction in [0,360] degrees. At zero speed allow missing direction and use zero vector wind."),
    Variable('moisture_transport_launch', None, 'Store the local YYYY-MM-DD HH:MM:SS identity of the eligible launch with greatest signed northward 925–700 hPa water-vapour transport; exact ties select earliest launch.'),
    Variable('northward_layer_transport', None, 'Store the selected signed northward transport in kg m^-1 s^-1 to 2 decimals. Use the ideal-gas specific humidity (water mass / moist-air mass), Bolton liquid-water saturation coefficients 6.112 hPa, 17.67 and 243.5 °C, molecular-mass ratio 0.622; trapezoidally integrate humidity times the horizontal wind component in increasing pressure (Pa), divided by g=9.80665 m/s². Retain unrounded level quantities.'),
    Variable('eastward_layer_transport', None, 'Store the signed eastward transport for that same launch and three-level approximation in kg m^-1 s^-1 to 2 decimals.'),
    Variable('layer_water_kg_m2', None, 'Store the same launch’s 925–700 hPa water mass per horizontal area in kg/m² to 2 decimals, using the same pressure quadrature and specific humidity.'),
    Variable('southward_profiles', None, 'Store the exact number of eligible launches with strictly negative signed northward layer transport.'),
]

PRECISION = {'moisture_transport_profiles': 'count', 'moisture_transport_launch': 'timestamp', 'northward_layer_transport': 2, 'eastward_layer_transport': 2, 'layer_water_kg_m2': 2, 'southward_profiles': 'count'}

def _check(runtime, names):
    got = {name: runtime.retrieve(name) for name in names}
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    for name, value in got.items():
        kind = PRECISION[name]
        if kind == "timestamp":
            try:
                stamp = pd.Timestamp(value)
                if stamp.tzinfo is not None:
                    stamp = stamp.tz_convert("Asia/Hong_Kong").tz_localize(None)
                valid = isinstance(value, str) and not pd.isna(stamp) and stamp == pd.Timestamp(expected[name])
            except (TypeError, ValueError, OverflowError):
                valid = False
        elif kind == "identity":
            valid = isinstance(value, str) and value.strip() == expected[name]
        elif kind == "count":
            valid = is_finite_number(value) and value == expected[name]
        else:
            valid = is_finite_number(value) and reports_as(value, expected[name], decimals=kind)
        if not valid:
            errors.append(f"{name}={value!r}, expected {expected[name]!r}")
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")


def validate_turn_1(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check(runtime, ('moisture_transport_launch', 'northward_layer_transport', 'eastward_layer_transport', 'layer_water_kg_m2', 'moisture_transport_profiles', 'southward_profiles'))


validators = {'validate_turn_1': validate_turn_1}
