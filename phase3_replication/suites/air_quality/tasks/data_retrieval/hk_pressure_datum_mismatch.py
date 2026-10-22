"""ERA5 is 4 hPa "low" against the Observatory, and the record proves the
offset is a datum rather than an error (data_retrieval).

BASELINE, hard, rebuilt 2026-09-01 on the surface rule
(`docs/query_surface_audit.md`): the query asks for a validation and a
decision, not for the statistics that make the decision; PV scores the
conclusions and the three numbers every defensible route reproduces.

**The situation.** A desk about to use ERA5 for Hong Kong validates its
surface pressure against the Observatory and finds it 4 hPa low with a
correlation of 0.999. The two reflex moves — reject the product, or fit a
bias correction — are both wrong, and the database holds the evidence on both
sides of the comparison. Neither datum is hidden: the domain prompt says the
weather table's pressure is at mean sea level, and the ERA5 column is named
`surface_pressure_hpa`. What the case tests is whether a response USES two
disclosed definitions instead of calling their difference a bias, and whether
it goes and gets the evidence.

**The reference route.** The ERA5 cell nearest the Observatory
(`grid_22.25N_114.25E`, 0.09 degrees away), 2025, 8,757 paired hours:

    Observatory mean sea level pressure     1012.87 hPa
    ERA5 cell surface pressure              1008.72
    mean difference (ERA5 - Observatory)       -4.154
    RMSE                                        4.168
    RMSE after removing the mean difference      0.335
    correlation                                 0.998790

**The evidence on both sides.**

*The observations are reduced to sea level.* Thirteen weather stations report
pressure, at altitudes from 4 m (Wetland Park) to 72 m (Cheung Chau). If
those were station-level readings, the hydrostatic gradient at 1013 hPa and
24.4 degrees (air density 1.186 kg/m3, 11.6 hPa per 100 m) would spread their
annual means by nearly 8 hPa. The actual spread is 0.85 hPa, from Sheung
Shui's 1012.56 to Tai Po's 1013.41, a regression of annual mean on altitude
gives -0.14 hPa per 100 m (one eighty-fifth of the hydrostatic slope), and
both extremes are low-lying stations while Cheung Chau at 72 m sits mid-pack.
There is no altitude signal in the observations at all.

*ERA5's cells are not reduced, and their offsets are terrain.* The same
comparison at each of the six cells:

    cell                    bias vs Observatory   implied height
    grid_22.25N_114.50E            -1.09 hPa            9 m
    grid_22.25N_114.25E            -4.15               36
    grid_22.25N_114.00E            -4.85               42
    grid_22.50N_114.50E            -5.83               50
    grid_22.50N_114.00E            -6.36               55
    grid_22.50N_114.25E            -8.89               77

Implied heights invert the hydrostatic relation on the two means,
h = (R T / g) ln(p_msl / p_sfc), with T the mean Observatory temperature over
the paired hours (297.52 K). The spread of the biases is 7.80 hPa across a
28 km grid, ordered as the terrain is: open sea to the south-east, the New
Territories hills at 22.50N 114.25E. A model bias cannot depend on which cell
you compare against a fixed station; a height difference must. That kills the
bias-correction move too: a correction fitted at one cell is wrong by up to
7.8 hPa at another. ERA5's own orography was not ingested, so the implied
heights are inferred and cannot be checked against the model's terrain here;
saying what would check them is part of what the claims ask for.

*Levels are corrupted; differences survive.* The offset is nearly constant:
4.23 hPa in January, 4.13 in July, across a 19 hPa seasonal swing (January
minus July is 19.26 on the Observatory and 19.15 on ERA5). A pressure LEVEL
taken from this product is 4 hPa wrong; a difference, anomaly or gradient is
good to a tenth of a hPa at a cell; a gradient between cells is not, because
the offset differs by cell.

**What survives every route.** The pairing can be done four ways an analyst
might choose — the domain's hour-ending year, the calendar year, ERA5's
instantaneous value matched to the hour it starts rather than ends, or the
reverse — and `_routes()` recomputes the scored conclusions under all four at
validation time:

    offset at the nearest cell, whole hPa      -4 under every pairing
    (-4.154, -4.154, -4.154, -4.155)
    tracks the hour-to-hour variability        residual 0.34 to 0.73 hPa,
                                               correlation 0.994 to 0.999
    most-negative cell                         grid_22.50N_114.25E, every route
    spread across the six cells, whole hPa     8 (7.80), every route
    January and July offsets agree to 1 hPa    4.2 / 4.1 under every route

    NOT scored: the residual RMSE and correlation to any precision (they move
    with the pairing), the per-cell implied heights (they depend on which
    temperature is used and cannot be verified against the model), the
    station-altitude slope (a regression whose exact value depends on the
    station set).

**What the earlier version scored, and why it is gone.** Eighteen numbers,
with the query naming the de-meaned RMSE (the very statistic that separates a
datum from a bias), the station-altitude regression, the six-cell spread and
the hydrostatic inversion — the whole argument, dictated. Two Gate C runs
reproduced all eighteen once the month convention was pinned
(`gate_c_hk_pressure_datum_mismatch.md`); they had been told what to compute.

**Measured and NOT used.** The offset should depend slightly on temperature
(rho g h, and rho falls as air warms): across temperature quartiles it reads
4.170, 4.181, 4.133, 4.131 hPa — the right direction, an order of magnitude
too small to serve as a test, and swamped by the seasonal cycle of sea-level
pressure itself.

**Overlap, stated.** `hk_era5_grid_choice_instability` uses the same six cells
but asks which one you call Hong Kong and measures boundary-layer height's
sensitivity to that choice; here the six cells are the instrument that
identifies a datum. `beijing_below_ground_level` is pressure-level reanalysis
extrapolated beneath the terrain — the same family of vertical-semantics
defect, in a different product and direction.
`hk_ozone_and_pm_episode_meteorology` scores Observatory pressure LEVELS on
episode days, which is precisely the analysis this case says ERA5 cannot be
substituted into.

All ground truths are recomputed from the database and `met_era5.csv` at
validation time, under four pairings at once.

**Gate C on the rebuilt case (2026-09-02, `gate_c_t1`) found two pins
missing.** The flash model described the terrain-height mechanism correctly
and still labelled the offset 'model bias' and recommended one flat
correction; the three strings had carried no meanings, so the boundary
between a datum and a bias was the model's to draw. The pro model stored
`differences_usable` False because the variable said "differences,
anomalies and gradients" and cell-to-cell gradients are indeed unusable
as they stand (the offsets differ by 8 hPa across the six cells) — a
correct answer to the question the variable asked. Both variables now say
what they mean: the enums carry their definitions, and the usability
verdict is about changes over time and anomalies at a given cell.


**Gate B round 21 (2026-09-03) struck one sentence from the terrain claim.**
It required the response to infer "that a model bias cannot depend on which
cell you compare against a fixed station", and that is false as stated: model
error can vary from grid cell to grid cell, and each remote cell is being
compared with one fixed station, so real horizontal pressure gradients enter
the contrast as well. The ingested extract carries no orography or geopotential
with which to check the implied heights. The claim now asks for what the spread
does establish — that no single flat correction can serve — with terrain as the
leading explanation rather than a proof. The recommendation is unaffected: the
two products are different quantities by definition, which is settled by the
documentation and not by the cell spread.


**Gate A review 2026-09-06 defined "closely enough to use" on the variable.**
The verdict was computed as a residual under 1 hPa and a correlation above
0.99, neither of which appeared on any surface, and the phrase left the analyst
to supply a threshold of their own. The residual criterion is now stated. The
margin is wide — the measured residual is 0.335 hPa and the correlation
0.998790,
so no defensible reading was flipping it — but a scored word that the agent
cannot resolve is a defect whether or not it changes an answer.
"""

import math
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, is_finite_number, reports_as
from domains.hk.db import read_frame

_STATION = "HK Observatory"
_OBSERVATORY = (22.301944, 114.174167)

KIND_DATUM = "datum difference"
KIND_BIAS = "model bias"
KIND_ERROR = "data error"
REC_DROP = "drop the product"
REC_CORRECT = "apply one correction"
REC_CONVERT = "convert the datum"


def _observatory() -> pd.DataFrame:
    frame = read_frame(text("""
        select h.datetime, h.pressure, h.temperature
        from hourly_station_weather h
        join weather_station s on s.id = h.station_id
        where s.name_en = :station
          and h.datetime > '2024-12-31' and h.datetime <= '2026-01-02'
    """), {"station": _STATION})
    return frame.set_index("datetime")


def _era5() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "met_era5.csv",
                       parse_dates=["datetime"])


def _nearest_cell(cells) -> str:
    """The cell centre closest to the Observatory, from the grid_<lat>N_<lon>E name."""
    lat0, lon0 = _OBSERVATORY
    best, best_d = None, None
    for name in cells:
        lat, lon = name.replace("grid_", "").replace("E", "").split("N_")
        d = math.hypot(float(lat) - lat0, (float(lon) - lon0) * math.cos(math.radians(lat0)))
        if best_d is None or d < best_d:
            best, best_d = name, d
    return best


def _routes() -> List[Tuple[str, str, str, int]]:
    """Four pairings an analyst might choose: (name, lo, hi, ERA5 stamp shift)."""
    return [
        ("hour-ending year", "2025-01-01 00:00", "2026-01-01 00:00", 0),
        ("calendar year", "2024-12-31 23:59", "2025-12-31 23:00", 0),
        ("ERA5 taken as the hour it starts", "2025-01-01 00:00", "2026-01-01 00:00", 1),
        ("ERA5 taken an hour early", "2025-01-01 00:00", "2026-01-01 00:00", -1),
    ]


def _paired(era: pd.DataFrame, obs: pd.DataFrame, cell: str,
            lo: str, hi: str, shift: int) -> pd.DataFrame:
    series = era[era["station"] == cell].set_index("datetime")[["surface_pressure_hpa"]]
    if shift:
        series.index = series.index + pd.Timedelta(hours=shift)
    joined = series.join(obs, how="inner").dropna()
    return joined[(joined.index > pd.Timestamp(lo)) & (joined.index <= pd.Timestamp(hi))]


def _conclusions(era: pd.DataFrame, obs: pd.DataFrame, cell: str,
                 lo: str, hi: str, shift: int) -> Dict[str, object]:
    frame = _paired(era, obs, cell, lo, hi, shift)
    difference = frame["surface_pressure_hpa"] - frame["pressure"]
    offset = float(difference.mean())
    residual = float(np.sqrt(((difference - offset) ** 2).mean()))
    correlation = float(frame["surface_pressure_hpa"].corr(frame["pressure"]))
    biases = {}
    for name in sorted(era["station"].unique()):
        sub = _paired(era, obs, name, lo, hi, shift)
        biases[name] = float((sub["surface_pressure_hpa"] - sub["pressure"]).mean())
    most_negative = min(biases, key=lambda k: biases[k])
    spread = max(biases.values()) - min(biases.values())
    month = (frame.index - pd.Timedelta(hours=1)).month
    jan = float((frame["pressure"] - frame["surface_pressure_hpa"])[month == 1].mean())
    jul = float((frame["pressure"] - frame["surface_pressure_hpa"])[month == 7].mean())
    # A constant offset with the variability intact is a datum; scatter with
    # no offset would be error; an offset that varied with the level or the
    # cell in no physical pattern would be bias. The cell spread is the tell.
    if residual < 1.0 and correlation > 0.99 and spread > 3.0:
        kind = KIND_DATUM
    elif residual >= 1.0:
        kind = KIND_ERROR
    else:
        kind = KIND_BIAS
    return {
        "offset_nearest_cell_hpa": offset,
        "offset_kind": kind,
        "tracks_variability": bool(residual < 1.0 and correlation > 0.99),
        "recommendation": REC_CONVERT if kind == KIND_DATUM else REC_DROP,
        "most_negative_offset_cell": most_negative,
        "offset_spread_across_cells_hpa": float(spread),
        "levels_usable_as_they_are": bool(abs(offset) < 0.5),
        "differences_usable": bool(abs(jan - jul) < 1.0 and residual < 1.0),
    }


def _figures() -> Dict[str, object]:
    """The scored conclusions, refused if the four pairings disagree on any."""
    era, obs = _era5(), _observatory()
    cell = _nearest_cell(sorted(era["station"].unique()))
    table = [(name, _conclusions(era, obs, cell, lo, hi, shift))
             for name, lo, hi, shift in _routes()]
    out: Dict[str, object] = {}
    for key in table[0][1]:
        values = [row[key] for _, row in table]
        if isinstance(values[0], float):
            reports = {round(v) for v in values}         # scored to whole hPa
            if len(reports) != 1:
                raise RuntimeError(f"{key} is not invariant to whole hPa across pairings: "
                                   + "; ".join(f"{n}={v:.3f}" for n, v in zip([t[0] for t in table], values)))
            out[key] = values[0]
        else:
            if len(set(values)) != 1:
                raise RuntimeError(f"{key} is not invariant across pairings: "
                                   + "; ".join(f"{n}={v!r}" for n, v in zip([t[0] for t in table], values)))
            out[key] = values[0]
    return out


def _normalise(value) -> str:
    return str(value).strip().lower().replace("_", " ")


def _check(got: Dict[str, object]) -> ValidatorResult:
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    for name, val in got.items():
        expected = gt[name]
        if isinstance(expected, bool):
            ok = (isinstance(val, bool) and val == expected) or (
                isinstance(val, str) and _normalise(val) in {str(expected).lower(),
                                                              "yes" if expected else "no"})
        elif isinstance(expected, float):
            ok = is_finite_number(val) and reports_as(val, expected, decimals=0)
        else:
            ok = _normalise(val) == _normalise(expected)
        if not ok:
            shown = f"{expected:.0f}" if isinstance(expected, float) else repr(expected)
            errors.append(f"{name}={val!r}, expected {shown}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(
        f"{n}={gt[n]:.0f}" if isinstance(gt[n], float) else f"{n}={gt[n]!r}" for n in got))


def validate_validation(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "offset_nearest_cell_hpa": runtime.retrieve("offset_nearest_cell_hpa"),
        "offset_kind": runtime.retrieve("offset_kind"),
        "tracks_variability": runtime.retrieve("tracks_variability"),
    })


def validate_decision(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "recommendation": runtime.retrieve("recommendation"),
        "most_negative_offset_cell": runtime.retrieve("most_negative_offset_cell"),
        "offset_spread_across_cells_hpa": runtime.retrieve("offset_spread_across_cells_hpa"),
    })


def validate_usability(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "levels_usable_as_they_are": runtime.retrieve("levels_usable_as_they_are"),
        "differences_usable": runtime.retrieve("differences_usable"),
    })


tools = []
variables = [
    Variable("offset_nearest_cell_hpa", None,
             "Store the mean of ERA5 surface pressure minus the Observatory's "
             "pressure over the 2025 hours you paired, for the ERA5 cell whose "
             "centre lies nearest the HK Observatory station, as a float in hPa "
             "to the nearest whole hPa (negative if ERA5 is lower)."),
    Variable("offset_kind", None,
             "Store what that offset is, as one of exactly these strings: 'datum "
             "difference' (the two series report pressure at different reference "
             "levels, so they are not the same quantity), 'model bias' (the same "
             "quantity at the same reference level, with a systematic error in "
             "the model), 'data error' (a fault in one record)."),
    Variable("tracks_variability", None,
             "Store True if, once the mean offset is set aside, the ERA5 series "
             "follows the Observatory's hour-to-hour variation closely enough to "
             "use, else False. Closely enough means both of these: the two "
             "have root-mean-square disagreement below one hectopascal once the constant difference "
             "is removed, and they correlate above 0.99."),
    Variable("recommendation", None,
             "Store what the desk should do, as one of exactly these strings: "
             "'drop the product', 'apply one correction' (one flat adjustment to "
             "the field), 'convert the datum' (bring the field onto the "
             "instruments' reference level, cell by cell, or take the product "
             "that is already on it)."),
    Variable("most_negative_offset_cell", None,
             "Store the name of the ERA5 cell whose mean difference from the "
             "Observatory is the most negative, as the string `met_df` uses for it."),
    Variable("offset_spread_across_cells_hpa", None,
             "Store the least negative minus the most negative of the six cells' "
             "mean differences from the Observatory, as a float in hPa to the "
             "nearest whole hPa."),
    Variable("levels_usable_as_they_are", None,
             "Store True if an absolute pressure level taken from this ERA5 field "
             "can be compared directly with Hong Kong sea-level pressure observations without converting its datum, else False."),
    Variable("differences_usable", None,
             "Store True if changes over time and anomalies taken from this "
             "field at a given cell meet the nearest-cell variability criterion defined above without converting its datum, else "
             "False."),
]


def validate_evidence_and_conclusion_full_review(response: str, runtime, turn: Turn) -> ValidatorResult:
    values = {
        'recommendation': runtime.retrieve("recommendation"),
        'most_negative_offset_cell': runtime.retrieve("most_negative_offset_cell"),
        'offset_spread_across_cells_hpa': runtime.retrieve("offset_spread_across_cells_hpa"),
        'levels_usable_as_they_are': runtime.retrieve("levels_usable_as_they_are"),
        'differences_usable': runtime.retrieve("differences_usable"),
    }
    missing = [name for name, value in values.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    result = validate_decision(response, runtime, turn)
    if not result.success:
        return result
    result = validate_usability(response, runtime, turn)
    if not result.success:
        return result
    return ValidatorResult(True, "computed evidence and conclusion accepted")

validators = {
    "validate_validation": validate_validation,
    "validate_decision": validate_decision,
    "validate_usability": validate_usability,
    'validate_evidence_and_conclusion_full_review': validate_evidence_and_conclusion_full_review,
}
