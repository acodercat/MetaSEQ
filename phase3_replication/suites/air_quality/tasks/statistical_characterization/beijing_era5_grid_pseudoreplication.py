"""Beijing ERA5 meteorology — twelve records, five grid cells
(statistical_characterization).

Diagnostic TRAP. ERA5 is a 0.25 degree reanalysis and the twelve benchmark
stations do not fall in twelve distinct cells, so the "per-station" hourly
meteorology in this corpus is five distinct series wearing twelve labels:

- Aotizhongxin, Dongsi, Nongzhanguan, Tiantan share one
- Guanyuan, Gucheng, Wanliu, Wanshouxigong share one
- Changping and Dingling share one
- Huairou and Shunyi stand alone

The partition is fully explained by the ingest, and worth writing down because
the obvious shortcut reproduces the fact of duplication but not the grouping.
`scripts/ingest/fetch_era5.py` requests the box 39.8-40.5 N by 116.0-116.8 E and
takes the nearest node, so the available grid is latitudes 40.5/40.25/40.0 and
longitudes 116.0/116.25/116.5/116.75 — the 39.75 band falls outside the request.
Snapping the station coordinates to the nearest 0.25 multiple without that
constraint yields SEVEN groups, not five, because it sends Tiantan (39.8745 N)
and Wanshouxigong (39.8673 N) south to a row that was never downloaded. Both in
fact carry the meteorology of a cell centred 0.13 degrees to their north. An
agent cannot derive the grouping from the coordinates; it has to compare the
series.

The same reduction happens on the time axis, measured on this record: the
daily network-mean PM2.5 series of 2020-2025 carries a lag-1 autocorrelation of
0.624, which turns 2192 daily observations into 508 effective ones. This case
reduces twelve spatial records to five. A network's nominal size is not its
information content in either direction.

- Turn 1 (independent_met_series_2023, largest_shared_series_stations): 5 and 4.
- Turn 2 (two verdicts since 2026-09-02; the figures behind them): the
  largest gap falls on 2023-07-05 at -569.85 m2/s. Weighting the twelve station labels equally gives a daily mean
  ventilation coefficient of 4427.27 that day; weighting the five distinct
  series equally gives 4997.12. The station weighting is not a citywide average
  — it is an average over how many stations happen to sit in each grid cell, so
  the four-station cells count four times and Huairou once.

  The gap needs BOTH ingredients, which is why the claim asks for both. Unequal
  4/4/2/1/1 multiplicities acting on identical values would produce nothing; the
  five cells have to differ as well, and on this date they span 2933 m2/s. What
  the case denies is not that the cells differ — that is arithmetically
  necessary — but that twelve labelled rows are twelve independent readings of
  the atmosphere. The differing quantities are a model's cell values, and an
  earlier version of the claim conflated the two and could have penalised a
  response that got this exactly right.

The naive path is to treat the twelve rows per hour as twelve independent
meteorological observations: 12 on Turn 1, and the 4427.27 figure reported as
the city's daily ventilation on Turn 2. The runtime schema invites it — it
describes this table as "one row per station-hour" and says nothing about
duplication — but the trap is fair rather than hidden: the provenance manifest
records the product's native resolution as 0.25 degrees, which is the breadcrumb
an agent can follow before it computes anything, and `datasets/README.md`
already lists reanalysis-is-not-observation among the corpus hazards.

Why this day, and why the station weighting is low. On 2023-07-05 the five cells
run 3172, 4493, 5147, 6069 and 6105 m2/s — a 2933 spread, the 99.7th percentile
of daily spread that year against a median of 358. The two cells holding four
stations each are the two least ventilated, and the two best-ventilated cells
hold one station apiece, so weighting by station label pulls the citywide figure
down toward the stagnant west and centre. Across 2023 the size of the gap tracks
the spread between cells at r = 0.76, so this is the mechanism and not a
coincidence of one date. The runner-up, 2023-12-20 at +375.48, is a third
smaller and of the opposite sign, so there is no near-tie for the date to
arbitrate.

Tolerances.

- Turn 1 takes 0 on both counts, and the grouping is unusually robust: 4/4/2/1/1
  under all six meteorological fields jointly, under any single field alone,
  under rounding to 0 or 2 decimals, and in every year from 2020 to 2026. No
  convention moves it.
- Turn 2's date and gap were scored until 2026-09-02; the date was matched
  exactly, and no near-miss can arise: the largest
  magnitude is 569.85 and the runner-up 375.48, a margin of 194 m2/s, with
  exactly one date inside 1 m2/s of the maximum and no two dates tied to any
  precision. A tie-break would have nothing to break, so the query does not
  carry one. The gap value takes +/-0.01 m2/s, covering the 2-decimal reporting
  the variable asks for (0.005) and the 0.0002 difference between the stored
  hourly coefficient and a recomputed boundary-layer height times wind speed.

Two conventions were pinned in the earlier query because each moved the
scored gap outside any defensible band; the rebuilt verdicts hold under both.

- Absolute rather than signed maximisation. "The two figures differ most" reads
  either way, and the readings disagree completely: the largest MAGNITUDE is
  2023-07-05 at -569.85, the largest SIGNED value 2023-12-20 at +375.48. Both
  outputs change, so the query says "differ most in absolute size" and then asks
  for the signed gap on that date. The validator applied `abs().idxmax()`
  silently until Gate B caught it.
- The daily aggregation order. Taking the product of the day's mean height and
  the day's mean wind speed, rather than the mean of the hourly coefficients,
  gives -218.69 on 2023-07-05 and moves the largest gap to 2023-12-20 entirely.

Ground truth is recomputed here from the CSV.

**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier first turn told the agent to establish how many of the records
are distinct — the duplication was the reveal — and the second dictated the
two weightings and scored the date and size of the largest gap. The rebuilt
turns ask whether twelve records are twelve samples and whether their
average is a citywide figure; the counts stay (robust under every field and
rounding), the date and value go, and three verdicts are scored, the
material-difference one holding under both constructions of the day's
figure: the largest day's gap is 570 m2/s with the mean of hourly
coefficients and 332 with the day's mean height times its mean wind,
against a 100 m2/s line.


**Gate B round 21 (2026-09-03) removed `station_average_is_citywide`.** The
record proves the twelve labels are five series and that the choice of weights
moves the daily figure by hundreds of m2/s; it does not establish which
weighting is the correct citywide one, because no target — area, population,
airshed — is stated anywhere, and equal weight on five sampled ERA5 cells is
not a citywide average either. A label-weighted monitoring-network summary,
accurately labelled, is defensible and used to fail the bool. The counts and
the weighting-gap verdict stay; naming the target moved to the claims.
"""

import hashlib

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn

_YEAR = 2023
_MATERIAL_M2S = 100.0
_FIELDS = [
    "blh_m",
    "wind_speed_ms",
    "wind_dir_deg",
    "t2m_c",
    "surface_pressure_hpa",
    "ventilation_m2s",
]


def _met() -> pd.DataFrame:
    """The pinned year's hourly meteorology, tagged with its distinct series."""
    df = pd.read_csv(DATA_DIR / "met_era5.csv")
    df = df[df["year"] == _YEAR].copy()

    series = {}
    for station, group in df.groupby("station"):
        block = group.sort_values("datetime")[_FIELDS].to_numpy()
        series[station] = hashlib.md5(np.ascontiguousarray(block).tobytes()).hexdigest()
    df["series"] = df["station"].map(series)
    return df


def _counts() -> dict:
    df = _met()
    stations_per_series = df.groupby("series")["station"].nunique()
    return {
        "series": int(len(stations_per_series)),
        "largest": int(stations_per_series.max()),
    }


def _gap() -> dict:
    """Whether weighting by station label rather than by distinct series moves
    the citywide daily ventilation coefficient materially — asserted on two
    constructions of the day's figure (mean of hourly coefficients: largest
    gap 570 m2/s; the day's mean height times its mean wind: 332)."""
    df = _met()
    df["date"] = pd.to_datetime(df[["year", "month", "day"]])
    gaps = {}
    hourly = df.groupby("date")["ventilation_m2s"].mean()
    series = df.groupby(["date", "series"])["ventilation_m2s"].mean().groupby("date").mean()
    gaps["mean of hourly coefficients"] = float((hourly - series).abs().max())
    by_station = df.groupby("date")["blh_m"].mean() * df.groupby("date")["wind_speed_ms"].mean()
    by_series_frame = df.groupby(["date", "series"])[["blh_m", "wind_speed_ms"]].mean()
    by_series = (by_series_frame["blh_m"] * by_series_frame["wind_speed_ms"]).groupby("date").mean()
    gaps["mean height times mean wind"] = float((by_station - by_series).abs().max())
    verdicts = {g >= _MATERIAL_M2S for g in gaps.values()}
    if len(verdicts) != 1:
        raise RuntimeError(f"the weighting verdict is not invariant: {gaps}")
    return {"weighting_changes_the_figure_materially": verdicts.pop()}


def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_series_count(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "independent_met_series_2023": runtime.retrieve("independent_met_series_2023"),
        "largest_shared_series_stations": runtime.retrieve("largest_shared_series_stations"),
    }
    for name, val in got.items():
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")
    twelve = runtime.retrieve("twelve_independent_samples")
    if twelve is None:
        return ValidatorResult(False, "twelve_independent_samples not set", variables_not_set=True)
    gt = _counts()
    errors = []
    if not compare_numeric(got["independent_met_series_2023"], gt["series"], tolerance=0):
        errors.append(f"independent_met_series_2023={got['independent_met_series_2023']}, expected {gt['series']}")
    if not compare_numeric(got["largest_shared_series_stations"], gt["largest"], tolerance=0):
        errors.append(f"largest_shared_series_stations={got['largest_shared_series_stations']}, expected {gt['largest']}")
    if not _bool_ok(twelve, False):
        errors.append(f"twelve_independent_samples={twelve!r}, expected False")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: {gt['series']} distinct series, largest shared by {gt['largest']}; "
                                 "not twelve samples")


def validate_weighting_gap(response: str, runtime, turn: Turn) -> ValidatorResult:
    material = runtime.retrieve("weighting_changes_the_figure_materially")
    if material is None:
        return ValidatorResult(False, "weighting_changes_the_figure_materially not set",
                               variables_not_set=True)
    gt = _gap()
    expected = gt["weighting_changes_the_figure_materially"]
    if not _bool_ok(material, expected):
        return ValidatorResult(False,
                               f"weighting_changes_the_figure_materially={material!r}, expected {expected}")
    return ValidatorResult(True, "correct: which weights are used moves the figure materially")


tools = []
variables = [
    Variable("independent_met_series_2023", None,
             "Store the number of distinct hourly series found among the twelve "
             "station records for 2023, as an integer count of series (not of "
             "rows or hours)."),
    Variable("largest_shared_series_stations", None,
             "Store the number of stations sharing the single most widely shared "
             "series, as an integer."),
    Variable("twelve_independent_samples", None,
             "Store True if the twelve records can be treated as twelve "
             "independent samples of the city's meteorology, else False."),
    Variable("weighting_changes_the_figure_materially", None,
             "Store True if giving each distinct series equal weight, instead of "
             "each station record, moves the citywide daily ventilation "
             "coefficient by at least 100 m2/s on some day of 2023, else False."),
]
validators = {
    "validate_series_count": validate_series_count,
    "validate_weighting_gap": validate_weighting_gap,
}
