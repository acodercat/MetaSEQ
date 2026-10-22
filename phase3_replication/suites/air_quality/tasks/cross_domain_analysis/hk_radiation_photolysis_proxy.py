"""Screen a broadband-radiation photolysis parameterization, not measured actinic flux.
Source: https://amt.copernicus.org/articles/2/725/2009/amt-2-725-2009.pdf
Trebs et al. 2009, Eq. 2; low altitude <800 m, UV-A albedo <0.2. King's Park
is 64.8 m. The 100–900 W/m² screen is a conservative desk-defined band inside
the fitted irradiance span, not universal physical cutoffs. Applying a fit to
half-hour averages to isolated one-minute samples is a temporal-transfer approximation.
Wrong paths: inverse mean J lifetime 164.80 rather than mean individual 206.53 s;
linear-only mean J .007562, J at mean G .006342, missing albedo .005779 s^-1.
The albedo range is a scenario sensitivity, not a confidence interval or net ozone yield.
All three albedo scenarios are scored in one turn: their multiplicative
rescaling is valid algebra, not a second independent analysis task.

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
    frame = pd.read_csv(DATA_DIR / "radiation_1min_hko.csv")
    valid = (frame.year.eq(2025) & frame.station.eq("King's Park") & frame.hour.isin([10, 11, 12, 13, 14])
             & np.isfinite(frame.global_radiation_wm2) & frame.global_radiation_wm2.between(100, 900))
    g = frame.loc[valid, "global_radiation_wm2"].to_numpy()
    base = 1.47e-5 * g - 4.84e-9 * g ** 2
    j = 1.05 * base
    return dict(photolysis_samples=len(g), mean_j_no2_s1=float(j.mean()),
                mean_photolysis_lifetime_s=float((1 / j).mean()), mean_screen_radiation_wm2=float(g.mean()),
                lower_albedo_mean_j_s1=float((1.02 * base).mean()), upper_albedo_mean_j_s1=float((1.10 * base).mean()))


tools = []
variables = [
    Variable('photolysis_samples', None, "Store the exact count of King's Park 2025 radiation_1min_hko samples with source hour labels 10–14 inclusive and finite global radiation G in [100,900] W/m². This desk-defined irradiance band limits low-light and extrapolation effects. Weight retained one-minute samples equally, without filling or duration integration."),
    Variable('mean_j_no2_s1', None, 'Store mean sample J(NO2) in s^-1 to 6 decimals for assumed constant UV-A albedo α=0.05. Use the Trebs et al. (2009) central parameterization J(NO2)=(1+α)(1.47e-5 G - 4.84e-9 G²), G in W/m². This is a low-altitude (<800 m), low-albedo (<0.2) empirical scenario. The source study paired half-hour mean irradiance and photolysis observations for its fit (§2.3); this dataset supplies isolated one-minute samples once per hour. Retain unrounded sample estimates.'),
    Variable('mean_photolysis_lifetime_s', None, 'Store the arithmetic mean of individual samples’ fixed-condition, photolysis-only e-folding lifetimes in seconds to 2 decimals, using the same α=0.05 cohort.'),
    Variable('mean_screen_radiation_wm2', None, 'Store arithmetic mean global radiation of this same cohort in W/m² to 2 decimals.'),
    Variable('lower_albedo_mean_j_s1', None, 'Store mean sample J(NO2) in s^-1 to 6 decimals for constant UV-A albedo α=0.02, using exactly the same samples and parameterization.'),
    Variable('upper_albedo_mean_j_s1', None, 'Store mean sample J(NO2) in s^-1 to 6 decimals for constant UV-A albedo α=0.10, using exactly the same samples and parameterization.'),
]

PRECISION = {'photolysis_samples': 'count', 'mean_j_no2_s1': 6, 'mean_photolysis_lifetime_s': 2, 'mean_screen_radiation_wm2': 2, 'lower_albedo_mean_j_s1': 6, 'upper_albedo_mean_j_s1': 6}

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
    return _check(runtime, ('photolysis_samples', 'mean_j_no2_s1', 'mean_photolysis_lifetime_s',
                            'mean_screen_radiation_wm2', 'lower_albedo_mean_j_s1', 'upper_albedo_mean_j_s1'))


validators = {'validate_turn_1': validate_turn_1}
