"""Beijing mean wind direction — the circular-statistics trap (statistical_characterization).

Diagnostic trap. Wind direction is an angular quantity on a wrapped scale, so it has
no meaningful arithmetic mean: averaging degree values treats the 0/360 discontinuity
as a numeric gap. The mean direction is the argument of the summed unit vectors
(atan2 of mean sin over mean cos).

Dongsi, January 2023 — a month dominated by the winter northwesterly:

- correct path: circular/vector mean = 347.3 deg, i.e. north-northwest, which is the
  physically right answer for Beijing's winter flow.
- wrong path: the plain mean of the degree column = 202.8 deg, i.e. south-
  southwest — very nearly the OPPOSITE bearing, produced entirely by the wrap
  artefact (263 of the 744 hours are above 300 deg and 156 are below 60 deg).

The month has all 744 hourly records with no nulls, so there is no missing-data
convention to settle. The query does pin equal hourly weighting, because the
other established meteorological average — the true-vector (speed-weighted)
mean, which NOAA documents alongside the unit-vector one — gives 332.4 deg here,
15 deg away and outside any sane tolerance.

The ground truth is recomputed here from the CSV; the 202.8 naive reading is
quoted from measurement rather than recomputed on each call.

Report the direction to one decimal in [0, 360): 347.3 degrees. reports_as
checks that report; the former 2-degree band accepted different reported
answers and was removed in the October 2026 full review.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, is_finite_number, reports_as
from tasks import Turn

_STATION, _YEAR, _MONTH = "Dongsi", 2023, 1


def _series() -> pd.Series:
    met = pd.read_csv(DATA_DIR / "met_era5.csv")
    sel = met[
        (met["station"] == _STATION)
        & (met["year"] == _YEAR)
        & (met["month"] == _MONTH)
    ]
    return sel["wind_dir_deg"].dropna()


def _means() -> dict:
    deg = _series()
    rad = np.deg2rad(deg)
    circ = (np.rad2deg(np.arctan2(np.sin(rad).mean(), np.cos(rad).mean())) + 360) % 360
    return {"correct": float(circ)}


def _angular_gap(a: float, b: float) -> float:
    """Smallest absolute separation between two bearings, in degrees (0..180)."""
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def validate_mean_wind_direction(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("mean_wind_direction_deg")
    if val is None:
        return ValidatorResult(
            False, "mean_wind_direction_deg not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"mean_wind_direction_deg={val!r} is not a number"
        )

    gt = _means()
    # The query requests a normalized bearing and one decimal place.
    # Nearby bearings and extra full rotations are not that reported answer.
    if 0 <= float(val) < 360 and reports_as(val, gt["correct"], decimals=1):
        return ValidatorResult(
            True, f"correct: {val} ~ {gt['correct']:.1f} deg"
        )
    return ValidatorResult(
        False,
        f"mean_wind_direction_deg={val}, expected ~{gt['correct']:.1f} deg",
    )


tools = []
variables = [
    Variable(
        "mean_wind_direction_deg",
        None,
        "Store the mean direction the wind blew from over the month as a float bearing "
        "in degrees, 0 to 360 (0 = north, increasing clockwise), 1 decimal place.",
    ),
]
validators = {"validate_mean_wind_direction": validate_mean_wind_direction}
