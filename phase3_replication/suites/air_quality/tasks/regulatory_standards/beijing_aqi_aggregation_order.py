"""Beijing 2024 AQI — averaging the index is not indexing the average
(regulatory_standards).

Aggregation-order BASELINE, declared one from the start: the two turns name
both orders between them, so the one the case forecloses is not a naive path
(the Round 9 ruling). The
diagnostic weight sits in the CC channel.

The AQI of HJ 633-2012 is the MAXIMUM of six sub-indices, each a piecewise
linear function of a pollutant's daily figure. Two orders of operation on the
same year:

- Turn 1 (mean_of_daily_aqi, distinct_daily_drivers): scoring each day and then
  averaging gives 75.46, and over the 366 days the index is driven by four
  different pollutants.
- Turn 2 (aqi_of_annual_means): averaging each pollutant over the year and then
  scoring once gives 56.

A gap of 19 points, a quarter of the reported value. The maximum does not
commute with the mean, and the reason is visible in the second variable rather
than argued: ozone drives the daily index on about half the days, particulate
on most of the rest, nitrogen dioxide on a few dozen. Average the pollutants
first and every one of them lands in the middle of its own range, so the annual
figure is driven by PM10 at 56 — a pollutant that leads on well under a third
of the individual days. Averaging first does not merely lower the number; it
changes which pollutant the index is reporting.

The exact driver counts are NOT scored, and that was decided on measurement
rather than taste. On the interpolated sub-indices the counts are ozone 187
days, PM10 72, PM2.5 68, NO2 39, but the clause 6.2 round-up the case applies
leaves 11 days with two pollutants tied for the lead (see below), so how often
each one leads depends on a tie-break the standard does not give. The case
therefore scores how MANY pollutants take the lead — four — and leaves how
often to the docstring and the CC claim. (The decision was first taken on a
0.002 margin between ozone and the runner-up on one day; on the HJ 663 natural
day that margin is gone, and the ties alone carry it.)

Pins, each measured.

- CO IN mg/m3. The dataset publishes CO in ug/m3 and HJ 633 tabulates it in
  mg/m3, so an unconverted sub-index pins to its 500 ceiling on nearly every
  day. That failure is total rather than partial: BOTH figures become exactly
  500.000 and the gap this case is about vanishes to zero. The trap itself is
  `beijing_aqi_co_unit`'s subject on a different scope (Dongsi, January 2021);
  here it is a precondition, and it is in the probe table.
- OZONE AGGREGATED PER HJ 663-2013 A.2: the city figure is the arithmetic mean
  of the city assessment points' own daily maxima — the ELEVEN stations
  `included_in_city_aggregate`, which is what this case computes and what
  `mean_of_daily_aqi` states. An earlier draft of this line said "twelve",
  contradicting both the code and the paragraph below that records excluding
  Dingling as the change that moved the figures; an external audit caught the
  contradiction. Taking the daily maximum of a
  network-mean hourly series instead — which is what this case and the shared
  helper both did until Gate B read A.2 — gives 75.2705 against 75.4590, ninety-four bands out. The counts and the annual figure do not move.
- OZONE AS THE DAILY MAXIMUM 8-HOUR MEAN per HJ 663-2013, every day it reports.
  Taking the daily maximum 1-hour value of the network-mean series instead
  reads 80.1639 against 75.4590, nearly five points out. Note that it does NOT move the annual figure, which stays at 56
  because PM10 still leads the annual means: the second turn does not
  discriminate this convention and the first one carries it alone. This is the
  largest single convention in the case, and `mean_of_daily_aqi` names it.
- THE DAY THE HOUR LABELS BELONG TO. The record labels hour 0-23, and label h
  is the hour ENDING at h:00, so label 0 is the previous date's 24:00. HJ
  663-2013 A.1 stamps a natural day's hourly values 1:00 to 24:00, CNEMC's own
  running 8-hour ozone (`O3_8h` in the city record) restarts at label 1, not 0,
  and the shared MDA8 helper already owned the 00:00 window to the previous
  date. The 24-hour means must sit on the same day: labels 1-23 of the date
  and label 0 of the next. Grouping a date's labels 0-23 instead — which this
  case did until an audit set its two day definitions side by side — reads
  75.5137 against 75.4590, twenty-seven bands out, while the annual figure and
  the driver count do not move. The labels' meaning is a property of the data
  the agent had no way to learn when this pin was added (the schema then said
  only "hour of day"), so `mean_of_daily_aqi` states it; the system prompt's
  TIMESTAMPS block now carries the same reading for every case.
- THE 6-OF-8 WINDOW RULE (GB 3095-2012 Table 4), stated in `mean_of_daily_aqi`
  because "every day it reports" pins the day set and the window rule decides
  which days report. Requiring all 8 clock hours of a window instead drops one
  day and reads 74.9342 over 365 days against 75.4590 over 366 — far outside the
  band — so a careful agent that took the strict reading would fail on a rule
  the text never gave it. The window is the 8 clock hours ending at its end
  time, not the last 8 rows, so a gap shortens the window rather than reaching
  further back.
- 2024, all 366 days. Every day of 2024 carries a value for all six pollutants,
  so the day-completeness rule that bites elsewhere in this corpus is vacuous
  here — measured, not assumed.
- THE ANNUAL MEAN IS THE UNWEIGHTED MEAN OF THE 366 DAILY FIGURES, and this pin
  was bought the hard way. The first live run read "average each pollutant over
  the whole of 2024" as the mean of the HOURLY network means, which weights a
  day by how many hours it reported, and got 55.07 — 0.05 out, just past the
  band. The two readings are both defensible on the wording the query then had,
  so this was a specification defect rather than a model error, exactly as
  `beijing_forecast_skill_floor`'s predecessor ambiguity was.
  `aqi_of_annual_means` now says which mean, and says the two summaries use the
  same daily figures so that they differ only in WHERE the index sits.

- WHICH STANDARD'S ROUNDING RULE APPLIES, settled from the texts rather than
  chosen. HJ 663-2013 6.3 requires "各污染物项目的数据统计结果" to be rounded per
  GB/T 8170 before assessment, and adds that hourly values, "作为基础数据单元",
  must be rounded before use too. That clause belongs to HJ 663's own assessment
  framework. The AQI is HJ 633-2012's instrument, and HJ 633 contains no
  rounding requirement for concentrations at all — the word 修约 does not appear
  in it. Its only rule is 6.2, the upward rounding of index results, which this
  case applies. So the daily concentrations feeding the sub-indices are used
  unrounded, and `mean_of_daily_aqi` says so.

  Stated as a BENCHMARK CONVENTION, not as a normative conclusion: HJ 633's
  silence on concentration rounding does not by itself prove that an HJ 663 A.2
  statistic loses 6.3 preprocessing when it is fed to the AQI. The variable pins
  "unrounded" so the case has one answer, and this note records that the
  pin is the benchmark's choice among readings the standards leave open.

  It matters here and only here: rounding the daily values first moves the
  figure by about 0.2, measured at the time on the twelve-station chain, before
  A.2 restricted this case to the eleven city assessment points. Measured on the HJ 663 ozone cases the same
  ambiguity is immaterial — beijing_o3_percentile_metric reports 190 either way
  (189.6375 against 189.7000, both rounding up to 190) and the 2023 city
  exceedance count is 52 under all three schemes — which is why only this case
  had to resolve it.
- THE ROUNDING RULE FOR THE INDEX ITSELF, which is normative and which the first two revisions of
  this case got wrong. HJ 633-2012 clause 6.2 reads
  "环境空气质量指数及空气质量分指数的计算结果应全部进位取整数，不保留小数": every
  index result, sub-index and AQI alike, is rounded UP to a whole number. Not
  to the nearest — UP. The consequences are not cosmetic. Ceiling each
  sub-index before the daily maximum gives 75.4590 where the raw interpolation
  gives 74.9569 and nearest-rounding gives 74.9617, and the annual figure
  becomes exactly 56 rather than 55.4564 or 55. Both earlier revisions scored
  the interpolated value, so the case would have marked the answer the standard
  prescribes WRONG on both turns. Gate B caught it against the published text.
  The case now states the rule, because its subject is the aggregation order
  and a second hidden discriminator would make a failure ambiguous.

Measured indifferent, so stated rather than pinned: the daily recipe. Pooling
station-hours in place of the point daily means gives 75.4344, and averaging the
hourly network means first gives 75.4262; both give the same 56 and leave the
driver count unchanged. Neither is the A.2 recipe, so neither is accepted.

The ceiling rule also puts 11 of the 366 days into a tie for the daily maximum,
which is why the driver COUNT is scored and the per-pollutant tallies are not.
The count is 4 whether ties are broken by first or last column, and the union of
every tied leader across the year is the same four pollutants.

Distinct from the corpus's two other AQI cases on subject, not just on scope.
`beijing_aqi_co_unit` is about the unit; `beijing_aqi_primary_pollutant` asks
which pollutant leads on a single named day. Neither compares aggregation
orders, and neither reads the whole year.

Tolerances: +/-0.002 on the mean of daily values, against 3-decimal reporting,
which needs 0.0005. Every deviation the case forbids is outside it: the
label-date day by 0.0547, the pooled recipe by 0.0246, the 8-of-8 window by
0.5248, the two wrong rounding
rules by 0.5021 and 0.4973, the 1-hour ozone basis by 4.7049. 0 on the annual figure and on the driver count — clause 6.2 makes the
annual answer an exact integer, so no band is needed and none is given. The
+/-0.03 band an earlier revision carried existed only to paper over the rounding
error the standard resolves outright, and the sweep's whitelist for this case is
now empty: nothing here is equivalent, everything is pinned.

Observed live behaviour across two runs of one model, BOTH AGAINST EARLIER
REVISIONS of this case, so their figures are on the old continuous basis and are
not comparable to the ground truth above. They are kept because the failure
modes are.

- Run 1 gave 74.03 and 55.07. The 55.07 was a QUERY DEFECT in the annual-mean
  wording, diagnosed and fixed above. The 74.03 is NOT explained: no ozone basis
  tested reproduces it, and while its code shows a rolling 8-hour mean without
  the HJ 663 window ownership, that alone lands two points higher. It is probed
  with its mechanism recorded as UNKNOWN, because a guessed mechanism in a
  docstring is worse than an admitted gap.
- Run 2 gave 76.16 and 194.97. The first is the unrestricted ozone window basis,
  which under the correct rounding reads 76.9426. The 194.97 is the sub-index of
  the ozone annual MAXIMUM, 259.97 ug/m3, used where the case asks for the
  mean — taken alongside means for the other five, since the same slip applied
  to all six would read 227.53.

Neither model applied clause 6.2, which is the same thing the case's own first
two revisions got wrong; `mean_of_daily_aqi` now states it. Both got
`distinct_daily_drivers` right at 4, and both failed turn 1 on the ozone window
set. That convention is pinned only by naming HJ 663-2013, which is
the corpus's established practice — `beijing_o3_mda8_exceedance` words it the
same way and probes 41, 48 and 49 as the deviations it produces. The tension is
worth stating plainly: here that convention moves the answer by two AQI points,
whereas `beijing_aqi_co_unit` measured it indifferent on its own scope. This
case therefore inherits a discriminator rather than an ambiguity, and a model
that reads the annex loosely is expected to fail it.

All three ground truths are recomputed here from the CSV.

HJ 663-2013 A.2 admits only 城市点: its footnote reads "点位指城市点，不包括
区域点、背景点、污染监控点和路边交通点", and it sits under every row of Table A.2,
so it governs the particulate and gas statistics as well as ozone. Dingling is
the network's background site; `station_metadata.csv` has carried the flag in
`included_in_city_aggregate` since the dataset was built, and until Gate B read
the footnote only `beijing_product_provenance` was using it. Excluding Dingling is what moved this case's figures: keeping all twelve
stations reads 74.7486 against 75.4590.

"""

import math

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn
from domains.beijing.mda8 import _city_points, hourly_to_mda8

_YEAR = 2024
_IAQI = [0, 50, 100, 150, 200, 300, 400, 500]
_BP = {
    "PM2.5": [0, 35, 75, 115, 150, 250, 350, 500],
    "PM10": [0, 50, 150, 250, 350, 420, 500, 600],
    "SO2": [0, 50, 150, 475, 800, 1600, 2100, 2620],
    "NO2": [0, 40, 80, 180, 280, 565, 750, 940],
    "CO": [0, 2, 4, 14, 24, 36, 48, 60],
    "O3": [0, 100, 160, 215, 265, 800],
}
_DAILY_MEAN = ("PM2.5", "PM10", "SO2", "NO2", "CO")


def _sub_index(conc: float, pollutant: str) -> float:
    """HJ 633-2012 piecewise linear sub-index, BEFORE the clause 6.2 rounding.

    Clause 6.2 requires every index result to be rounded UP to a whole number
    ("进位取整数，不保留小数"), which `_rounded` applies. The interpolation is
    kept separate so the rounding is visible at the point of use rather than
    buried here.
    """
    bp = _BP[pollutant]
    levels = _IAQI[: len(bp)]
    if not np.isfinite(conc):
        return np.nan
    if conc <= bp[0]:
        return 0.0
    if conc >= bp[-1]:
        return float(levels[-1])
    for i in range(1, len(bp)):
        if conc <= bp[i]:
            return (levels[i] - levels[i - 1]) / (bp[i] - bp[i - 1]) * (
                conc - bp[i - 1]
            ) + levels[i - 1]
    return float(levels[-1])


def _rounded(value: float) -> float:
    """HJ 633-2012 clause 6.2: index results are rounded UP, no decimals."""
    return float(math.ceil(value)) if np.isfinite(value) else value


def _daily_table() -> pd.DataFrame:
    aq = pd.read_csv(DATA_DIR / "air_quality.csv")
    aq["ts"] = pd.to_datetime(aq[["year", "month", "day", "hour"]])
    # HJ 663-2013 A.1: a natural day's hourly values are stamped 1:00 to 24:00,
    # and label h is the hour ending at h:00, so label 0 is the previous
    # date's 24:00. The 24-hour mean and the ozone windows both use that day.
    aq["date"] = (aq["ts"] - pd.Timedelta(hours=1)).dt.normalize()
    aq["CO"] = aq["CO"] / 1000.0  # ug/m3 in the file, mg/m3 in the standard
    # HJ 663-2013 A.2 footnote: "点位指城市点，不包括区域点、背景点、污染监控点和
    # 路边交通点". The footnote sits under every row of Table A.2, so it governs
    # the particulate and gas statistics as well as ozone, not ozone alone.
    year = aq[(aq["date"].dt.year == _YEAR) & aq["station"].isin(_city_points())]

    columns = {}
    for pollutant in _DAILY_MEAN:
        present = year.dropna(subset=[pollutant])
        # A.2 again: the city 24-hour mean is "各点位24小时平均浓度值的算术平均值",
        # each point's own daily mean averaged over points. The measured
        # alternatives are 75.4344 pooled and 75.4262 hourly-first, both of
        # which the docstring's daily-recipe paragraph carries.
        columns[pollutant] = (
            present.groupby(["date", "station"])[pollutant].mean()
            .groupby(level=0).mean()
        )
    # HJ 663-2013 A.2: the city daily maximum 8-hour ozone is the arithmetic
    # mean of the stations' own daily maxima, not the daily maximum of a
    # network-mean hourly series. The two differ by 0.19 on this case's answer.
    columns["O3"] = pd.concat(
        [
            hourly_to_mda8(g.set_index("ts")["O3"])
            for _, g in year.dropna(subset=["O3"]).groupby("station")
        ],
        axis=1,
    ).mean(axis=1)

    table = pd.DataFrame(columns)
    table.index = pd.to_datetime(table.index)
    return table[table.index.year == _YEAR].dropna()


def _figures() -> dict:
    daily = _daily_table()
    sub = daily.apply(
        lambda col: col.map(lambda v: _rounded(_sub_index(v, col.name)))
    )
    annual = {p: _sub_index(daily[p].mean(), p) for p in daily.columns}
    return {
        "mean_of_daily_aqi": float(sub.max(axis=1).mean()),
        "distinct_daily_drivers": int(sub.idxmax(axis=1).nunique()),
        "aqi_of_annual_means": _rounded(max(annual.values())),
    }


def _check(runtime, names, tolerances) -> ValidatorResult:
    got = {}
    for name in names:
        val = runtime.retrieve(name)
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")
        got[name] = val

    gt = _figures()
    errors = [
        f"{name}={got[name]}, expected {gt[name]:.4f}"
        for name in names
        if not (reports_as(got[name], gt[name], decimals=3) if name == "mean_of_daily_aqi" else compare_numeric(got[name], gt[name], tolerance=0))
    ]
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True, "correct: " + ", ".join(f"{n} {gt[n]:.4f}" for n in names)
    )


def validate_daily_then_mean(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check(
        runtime,
        ("mean_of_daily_aqi", "distinct_daily_drivers"),
        {"mean_of_daily_aqi": 0.002, "distinct_daily_drivers": 0},
    )


def validate_mean_then_index(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check(runtime, ("aqi_of_annual_means",), {"aqi_of_annual_means": 0})


tools = []
variables = [
    Variable(
        "mean_of_daily_aqi",
        None,
        "Store the mean of the 366 daily AQI values as a float, 3 decimal "
        "places; the daily values are whole numbers, their mean is not. Build "
        "each day the standard's way: the city figure for a pollutant is the "
        "arithmetic mean over the city assessment points (the eleven stations "
        "flagged as included in the city aggregate; the background site is not "
        "one of them) of that point's own daily value — its 24-hour mean for "
        "PM2.5, PM10, SO2, NO2 and CO, its HJ 663-2013 maximum daily 8-hour "
        "running mean for ozone — the largest of the 8-hour running means "
        "whose window ends between 08:00 and 24:00 of that day, each window "
        "being the 8 clock hours ending at its end time and counting when at "
        "least 6 of them have a value — over every day it reports. The record labels each hour by the time it ends, so "
        "hour 0 is the 24:00 that closes the previous date: a date's day, for "
        "the 24-hour means as for the ozone windows, runs from its hour 1 "
        "through hour 0 of the next date. Convert CO to "
        "mg/m3 for the sub-index table, since the record stores it in ug/m3. "
        "Use the daily concentrations unrounded, round each sub-index UP to a "
        "whole number as clause 6.2 requires, and take the day's AQI as the "
        "largest of the six.",
    ),
    Variable(
        "distinct_daily_drivers",
        None,
        "Store the number of different pollutants that determine the daily AQI "
        "on at least one day, as an integer, under the same daily construction.",
    ),
    Variable(
        "aqi_of_annual_means",
        None,
        "Store the AQI computed from the annual mean concentrations as an "
        "integer. Each annual mean is the unweighted mean of that pollutant's "
        "own 366 daily figures — the same daily figures the daily AQI used, so "
        "the two summaries differ only in where the index is applied — with "
        "the same CO unit conversion and the same round-up of each sub-index.",
    ),
]
validators = {
    "validate_daily_then_mean": validate_daily_then_mean,
    "validate_mean_then_index": validate_mean_then_index,
}
