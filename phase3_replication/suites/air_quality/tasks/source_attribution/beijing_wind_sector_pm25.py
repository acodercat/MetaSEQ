"""Beijing winter PM2.5 by wind sector (source_attribution).

A sector-conditioning baseline. The scored measurements are equal-weight
station-hour PM2.5 means, with concurrent wind joined on timestamp and station.
No direction is averaged. Southerly bounds are inclusive 135..225 degrees;
northerly bounds are >=315 or <=45 degrees.

Winter membership follows the observation day (hour-ending timestamp minus
one hour), restricted to December, January and February in 2020..2025. The
meteorology join still uses the concurrent timestamp. The October 2026 full
review corrected the former raw-calendar-month filter, whose boundary rows
changed the southerly two-decimal report.

The months are those of each calendar year 2020..2025, which the query states
("January 2020 to December 2025, not whole winters"): read as the five whole
winters December 2020..February 2025, the same construction gives 45.73 and
29.50 (stated after the 2026-10-07 triage, where one run read it so).

Independent observation-day results:
- southerly_pm25_mean: 47.8924835625 µg/m³, reported 47.89;
- northerly_pm25_mean: 32.4665092221 µg/m³, reported 32.47.

Both are checked within 0.01 ug/m3 of the unrounded figure. Pooling qualifying
station-hours is explicit in the variable descriptions; station-first means
(47.94 / 32.86) or an arithmetic mean of wind direction are different
calculations and lie outside the band. The band was widened from the
two-decimal report after the reliability_tool study (2026-10-12): under
reports_as the southerly figure turned on whether 1 March 00:00 belongs to
February — 47.8964 under the label month against 47.8925 — a boundary hour the
query and variables do not test, and every one of 51 failed turns across three
models failed on it alone.

The sector contrast is consistent with regional transport and ventilation,
but it does not identify direction alone as a causal effect. Concurrent wind
speed, mixing depth and other weather can contribute to the contrast.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn

_MONTHS = (12, 1, 2)
_YEARS = range(2020, 2026)


def _sector_means() -> dict:
    bj = DATA_DIR
    aq = pd.read_csv(bj / "air_quality.csv")
    met = pd.read_csv(bj / "met_era5.csv")

    joined = aq.merge(
        met[["year", "month", "day", "hour", "station", "wind_dir_deg"]],
        on=["year", "month", "day", "hour", "station"],
        how="inner",
    ).dropna(subset=["PM2.5"])
    observation_day = (pd.to_datetime(joined[["year", "month", "day", "hour"]])
                       - pd.Timedelta(hours=1))
    winter = joined[
        observation_day.dt.month.isin(_MONTHS) & observation_day.dt.year.isin(list(_YEARS))
    ]

    wd = winter["wind_dir_deg"]
    south = winter[(wd >= 135) & (wd <= 225)]
    north = winter[(wd >= 315) | (wd <= 45)]
    return {
        "south": float(south["PM2.5"].mean()),
        "north": float(north["PM2.5"].mean()),
    }


def validate_sector_means(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {}
    for name in ("southerly_pm25_mean", "northerly_pm25_mean"):
        val = runtime.retrieve(name)
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")
        got[name] = val

    gt = _sector_means()
    errors = []
    if not compare_numeric(got["southerly_pm25_mean"], gt["south"], tolerance=0.01):
        errors.append(
            f"southerly_pm25_mean={got['southerly_pm25_mean']}, "
            f"expected ~{gt['south']:.2f}"
        )
    if not compare_numeric(got["northerly_pm25_mean"], gt["north"], tolerance=0.01):
        errors.append(
            f"northerly_pm25_mean={got['northerly_pm25_mean']}, "
            f"expected ~{gt['north']:.2f}"
        )
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True,
        f"correct: southerly {gt['south']:.2f}, northerly {gt['north']:.2f} ug/m3",
    )


tools = []
variables = [
    Variable(
        "southerly_pm25_mean",
        None,
        "Store the southerly-sector mean as a float in ug/m3, 2 decimal "
        "places. Give every qualifying station-hour equal weight — pool the "
        "observations themselves rather than averaging each station first "
        "and then the stations.",
    ),
    Variable(
        "northerly_pm25_mean",
        None,
        "Store the northerly-sector mean as a float in ug/m3, 2 decimal "
        "places, on the same equal-weight pooling of station-hours.",
    ),
]
validators = {"validate_sector_means": validate_sector_means}
