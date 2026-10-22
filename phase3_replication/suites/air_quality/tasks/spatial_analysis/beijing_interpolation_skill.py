"""Beijing 2023 — can eleven stations reconstruct the twelfth?
(spatial_analysis).

Cross-validation BASELINE, deliberately not a diagnostic trap: both operations
are stated and the content is the comparison between them. Leave-one-out is the
standard way to ask whether a monitoring network can fill its own gaps, and the
answer only means something against a comparator.

Hiding each station in turn and predicting its daily PM2.5 from the other
eleven, over the 281 days of 2023 on which all twelve report at least 20 valid
hours:

- idw_loo_mae: 3.18 ug/m3, weighting the eleven by inverse squared distance.
- equal_weight_loo_mae: 4.27, weighting them equally — a plain average of the
  rest of the network.

Distance weighting buys 1.09 ug/m3, a 25 % reduction. The comparator is the
point of the case: "mean absolute error 3.18" is a number with no scale
attached, and only the gap to a spatially blind predictor says whether the
geometry contributed anything. The same argument this corpus makes for
forecasts in `beijing_forecast_skill_floor` applies to interpolation.

A property worth recording because it is unusual here: this answer is EXACTLY
invariant to the Earth radius. Radii of 6367 and 6378.137 km give the same value,
because inverse-distance weights are ratios and the radius cancels out of them.
Every other spatial case in the corpus needs a band to absorb that choice; this
one does not, and the band it carries is for reporting precision alone.

Pins, each measured.

- The weighting POWER, which is load-bearing: power 1 gives 3.53 and power 3
  gives 3.04, so `idw_loo_mae` names the square.
- The DAY-COMPLETENESS RULE, and this pin was added after review. Requiring
  only that a station reported *something* admits station-days built on as few
  as 3 hourly observations — 104 of the 4128 station-days in that looser set
  carry under 20 hours — and a daily mean from 3 hours is not the same
  quantity as one from 24. Requiring 20 valid hours, the rule this corpus
  already uses in `beijing_compound_pollution_days`, leaves 281 days and reads
  3.1840 against the looser set's 3.2664. Predicting on every day with a
  pairwise-complete average is a third reading and also excluded.
- The year, the benchmark coordinates, and great-circle distance.

A design was rejected on measurement and is recorded so it is not retried:
scoring WHICH station is hardest to reconstruct. On this basis Huairou (5.584)
leads Dingling (5.383) by only 0.20; on the looser day rule Dingling leads by
0.050, and moving one hour across midnight was enough to swap the two there
(the label-date day put Huairou 0.045 ahead). An
identity that moves with the convention is not a P1-safe target, however
tempting the finding — that the
network's edges are its least redundant members — may be.

Tolerances: +/-0.01 on both figures, covering the 2-decimal reporting the
variables ask for. The band excludes the two alternative powers (3.53 and
3.04) and the looser day rule (3.27). The label-date day's 3.19 and 4.28 sit
inside it (0.006 and 0.009 away): one hour moved across each midnight changes
the answer by less than the reporting precision.

Observed live behaviour, recorded because it is what these anchors are for: in
three runs of one model against an earlier revision, two ended the turn after a single step of narration
without executing anything, leaving the variables unset; the third computed
both figures correctly. The failures this case collects are execution
discipline, not method — the same pattern seen on
`beijing_nocturnal_titration`.

Both ground truths are recomputed here from the CSVs.

**Query trimmed 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`):
"two ways: weighted by distance, and weighted equally" is gone; the query
asks for the reconstruction against a comparator that ignores geometry, and
the variables carry the two weightings as before.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_YEAR = 2023
_POWER = 2
_MIN_HOURS = 20
_R_EARTH_KM = 6371.0


def _haversine_km(lat1, lon1, lat2, lon2):
    p = np.pi / 180.0
    a = (
        np.sin((lat2 - lat1) * p / 2) ** 2
        + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    )
    return 2 * _R_EARTH_KM * np.arcsin(np.sqrt(a))


def _skill() -> dict:
    bj = DATA_DIR
    aq = pd.read_csv(bj / "air_quality.csv")
    st = pd.read_csv(bj / "station_metadata.csv", dtype={"station_code": "string"})
    # Hour h ends at h:00: a date's hours are its labels 1-23 and label 0 of
    # the next date, and 2023 runs to the 00:00 label of 1 January 2024.
    aq["date"] = (pd.to_datetime(aq[["year", "month", "day", "hour"]])
                  - pd.Timedelta(hours=1)).dt.normalize()

    coords = {r.station: (r.latitude, r.longitude) for r in st.itertuples()}
    year = aq[aq["date"].dt.year == _YEAR].dropna(subset=["PM2.5"])
    by_station_day = year.groupby(["date", "station"])["PM2.5"]
    daily = by_station_day.mean().unstack()
    hours = by_station_day.size().unstack()
    complete = daily.notna().all(axis=1) & (hours >= _MIN_HOURS).all(axis=1)
    wide = daily[complete]

    idw_errors, flat_errors = [], []
    for held_out in wide.columns:
        others = [s for s in wide.columns if s != held_out]
        distances = np.array(
            [_haversine_km(*coords[held_out], *coords[s]) for s in others]
        )
        weights = distances ** -_POWER
        weights /= weights.sum()
        observed = wide[held_out].to_numpy()
        neighbours = wide[others].to_numpy()
        idw_errors.append(np.abs(observed - neighbours @ weights).mean())
        flat_errors.append(np.abs(observed - neighbours.mean(axis=1)).mean())

    return {
        "idw": float(np.mean(idw_errors)),
        "flat": float(np.mean(flat_errors)),
    }


def validate_interpolation_skill(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = ("idw_loo_mae", "equal_weight_loo_mae")
    got = {}
    for name in names:
        val = runtime.retrieve(name)
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")
        got[name] = val

    gt = _skill()
    errors = [
        f"{name}={got[name]}, expected ~{gt[key]:.2f} ug/m3"
        for name, key in zip(names, ("idw", "flat"))
        if not reports_as(got[name], gt[key], decimals=2)
    ]
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True,
        f"correct: distance-weighted {gt['idw']:.2f}, "
        f"equal-weighted {gt['flat']:.2f} ug/m3",
    )


tools = []
variables = [
    Variable(
        "idw_loo_mae",
        None,
        "Store the distance-weighted mean absolute error as a float in ug/m3, "
        "2 decimal places. Use the days of 2023 on which every one of the "
        "twelve stations reports PM2.5 in at least 20 hours, each station's "
        "daily mean formed from the hours it reports. Weight the eleven "
        "predictors by the inverse square of their great-circle distance from "
        "the held-out site, on the benchmark-reproduction coordinates, and "
        "average the mean absolute error over the twelve held-out stations.",
    ),
    Variable(
        "equal_weight_loo_mae",
        None,
        "Store the equal-weighted mean absolute error as a float in ug/m3, "
        "2 decimal places — the same days, the same held-out stations, the "
        "eleven predictors weighted equally.",
    ),
]
validators = {"validate_interpolation_skill": validate_interpolation_skill}
