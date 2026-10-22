"""The average place is not where the average person lives
(exposure_assessment).

BASELINE, and the case that closes Hong Kong's last empty capability. Both
figures are asked for explicitly, so there is no naive path in the Round 9
sense; what the case tests is whether the agent reads the gap between them as a
statement about where people are rather than about where the air is worst.

**The finding.** Assigning each of the 1,496 population grid cells to the
nearest general station and taking that station's pooled hourly NO2 over
2020-2025:

    weighted by the 7,490,702 people in the cells    35.733 ug/m3
    every cell counted once                          30.039
    difference                                        +5.694

Hong Kong's population is not spread evenly over its NO2 field. Sham Shui Po's
catchment holds **15.643 %** of the territory's people at 43.91 ug/m3 and Kwun
Tong's a further 11.383 % at 43.69. What that share licenses saying is
leverage, not a guaranteed outage effect — Gate B round 8's distinction, and
the claim now makes it: an error of delta at that one site moves the aggregate
by 0.1564 x delta, and under the one scenario Gate B computed (drop Sham Shui
Po, reassign its cells to the next-nearest general station, whose catchment
mean is 37.2246) the figure moves from 35.7330 to 34.6867, -1.05 ug/m3 or
-2.9 % — material, but a property of that scenario, not of the share alone.
All three figures were reproduced here before being recorded. What pulls the unweighted figure down is
the other end: Tap Mun's catchment is 7.42 % of the CELLS and 0.22 % of the
PEOPLE at 8.38 ug/m3, so counting cells gives it thirty-four times the say that
counting residents does. The
concentration at the average LOCATION and the concentration at the average
PERSON differ by 19 %, and only the second is an exposure statement.

**What separates this from `hk_receptor_station_representativeness`.** That case
also assigns receptors to nearest stations over 2020-2025 with the same pooling
rule, and also contrasts nearest-any-station against nearest-general — its
turn 2 scores 41.49 and 35.60 for schools. Building this case on the same
contrast would have repeated it, which the proposal that suggested this case
would have done. The contrast here is a different one: **weighting**, over a
single receptor set and a single station set. Assigning to any station instead
of a general one reads 40.486 and is deliberately NOT scored, because that is
the earlier case's question.

**The first live run split on a set the query had described two ways.** It
said "every populated grid cell" and then asked for the mean with "every cell
counted once". Those are different sets: 69 of the 1,496 cells carry no people,
and excluding them reads 30.213 where including them reads 30.039. The model
took the first phrasing and was not wrong to. `grid_cells` now says every cell
the grid contains and names the 69, and it is scored, so the choice is visible
rather than absorbed.

**Convention sweep — three axes, eight combinations, all computed.**
The distance
metric moves the answer — great-circle reads 35.733 where degree distance reads
35.804, because a degree of longitude is shorter than a degree of latitude at
this latitude and the nearest cell changes for cells near a catchment boundary.
Forming each station's level from daily means before averaging the days reads
35.756. Neither is stated in the query: the HK domain prompt pins both, the
first under its haversine instruction and the second under STATION LEVELS.

The window endpoint moves it by only 0.00017, which no reasonable band on a
concentration would exclude. `general_station_no2_hours` is the guard: the
half-open year reads **755,933** station-hours and an inclusive end 755,948, an
exact integer either way. Where a convention changes which readings are in the
sample, score the size of the sample.

**Tolerances.** Both concentrations use `decimals=3`, deriving +/-0.0006. The
nearest excluded reading is the daily-first temporal aggregation at 0.023, 38
bands out; degree distance is 0.071 out, 118 bands. The station-hour count and
the population share are exact.

**What the numbers are and are not.** A population-weighted concentration built
this way is a proxy for the residential ambient level the population lives
among. It is not personal exposure and not a dose: it takes no account of where
people go during the day, of time indoors, of infiltration, or of the fact that
a whole catchment is represented by one station's reading. EPD's own network
description says the general stations reflect the ambient conditions most
people experience most of the time, which is what makes the proxy defensible
and also what bounds it. One of the claims requires the response to keep that
line.

Ground truth is recomputed from the database and `pop_df` at validation time.

**Turn 2 rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`):
the query no longer asks which figure belongs in the paper as if either
might; it asks the study's question and scores the answer as a variable
alongside the catchment share, which stays exact under the domain prompt's
great-circle pin.
"""

from typing import Dict

import numpy as np
import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.data import load_population
from domains.hk.db import read_frame

_SPAN = ("2020-01-01", "2026-01-01")
_EARTH_RADIUS_KM = 6371.0088
FIGURE_WEIGHTED = "the population-weighted figure"
FIGURE_GRID = "the grid mean"
FIGURE_EITHER = "either"


def _population() -> pd.DataFrame:
    """The 1 km population grid, as the runtime hands it to the agent."""
    return load_population()


def _general_stations() -> pd.DataFrame:
    """General stations with their coordinates and pooled NO2 over the span."""
    return read_frame(text("""
        select s.name_en,
               st_y(s.coordinate::geometry) as lat,
               st_x(s.coordinate::geometry) as lon,
               avg(a.no2) as no2,
               count(a.no2) as hours
        from air_quality_station s
        join hourly_station_air_quality a on a.station_id = s.id
        where s.station_type = 'GENERAL'
          and a.datetime > :lo and a.datetime <= :hi
          and a.no2 is not null
        group by 1, 2, 3
    """), {"lo": _SPAN[0], "hi": _SPAN[1]})


def _nearest(cells: pd.DataFrame, stations: pd.DataFrame) -> np.ndarray:
    """Index of the nearest station to each cell, by great-circle distance."""
    cell_lat = np.radians(cells["latitude"].to_numpy())[:, None]
    cell_lon = np.radians(cells["longitude"].to_numpy())[:, None]
    st_lat = np.radians(stations["lat"].to_numpy())[None, :]
    st_lon = np.radians(stations["lon"].to_numpy())[None, :]
    haversine = (np.sin((st_lat - cell_lat) / 2) ** 2
                 + np.cos(cell_lat) * np.cos(st_lat)
                 * np.sin((st_lon - cell_lon) / 2) ** 2)
    return (2 * _EARTH_RADIUS_KM * np.arcsin(np.sqrt(haversine))).argmin(axis=1)


def _figures() -> Dict[str, object]:
    """The four scored quantities."""
    cells = _population()
    stations = _general_stations()
    assigned = stations["no2"].to_numpy()[_nearest(cells, stations)]
    people = cells["population"].to_numpy()

    catchment_share = (pd.Series(people, index=_nearest(cells, stations))
                       .groupby(level=0).sum() / people.sum())
    return {
        "population_weighted_no2": float((assigned * people).sum() / people.sum()),
        "grid_mean_no2": float(assigned.mean()),
        # Pinned and scored because the first live run split on it: 69 of the
        # 1,496 cells carry no people, and dropping them reads 30.213 against
        # 30.039. The query had said "every populated grid cell" and then
        # "every cell counted once", which are not the same set; `grid_cells`
        # now carries the rule.
        "grid_cells": int(len(cells)),
        "largest_catchment_population_share": float(catchment_share.max()),
        # Exact guard: the window endpoint moves the concentrations by 0.00017,
        # which no reasonable band would exclude, and this count by 15.
        "general_station_no2_hours": int(stations["hours"].sum()),
        # A judgement, not a computation: only the weighted figure is a
        # statement about the population the study is about.
        "figure_for_the_paper": FIGURE_WEIGHTED,
    }


def _unusable(name: str, val) -> ValidatorResult:
    """The failure for a variable that is missing or not a number, else None.

    `runtime.retrieve` stays in the validators: `tests/test_turn_stores.py`
    reads the names out of the validator source to check them against the
    turn's `stores`, and hiding the call here would take that check away.
    """
    if val is None:
        return ValidatorResult(False, f"{name} not set", variables_not_set=True)
    if not is_finite_number(val):
        return ValidatorResult(False, f"{name}={val!r} is not a number")
    return None


def validate_weighted_against_grid(
        response: str, runtime, turn: Turn) -> ValidatorResult:
    weighted = runtime.retrieve("population_weighted_no2")
    grid = runtime.retrieve("grid_mean_no2")
    cells = runtime.retrieve("grid_cells")
    hours = runtime.retrieve("general_station_no2_hours")

    levels = {"population_weighted_no2": weighted, "grid_mean_no2": grid}
    for name, val in levels.items():
        failure = _unusable(name, val)
        if failure is not None:
            return failure
    counts = {"grid_cells": cells, "general_station_no2_hours": hours}
    for name, val in counts.items():
        if val is None:
            return ValidatorResult(False, f"{name} not set",
                                   variables_not_set=True)
        if not isinstance(val, int) or isinstance(val, bool):
            return ValidatorResult(False, f"{name}={val!r} is not an integer")

    gt = _figures()
    wrong = [f"{name}={val}, expected ~{gt[name]:.3f}"
             for name, val in levels.items()
             if not reports_as(val, gt[name], decimals=3)]
    wrong += [f"{name}={val}, expected {gt[name]}"
              for name, val in counts.items() if val != gt[name]]
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {weighted} weighted against {grid} unweighted")


def validate_catchment_concentration(
        response: str, runtime, turn: Turn) -> ValidatorResult:
    share = runtime.retrieve("largest_catchment_population_share")
    figure = runtime.retrieve("figure_for_the_paper")
    failure = _unusable("largest_catchment_population_share", share)
    if failure is not None:
        return failure
    if figure is None:
        return ValidatorResult(False, "figure_for_the_paper not set", variables_not_set=True)
    gt = _figures()
    wrong = []
    if not reports_as(share, gt["largest_catchment_population_share"],
                           decimals=4):
        wrong.append(f"largest_catchment_population_share={share}, "
                     f"expected ~{gt['largest_catchment_population_share']:.4f}")
    if str(figure).strip().lower() != gt["figure_for_the_paper"]:
        wrong.append(f"figure_for_the_paper={figure!r}, expected {gt['figure_for_the_paper']!r}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(True, f"correct: {share} of the population; {gt['figure_for_the_paper']}")


tools = []
variables = [
    Variable(
        "population_weighted_no2",
        None,
        "Store the mean NO2 across the population grid weighted by each cell's "
        "population, as a float in ug/m3 to 3 decimal places. Assign each cell "
        "to the GENERAL station whose site lies closest to it, and take that "
        "station's level over the window as the cell's NO2.",
    ),
    Variable(
        "grid_mean_no2",
        None,
        "Store the same mean under the same assignment with every grid cell "
        "counted once regardless of how many people it holds, as a float in "
        "ug/m3 to 3 decimal places.",
    ),
    Variable(
        "grid_cells",
        None,
        "Store how many grid cells the two means were taken over, as an "
        "integer. Every cell the grid contains is in scope, the 69 that hold "
        "no people included: they are part of the territory the unweighted "
        "figure describes.",
    ),
    Variable(
        "general_station_no2_hours",
        None,
        "Store how many hourly NO2 readings the general stations contribute "
        "across the window, as an integer.",
    ),
    Variable(
        "largest_catchment_population_share",
        None,
        "Store the share of the territory's population assigned to the single "
        "station that serves the most people, as a float between 0 and 1 to 4 "
        "decimal places.",
    ),
    Variable(
        "figure_for_the_paper",
        None,
        "Store which figure answers the stated resident-average background NO2 question, as one "
        f"of exactly these strings: '{FIGURE_WEIGHTED}', '{FIGURE_GRID}', "
        f"'{FIGURE_EITHER}'.",
    ),
]
validators = {
    "validate_weighted_against_grid": validate_weighted_against_grid,
    "validate_catchment_concentration": validate_catchment_concentration,
}
