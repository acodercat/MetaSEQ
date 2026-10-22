"""Hong Kong LUR: numerical fit, coefficient sensitivity and causal limits.

Execution baseline under the desk's explicit spatial specification. The design
is full rank (18 observations, 5 parameters); the industrial OLS coefficient is
estimable, but leave-one-station sensitivity and land-layer semantics limit its
interpretation. Neither sign stability nor cross-validation identifies a causal
industrial-emission effect. Descriptive estimates may be reported with limits;
there is no universal publication-permission boolean.

Frozen independent design/results: .codex-review/new_rules_fix_20261008/.
Industrial coefficient -0.265631; leave-one-out range [-0.631051, 0.279030];
Central reverses its sign. All three nearby INDUSTRIAL polygons are military.
Coefficients use 3 decimal places, fitted roadside coefficient whole units,
R-squared 1 decimal; counts exact. NIST influence diagnostics:
https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/regrdiag.htm
"""

from typing import Dict

import numpy as np
import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

_ROAD_CLASSES = ("motorway", "trunk", "primary", "secondary",
                 "motorway_link", "trunk_link", "primary_link", "secondary_link")
_SPAN = ("2025-01-01", "2026-01-01")
_TERMS = ("building", "road", "industrial", "roadside")

LAYER_INDUSTRIAL = "industrial"
LAYER_MILITARY = "military"
LAYER_MIXED = "mixed"


def _stations() -> pd.DataFrame:
    frame = read_frame(text(f"""
        with s as (select id, name_en, station_type, coordinate::geography as g
                   from air_quality_station)
        select s.id, s.name_en, s.station_type,
          coalesce((select sum(st_area(st_intersection(
                       o.geometry::geography, st_buffer(s.g, 500)::geography)::geography))
                    from osm_feature o
                    where o.main_type = 'BUILDING'
                      and o.geometry_type in ('POLYGON', 'MULTIPOLYGON')
                      and st_dwithin(o.geometry::geography, s.g, 500)), 0) as building_m2,
          coalesce((select sum(st_length(st_intersection(
                       o.geometry::geography, st_buffer(s.g, 500)::geography)::geography))
                    from osm_feature o
                    where o.main_type = 'ROAD' and o.geometry_type = 'LINESTRING'
                      and o.sub_type in {_ROAD_CLASSES}
                      and st_dwithin(o.geometry::geography, s.g, 500)), 0) as road_m,
          coalesce((select sum(st_area(st_intersection(
                       o.geometry::geography, st_buffer(s.g, 1000)::geography)::geography))
                    from osm_feature o
                    where o.main_type = 'INDUSTRIAL'
                      and o.geometry_type in ('POLYGON', 'MULTIPOLYGON')
                      and st_dwithin(o.geometry::geography, s.g, 1000)), 0) as industrial_m2
        from s
    """))
    response = read_frame(text("""
        select h.station_id as id, avg(h.no2) as no2
        from hourly_station_air_quality h
        where h.no2 is not null and h.datetime > :lo and h.datetime <= :hi
        group by h.station_id
    """), {"lo": _SPAN[0], "hi": _SPAN[1]})
    frame = frame.merge(response, on="id").sort_values("name_en").reset_index(drop=True)
    frame["roadside"] = (frame["station_type"] == "ROADSIDE").astype(float)
    return frame


def _design(frame: pd.DataFrame) -> np.ndarray:
    return np.column_stack([np.ones(len(frame)), frame["building_m2"] / 1e4,
                            frame["road_m"] / 1e3, frame["industrial_m2"] / 1e4,
                            frame["roadside"]])


def _fit(frame: pd.DataFrame) -> np.ndarray:
    return np.linalg.lstsq(_design(frame), frame["no2"].values, rcond=None)[0]




def _layer_near(station: str) -> Dict[str, int]:
    """Counts of the OSM INDUSTRIAL features within 1 km, by sub type."""
    frame = read_frame(text("""
        select o.sub_type, count(*) as n
        from osm_feature o, air_quality_station s
        where s.name_en = :station and o.main_type = 'INDUSTRIAL'
          and o.geometry_type in ('POLYGON', 'MULTIPOLYGON')
          and st_dwithin(o.geometry::geography, s.coordinate::geography, 1000)
        group by o.sub_type
    """), {"station": station})
    return dict(zip(frame["sub_type"], frame["n"]))




def _figures() -> Dict[str, object]:
    stations = _stations()
    beta = _fit(stations)
    refits = {}
    for position in range(len(stations)):
        rest = stations.drop(stations.index[position])
        refits[str(stations["name_en"].iloc[position])] = _fit(rest)

    # Which station decides the industrial sign: by sign flip on removal, and
    # by the largest absolute shift of the coefficient on removal. Both
    # readings must agree for the answer to be scorable.
    flips = [name for name, b in refits.items() if np.sign(b[3]) != np.sign(beta[3])]
    shifts = {name: abs(b[3] - beta[3]) for name, b in refits.items()}
    largest_shift = max(shifts, key=lambda k: shifts[k])
    if len(flips) != 1 or flips[0] != largest_shift:
        raise RuntimeError(f"the deciding station is not invariant: flips={flips}, "
                           f"largest shift={largest_shift}")
    deciding = flips[0]

    ranges = {}
    for index, term in enumerate(_TERMS, start=1):
        values = [b[index] for b in refits.values()]
        ranges[term] = (min(values), max(values))
    relative_width = {term: ((hi - lo) / abs(beta[i]) if beta[i] != 0 else float("inf")) for i, term in enumerate(_TERMS, start=1)
                      for lo, hi in [ranges[term]]}
    most_stable = min(relative_width, key=lambda k: (relative_width[k], k))

    kinds = _layer_near(deciding)
    military = kinds.get("military", 0)
    layer = (LAYER_MILITARY if military and military == sum(kinds.values())
             else LAYER_INDUSTRIAL if not military else LAYER_MIXED)

    residuals = stations["no2"].values - _design(stations) @ beta
    r2 = 1.0 - (residuals ** 2).sum() / ((stations["no2"] - stations["no2"].mean()) ** 2).sum()
    return {
        "coef_roadside_whole": float(beta[4]),
        "insample_r2_1dp": float(r2),
        "industrial_coefficient": float(beta[3]),
        "industrial_loo_min": float(ranges["industrial"][0]),
        "industrial_loo_max": float(ranges["industrial"][1]),
        "station_that_decides_the_industrial_sign": deciding,
        "most_stable_term": most_stable,
        "industrial_layer_near_that_station": layer,
        "industrial_polygons_near_station": int(sum(kinds.values())),
        # Validation folds cannot by themselves identify a causal source effect.
        "grouped_cv_would_fix_the_industrial_term": False,
    }


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
            decimals = (3 if name in {"industrial_coefficient", "industrial_loo_min", "industrial_loo_max"}
                        else 1 if name == "insample_r2_1dp" else 0)
            ok = is_finite_number(val) and reports_as(val, expected, decimals=decimals)
        elif isinstance(expected, int):
            ok = is_finite_number(val) and compare_numeric(val, expected, tolerance=0)
        else:
            ok = _normalise(val) == _normalise(expected)
        if not ok:
            errors.append(f"{name}={val!r}, expected {expected!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


def validate_model_fit(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "coef_roadside_whole": runtime.retrieve("coef_roadside_whole"),
        "insample_r2_1dp": runtime.retrieve("insample_r2_1dp"),
    })


def validate_sensitivity(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "industrial_coefficient": runtime.retrieve("industrial_coefficient"),
        "industrial_loo_min": runtime.retrieve("industrial_loo_min"),
        "industrial_loo_max": runtime.retrieve("industrial_loo_max"),
        "station_that_decides_the_industrial_sign": runtime.retrieve(
            "station_that_decides_the_industrial_sign"),
        "most_stable_term": runtime.retrieve("most_stable_term"),
    })


def validate_layer_and_diagnosis(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "industrial_layer_near_that_station": runtime.retrieve("industrial_layer_near_that_station"),
        "industrial_polygons_near_station": runtime.retrieve("industrial_polygons_near_station"),
        "grouped_cv_would_fix_the_industrial_term":
            runtime.retrieve("grouped_cv_would_fix_the_industrial_term"),
    })


_SPEC = (
    "The desk's specification: ordinary least squares with an intercept on the "
    "eighteen air-quality stations, one row each; the response is each "
    "station's 2025 annual mean NO2 (the domain's hour-ending year); the "
    "predictors are building area within 500 m in hectares (OSM features whose "
    "main type is BUILDING with polygon or multipolygon geometry, clipped to "
    "the circle), the length within 500 m in kilometres of OSM ROAD linestrings "
    "of sub type motorway, trunk, primary or secondary or any of their links "
    "(clipped), industrial-land area within 1 km in hectares (OSM INDUSTRIAL "
    "polygons, clipped), and an indicator that is 1 at the three roadside "
    "stations. Distances and areas are on the sphere (geography). "
)
tools = []
variables = [
    Variable("coef_roadside_whole", None,
             "Store the fitted coefficient on the roadside indicator, as a float "
             "in ug/m3 to the nearest whole ug/m3. " + _SPEC),
    Variable("insample_r2_1dp", None,
             "Store the model's in-sample R-squared, as a float, 1 decimal place."),
    Variable("industrial_coefficient", None,
             "Store the full-sample OLS industrial-area coefficient in µg/m³ per "
             "hectare to 3 decimal places under the desk's fixed specification."),
    Variable("industrial_loo_min", None,
             "Store the minimum industrial-area coefficient across eighteen OLS "
             "refits, removing exactly one station each time while retaining the "
             "same predictors and intercept, in µg/m³ per hectare to 3 decimal places."),
    Variable("industrial_loo_max", None,
             "Store the maximum industrial-area coefficient across those same "
             "refits, in µg/m³ per hectare to 3 decimal places."),
    Variable("station_that_decides_the_industrial_sign", None,
             "Store the name of the one station whose removal from the fit "
             "changes the sign of the industrial coefficient, as a string, or "
             "'none' if no single station changes it."),
    Variable("most_stable_term", None,
             "Store which of the four terms is the most stable across the "
             "eighteen leave-one-station-out refits: minimise coefficient range divided "
             "by the absolute full-sample coefficient, assigning infinite relative "
             "width to an exactly zero coefficient. Break exact ties alphabetically. "
             "Store one of exactly these "
             "strings: 'building', 'road', 'industrial', 'roadside'."),
    Variable("industrial_layer_near_that_station", None,
             "Store what the industrial layer actually contains within 1 km of "
             "that station, as one of exactly these strings: 'industrial', "
             "'military', 'mixed'."),
    Variable("industrial_polygons_near_station", None,
             "Store the exact integer count of INDUSTRIAL-tagged polygons or multipolygons "
             "intersecting the 1 km neighbourhood of the identified station, counted "
             "as source features, not fragments after clipping."),
    Variable("grouped_cv_would_fix_the_industrial_term", None,
             "Store True if moving to grouped cross-validation, with whole "
             "stations held out instead of individual rows, would by itself identify "
             "the industrial-area coefficient as a causal industrial-emission effect, "
             "else False."),
]
validators = {
    "validate_model_fit": validate_model_fit,
    "validate_sensitivity": validate_sensitivity,
    "validate_layer_and_diagnosis": validate_layer_and_diagnosis,
}
