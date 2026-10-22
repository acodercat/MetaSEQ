"""Moist potential instability despite positive dry potential-temperature change.

Decision: select a layer for moist-convection follow-up rather than ruling out
potential instability from its dry stability. A bulk screen is not an observation
of convection, and does not describe every intervening sublayer.
Sources: Bolton (1980), doi:10.1175/1520-0493(1980)108<1046:TCOEPT>2.0.CO;2,
eqs. 21 and 43; https://www.weather.gov/lmk/indices.
Baseline/execution with a pinned Bolton thermodynamic approximation.
Provisional hard difficulty; repeated-model calibration remains outstanding.

Before-authoring freeze: .codex-review/new_designs_20261008/verified_answers.json.
361 eligible pairs; 218 qualify; strongest 2025-08-08 08:00:00,
delta theta_e=-30.08513471877336 K and delta theta=13.744283852881551 K.
All 361 pairs are dry stable. Raw temperature decreases in 360, a wrong screen.
Minimum abs(delta theta_e)=0.05652 K; winner gap=0.89017 K.
Counts and launch exact; signed temperature changes use reports_as at 2 decimals.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.hk.data import DATA_DIR
from tasks import Turn
from domains.scientific_outputs import check_evidence


def _ground_truth():
    frame = pd.read_csv(DATA_DIR / "profile_sounding.csv", parse_dates=["datetime"])
    frame = frame[frame.datetime.ge("2025-01-01") & frame.datetime.lt("2026-01-01")
                  & frame.hour.eq(8) & frame.pressure_hpa.isin([925, 700])]
    rows = []
    for launch, group in frame.groupby("datetime"):
        if len(group) != 2 or set(group.pressure_hpa) != {925, 700}:
            continue
        if not np.isfinite(group[["temperature_c", "relative_humidity_pct"]]).all().all():
            continue
        if not group.relative_humidity_pct.between(0, 100, inclusive="right").all():
            continue
        endpoints = group.set_index("pressure_hpa").loc[[925, 700]]
        tc = endpoints.temperature_c.to_numpy()
        t, p = tc + 273.15, np.array([925., 700.])
        e = endpoints.relative_humidity_pct.to_numpy() / 100 * 6.112 * np.exp(17.67*tc/(tc+243.5))
        r = .622 * e / (p-e)
        tl = 55 + 2840 / (3.5*np.log(t)-np.log(e)-4.805)
        theta = t*(1000/p)**.2854
        theta_e = t*(1000/p)**(.2854*(1-.28*r))*np.exp((3376/tl-2.54)*r*(1+.81*r))
        rows.append((launch, float(theta[1]-theta[0]), float(theta_e[1]-theta_e[0])))
    layers = pd.DataFrame(rows, columns=["launch", "dtheta", "dthetae"])
    qualifying = layers[layers.dtheta.gt(0) & layers.dthetae.lt(0)]
    best = qualifying.sort_values(["dthetae", "launch"]).iloc[0]
    return dict(eligible_moist_layers=len(layers), potentially_unstable_layers=len(qualifying),
                strongest_moist_launch=str(best.launch), selected_delta_thetae_k=float(best.dthetae),
                selected_delta_theta_k=float(best.dtheta))


tools = []
variables = [
    Variable("eligible_moist_layers", None,
             "Store the exact integer count of eligible sounding_df launches in calendar 2025 at 08:00 HKT "
             "(instantaneous launch timestamps). Require exactly one reported endpoint at each of 925 and 700 hPa, "
             "finite temperature and 0<RH<=100% at both; omit incomplete pairs, without interpolation. "
             "The diagnostic is a two-endpoint bulk layer screen."),
    Variable("potentially_unstable_layers", None,
             "Store the exact integer count of eligible layers satisfying both dry static stability and moist "
             "potential instability. Use unrounded diagnostic values and strict stability/instability signs."),
    Variable("strongest_moist_launch", None,
             "Store a local YYYY-MM-DD HH:MM:SS string for the qualifying launch with the most negative "
             "upper-minus-lower equivalent-potential-temperature change; exact ties choose the earliest launch."),
    Variable("selected_delta_thetae_k", None,
             "Store selected 700 hPa minus 925 hPa equivalent potential temperature in K as a signed number "
             "to 2 decimal places. Reference: Bolton (1980) eqs.21,43; Tc in °C, T=Tc+273.15 K, p in hPa, "
             "e=(RH/100)*6.112*exp(17.67*Tc/(Tc+243.5)) hPa, r=0.622*e/(p-e) kg/kg dry air, "
             "TL=55+2840/(3.5*ln(T)-ln(e)-4.805) K, "
             "theta_e=T*(1000/p)**(0.2854*(1-0.28*r))*exp((3376/TL-2.54)*r*(1+0.81*r)). "
             "All intermediate quantities unrounded; ln means natural logarithm."),
    Variable("selected_delta_theta_k", None,
             "Store selected 700 hPa minus 925 hPa dry potential temperature in K as a signed number "
             "to 2 decimal places. For this screen calculate theta=T*(1000/p)**0.2854, "
             "T in K and p in hPa, rather than using the rounded supplied potential_temperature_k column."),
]

FORMATS = dict(eligible_moist_layers="count", potentially_unstable_layers="count",
               strongest_moist_launch="timestamp", selected_delta_thetae_k=2, selected_delta_theta_k=2)


def validate_evidence(response: str, runtime, turn: Turn):
    return check_evidence(runtime, _ground_truth, FORMATS)


validators = {"validate_evidence": validate_evidence}
