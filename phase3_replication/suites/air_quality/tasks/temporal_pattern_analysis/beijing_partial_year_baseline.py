"""Beijing ozone year-on-year — the partial-year baseline
(temporal_pattern_analysis).

Baseline, and it was a trap until the query had to pin the baseline window.
The city record stops on 2026-07-20, so 2026 exists only as a 201-day,
summer-weighted fragment. Judging it against a FULL calendar year measures the
seasonal cycle, not a year-on-year change — and for ozone, whose season is the
opposite of PM2.5's, it reverses the verdict:

- pinned path: the baseline is the same calendar span. Daily means over
  1 January to 20 July give 76.79 in 2025 and 71.96 in 2026 -> -6.28 %,
  ozone DOWN.
- the reading the case now forbids: judging the 2026 fragment against the 2025
  full-year mean (64.56) -> +11.47 %, ozone UP. The same number arises whether
  the agent labels the fragment "2026" or "2026 to date", because the record
  contains nothing after 20 July.

Why it is no longer a trap. The query used to ask for the change "relative to
the earlier figure" and never said what the earlier figure spanned. For a
question about 2026, reading "the earlier figure" as 2025 is what the words
mean, so the full-year baseline was not a misreading the query forbade — it was
one of two readings the query admitted, and P1 requires exactly one. Two
separate runs returned +11.144 (the full-year reading on days taken as the
labels 0-23) — the same value to three decimals, which is
what a second defensible reading looks like rather than a slip — and an
external review ruled the case at fault rather than the model. The variable
now requires the earlier period to run to the same calendar start and end
dates as the 2026 record.

Pinning it dissolves the trap, which is the documented consequence of P1 (see
`case_design_standard.md`, "P1 dissolves traps, and that is not a bug"), so the
case is declared `baseline`. The diagnostic weight it used to carry in PV was
already duplicated in CC and stays there: `matched_baseline` asks for the
earlier-period figure the response divided by, and `seasonality_reason` asks
whether it can say why a whole-year baseline would measure seasonal coverage
instead of a change between years. Knowing to match the window is now scored
where knowing is what is being tested.

`matched_baseline` has been reworded twice, and the second time an external
audit was right about it. The original asked whether the response computed the
baseline "over the same 1 January to 20 July span" — wording that shares 46 %
of its content words with the pinned wording, above the ~40 % at which a claim
is answerable by paraphrasing the question back. The fix asked for the NUMBER
and for it to be distinguished "from 65 ug/m3, the figure a whole-2025 average
would give", which no paraphrase produces.

But 65 is a quantity the question never asks for, and
`core/system_instructions.py` tells every agent to "just focus on the user's
query and don't perform unnecessary analysis". The claim was therefore
penalising a response for obeying its own instructions — a direct conflict
between two surfaces the agent reads. It now asks for the baseline number
(~77) and for it to be identified as the MATCHING span rather than the whole
year, which still cannot be paraphrased from the question and still cannot be
produced without computing it, while requiring no extra analysis. The
whole-year figure stays in this docstring as the contrast, where it belongs.

The variable pins the *rule* — same start and end date as the 2026 record —
and deliberately not the dates themselves. Naming 20 July would hand over the answer
to `record_endpoint`, whose whole content is that the agent noticed where the
record stops.

Day completeness is load-bearing here and is therefore pinned on the variable
rather than left to the agent. The city file is NOT complete: the two 201-day
spans hold 4,710 and 4,725 hourly rows against 4,824 possible, and the thinnest
day reports a single hour. Admitting such days as "daily means" moves the answer
by more than a point (-7.46 %). The variable pins GB 3095-2012 Table 4 data
validity — a 24-hour mean needs at least 20 valid hourly values — applied to
each period on its own.

The remaining choices are small but they are NOT nuisance, and an earlier
revision of this paragraph called them that. A 12-combination sweep over
{20, 18, 1}-hour validity x {daily-then-mean, pooled} x {same window, full
year} gives, against the pinned -6.2794, on the hour-ending day (hours 1-23
and the next date's hour 0):

    20-hour minimum, pooled                 -6.2654   0.0140 away
    18-hour minimum, daily-then-mean        -6.2467   0.0327
    18-hour minimum, pooled                 -6.2420   0.0374
    no validity rule, pooled                -6.4567   0.1773
    no validity rule, daily-then-mean       -7.4572   1.1778
    any of the above against a full year    +10.32 to +11.47

Taking the days as the labels 0-23 instead, against the domain's stated
convention, gives -6.2469, 0.0325 away and outside the band.

The variable names 20 hours and names daily-then-mean, so the first three are
readings the case FORBIDS, and the +/-0.15 band this case used to carry admitted all
three. That band was set to be "robust to the nuisance choices", which is
precisely the thing a band must not do. Intersecting the two years' valid-date
sets (-7.46 %) is separately and deliberately NOT required: "valid in both
years" is a different matching rule from the one the variable names, and it
would drop dates that rule keeps.

Distinct from the corpus's other period-comparison cases: `regression_to_mean`
is selection bias on extreme days, `regional_trend_attribution` is a confounded
control group. This one is a baseline-window match.

Tolerance +/-0.005 percentage points against 3-decimal reporting, which needs
0.0005. Every reading in the sweep above is outside it: the nearest, the pooled
mean, sits 2.8 bands out, and the forbidden full-year baseline is three
orders of magnitude further. The extra decimal keeps the band ten times the
reporting error; at 2 decimals it would be no wider than the rounding.

Both ground truths are recomputed here from the CSV.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_CITY = "北京"
_WINDOW = ("01-01", "07-20")
_EARLIER, _LATER = 2025, 2026
# GB 3095-2012 Table 4, checked against the published text: "24小时平均 /
# 每日至少有20个小时平均浓度值或采样时间". Table 3 is the analysis-methods
# table; an earlier revision cited it by mistake.
_MIN_VALID_HOURS = 20


def _daily_means(frame: pd.DataFrame) -> pd.Series:
    hours = frame.groupby("date")["O3"].apply(lambda s: s.notna().sum())
    qualifying = frame[frame["date"].isin(hours[hours >= _MIN_VALID_HOURS].index)]
    return qualifying.groupby("date")["O3"].mean()


def _changes() -> dict:
    cities = pd.read_csv(DATA_DIR / "region_cities.csv")
    bj = cities[cities["city"] == _CITY].copy()
    # Hour h is the hour ENDING at h:00: a day is its hours 1-23 and hour 0 of
    # the next date, so the record's last label, 20 July 23:00, closes a
    # 23-hour 20 July and the 2026 record is 1 January to 20 July.
    stamp = pd.to_datetime(bj[["year", "month", "day", "hour"]])
    bj["date"] = (stamp - pd.Timedelta(hours=1)).dt.normalize()

    def window(year: int) -> pd.DataFrame:
        lo, hi = f"{year}-{_WINDOW[0]}", f"{year}-{_WINDOW[1]}"
        return bj[(bj["date"] >= lo) & (bj["date"] <= hi)]

    earlier_window = _daily_means(window(_EARLIER)).mean()
    later_window = _daily_means(window(_LATER)).mean()

    return {
        "correct": float((later_window - earlier_window) / earlier_window * 100),
        "earlier_window": float(earlier_window),
        "later_window": float(later_window),
    }


def validate_year_on_year(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("o3_year_on_year_pct")
    if val is None:
        return ValidatorResult(
            False, "o3_year_on_year_pct not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"o3_year_on_year_pct={val!r} is not a number"
        )

    gt = _changes()
    # 0.005 covers 3-decimal reporting and excludes every reading of the
    # docstring's sweep, the nearest of which (an 18-hour minimum) is 0.011 away.
    if reports_as(val, gt["correct"], decimals=3):
        return ValidatorResult(
            True,
            f"correct: {val} ~ {gt['correct']:.2f} % "
            f"({gt['earlier_window']:.1f} -> {gt['later_window']:.1f})",
        )
    return ValidatorResult(
        False, f"o3_year_on_year_pct={val}, expected ~{gt['correct']:.2f} %"
    )


tools = []
variables = [
    Variable(
        "o3_year_on_year_pct",
        None,
        "Store the year-on-year change in Beijing city ozone as a float "
        "percent, 3 decimal places (negative = lower in the later period). "
        "The 2025 comparison period runs from the same calendar start date to "
        "the same calendar end date as the 2026 record. Count a date only "
        "when the city record reports at least 20 valid hourly ozone values "
        "that day, applying the rule to each period on its own; form each "
        "counted date's mean ozone, then average those daily values over the "
        "period.",
    ),
]
validators = {"validate_year_on_year": validate_year_on_year}
