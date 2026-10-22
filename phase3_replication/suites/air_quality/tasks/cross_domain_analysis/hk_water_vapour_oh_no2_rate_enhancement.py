"""Water-vapour third-body enhancement of total forward OH+NO2 association.

Decision: select the largest modeled humidity sensitivity at a common pressure,
while distinguishing coefficient sensitivity from atmospheric OH loss.
Source: https://iupac-aeris.ipsl.fr/datasheets/pdf/NOx13.pdf, July 2026 revision,
preferred values and atmospheric mixture expression pp.4–5. Coefficients are
frozen below, so changes to the remote reference do not change the benchmark.
Baseline/execution: explicit physical model, provisional hard difficulty.

Raw-data freeze predating implementation:
.codex-review/new_designs_20261008/verified_answers.json.
361 eligible; exact maxima July 29 and August 3, 2025 at 08:00 HKT;
enhancement=8.658683747392516%, dry k=1.1639737737723473e-11,
wet k=1.2647585817458849e-11 cm3 molecule-1 s-1.
RH alone selects 35 maxima; the first has only 3.11997% enhancement.
Maximizing absolute wet k selects December 26, enhancement 2.55635%.
Rate precision is 4 significant figures (not a generic absolute tolerance).
Only the wet coefficient is reported alongside the enhancement, avoiding
three outputs that encode just two independent quantities. Enhancement still
uses unrounded wet and dry calculations; counts and the timestamp set are exact.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.hk.data import DATA_DIR
from tasks import Turn
from domains.scientific_outputs import check_evidence


def _rate_coefficient(temperature_k, water_fraction):
    t, x = temperature_k, water_fraction
    density = 92500 / (1.380649e-23*t) / 1e6
    low = density*((1-x)*(.79*2.6e-30+.21*1.8e-30)*(t/300)**-3.6
                   + x*15.9e-30*(t/300)**-3.4)
    high, fc = 6.3e-11, .39
    n = .75 - 1.27*np.log10(fc)
    broadening = 10**(np.log10(fc)/(1+(np.log10(low/high)/n)**2))
    return low*high/(low+high)*broadening


def _ground_truth():
    frame = pd.read_csv(DATA_DIR / "profile_sounding.csv", parse_dates=["datetime"])
    frame = frame[frame.datetime.ge("2025-01-01") & frame.datetime.lt("2026-01-01")
                  & frame.hour.eq(8) & frame.pressure_hpa.eq(925)].copy()
    frame = frame[np.isfinite(frame[["temperature_c", "relative_humidity_pct"]]).all(axis=1)
                  & frame.relative_humidity_pct.between(0, 100)].copy()
    if frame.datetime.duplicated().any():
        raise ValueError("925 hPa launch endpoints must be unique")
    t = frame.temperature_c + 273.15
    if not t.between(220, 400).all():
        raise ValueError("cohort is outside the kinetic reference's temperature range")
    vapour = frame.relative_humidity_pct/100*6.112*np.exp(
        17.67*frame.temperature_c/(frame.temperature_c+243.5))
    frame["dry"] = _rate_coefficient(t, 0)
    frame["wet"] = _rate_coefficient(t, vapour/925)
    frame["enhancement"] = 100*(frame.wet/frame.dry-1)
    maxima = frame[frame.enhancement.eq(frame.enhancement.max())].sort_values("datetime")
    best = maxima.iloc[0]
    return dict(kinetic_launch_count=len(frame),
                maximum_enhancement_launches=maxima.datetime.astype(str).tolist(),
                water_enhancement_pct=float(best.enhancement), selected_wet_rate=float(best.wet))


tools = []
variables = [
    Variable("kinetic_launch_count", None,
             "Store the exact integer count of eligible sounding_df records at 925 hPa, 08:00 HKT launches "
             "in calendar 2025, with unique record per launch, finite temperature and 0<=RH<=100%. "
             "Timestamps denote launch instants. No interpolation or missing-value filling."),
    Variable("maximum_enhancement_launches", None,
             "Store a list of all maximizing local launch strings YYYY-MM-DD HH:MM:SS, each once, "
             "in any order. Compare unrounded enhancements. If maxima have different coefficients, "
             "the selected wet-coefficient output refers to the earliest maximizing launch."),
    Variable("water_enhancement_pct", None,
             "Store maximum 100*(k_wet/k_dry-1) in percent to 2 decimal places, calculated from unrounded "
             "coefficients. Compare each observed-temperature moist mixture to dry gas at the same T and "
             "total p=925 hPa. Model only N2, O2 and H2O; the dry N2:O2 fractions are 0.79:0.21. "
             "Tc is temperature_c, T=Tc+273.15 K; e=(RH/100)*6.112*exp(17.67*Tc/(Tc+243.5)) hPa, "
             "x=e/p. Wet mole fractions (xN2,xO2,xH2O)=(0.79*(1-x),0.21*(1-x),x); "
             "dry fractions=(0.79,0.21,0)."),
    Variable("selected_wet_rate", None,
             "Store selected wet total forward OH+NO2 association coefficient in cm³ molecule⁻¹ s⁻¹ "
             "to 4 significant figures. IUPAC NOx13 July 2026 model (both product channels): "
             "M=(100*p)/(1.380649e-23*T)/1e6 molecule/cm³, "
             "L=M*((2.6e-30*xN2+1.8e-30*xO2)*(T/300)**(-3.6)+15.9e-30*xH2O*(T/300)**(-3.4)), "
             "H=6.3e-11, Fc=0.39, N=0.75-1.27*log10(Fc), "
             "F=10**(log10(Fc)/(1+(log10(L/H)/N)**2)), k=L*H/(L+H)*F. "
             "p is hPa and T is K. Keep all intermediate values unrounded."),
]

FORMATS = dict(kinetic_launch_count="count", maximum_enhancement_launches="timestamp_set",
               water_enhancement_pct=2, selected_wet_rate="sig4")


def validate_evidence(response: str, runtime, turn: Turn):
    return check_evidence(runtime, _ground_truth, FORMATS)


validators = {"validate_evidence": validate_evidence}
