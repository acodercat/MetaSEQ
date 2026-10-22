"""Beijing PM2.5 — complete-case filtering is not the conservative choice
(data_retrieval).

Diagnostic TRAP. Restricting a network series to the hours when every station
reported feels like the careful option: no station composition changes, no
apples-to-oranges comparison across hours. What the case shows is that the
restriction cannot be assumed to move an estimate in any known direction — the
hours it discards are not missing at random, and the selection does not even
lean the same way from one year to the next.

Measured, not assumed: within 2020 the number of reporting stations correlates
+0.116 with the hour's network PM2.5, and within 2024 it correlates -0.115. The
1747 incomplete hours of 2020 averaged 26.4 ug/m3 against 40.6 for the complete
ones, so dropping them raised the annual figure; the 2095 incomplete hours of
2024 averaged 37.4 against 30.3, so dropping them lowered it. Why the sign flips
is not something this data settles — outage timing, maintenance schedules and
episode coincidence are all candidates and none is recorded here.

What the case must NOT claim, and an earlier version of its required claim did.
Bias is distance from an unobserved truth, and this data holds no counterfactual
for the hours that went missing, so nothing here can say which of the two
estimates is the more accurate. A correction can legitimately push up in one
sample and down in another. The supported conclusion is narrower and still
sufficient: unstable IMPACT means the filter cannot be treated as a conservative
default, which is exactly how it is usually treated. Gate B caught the
over-reach.

- Turn 1 (the direction each year): +2.86 and -1.71 ug/m3 on hourly network
  means. Across 2020 to 2024 the full series runs +2.861, -0.429, +0.288,
  +0.955, -1.713 — the filter raises the annual mean in three years and lowers
  it in two, so it has no fixed direction to correct for.
- Turn 2 (complete_hours_2024, complete_hours_2025): 6585 and 0. By 2025 the
  filter leaves nothing at all. Gucheng reports 134 hours that year, Dingling
  2331 and Shunyi 6925, against 8337 to 8438 for the other nine, so no hour of
  2025 has twelve reporting stations and the "safe" series is empty. In 2026 it
  is empty again.

The naive path is to pool every station-hour rather than average the hourly
network means, which gives +2.54 and -1.56 — both shrunk toward zero, and both
close enough to the right answer to look right. The mechanism is worth naming
because it is systematic rather than noise: pooling weights an hour by how many
stations reported it, the complete hours carry the most, so the all-hours
baseline is dragged toward the complete-case figure and the difference between
them narrows. It understates the very quantity the case is about. The second
naive path is to read
completeness off row count instead of reported values: 7137 hours for 2024 and
23 for 2025, since a row can exist with no PM2.5 in it. Missing row is not the
same as missing value, and neither is zero. This one is not hypothetical — an
evaluated model produced 7137 and 24 (the row count on calendar labels) on the
first live run of this case,
having read "all twelve reported" as "twelve rows present" despite the case
saying "reported a value", and carried the same definition into Turn 1 for
-0.14 and -1.94.

A year is its hours as the record labels them by their END: from the 01:00
label of 1 January through the 00:00 label of the next 1 January. Counting the
calendar labels instead moves no direction and neither count (it shifts the
deltas by at most 0.003 and the 2025 row count from 23 to 24), so the case is
indifferent to it; the figures above are on the hour-ending year.

Why 2020 and 2024 rather than the whole series. The two years carry the largest
deltas of opposite sign, which is the point of the case; asking for all five
would make the turn an exercise in transcription. The other three are in the
docstring above so a reviewer can see the sign pattern is real and not a
two-point coincidence.

Tolerances.

- Turn 1 scored the two deltas at +/-0.01 until 2026-09-02, a band that
  excluded the pooled-station-hour readings at 0.32 and 0.15 away; it now
  scores directions, which the pooled readings (+2.54 / -1.56) share.
- Turn 2 takes 0 on both counts. They are counts of hours under a condition
  the case states outright, and the row-count misreading is 552 and 23 away.

One aggregation convention is pinned because each moves the
answer well outside those bands: an hour counts as complete when all twelve
stations report a value rather than when twelve rows exist, and an annual figure
is the mean of the hourly network means rather than the pooled mean of every
station-hour.

Both ground truths are recomputed here from the CSV.

**Turn 1 rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier turn dictated the two-computation recipe and scored two deltas
to two decimals; the rebuilt turn asks whether the restriction changes the
annual mean and in which direction, and scores the direction each year
(invariant across hourly network means, pooled station-hours and daily
means) and whether the restriction has a fixed direction. The row-count
misreading ("twelve rows present") reads -0.14 for 2020 and would report
the wrong direction, which is the probe.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn

_STATIONS = 12
_DELTA_YEARS = (2020, 2024)
_COUNT_YEARS = (2024, 2025)


def _hourly() -> pd.DataFrame:
    """Network mean, reporting-station count and station-sum for every hour on
    record, with the year and date the hour belongs to.

    Label h is the hour ending at h:00, so label 0 closes the previous date and
    a year runs from its 01:00 label through 00:00 of the next 1 January.
    """
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    df = df.dropna(subset=["PM2.5"])
    hourly = (
        df.groupby(["year", "month", "day", "hour"])["PM2.5"]
        .agg(["mean", "count", "sum"])
        .reset_index()
    )
    owner = pd.to_datetime(hourly[["year", "month", "day", "hour"]]) - pd.Timedelta(hours=1)
    hourly["date"] = owner.dt.normalize()
    hourly["year"] = owner.dt.year
    return hourly


RAISED = "raised it"
LOWERED = "lowered it"
UNCHANGED = "left it unchanged"


def _deltas() -> dict:
    """The direction the restriction moves each year's annual mean, asserted
    across the constructions of the annual figure: hourly network means
    averaged, station-hours pooled, and daily means then the year."""
    hourly = _hourly()
    out = {}
    for year in _DELTA_YEARS:
        rows = hourly[hourly["year"] == year]
        complete = rows[rows["count"] == _STATIONS]
        deltas = {
            "hourly network means": float(complete["mean"].mean() - rows["mean"].mean()),
            "pooled station-hours": float(complete["sum"].sum() / complete["count"].sum()
                                          - rows["sum"].sum() / rows["count"].sum()),
            "daily means": float(complete.groupby("date")["mean"].mean().mean()
                                 - rows.groupby("date")["mean"].mean().mean()),
        }
        directions = {RAISED if d > 0.05 else LOWERED if d < -0.05 else UNCHANGED for d in deltas.values()}
        if len(directions) != 1:
            raise RuntimeError(f"the {year} direction is not invariant: {deltas}")
        out[year] = directions.pop()
    out["fixed_direction"] = len(set(out[y] for y in _DELTA_YEARS)) == 1
    return out


def _complete_hours() -> dict:
    hourly = _hourly()
    complete = hourly[hourly["count"] == _STATIONS]
    return {
        year: int((complete["year"] == year).sum()) for year in _COUNT_YEARS
    }


def validate_complete_case_delta(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        2020: runtime.retrieve("restriction_direction_2020"),
        2024: runtime.retrieve("restriction_direction_2024"),
    }
    fixed = runtime.retrieve("restriction_has_a_fixed_direction")
    missing = [f"restriction_direction_{y}" for y, v in got.items() if v is None]
    if fixed is None:
        missing.append("restriction_has_a_fixed_direction")
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _deltas()
    errors = [f"restriction_direction_{year}={got[year]!r}, expected {gt[year]!r}"
              for year in _DELTA_YEARS if str(got[year]).strip().lower() != gt[year]]
    ok = (isinstance(fixed, bool) and fixed == gt["fixed_direction"]) or (
        isinstance(fixed, str) and fixed.strip().lower() in
        {str(gt["fixed_direction"]).lower(), "yes" if gt["fixed_direction"] else "no"})
    if not ok:
        errors.append(f"restriction_has_a_fixed_direction={fixed!r}, expected {gt['fixed_direction']}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{y} {gt[y]}" for y in _DELTA_YEARS)
                                 + "; no fixed direction")


def validate_complete_hours(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {}
    for year in _COUNT_YEARS:
        name = f"complete_hours_{year}"
        val = runtime.retrieve(name)
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")
        got[year] = val

    gt = _complete_hours()
    errors = [
        f"complete_hours_{year}={got[year]}, expected {gt[year]}"
        for year in _COUNT_YEARS
        if not compare_numeric(got[year], gt[year], tolerance=0)
    ]
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True,
        "correct: " + ", ".join(f"{year} {gt[year]} hours" for year in _COUNT_YEARS),
    )


tools = []
variables = [
    Variable("restriction_direction_2020", None,
             "Store what restricting Beijing's 2020 annual mean PM2.5 to the "
             "hours in which all twelve stations reported a value did to it, "
             f"as one of exactly these strings: '{RAISED}', '{LOWERED}', "
             f"'{UNCHANGED}'. An hour counts as fully reported when all twelve "
             "stations carry a PM2.5 value in it."),
    Variable("restriction_direction_2024", None,
             "Store the same for 2024, as one of the same three strings."),
    Variable("restriction_has_a_fixed_direction", None,
             "Store True if the restriction can be assumed to move an annual "
             "estimate in a known direction, else False."),
    Variable(
        "complete_hours_2024",
        None,
        "Store the 2024 count of surviving hours as an integer.",
    ),
    Variable(
        "complete_hours_2025",
        None,
        "Store the 2025 count of surviving hours as an integer.",
    ),
]
validators = {
    "validate_complete_case_delta": validate_complete_case_delta,
    "validate_complete_hours": validate_complete_hours,
}
