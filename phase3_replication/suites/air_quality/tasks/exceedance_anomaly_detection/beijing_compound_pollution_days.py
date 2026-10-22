"""Compound O3 + PM2.5 exceedance — independence fails (exceedance_anomaly_detection).

Compound-event methodology on real data: Beijing exceeded the Grade II ozone
basis (HJ 663 windows) on 52 days of 2023 and the 24-hour PM2.5 limit on 39
days, so an independence estimate predicts 52 x 39 / 365 = 5.6 joint days. The
record holds exactly ONE (30 March 2023, where spring-dust PM met early-season
photochemistry). Ozone peaks in the warm months and fine particles in the cold
and dusty ones, so the two hazards are seasonally segregated and multiplying
marginal frequencies overstates compound risk more than five-fold — the central lesson of
the compound-events literature.

- Turn 1: the two marginal counts, 52 and 39. Unique.
- Turn 2 (compound_days): 1. The nearest wrong path is ~5.6 — an agent that
  ESTIMATES the joint count from the product of frequencies instead of counting
  actual co-occurrence.

Tolerance 0 throughout. All three are small integers over a fully pinned
recipe — the query names HJ 663-2013, both thresholds, and "every day of the
year whatever number of hours it reports" — so nothing is left to vary. The
joint count also stays exactly 1 under +/-2 ug/m3 shifts of either threshold.

Both daily figures sit on HJ 663-2013's natural day, which A.1 stamps 1:00 to
24:00. The record's hour h is the hour ending at h:00, so label 0 is the
previous date's 24:00; the shared MDA8 helper already owns the 00:00 window to
the previous date, so the PM2.5 day mean takes a date's labels 1-23 and label 0
of the next. Grouping each date's labels 0-23 instead counts 40 PM2.5 days
rather than 39 (2 April and 22 November in, 5 February out) and leaves the
ozone and joint counts unchanged. The domain prompt's TIMESTAMPS block states
what the labels mean.

An earlier version carried +/-3 on the marginals and justified it as covering
"movement by at most 5", which is incoherent on its face: three cannot cover
five. The 5 came from day-completeness rules the query already rules out (a
24-hour requirement drops PM2.5 from 39 to 33). Gate B caught the contradiction.

Both ground truths are recomputed here from the CSV.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn
from domains.beijing.mda8 import frame_to_mda8

_CITY, _YEAR = "北京", 2023
_O3_LIMIT, _PM_LIMIT = 160.0, 75.0


def _counts() -> dict:
    cities = pd.read_csv(DATA_DIR / "region_cities.csv")
    # HJ 663-2013 A.1: a natural day runs 1:00-24:00, and label h is the hour
    # ending at h:00, so label 0 is the previous date's 24:00. Selecting and
    # grouping on that day puts the 24-hour means on the same day the ozone
    # windows are owned by, and gives 31 December its 24:00 window.
    ts = pd.to_datetime(cities[["year", "month", "day", "hour"]])
    natural = (ts - pd.Timedelta(hours=1)).dt.normalize()
    keep = (cities["city"] == _CITY) & (natural.dt.year == _YEAR)
    sel = cities[keep]
    by_day = sel.groupby([natural[keep].dt.month, natural[keep].dt.day])
    mda8 = frame_to_mda8(sel)
    mda8 = mda8[mda8.index.year == _YEAR]
    o3 = pd.Series(mda8.to_numpy(), index=[(t.month, t.day) for t in mda8.index])
    pm = by_day["PM2.5"].mean()
    o3_days = set(o3[o3 > _O3_LIMIT].index)
    pm_days = set(pm[pm > _PM_LIMIT].index)
    return {
        "o3": len(o3_days),
        "pm": len(pm_days),
        "joint": len(o3_days & pm_days),
    }


def validate_marginal_days(response: str, runtime, turn: Turn) -> ValidatorResult:
    vals = {}
    for name in ("o3_exceedance_days_2023", "pm25_exceedance_days_2023"):
        v = runtime.retrieve(name)
        if v is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(v):
            return ValidatorResult(False, f"{name}={v!r} is not a number")
        vals[name] = v

    gt = _counts()
    errors = []
    if not compare_numeric(vals["o3_exceedance_days_2023"], gt["o3"], tolerance=0):
        errors.append(f"o3_exceedance_days_2023={vals['o3_exceedance_days_2023']}, expected ~{gt['o3']}")
    if not compare_numeric(vals["pm25_exceedance_days_2023"], gt["pm"], tolerance=0):
        errors.append(f"pm25_exceedance_days_2023={vals['pm25_exceedance_days_2023']}, expected ~{gt['pm']}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: {gt['o3']} ozone days, {gt['pm']} PM2.5 days")


def validate_compound_days(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("compound_days")
    if val is None:
        return ValidatorResult(False, "compound_days not set", variables_not_set=True)
    if not is_finite_number(val):
        return ValidatorResult(False, f"compound_days={val!r} is not a number")

    gt = _counts()

    # Cross-turn consistency (standard R5): a day in the joint count is by
    # definition in both marginal counts, so the stored compound_days can
    # never exceed the smaller of turn 1's stored marginals. Checked against
    # the model's OWN turn-1 values, not the ground truth, because the point
    # is internal coherence: discovery round 1 found a model answering two
    # turns of one case from two different records.
    o3_days = runtime.retrieve("o3_exceedance_days_2023")
    pm_days = runtime.retrieve("pm25_exceedance_days_2023")
    if is_finite_number(o3_days) and is_finite_number(pm_days):
        ceiling = min(o3_days, pm_days)
        if val > ceiling:
            return ValidatorResult(
                False,
                f"inconsistent with turn 1: compound_days={val} exceeds the "
                f"smaller marginal it must be contained in ({ceiling})",
            )

    if compare_numeric(val, gt["joint"], tolerance=0):
        return ValidatorResult(True, f"correct: {val} joint day(s)")
    return ValidatorResult(
        False, f"compound_days={val}, expected {gt['joint']}"
    )


tools = []
variables = [
    Variable(
        "o3_exceedance_days_2023",
        None,
        "Store the number of 2023 days whose daily maximum 8-hour ozone "
        "exceeded the limit, as an integer. " "A day's maximum 8-hour ozone is the largest of the 8-hour "
        "running means whose window ENDS between 08:00 and 24:00 of that "
        "day, per HJ 663-2013.",
    ),
    Variable(
        "pm25_exceedance_days_2023",
        None,
        "Store the number of 2023 days whose daily mean PM2.5 exceeded the limit, "
        "as an integer.",
    ),
    Variable(
        "compound_days",
        None,
        "Store the number of 2023 days on which both limits were exceeded, as an "
        "integer.",
    ),
]
validators = {
    "validate_marginal_days": validate_marginal_days,
    "validate_compound_days": validate_compound_days,
}
