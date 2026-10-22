"""Typed, precision-aware checks for scalar evidence and exact launch sets.

Copied from AirBench `evals/_shared/scientific_outputs.py`; the only change is that it
imports the lab's `validation` module. Task modules import it as
`domains.scientific_outputs`; agents cannot import `domains`.
"""

import math

import pandas as pd

from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise ValueError("missing timestamp")
    if stamp.tzinfo is not None:
        stamp = stamp.tz_convert("Asia/Hong_Kong").tz_localize(None)
    return stamp


def check_evidence(runtime, ground_truth, formats):
    """Recompute GT only after checking that every required output is set.

    Integer format values mean decimal places. 'sig4' means four significant
    figures of the nonzero GT, never a fixed absolute error on a tiny rate.
    Timestamp lists are order-insensitive; missing/extra/duplicate events fail.
    """
    got = {name: runtime.retrieve(name) for name in formats}
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    expected = ground_truth()
    errors = []
    for name, kind in formats.items():
        value, truth = got[name], expected[name]
        try:
            if kind == "count":
                valid = compare_numeric(value, truth, tolerance=0)
            elif kind == "identity":
                valid = isinstance(value, str) and value.strip() == truth
            elif kind == "timestamp":
                valid = _timestamp(value) == _timestamp(truth)
            elif kind == "timestamp_set":
                valid = isinstance(value, list) and len(value) == len(truth)
                if valid:
                    stamps = [_timestamp(v) for v in value]
                    valid = len(set(stamps)) == len(stamps) and set(stamps) == {
                        _timestamp(v) for v in truth}
            elif kind == "sig4":
                places = 3 - math.floor(math.log10(abs(truth)))
                valid = is_finite_number(value) and reports_as(value, truth, decimals=places)
            else:
                valid = reports_as(value, truth, decimals=kind)
        except (TypeError, ValueError, OverflowError):
            valid = False
        if not valid:
            errors.append(f"{name}={value!r}, expected {truth!r}")
    return ValidatorResult(not errors,
                           "; ".join(errors) if errors else "all objective evidence accepted")
