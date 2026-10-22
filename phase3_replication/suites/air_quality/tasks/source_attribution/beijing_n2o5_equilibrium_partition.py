"""Prioritize paired radical monitoring by conditional thermal-equilibrium partition.
Primary source: https://pubmed.ncbi.nlm.nih.gov/19462574/
Osthoff et al. (2007), DOI 10.1039/b709193a; central Kc fit measured at 278–323 K.
Uses reference-state NO2 mass concentration converted to ambient molecular density.
ERA5 endpoint T/P paired with hourly AQ is a collocation approximation.
Wrong paths: NO2-only rank Wanliu; coldest-station rank Shunyi; using reference
volume gives 62.828 versus 65.878, and applying Kc to station mean conditions 34.665.
This conditional ratio is not observed N2O5, aerosol nitrate yield or equilibrium proof.

Independent raw-data answers frozen before this helper was authored:
.codex-review/proxy_cases_20261008/frozen_answers.json
The prescribed cohort and physical approximation make this baseline/execution.
Float acceptance is reports_as at declared precision; counts and identities are exact.
Alternative-path and adjacent-report probes live in scripts/verdict_baseline.py.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, is_finite_number, reports_as

def _ground_truth():
    aq = pd.read_csv(DATA_DIR / "air_quality.csv")
    aq["datetime"] = pd.to_datetime(aq[["year", "month", "day", "hour"]])
    aq = aq[aq.datetime.gt("2025-01-01") & aq.datetime.le("2026-01-01") & aq.hour.isin([21, 22, 23, 0, 1, 2, 3, 4, 5])]
    met = pd.read_csv(DATA_DIR / "met_era5.csv", parse_dates=["datetime"])
    frame = aq.merge(met[["station", "datetime", "t2m_c", "surface_pressure_hpa"]], on=["station", "datetime"], validate="one_to_one")
    kelvin = frame.t2m_c + 273.15
    valid = np.isfinite(frame[["NO2", "t2m_c", "surface_pressure_hpa"]]).all(axis=1)
    frame = frame[valid & frame.NO2.gt(0) & frame.surface_pressure_hpa.gt(0) & kelvin.between(278, 323)].copy()
    kelvin = frame.t2m_c + 273.15
    number = frame.NO2 * (6.02214076e11 / 46) * (frame.surface_pressure_hpa / 1013.25) * (298.15 / kelvin)
    frame["ratio"] = 5.1e-27 * np.exp(10871 / kelvin) * number
    ranked = frame.groupby("station").agg(ratio=("ratio", "mean"), no2=("NO2", "mean"), n=("ratio", "size")).reset_index()
    best = ranked.sort_values(["ratio", "station"], ascending=[False, True]).iloc[0]
    return dict(equilibrium_station=best.station, mean_n2o5_no3_ratio=float(best.ratio),
                equilibrium_station_hours=int(best.n), equilibrium_total_hours=len(frame), selected_mean_no2_ugm3=float(best.no2))


tools = []
variables = [
    Variable('equilibrium_station', None, 'Store the exact station identifier with greatest mean conditional thermal-equilibrium [N2O5]/[NO3] molecular ratio. Use AQ labels > 2025-01-01 00:00 and <= 2026-01-01 00:00, at hours 21,22,23,00,01,02,03,04,05; pair station ERA5 at the ending timestamp. Require finite positive NO2 and surface pressure and 278 <= T <= 323 K. Average over each station’s own eligible hours equally, no filling; exact ties select alphabetically first station.'),
    Variable('mean_n2o5_no3_ratio', None, 'Store that station’s mean unrounded equilibrium ratio to 3 decimals. For NO2 + NO3 ⇌ N2O5 use the Osthoff et al. (2007) central fit Kc=5.1e-27 exp(10871/T) cm³ molecule^-1, T in K. Treat reported NO2 µg/m³ as referenced to 298.15 K and 1013.25 hPa; use NO2 molar mass 46 g/mol and Avogadro constant 6.02214076e23 mol^-1. Apply equilibrium at paired ambient T and pressure.'),
    Variable('equilibrium_station_hours', None, 'Store the selected station’s exact eligible-hour count.'),
    Variable('equilibrium_total_hours', None, 'Store the exact total eligible station-hour count across all stations in this screening cohort.'),
    Variable('selected_mean_no2_ugm3', None, 'Store the selected station’s arithmetic mean reported NO2 in µg/m³ on precisely its equilibrium-screen cohort, to 3 decimals.'),
]

PRECISION = {'equilibrium_station': 'identity', 'mean_n2o5_no3_ratio': 3, 'equilibrium_station_hours': 'count', 'equilibrium_total_hours': 'count', 'selected_mean_no2_ugm3': 3}

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
    return _check(runtime, ('equilibrium_station', 'mean_n2o5_no3_ratio', 'equilibrium_station_hours', 'equilibrium_total_hours', 'selected_mean_no2_ugm3'))


validators = {'validate_turn_1': validate_turn_1}
