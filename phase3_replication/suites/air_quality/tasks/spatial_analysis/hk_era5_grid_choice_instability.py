"""Which reanalysis cell you call Hong Kong decides the answer (spatial_analysis).

BASELINE. The pre-rebuild query named both constructions and asks for the consequence, so
there is no naive path left to fall into; the case measures whether the agent
reads the gap as a property of the product's resolution rather than as
variation someone measured.

**This is not the Beijing pseudoreplication case with a different city.**
`beijing_era5_grid_pseudoreplication` hides the coarseness behind station
labels: twelve monitoring sites carry twelve reanalysis records that are five
distinct series, and the defect is treating them as twelve independent samples.
Here the coarseness is disclosed — `met_df` says in its own description that the
six values are ERA5 0.25-degree grid cells and that they differ for the same
hour — so pseudoreplication cannot arise. What can arise is that two defensible
constructions of "the boundary layer height over Hong Kong" disagree, and an
analysis that does not say which one it used is not reproducible. Beijing tests
non-independence; this tests choice sensitivity. Same coarse product, different
failure.

The geography is the reason it is a different failure. Hong Kong spans about
40 km against a 0.25-degree cell of roughly 28 km, so the territory falls
across six cells that straddle land, harbour and open sea; Beijing's network
sits inland on a plain. The land-sea contrast is what makes the cells disagree
by as much as they do in the afternoon.

**Measured over 2025** (8,760 hours, all six cells present in every one, no
missing BLH):

    largest simultaneous range across the six cells   1576.1 m
    on                                                2025-03-20
    median simultaneous range                          183.7 m
    mean                                               229.5 m

A 184 m median disagreement is the everyday state, not the tail. Classifying an
hour as low-boundary-layer below 500 m, the cell nearest King's Park calls 4,698
hours low and the six-cell mean calls 4,961, and they disagree on 545:

    nearest cell says low, six-cell mean does not     141 hours
    six-cell mean says low, nearest cell does not     404 hours

**The claim asks about reconcilability, not about direction, and an earlier
version confused the two.** It rejected any response saying one reading runs
systematically low or high — but that is simply true: the six-cell mean sits
below the nearest cell in 5,515 hours and above it in 3,243, mean difference
-13.185 m, median -10.300 m. Gate B round 5 found the live response penalised
for saying "tends to pull down", which is correct. What the counts do establish
is that no FIXED correction reconciles the two: `mean - nearest` spans -223.133
to +209.800 m, and the best constant threshold shift still misclassifies 486
hours. The claim now excludes a single additive correction and explicitly
permits the directional statement alongside it.

**Both directions matter, and the rebuilt turn scores that as a verdict.**
The totals alone (4,698 against 4,961) invite reading the difference as an
offset one method carries against the other, which an analyst could imagine
correcting. The 141 hours going the other way say it is not an offset: no
shift of either series reproduces the other, and `disagreement_is_a_fixed_offset`
is False for that reason.

**Convention sweep — four axes, 24 combinations, all computed.**
Only one axis moves the answer:

    aggregate  threshold  endpoint   nearest       near_only  mean_only
    mean       <          exclusive  great-circle        141        404  (the earlier pin)
    median     (any)      (any)      (any)               151        426
    area       (any)      (any)      (any)               141        404  identical

`aggregate` is how the six cells become one territory figure. The median reads
151 and 426; the earlier query pinned the mean, and the rebuilt verdicts hold
under both. Cosine-of-latitude area weighting is
reported here as measured-indifferent rather than assumed so: the six cells span
22.25-22.50 N, so their weights differ by 0.0003 and every scored output is
identical to the unweighted mean.

The other three axes are likewise identical, not merely within a band.
`threshold` open versus closed cannot matter because no six-cell mean and no
nearest-cell value in the year is exactly 500.0 (five grid-hours elsewhere are).
`endpoint` cannot matter because the hour at 2026-01-01 00:00 changes no maximum
and no count. `nearest` cannot matter because grid_22.25N_114.25E is closest to
King's Park by both great-circle distance (10.51 km against 19.07 for the
runner-up) and by degrees, with margin to spare.

**The date, not the hour, and the reason is a near miss.** The largest range
falls at 15:00 on 2025-03-20 at 1576.1 m, and the second largest is the
ADJACENT HOUR, 16:00 the same day, at 1574.9 m — 1.2 m behind, 0.08 %. Asking
for the timestamp would make the answer turn on that margin and would fail any
agent with an hour-labelling slip while telling us nothing about whether it
understood the grid. The date absorbs it: the three largest ranges all fall on
2025-03-20 and the next day back is 253 m further down. The date is matched
exactly, as a string; no tolerance applies, and the near miss it does have to
survive is the one just described, which it clears by a full day.

**Tolerances.** `max_blh_spread_m` uses `decimals=1`, deriving +/-0.06, which
is the precision the source carries — every BLH value in the file has one
decimal place. The second turn's two verdicts and its straddle share hold
under the mean and the median alike, so the aggregate no longer needs
pinning (see the rebuild note below).

Ground truth is recomputed from `datasets/HK/met_era5.csv` at validation time.

**ERA5 is model output.** `met_df`'s own description says so, and the corpus
hazard list forbids calling BLH an observed boundary layer height. The case is
written to respect that: what it measures is the spatial resolution of a
reanalysis product, not boundary layer variation anyone observed across Hong
Kong, and one of the claims requires the response to keep that distinction.

**Turn 2 rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier turn told the study to mark the hours twice — nearest cell and
all-cell mean — and report the disagreement in each direction; the two
counts (141 and 404) were the mean's, and the median's were 151 and 426.
The rebuilt turn asks what the product means for how the study should
report its stagnation hours, and scores three conclusions that hold under
every construction: the marked set depends on the cell choice (the nearest
cell disagrees with the mean on 545 hours and with the median on 577; no
two of the eight constructions agree within 160), the disagreement is not
a fixed offset (the best constant shift of the mean still misclassifies 486
hours), and the cells straddle the threshold on 39 % of hours — scored to
the nearest ten as 40.


**Gate A review 2026-09-06 defined "materially" on the variable.** The verdict
was computed as at least a hundred disagreeing hours, a threshold that appeared
nowhere the agent could read, and the word doing the work was "materially" — a
judgement about size that a competent analyst could resolve either way on 545
disagreeing hours out of 8,760. The threshold is now stated. It is a definition
of the word, which P4a's third remedy allows, and it does not say which side of
it the record falls on.
"""

from math import asin, cos, radians, sin, sqrt
from typing import Dict

import pandas as pd
from cave_agent import Variable

from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

_SPAN = ("2025-01-01", "2026-01-01")
_LOW_BLH_M = 500.0
# King's Park, Hong Kong's only upper-air station — the anchor the query names.
# Its own coordinates, as carried by `sounding_df`.
_KINGS_PARK = (22.3119, 114.1728)


def _cells() -> pd.DataFrame:
    """Hours x the six ERA5 cells, boundary layer height in metres."""
    met = pd.read_csv(
        DATA_DIR / "met_era5.csv",
        parse_dates=["datetime"], usecols=["datetime", "station", "blh_m"],
    )
    met = met[(met["datetime"] >= _SPAN[0]) & (met["datetime"] < _SPAN[1])]
    return met.pivot_table(index="datetime", columns="station", values="blh_m")


def _nearest_cell(columns) -> str:
    """The cell centre closest to King's Park, by great-circle distance.

    The centre is in the name: `grid_<lat>N_<lon>E`. The choice is invariant to
    the metric — measured, not assumed: by degrees the same cell wins, and
    either way the runner-up is 19.07 km out against 10.51.
    """
    def separation(name: str) -> float:
        _, lat, lon = name.split("_")
        lat1, lon1 = radians(_KINGS_PARK[0]), radians(_KINGS_PARK[1])
        lat2, lon2 = radians(float(lat[:-1])), radians(float(lon[:-1]))
        h = (sin((lat2 - lat1) / 2) ** 2
             + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2)
        return 2 * 6371.0088 * asin(sqrt(h))

    return min(columns, key=separation)


def _figures() -> Dict[str, object]:
    """The five scored quantities."""
    cells = _cells()
    spread = cells.max(axis=1) - cells.min(axis=1)
    nearest = cells[_nearest_cell(cells.columns)]
    low = {name: cells[name] < _LOW_BLH_M for name in cells.columns}
    low["mean"] = cells.mean(axis=1) < _LOW_BLH_M
    low["median"] = cells.median(axis=1) < _LOW_BLH_M
    near_low = nearest < _LOW_BLH_M
    # Every construction disagrees with every other on hundreds of hours
    # (the smallest pair, mean against median, on 162); the verdict asks for
    # at least a hundred against the nearest cell under both aggregates.
    disagreements = {name: int((near_low != flags).sum()) for name, flags in low.items()
                     if name in ("mean", "median")}
    # No constant shift of an aggregate reproduces the nearest cell's set.
    residual = {name: min(int(((series + shift < _LOW_BLH_M) != near_low).sum())
                          for shift in range(-300, 301))
                for name, series in (("mean", cells.mean(axis=1)), ("median", cells.median(axis=1)))}
    straddle = ((cells.min(axis=1) < _LOW_BLH_M) & (cells.max(axis=1) >= _LOW_BLH_M)).mean()
    return {
        "max_blh_spread_m": float(spread.max()),
        "max_blh_spread_date": str(spread.idxmax().date()),
        "marked_set_depends_on_cell_choice": bool(min(disagreements.values()) >= 100),
        "disagreement_is_a_fixed_offset": bool(max(residual.values()) == 0),
        "hours_cells_straddle_threshold_pct": int(10 * round(100 * straddle / 10)),
    }


def _not_an_integer(name: str, val) -> ValidatorResult:
    """A count must be an int; `bool` is excluded as an `int` subclass."""
    if val is None:
        return ValidatorResult(False, f"{name} not set", variables_not_set=True)
    if not isinstance(val, int) or isinstance(val, bool):
        return ValidatorResult(False, f"{name}={val!r} is not an integer")
    return None


def validate_grid_spread(response: str, runtime, turn: Turn) -> ValidatorResult:
    spread = runtime.retrieve("max_blh_spread_m")
    date = runtime.retrieve("max_blh_spread_date")
    if spread is None or date is None:
        missing = [n for n, v in (("max_blh_spread_m", spread),
                                  ("max_blh_spread_date", date)) if v is None]
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)
    if not is_finite_number(spread):
        return ValidatorResult(False, f"max_blh_spread_m={spread!r} is not a number")

    gt = _figures()
    wrong = []
    if not reports_as(spread, gt["max_blh_spread_m"], decimals=1):
        wrong.append(f"max_blh_spread_m={spread}, "
                     f"expected ~{gt['max_blh_spread_m']:.1f}")
    # A date, matched exactly as an ISO string; the near miss it survives is the
    # adjacent HOUR, which is why the hour is not what is asked for.
    if str(date).strip() != gt["max_blh_spread_date"]:
        wrong.append(f"max_blh_spread_date={date!r}, "
                     f"expected {gt['max_blh_spread_date']!r}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {spread} m on {gt['max_blh_spread_date']}")


def _normalise(value) -> str:
    return str(value).strip().lower()


def validate_stagnation_advice(
        response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "marked_set_depends_on_cell_choice": runtime.retrieve("marked_set_depends_on_cell_choice"),
        "disagreement_is_a_fixed_offset": runtime.retrieve("disagreement_is_a_fixed_offset"),
        "hours_cells_straddle_threshold_pct": runtime.retrieve("hours_cells_straddle_threshold_pct"),
    }
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    wrong = []
    for name in ["marked_set_depends_on_cell_choice", "disagreement_is_a_fixed_offset"]:
        val, expected = got[name], gt[name]
        if not ((isinstance(val, bool) and val == expected) or
                (isinstance(val, str) and _normalise(val) in
                 {str(expected).lower(), "yes" if expected else "no"})):
            wrong.append(f"{name}={val!r}, expected {expected}")
    pct = got["hours_cells_straddle_threshold_pct"]
    if not is_finite_number(pct) or int(10 * round(float(pct) / 10)) != gt["hours_cells_straddle_threshold_pct"]:
        wrong.append(f"hours_cells_straddle_threshold_pct={pct!r}, "
                     f"expected {gt['hours_cells_straddle_threshold_pct']}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


tools = []
variables = [
    Variable(
        "max_blh_spread_m",
        None,
        "Store the largest difference between the highest and lowest boundary "
        "layer height reported for the same hour across the reanalysis cells "
        "covering Hong Kong in 2025, as a float in metres to 1 decimal place.",
    ),
    Variable(
        "max_blh_spread_date",
        None,
        "Store the calendar date on which that largest difference occurs, as a "
        "string 'YYYY-MM-DD' in Hong Kong local time.",
    ),
    Variable(
        "marked_set_depends_on_cell_choice",
        None,
        "Store True if which hours of 2025 get marked as stagnant — boundary "
        "layer height strictly under 500 metres — depends on which cell, or "
        "which combination of cells, is taken to be Hong Kong, else False. "
        "Depends means the markings disagree on more than a hundred hours of "
        "the year.",
    ),
    Variable(
        "disagreement_is_a_fixed_offset",
        None,
        "Store True if the disagreement between the cell nearest King's Park "
        "and an all-cell figure could be removed by a constant correction to "
        "one of them, else False.",
    ),
    Variable(
        "hours_cells_straddle_threshold_pct",
        None,
        "Store the share of 2025's hours on which at least one cell is under "
        "500 metres and at least one is not, as a percentage to the nearest 10.",
    ),
]
validators = {
    "validate_grid_spread": validate_grid_spread,
    "validate_stagnation_advice": validate_stagnation_advice,
}
