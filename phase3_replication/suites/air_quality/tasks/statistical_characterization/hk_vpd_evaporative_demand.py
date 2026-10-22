"""Screen atmospheric evaporative demand without replacing VPD by relative humidity.
Source: https://www.fao.org/4/X0490E/x0490e07.htm (FAO-56, equation 11).
VPD estimates use hourly mean T/RH; they are not true within-hour mean VPD or ET.
Wrong paths: minimum RH selects January 12, not the VPD peak April 15;
minimum monthly RH selects January, not November. November mean-input VPD
is 1.065 kPa rather than mean individual estimates 1.044 kPa.

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

from sqlalchemy import text
from domains.hk.db import read_frame


def _ground_truth():
    frame = read_frame(text("SELECT h.datetime,h.temperature,h.humidity FROM hourly_station_weather h "
                            "JOIN weather_station s ON s.id=h.station_id WHERE s.name_en='King''s Park' "
                            "AND h.datetime>'2025-01-01' AND h.datetime<='2026-01-01' ORDER BY h.datetime"))
    frame["datetime"] = pd.to_datetime(frame.datetime)
    frame = frame[np.isfinite(frame[["temperature", "humidity"]]).all(axis=1) & frame.humidity.between(0, 100)].copy()
    def vpd(t, rh):
        return .6108 * np.exp(17.27 * t / (t + 237.3)) * (1 - rh / 100)
    frame["vpd"] = vpd(frame.temperature, frame.humidity)
    frame["month"] = (frame.datetime - pd.Timedelta(hours=1)).dt.strftime("%Y-%m")
    best = frame.sort_values(["vpd", "datetime"], ascending=[False, True]).iloc[0]
    monthly = frame.groupby("month").agg(mean_vpd=("vpd", "mean"), t=("temperature", "mean"),
                                         rh=("humidity", "mean"), n=("vpd", "size")).reset_index()
    month = monthly.sort_values(["mean_vpd", "month"], ascending=[False, True]).iloc[0]
    return dict(peak_vpd_timestamp=str(best.datetime), peak_vpd_kpa=float(best.vpd),
                peak_vpd_temperature_c=float(best.temperature), peak_vpd_rh_pct=float(best.humidity), vpd_hours=len(frame),
                highest_mean_vpd_month=month.month, monthly_mean_vpd_kpa=float(month.mean_vpd),
                monthly_vpd_hours=int(month.n), monthly_aggregation_bias_kpa=float(vpd(month.t, month.rh) - month.mean_vpd))


tools = []
variables = [
    Variable('peak_vpd_timestamp', None, "Store the local YYYY-MM-DD HH:MM:SS ending-hour label with greatest King's Park VPD estimate in 2025. Use hourly_station_weather rows with datetime > 2025-01-01 00:00 and <= 2026-01-01 00:00, finite temperature and RH in [0,100]%; exclude missing rows without filling. Exact ties select earliest label."),
    Variable('peak_vpd_kpa', None, 'Store the peak VPD in kPa to 3 decimals. Estimate each hour from its reported mean temperature and mean RH using FAO-56 equation 11 liquid-water saturation pressure: e_s(T)=0.6108 exp(17.27 T/(T+237.3)) kPa, T in °C. Use unrounded estimates throughout.'),
    Variable('peak_vpd_temperature_c', None, 'Store the selected hour’s reported mean temperature in °C to 2 decimals.'),
    Variable('peak_vpd_rh_pct', None, 'Store the same hour’s mean relative humidity in percent to 2 decimals.'),
    Variable('vpd_hours', None, 'Store the exact count of eligible hourly pairs in that 2025 ending-hour window.'),
    Variable('highest_mean_vpd_month', None, 'Store YYYY-MM for the month with largest arithmetic mean of individual hourly VPD estimates; each eligible hour has equal weight. Assign months by datetime minus one hour. Exact ties select earliest month.'),
    Variable('monthly_mean_vpd_kpa', None, 'Store the selected month’s mean individual hourly VPD estimate in kPa to 3 decimals.'),
    Variable('monthly_vpd_hours', None, 'Store the exact eligible-hour count in the selected month.'),
    Variable('monthly_aggregation_bias_kpa', None, 'Store VPD evaluated at the selected month’s mean temperature and mean RH minus the mean of its individual hourly VPD estimates, in kPa to 3 decimals. Both methods use exactly the same eligible hours and unrounded inputs.'),
]

PRECISION = {'peak_vpd_timestamp': 'timestamp', 'peak_vpd_kpa': 3, 'peak_vpd_temperature_c': 2, 'peak_vpd_rh_pct': 2, 'vpd_hours': 'count', 'highest_mean_vpd_month': 'identity', 'monthly_mean_vpd_kpa': 3, 'monthly_vpd_hours': 'count', 'monthly_aggregation_bias_kpa': 3}

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
    return _check(runtime, ('peak_vpd_timestamp', 'peak_vpd_kpa', 'peak_vpd_temperature_c', 'peak_vpd_rh_pct', 'vpd_hours'))


def validate_turn_2(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check(runtime, ('highest_mean_vpd_month', 'monthly_mean_vpd_kpa', 'monthly_vpd_hours', 'monthly_aggregation_bias_kpa'))


validators = {'validate_turn_1': validate_turn_1, 'validate_turn_2': validate_turn_2}
