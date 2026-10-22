"""hk_inversion_convective_instability — hard baseline.

Decision: Decide whether an inversion flag alone supports an all-day stagnation or no-convection forecast.
Source concept: https://www.ncei.noaa.gov/pub/data/igra/igra2-product-description-supplement.pdf
Plausible wrong paths: Treating an inversion as excluding every negative Lifted Index, confusing inversion nulls with missing launches, or selecting an evening launch.

Raw-data values were frozen before authoring in
.codex-review/new_cases_20261006/frozen_answers.json.
Reported answers: {'li_valid_morning_launches': 2141, 'inversion_morning_launches': 449, 'negative_li_morning_launches': 943, 'inversion_negative_li_launches': 190, 'strongest_coexistence_launch': '2025-08-21 08:00:00', 'coexistence_lifted_index': -8.0, 'coexistence_inversion_strength_k': 0.2, 'coexistence_inversion_height_m': 38.0}

Each declared numeric precision rejects adjacent reported answers; all integer
counts use tolerance zero and finite-number guards. Runtime ground truth is
recomputed from the source files/database. No causal judgement is PV-scored.
The target is a named published metric or an identified reported observation.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

def _ground_truth():
    frame = pd.read_csv(DATA_DIR / "sounding_indices.csv",parse_dates=["datetime"])
    frame = frame[frame.datetime.ge("2020-01-01") & frame.datetime.lt("2026-01-01") & frame.hour.eq(8) & np.isfinite(frame.lifted_index)]
    inverted = frame.inversion_temp_diff_k.notna()
    negative = frame.lifted_index.lt(0)
    joint = frame[inverted & negative].sort_values(["lifted_index","datetime"])
    best = joint.iloc[0]
    return dict(li_valid_morning_launches=len(frame), inversion_morning_launches=int(inverted.sum()), negative_li_morning_launches=int(negative.sum()), inversion_negative_li_launches=len(joint), strongest_coexistence_launch=f"{best.datetime:%Y-%m-%d %H:%M:%S}", coexistence_lifted_index=float(best.lifted_index), coexistence_inversion_strength_k=float(best.inversion_temp_diff_k), coexistence_inversion_height_m=float(best.inversion_height_agl_m))


tools = []
variables = [
    Variable('li_valid_morning_launches', None, "Store the exact integer number of reported 08:00 local King's Park launches in 2020-2025 with a finite reported Lifted Index; this is the common cohort for all four launch counts."),
    Variable('inversion_morning_launches', None, 'Store the exact integer number of those launches reporting an elevated inversion. For this IGRA derived product, null inversion fields denote absence on a reported launch, while an absent launch is not an observed absence.'),
    Variable('negative_li_morning_launches', None, 'Store the exact integer number of those launches with reported Lifted Index strictly below zero.'),
    Variable('inversion_negative_li_launches', None, 'Store the exact integer number of those launches with both a reported elevated inversion and a strictly negative Lifted Index.'),
    Variable('strongest_coexistence_launch', None, 'Store the local launch timestamp, YYYY-MM-DD HH:MM:SS, with the smallest reported Lifted Index among the joint inversion/negative-index cohort. Break exact ties by earliest timestamp.'),
    Variable('coexistence_lifted_index', None, "Store that launch's reported Lifted Index, the environment-minus-lifted-parcel temperature contrast, in K to 1 decimal place."),
    Variable('coexistence_inversion_strength_k', None, "Store that same launch's reported elevated-inversion temperature contrast in K to 1 decimal place."),
    Variable('coexistence_inversion_height_m', None, "Store that same launch's reported inversion height in metres above the station to 1 decimal place; this is not height above sea level."),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "li_valid_morning_launches": runtime.retrieve("li_valid_morning_launches"),
        "inversion_morning_launches": runtime.retrieve("inversion_morning_launches"),
        "negative_li_morning_launches": runtime.retrieve("negative_li_morning_launches"),
        "inversion_negative_li_launches": runtime.retrieve("inversion_negative_li_launches"),
        "strongest_coexistence_launch": runtime.retrieve("strongest_coexistence_launch"),
        "coexistence_lifted_index": runtime.retrieve("coexistence_lifted_index"),
        "coexistence_inversion_strength_k": runtime.retrieve("coexistence_inversion_strength_k"),
        "coexistence_inversion_height_m": runtime.retrieve("coexistence_inversion_height_m"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    if not (is_finite_number(got["li_valid_morning_launches"]) and compare_numeric(got["li_valid_morning_launches"], expected["li_valid_morning_launches"], tolerance=0)):
        errors.append("li_valid_morning_launches="+repr(got["li_valid_morning_launches"])+", expected "+repr(expected["li_valid_morning_launches"]))
    if not (is_finite_number(got["inversion_morning_launches"]) and compare_numeric(got["inversion_morning_launches"], expected["inversion_morning_launches"], tolerance=0)):
        errors.append("inversion_morning_launches="+repr(got["inversion_morning_launches"])+", expected "+repr(expected["inversion_morning_launches"]))
    if not (is_finite_number(got["negative_li_morning_launches"]) and compare_numeric(got["negative_li_morning_launches"], expected["negative_li_morning_launches"], tolerance=0)):
        errors.append("negative_li_morning_launches="+repr(got["negative_li_morning_launches"])+", expected "+repr(expected["negative_li_morning_launches"]))
    if not (is_finite_number(got["inversion_negative_li_launches"]) and compare_numeric(got["inversion_negative_li_launches"], expected["inversion_negative_li_launches"], tolerance=0)):
        errors.append("inversion_negative_li_launches="+repr(got["inversion_negative_li_launches"])+", expected "+repr(expected["inversion_negative_li_launches"]))
    try:
        parsed = pd.Timestamp(got["strongest_coexistence_launch"])
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("Asia/Hong_Kong")
        valid = not pd.isna(parsed) and parsed.strftime("%Y-%m-%d %H:%M:%S") == expected["strongest_coexistence_launch"]
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not (valid):
        errors.append("strongest_coexistence_launch="+repr(got["strongest_coexistence_launch"])+", expected "+repr(expected["strongest_coexistence_launch"]))
    if not (is_finite_number(got["coexistence_lifted_index"]) and reports_as(got["coexistence_lifted_index"], expected["coexistence_lifted_index"], decimals=1)):
        errors.append("coexistence_lifted_index="+repr(got["coexistence_lifted_index"])+", expected "+repr(expected["coexistence_lifted_index"]))
    if not (is_finite_number(got["coexistence_inversion_strength_k"]) and reports_as(got["coexistence_inversion_strength_k"], expected["coexistence_inversion_strength_k"], decimals=1)):
        errors.append("coexistence_inversion_strength_k="+repr(got["coexistence_inversion_strength_k"])+", expected "+repr(expected["coexistence_inversion_strength_k"]))
    if not (is_finite_number(got["coexistence_inversion_height_m"]) and reports_as(got["coexistence_inversion_height_m"], expected["coexistence_inversion_height_m"], decimals=1)):
        errors.append("coexistence_inversion_height_m="+repr(got["coexistence_inversion_height_m"])+", expected "+repr(expected["coexistence_inversion_height_m"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
