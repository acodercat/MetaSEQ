"""Compare broadband transmission across seasons using a daily clearness index.

Decision: choose the month with highest normalized solar transmission for
radiative follow-up, rather than the month receiving the most solar energy.
Source: https://www.fao.org/4/X0490E/x0490e07.htm, FAO-56 eqs. 21, 23–25.
Baseline/execution: the physical approximation and daily estimand are visible.
Provisional medium difficulty; no repeated-model difficulty calibration.

Raw answers frozen before helper authoring in
.codex-review/new_designs_20261008/verified_answers.json:
January, mean Kt 0.576213656566353, mean G 14.818064516129033,
31 selected-month days / 361 year days. Ranking raw G selects July instead.
The next index is lower by 0.0737694, so the winner is unambiguous.
Counts/month are exact; reports_as uses 4 decimals for Kt and 3 for radiation.
The extra Kt digit distinguishes daily-ratio mean 0.5762 from monthly-mean
ratio 0.5761; it is computational reporting precision, not physical accuracy
or independent evidence of difficult atmospheric reasoning.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.hk.data import DATA_DIR
from tasks import Turn
from domains.scientific_outputs import check_evidence


def _ground_truth():
    frame = pd.read_csv(DATA_DIR / "radiation_hko.csv", parse_dates=["date"])
    frame = frame[frame.date.ge("2025-01-01") & frame.date.lt("2026-01-01")
                  & frame.global_solar_radiation_mj_m2_completeness.eq("C")].copy()
    frame = frame[np.isfinite(frame.global_solar_radiation_mj_m2)
                  & frame.global_solar_radiation_mj_m2.ge(0)].copy()
    if frame.date.duplicated().any():
        raise ValueError("daily radiation dates must be unique")
    j = frame.date.dt.dayofyear.to_numpy()
    phi = np.deg2rad(22.3119)
    dr = 1 + .033 * np.cos(2 * np.pi * j / 365)
    delta = .409 * np.sin(2 * np.pi * j / 365 - 1.39)
    ws = np.arccos(-np.tan(phi) * np.tan(delta))
    ra = 1440 / np.pi * .0820 * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))
    frame["kt"] = frame.global_solar_radiation_mj_m2 / ra
    frame["month_key"] = frame.date.dt.strftime("%Y-%m")
    monthly = frame.groupby("month_key").agg(
        kt=("kt", "mean"), radiation=("global_solar_radiation_mj_m2", "mean"),
        n=("kt", "size")).reset_index()
    best = monthly.sort_values(["kt", "month_key"], ascending=[False, True]).iloc[0]
    return dict(clearness_peak_month=best.month_key, monthly_clearness_index=float(best.kt),
                selected_mean_radiation=float(best.radiation), clearness_month_days=int(best.n),
                clearness_year_days=len(frame))


tools = []
variables = [
    Variable("clearness_peak_month", None,
             "Store a YYYY-MM string for the largest mean daily clearness index in radiation_df's "
             "2025 local calendar dates. Retain only finite nonnegative global_solar_radiation_mj_m2 "
             "with that field's completeness flag C; do not filter on other fields or fill missing days. "
             "Monthly index means the equal-valid-day arithmetic mean of daily indices. Exact ties choose earliest month."),
    Variable("monthly_clearness_index", None,
             "Store the selected month's dimensionless mean index to 4 decimal places. Daily index Kt=G/Ra, "
             "G is daily global radiation, Ra daily extraterrestrial radiation in MJ/m². Use FAO-56 eqs. "
             "21,23–25: phi=22.3119 degrees N, J=calendar day-of-year, dr=1+0.033*cos(2*pi*J/365), "
             "delta=0.409*sin(2*pi*J/365-1.39), ws=acos(-tan(phi)*tan(delta)), "
             "Ra=(1440/pi)*0.0820*dr*(ws*sin(phi)*sin(delta)+cos(phi)*cos(delta)*sin(ws)). "
             "Angles in radians after converting latitude; use unrounded values throughout."),
    Variable("selected_mean_radiation", None,
             "Store the selected month's arithmetic mean daily global radiation on the same valid days, "
             "in MJ/m²/day to 3 decimal places."),
    Variable("clearness_month_days", None, "Store the exact integer number of valid days in the selected month."),
    Variable("clearness_year_days", None, "Store the exact integer number of valid days across calendar 2025."),
]

FORMATS = dict(clearness_peak_month="identity", monthly_clearness_index=4,
               selected_mean_radiation=3, clearness_month_days="count", clearness_year_days="count")


def validate_evidence(response: str, runtime, turn: Turn):
    return check_evidence(runtime, _ground_truth, FORMATS)


validators = {"validate_evidence": validate_evidence}
