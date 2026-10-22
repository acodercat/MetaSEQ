"""Beijing ozone-temperature associations: baseline execution case.

All-days and JJA OLS regressions use the explicitly prescribed daily metrics.
Independent recomputation: slopes 3.4228578 and 8.5301492 µg/m³/°C on 2190 and
551 paired days respectively. Different seasonal populations yield different
marginal associations; neither slope identifies an isolated causal climate
penalty. Seasonal composition is a possible explanation, not a demonstrated
causal decomposition. Reusing the annual slope when asked for JJA violates the
specified scope, so it is not a diagnostic-trap path. PV uses reports_as at the
two-decimal reporting precision; CC checks interpretation and its limits.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn
from domains.beijing.mda8 import frame_to_mda8

_SPAN = ("2020-01-01", "2025-12-31")
_SUMMER = (6, 7, 8)


def _daily() -> pd.DataFrame:
    bj = DATA_DIR
    df = pd.read_csv(bj / "air_quality.csv")
    met = pd.read_csv(bj / "met_era5.csv")
    # Air-quality hour h ends at h:00, so label 0 belongs to the previous
    # date; the reanalysis is instantaneous and keeps its own dates.
    stamps = pd.to_datetime(df[["year", "month", "day", "hour"]])
    df["date"] = (stamps - pd.Timedelta(hours=1)).dt.normalize()
    met["date"] = pd.to_datetime(met[["year", "month", "day"]])
    df = df[(df["date"] >= _SPAN[0]) & (df["date"] <= _SPAN[1])]
    met = met[(met["date"] >= _SPAN[0]) & (met["date"] <= _SPAN[1])]

    mda8 = frame_to_mda8(df).rename("mda8")
    tmax = met.groupby("date")["t2m_c"].max().rename("tmax")
    return pd.concat([mda8, tmax], axis=1).dropna()


def _slopes() -> dict:
    daily = _daily()
    summer = daily[daily.index.month.isin(_SUMMER)]

    def slope(t: pd.DataFrame) -> float:
        return float(np.polyfit(t["tmax"], t["mda8"], 1)[0])

    return {"all_days": slope(daily), "summer": slope(summer)}


def validate_slope_all_days(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("slope_all_days")
    if val is None:
        return ValidatorResult(
            False, "slope_all_days not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(False, f"slope_all_days={val!r} is not a number")

    gt = _slopes()
    if reports_as(val, gt["all_days"], decimals=2):
        return ValidatorResult(
            True, f"correct: {val} ~ {gt['all_days']:.2f} ug/m3 per C"
        )
    return ValidatorResult(
        False, f"slope_all_days={val}, expected ~{gt['all_days']:.2f}"
    )


def validate_slope_summer(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("slope_summer")
    if val is None:
        return ValidatorResult(
            False, "slope_summer not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(False, f"slope_summer={val!r} is not a number")

    gt = _slopes()
    if reports_as(val, gt["summer"], decimals=2):
        return ValidatorResult(
            True, f"correct: {val} ~ {gt['summer']:.2f} ug/m3 per C"
        )
    return ValidatorResult(
        False, f"slope_summer={val}, expected ~{gt['summer']:.2f}"
    )


tools = []
variables = [
    Variable(
        "slope_all_days",
        None,
        "Store the OLS slope of daily maximum 8-hour ozone on daily maximum "
        "temperature over all days of 2020-2025, as a float in ug/m3 per "
        "degree C, 2 decimal places. The city daily maximum 8-hour ozone "
        "follows HJ 663-2013: each city assessment point's own daily maximum "
        "8-hour mean — the largest of the 8-hour running means whose window "
        "ENDS between 08:00 and 24:00 of that day, each window being the 8 "
        "clock hours ending at its end time and counting when at least 6 of "
        "them have a value — taken at the eleven "
        "stations flagged as included in the city aggregate, background site "
        "out, and averaged over those points, including "
        "every date on which a daily maximum can be formed at all, whatever "
        "number of valid 8-hour windows it holds. The day's maximum "
        "temperature is the highest single station-hour reading of that day.",
    ),
    Variable(
        "slope_summer",
        None,
        "Store the same OLS slope computed over June-August days only, on the "
        "same daily construction, as a float in ug/m3 per degree C, 2 decimal "
        "places.",
    ),
]
validators = {
    "validate_slope_all_days": validate_slope_all_days,
    "validate_slope_summer": validate_slope_summer,
}
