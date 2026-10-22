"""Worst days a year later — regression to the mean (comparative_assessment).

The selection-bias classic, with a sign-flipping punchline in real data: the
twenty dirtiest days of 2022 averaged 112.1 ug/m3, and the same calendar dates
in 2023 averaged 35.5 — a 68 % "improvement". But 2023 was actually WORSE than
2022 overall (annual mean 30.5 -> 35.4, +16 %). Days selected for being extreme
are extreme mostly through transient weather, so their follow-ups fall back
toward typical levels no matter what the trend does. The mirror image proves
it: 2022's twenty cleanest days "worsened" by about +15 ug/m3, and running the
selection the other way (2023's worst days vs the same 2022 dates) shows a
+338 % "deterioration".

- Turn 1 (worst_days_change_pct): -68.3 %, scored to the nearest ten. Unique: no ties at the 20-day
  boundary (89.96 vs 88.97) and every matched 2023 date exists.
- Turn 2 (annual_change_pct): +16.1 %, scored to the nearest ten. A plausible cross-turn error: carrying the
  selected-days figure over. The claims carry the reasoning: the collapse on
  selected dates is a selection artifact, and the honest verdict is that air
  quality did not improve.

Tolerances, until 2026-09-02: +/-1.0 percentage point on the selected-days
change and +/-1.5 on the annual change. The two answers are 84
points apart and of opposite sign, so carrying one turn's figure into the other
cannot pass.

Both ground truths are recomputed here from the CSV.

THE AGGREGATION ORDER is pinned in the query, and this one is a FALSE
NEGATIVE rather than the usual loose band. Gate B measured the alternative —
averaging hourly network means before forming the day — at -66.3325 / +16.1689
against the pinned -69.0236 / +16.1343, on days read as the labels 0-23. The
first is 2.7 out and the band REJECTS it, so an agent taking a defensible reading of an unpinned query would
have failed. Tightening a band cannot fix that; naming the order can, and an
earlier revision of the query did. The surface-rule rebuild took the naming
back out and coarsened the scored figures to the nearest ten instead, which is
what carries the case now. On the hour-ending day (hours 1-23 and the next
date's hour 0) the two recipes nearly coincide, -68.30 / +16.14 pooled and
-68.23 / +16.19 with hourly means first, and the nearest-ten answers are the
same as on the labels.


**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier turns dictated the daily recipe to make a one-decimal figure
unique; the rebuilt turns ask how the worst days fared and what the annual
figures say, and score both changes to the nearest ten per cent (-70 and
+20 under both daily recipes) plus the verdict that the air did not
improve. The 84-point gap between the two figures, of opposite sign, is
what the claims are about.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn

_BASE_YEAR, _NEXT_YEAR, _N_DAYS = 2022, 2023, 20


def _daily(year: int, pooled: bool) -> pd.Series:
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Hour h is the hour ENDING at h:00: a day is its hours 1-23 and hour 0 of
    # the next date, and a year runs from 1 January 01:00 to the next 00:00.
    df["stamp"] = pd.to_datetime(df[["year", "month", "day", "hour"]])
    df["date"] = (df["stamp"] - pd.Timedelta(hours=1)).dt.normalize()
    year_rows = df[df["date"].dt.year == year]
    if pooled:
        return year_rows.groupby("date")["PM2.5"].mean()
    return year_rows.groupby(["date", "stamp"])["PM2.5"].mean().groupby(level=0).mean()


def _changes() -> dict:
    """Both changes to the nearest 10 per cent, asserted across the daily
    recipe (pooled -68.3 / +16.1; hourly means first -68.2 / +16.2)."""
    readings = set()
    for pooled in (True, False):
        base, following = _daily(_BASE_YEAR, pooled), _daily(_NEXT_YEAR, pooled)
        worst = base.nlargest(_N_DAYS)
        matched = [following[d + pd.DateOffset(years=1)] for d in worst.index]
        worst_change = (np.mean(matched) - worst.mean()) / worst.mean() * 100
        annual_change = (following.mean() - base.mean()) / base.mean() * 100
        readings.add((int(10 * round(worst_change / 10)), int(10 * round(annual_change / 10))))
    if len(readings) != 1:
        raise RuntimeError(f"a change is not invariant to the nearest ten per cent: {readings}")
    worst, annual = readings.pop()
    return {"worst": worst, "annual": annual, "improved": annual < 0}


def _nearest_ten(val) -> int:
    return int(10 * round(float(val) / 10))


def validate_worst_days_change(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("worst_days_change_pct")
    if val is None:
        return ValidatorResult(False, "worst_days_change_pct not set", variables_not_set=True)
    if not is_finite_number(val):
        return ValidatorResult(False, f"worst_days_change_pct={val!r} is not a number")
    gt = _changes()
    if _nearest_ten(val) == gt["worst"]:
        return ValidatorResult(True, f"correct: {val} ~ {gt['worst']} %")
    return ValidatorResult(False, f"worst_days_change_pct={val}, expected ~{gt['worst']} %")


def validate_annual_change(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("annual_change_pct")
    improved = runtime.retrieve("air_improved")
    missing = [n for n, v in (("annual_change_pct", val), ("air_improved", improved)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    if not is_finite_number(val):
        return ValidatorResult(False, f"annual_change_pct={val!r} is not a number")
    gt = _changes()
    errors = []
    if _nearest_ten(val) != gt["annual"]:
        errors.append(f"annual_change_pct={val}, expected ~{gt['annual']} %")
    ok = (isinstance(improved, bool) and improved == gt["improved"]) or (
        isinstance(improved, str) and improved.strip().lower() in {str(gt["improved"]).lower(), "yes" if gt["improved"] else "no"})
    if not ok:
        errors.append(f"air_improved={improved!r}, expected {gt['improved']}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: {val} ~ {gt['annual']} %; the air did not improve")


tools = []
variables = [
    Variable("worst_days_change_pct", None,
             "Store the percent change from the mean of the twenty days of 2022 "
             "with the highest daily PM2.5 to the mean of the same calendar "
             "dates in 2023, relative to the 2022 value, as a float to the "
             "nearest 10 (negative = lower in 2023)."),
    Variable("annual_change_pct", None,
             "Store the percent change in the annual mean PM2.5 from 2022 to "
             "2023 as a float to the nearest 10."),
    Variable("air_improved", None,
             "Store True if Beijing's annual mean PM2.5 decreased from 2022 to 2023, "
             "else False."),
]
validators = {
    "validate_worst_days_change": validate_worst_days_change,
    "validate_annual_change": validate_annual_change,
}
