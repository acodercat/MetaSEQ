"""beijing_no3_production_kinetics — hard baseline.

Decision: Select a station-hour for additional nighttime radical and nitrate-process measurements, without substituting a precursor rank for a reaction-rate screen.
Primary sources: https://acp.copernicus.org/articles/4/1461/2004/acp-4-1461-2004.pdf
https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/201808/t20180815_629602.html
Naive path / excluded reading: Treating reported reference-state concentrations as ambient number densities gives 52.320 rather than 48.974 million molecules cm^-3 s^-1 at the selected sample. Ranking NO2 alone selects Nongzhanguan, 2025-03-01 02:00, rather than the joint-reaction maximum.

Raw-file outputs frozen before authoring:
.codex-review/diverse_cases_20261006/frozen_answers.json
Reported answers: {'no3_peak_station': 'Dongsi', 'no3_peak_timestamp': '2025-06-17 21:00:00', 'no3_peak_production_million': 48.974, 'no3_peak_temperature_c': 30.62, 'no3_peak_pressure_hpa': 998.8, 'no3_valid_station_hours': 31124}

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
from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

def _ground_truth():
    air=pd.read_csv(DATA_DIR / 'air_quality.csv')
    air['datetime']=pd.to_datetime(air[['year','month','day','hour']])
    air=air[air.datetime.gt('2025-01-01')&air.datetime.le('2026-01-01')&air.hour.isin([21,22,23,0,1,2,3,4,5])]
    met=pd.read_csv(DATA_DIR / 'met_era5.csv',parse_dates=['datetime'])
    f=air.merge(met[['station','datetime','t2m_c','surface_pressure_hpa']],on=['station','datetime'],validate='one_to_one')
    temperature=f.t2m_c+273.15
    f=f[np.isfinite(f[['NO2','O3','t2m_c','surface_pressure_hpa']]).all(axis=1)&f.NO2.gt(0)&f.O3.gt(0)&f.surface_pressure_hpa.gt(0)&temperature.between(230,360)].copy()
    number=f[['NO2','O3']].mul(6.02214076e11).div(pd.Series({'NO2':46.,'O3':48.}))
    ambient_factor=f.surface_pressure_hpa/1013.25*298.15/(f.t2m_c+273.15)
    number=number.mul(ambient_factor,axis=0)
    f['p']=1.4e-13*np.exp(-2470/(f.t2m_c+273.15))*number.NO2*number.O3/1e6
    best=f.sort_values(['p','station','datetime'],ascending=[False,True,True]).iloc[0]
    return dict(no3_peak_station=best.station,no3_peak_timestamp=str(best.datetime),no3_peak_production_million=float(best.p),no3_peak_temperature_c=float(best.t2m_c),no3_peak_pressure_hpa=float(best.surface_pressure_hpa),no3_valid_station_hours=len(f))

tools = []
variables = [
    Variable('no3_peak_station', None, "Store the station name verbatim from the source for the largest intrinsic NO3 production rate by NO2 + O3 for local hour-ending timestamps t satisfying 2025-01-01 00:00:00 < t <= 2026-01-01 00:00:00. Apply this interval to air-quality readings before pairing; retain ERA5 at each selected ending timestamp, including the upper endpoint. For this nocturnal screen retain air-quality readings labelled 21,22,23,00,01,02,03,04,05; pair each hour-ending reading with ERA5 temperature and surface pressure at that ending timestamp as an approximation. Require finite positive reactant concentrations, finite positive surface pressure and finite temperature within the Atkinson 2004 rate expression's 230–360 K range. Break exact rate ties alphabetically by station, then by earliest timestamp."),
    Variable('no3_peak_timestamp', None, 'Store the selected station-hour as a local YYYY-MM-DD HH:MM:SS string, retaining its hour-ending label.'),
    Variable('no3_peak_production_million', None, "Store the ambient-volume instantaneous production estimate in millions of molecules cm⁻³ s⁻¹ to 3 decimal places. Use the temperature-dependent Atkinson et al. 2004 IUPAC recommendation for NO2 + O3, with prefactor 1.4e-13 cm³ molecule⁻¹ s⁻¹ and activation-temperature parameter 2470 K. Interpret reported gaseous mass concentrations at the GB 3095-2012 2018 amendment's reference state, 298.15 K and 1013.25 hPa. Use the paired ERA5 temperature and surface pressure for the ambient state, molar masses 46 and 48 g/mol, and Avogadro constant 6.02214076e23 mol⁻¹; retain unrounded inputs."),
    Variable('no3_peak_temperature_c', None, 'Store the paired ERA5 temperature at that station-hour in °C to 2 decimal places.'),
    Variable('no3_peak_pressure_hpa', None, 'Store the paired ERA5 surface pressure at that station-hour in hPa to 2 decimal places.'),
    Variable('no3_valid_station_hours', None, 'Store the exact integer count of station-hours satisfying the same nocturnal pairing and validity definition.'),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "no3_peak_station": runtime.retrieve("no3_peak_station"),
        "no3_peak_timestamp": runtime.retrieve("no3_peak_timestamp"),
        "no3_peak_production_million": runtime.retrieve("no3_peak_production_million"),
        "no3_peak_temperature_c": runtime.retrieve("no3_peak_temperature_c"),
        "no3_peak_pressure_hpa": runtime.retrieve("no3_peak_pressure_hpa"),
        "no3_valid_station_hours": runtime.retrieve("no3_valid_station_hours"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    if not (isinstance(got["no3_peak_station"], str) and got["no3_peak_station"].strip().casefold() == expected["no3_peak_station"].casefold()):
        errors.append("no3_peak_station="+repr(got["no3_peak_station"])+", expected "+repr(expected["no3_peak_station"]))
    try:
        parsed = pd.Timestamp(got["no3_peak_timestamp"])
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("Asia/Shanghai").tz_localize(None)
        valid = isinstance(got["no3_peak_timestamp"], str) and not pd.isna(parsed) and parsed == pd.Timestamp(expected["no3_peak_timestamp"])
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not (valid):
        errors.append("no3_peak_timestamp="+repr(got["no3_peak_timestamp"])+", expected "+repr(expected["no3_peak_timestamp"]))
    if not (is_finite_number(got["no3_peak_production_million"]) and reports_as(got["no3_peak_production_million"], expected["no3_peak_production_million"], decimals=3)):
        errors.append("no3_peak_production_million="+repr(got["no3_peak_production_million"])+", expected "+repr(expected["no3_peak_production_million"]))
    if not (is_finite_number(got["no3_peak_temperature_c"]) and reports_as(got["no3_peak_temperature_c"], expected["no3_peak_temperature_c"], decimals=2)):
        errors.append("no3_peak_temperature_c="+repr(got["no3_peak_temperature_c"])+", expected "+repr(expected["no3_peak_temperature_c"]))
    if not (is_finite_number(got["no3_valid_station_hours"]) and compare_numeric(got["no3_valid_station_hours"], expected["no3_valid_station_hours"], tolerance=0)):
        errors.append("no3_valid_station_hours="+repr(got["no3_valid_station_hours"])+", expected "+repr(expected["no3_valid_station_hours"]))
    if not (is_finite_number(got["no3_peak_pressure_hpa"]) and reports_as(got["no3_peak_pressure_hpa"], expected["no3_peak_pressure_hpa"], decimals=2)):
        errors.append("no3_peak_pressure_hpa="+repr(got["no3_peak_pressure_hpa"])+", expected "+repr(expected["no3_peak_pressure_hpa"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
