"""Apparent dust-event propagation from two cities' concentration-peak lag.

Baseline execution under an explicit kinematic approximation: treat both PM10
peaks as the same translating structure and use city-centre great-circle distance.
Independent raw records give Beijing 09:00, Shijiazhuang 20:00, distance 264.098656
km and lag 11 h, hence apparent speed 24.008969 km/h. This is not a measured air
parcel velocity: source timing, removal, mixing and front geometry can change
concentration peaks. A plausible order of magnitude does not validate those
assumptions. PV checks lag and apparent speed (exact count / reports_as 2 dp);
CC checks the physical interpretation and limits.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_DATE = (2021, 3, 15)
_FROM, _TO = "北京", "石家庄"
_R_EARTH_KM = 6371.0


def _haversine_km(lat1, lon1, lat2, lon2):
    p = np.pi / 180.0
    a = (
        np.sin((lat2 - lat1) * p / 2) ** 2
        + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    )
    return 2 * _R_EARTH_KM * np.arcsin(np.sqrt(a))


def _kinematics() -> dict:
    cities = pd.read_csv(DATA_DIR / "region_cities.csv")
    # The date's hours are its labels 1-23 and label 0 of the next date (hour h
    # ends at h:00). Both peaks sit mid-day, so the label-date reading agrees.
    ending = pd.to_datetime(cities[["year", "month", "day", "hour"]]) - pd.Timedelta(hours=1)
    day = cities[ending.dt.normalize() == pd.Timestamp(*_DATE)]

    def peak(city: str):
        g = day[day["city"] == city]
        row = g.loc[g["PM10"].idxmax()]
        return int(row["hour"]), float(row["latitude"]), float(row["longitude"])

    h1, la1, lo1 = peak(_FROM)
    h2, la2, lo2 = peak(_TO)
    lag = h2 - h1
    dist = _haversine_km(la1, lo1, la2, lo2)
    return {"lag_h": lag, "distance_km": dist, "speed_kmh": dist / lag}


def validate_plume_lag(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("plume_lag_hours")
    if val is None:
        return ValidatorResult(
            False, "plume_lag_hours not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(False, f"plume_lag_hours={val!r} is not a number")

    gt = _kinematics()
    if compare_numeric(val, gt["lag_h"], tolerance=0):
        return ValidatorResult(True, f"correct: {val} h")
    return ValidatorResult(
        False, f"plume_lag_hours={val}, expected {gt['lag_h']}"
    )


def validate_plume_speed(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("plume_speed_kmh")
    if val is None:
        return ValidatorResult(
            False, "plume_speed_kmh not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(False, f"plume_speed_kmh={val!r} is not a number")

    gt = _kinematics()
    if reports_as(val, gt["speed_kmh"], decimals=2):
        return ValidatorResult(
            True,
            f"correct: {val} ~ {gt['speed_kmh']:.2f} km/h "
            f"({gt['distance_km']:.1f} km over {gt['lag_h']} h)",
        )
    return ValidatorResult(
        False,
        f"plume_speed_kmh={val}, expected ~{gt['speed_kmh']:.2f} km/h; check the "
        f"peak hours, the lag and the distance in turn",
    )


tools = []
variables = [
    Variable(
        "plume_lag_hours",
        None,
        "Store how many hours after the first city's PM10 peak the second city "
        "peaked, as an integer.",
    ),
    Variable(
        "plume_speed_kmh",
        None,
        "Store the apparent peak-lag propagation speed assuming one translating "
        "structure and city-centre great-circle distance, as a float "
        "in km/h, 2 decimal places.",
    ),
]
validators = {
    "validate_plume_lag": validate_plume_lag,
    "validate_plume_speed": validate_plume_speed,
}
