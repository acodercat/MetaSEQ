"""Ozone annual evaluation value — the statutory percentile (regulatory_standards).

China does not judge annual ozone compliance by an annual mean: HJ 663-2013
prescribes the 90th percentile of the daily maximum 8-hour ozone as the annual
evaluation value, compared against the 160 ug/m3 Grade II limit. The choice of
statistic inverts the conclusion at Dongsi in 2023:

- correct path: 90th percentile of daily MDA8 -> 190 ug/m3, 19 % ABOVE the
  limit. Non-attainment.
- wrong path: the mean of the daily MDA8 series -> 102.8, comfortably "below
  the limit" — the statistic an agent reaches for when it does not know the
  evaluation basis.
- wrong path: the year's highest MDA8 -> 301.1 — over-strict.
- wrong path: the plain mean of hourly ozone -> 71.3 — never even formed the
  daily metric.

The CC claim checks the consequence: the response must conclude non-attainment
despite the mean sitting far below the limit.

BOTH THE PERCENTILE AND ITS PRECISION ARE PRESCRIBED, and it took two revisions
to get there. Annex A.6 fixes the percentile: sort ascending, take the ordinal
k = 1 + (n - 1) x p% (A.3), let s be its integer part, and interpolate
m_p = X(s) + (k - s)(X(s+1) - X(s)) (A.4). On the 364 daily values here that
gives k = 327.70 and 189.6375. Clause 6.3 also asks for the daily values themselves to be rounded before use,
which was measured rather than argued over: rounding them first gives 189.7000
against 189.6375, and both report as 190, so the reading does not arbitrate this
case. Clause 6.3 then fixes the reporting: statistics
are rounded per GB/T 8170 to the decimals in Table 3, which gives ozone ZERO.
The evaluation value is therefore the integer 190, not 189.64.

Getting 6.3 right makes the case MORE robust, which is why it is worth having.
Rounding collapses four of the five interpolation conventions onto one answer:

    A.3/A.4 and numpy "linear"        189.6375  ->  190   <- the answer
    numpy "midpoint"                  189.5625  ->  190
    numpy "higher" / "nearest"        189.7500  ->  190
    numpy "lower"                     189.3750  ->  189
    >= 18 valid hours per day         188.1375  ->  188

So the interpolation choice, which an earlier revision tried to exclude with a
band, is settled by the standard itself except for the "lower" convention.

**Both of the surviving readings lived only in this docstring until an
external audit pointed that out.** "Lower" gives 189 and the >=18-hour daily
screen gives 188, each one integer off a zero-tolerance answer, and neither
was stated anywhere the agent reads: the query names the standard, and
inferring Annex A.3/A.4 from the name alone is exactly the "P1 rests on
recall" pattern this corpus rejects elsewhere. The variable now states both —
no completeness filter, and interpolate rather than truncate. Two
revisions got this wrong before Gate B caught it: the first carried a 2.5
tolerance that accepted everything in the column, the second tightened to 0.02
around an unrounded 189.64 and would have REJECTED the answer the standard
prescribes. The tolerance is now 0 because the answer is an exact integer.

**The required claim compared two things that are not comparable, and the
audit was right to reject it.** It used to contrast the statutory verdict with
"a simple annual average of the daily ozone metric" sitting far below the
limit. That average is a central measure of daily maxima and the 160 limit is
written for a single day's maximum, so the two have different bases and a
careful response would decline the comparison — and then fail the claim. It
now asks for the point the case actually makes, that attainment turns on the
upper tail rather than the typical day, and states that declining the
average-versus-limit comparison is consistent with the claim.

Both ground truths are recomputed here from the CSV.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn
from domains.beijing.mda8 import frame_to_mda8

_STATION, _YEAR = "Dongsi", 2023


def _values() -> dict:
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Hour h ends at h:00, so 2023 runs to the 00:00 label of 1 January 2024,
    # which closes 31 December's last window.
    ending = pd.to_datetime(df[["year", "month", "day", "hour"]]) - pd.Timedelta(hours=1)
    sel = df[(df["station"] == _STATION) & (ending.dt.year == _YEAR)]

    series = frame_to_mda8(sel)
    daily = series[series.index.year == _YEAR].dropna()
    # HJ 663-2013 6.3: statistics are rounded per GB/T 8170 to the decimals in
    # its Table 3, which gives ozone 0 — the evaluation value is an integer.
    return {
        "correct": float(round(np.percentile(daily, 90))),
    }


def validate_o3_evaluation_value(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("o3_evaluation_value")
    if val is None:
        return ValidatorResult(
            False, "o3_evaluation_value not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"o3_evaluation_value={val!r} is not a number"
        )

    gt = _values()
    if compare_numeric(val, gt["correct"], tolerance=0):
        return ValidatorResult(
            True, f"correct: {val} = {gt['correct']:.0f} ug/m3"
        )
    return ValidatorResult(
        False, f"o3_evaluation_value={val}, expected {gt['correct']:.0f}"
    )


tools = []
variables = [
    Variable(
        "o3_evaluation_value",
        None,
        "Store the 2023 annual evaluation value for ozone at Dongsi in "
        "ug/m3, rounded to a whole number as the standard requires. A "
        "day's maximum 8-hour ozone is the largest of the 8-hour running "
        "means whose window ENDS between 08:00 and 24:00 of that day, per "
        "HJ 663-2013. Apply no completeness filter: every day the station "
        "reports contributes, whatever number of valid hours or windows it "
        "holds. Take the percentile by the standard's own ordinal "
        "interpolation — sort ascending, k = 1 + (n-1)p, and interpolate "
        "linearly between the two neighbouring values — not by truncating "
        "to the lower one.",
    ),
]
validators = {"validate_o3_evaluation_value": validate_o3_evaluation_value}
