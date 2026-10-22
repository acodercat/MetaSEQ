"""Two rush hours, one is the cleanest air of the day (temporal_pattern_analysis).

BASELINE with an unnamed concept at its centre, built to the shape that
discovered a frontier-model deficit in `hk_roadside_night_cleanliness`: the
numbers are easy, and the concept is needed to ORGANISE them rather than to
gate a step. Nothing in the case names the boundary layer, mixing height,
dilution or stability.

Beijing's winter traffic is not meaningfully lighter in the morning than in
the evening, yet the two rush hours sit almost six micrograms apart, and the
day's worst air arrives three hours after the evening rush has ended.
Measured over the January, February and December of each year 2020-2025,
network hourly means then averaged by hour of day:

    morning rush, 07:00-09:00 mean      33.22 ug/m3
    evening rush, 17:00-19:00 mean      39.12
    the day's highest hour               21:00

The emissions account predicts a bump at each rush and a trough between; the
record delivers its MINIMUM inside one of the rushes and its maximum in the
late evening. The air the emissions enter is not the same air at each hour: on
the same construction the mixed layer runs 207 m at the morning rush, 1,201 m
at 15:00, 215 m by the evening rush and 163 m at 21:00.

**How far that carries, measured, because an earlier version of this paragraph
overstated it.** Across the 24 hour-of-day means the mixed layer varies by a
factor of **7.97**, NO2 by 1.73 and PM2.5 by only **1.31**; the correlation
between the hour-of-day curve and mixing depth is **-0.93 for NO2 and -0.37
for PM2.5**. So the diurnal PM2.5 curve is NOT a shallow-box curve either —
it is a slowly varying regional burden with a small diurnal swing on top,
which is itself the reason its peak sits where no rush hour is.

The sharpest thing in the record on this point is a third pollutant. SO2, also
primary, runs its MAXIMUM at 13:00 (4.58 ug/m3) and its minimum at 07:00
(3.11, against 3.21 to 3.34 through the small hours), the opposite phase to
NO2, which peaks at 21:00 (38.19) and bottoms at 14:00 (22.06). Two primary pollutants in one city with opposite-phase daily
curves cannot both be tracing when their sources emit: NO2 is a surface source
diluted by the growing layer, while SO2 is dominated by elevated stacks whose
plume is mixed DOWN to the ground when the layer deepens. A concentration curve
is a mixing curve as much as an emissions curve, and that is the case's point.

**The professional consequence, and it is not a hypothetical.** Read the
diurnal curve as an emissions signal and the 21:00 maximum looks like the hour
to target — an evening restriction, aimed at the peak, sized by the peak. What
the record will not do is tell the office what that restriction would deliver.
Beijing's files hold no traffic count, no activity series and no emissions
inventory: every pollutant in them is a CONCENTRATION, jointly set by what was
emitted and by the depth of air it went into, and the two cannot be separated
without a measure of one of them. That is the scored verdict of the second
turn, and it is what makes the sizing question unanswerable rather than merely
hard. The advice that survives is the reverse of the curve's: a tonne of
emission avoided at the morning rush, when the layer is about to grow
sevenfold, does less damage than a tonne avoided at 21:00 — but how much a
restriction at either hour would cut is not in these data.

Pins, each measured.

- JANUARY, FEBRUARY AND DECEMBER, stated in the query. It is load-bearing:
  over the whole year the evening rush reads 31.87 against the morning's
  32.92 — the contrast INVERTS, the paradox disappears and the peak moves to
  23:00, while over summer the figures are 25.25 and 19.75 with the peak at
  06:00. Both are probes.
- 2020 THROUGH 2025, stated in the query and enforced in code. Load-bearing,
  and it is the defect a Gate A review found on 2026-09-06: the file runs to
  2026-07-20, so an unfiltered winter silently carried January and February
  2026 with no December to match them. That reading gives 32.52 and 38.81
  against the complete-years 33.22 and 39.12 — 0.70 and 0.31 outside the band.
- WHICH MONTHS, as each calendar year's own January, February and December.
  The query used to say "December, January and February of 2020 through
  2025", which reads equally as winters that open with the previous December
  (33.52 and 39.34, 0.30 and 0.22 out) or as only the complete winters
  December 2020 - February 2025 (30.75 and 36.52), and eight of the nine
  failures in a Gate C round came from that split. The calendar-month set is the one
  the record serves without a half-winter at either end being argued over, so
  the query now names it — "the January, February and December of each year"
  — and the two winter readings are probes.
- HOURLY NETWORK MEANS FIRST, then averaged across days by hour of day,
  stated on the variables. Two neighbouring readings, both measured on the same
  window: pooling every station-hour instead reads 33.50 and 39.43, and
  collapsing the years so that each calendar slot rather than each day carries
  equal weight reads 33.62 and 39.14. The band excludes both on the morning
  figure — the closer, pooling, sits 0.28 away against a band of 0.2 — and the
  year-collapsed evening figure, 0.0165 away, is inside it, which is acceptable
  because that route differs from the scored one only in weighting and the
  morning figure already separates them.
- THE THREE-HOUR RUSH WINDOWS are given in the query because they are an
  arbitrary framing, not the exam.
- THE VERDICT IS AN EPISTEMIC ONE, not an attribution. Gate B round 21 read
  the enum this turn briefly carried — 'emission' against 'dilution' — and
  ruled that neither is identified: "an hourly PM2.5 curve joined to ERA5
  boundary-layer fields cannot distinguish added rush-hour emissions from
  reduced dilution ... the case supplies no traffic activity, emissions
  inventory, tracer, source-apportionment product, or counterfactual". That is
  right, and the measurements above are the reason it is right: the PM2.5
  curve does not follow mixing depth closely enough for a dilution account to
  be read off it, and nothing in the record measures emission at all. What IS
  settled is that the curve does not identify the answer, which is the
  question the office actually needs settled before it sizes anything.
- THE PEAK HOUR is scored rather than the trough hour: 21:00 is the maximum
  under every convention tested, while the trough sits at 07:00 or 08:00
  depending on the season definition and the aggregation, and those two hours
  differ by 0.007 — a coin toss, and not something to score.

Tolerances: +/-0.2 ug/m3 on each rush-window mean, covering 2-decimal
rounding while excluding the pooled reading (0.28 away on the morning figure),
the unfiltered-year reading (0.70 and 0.31 away) and the whole-year season
reading (7.3 away on the evening figure). The peak hour is an integer, matched
exactly, and is 21:00 under every convention tested.

All ground truths are recomputed here from the CSVs.

**Split 2026-09-02 (query length):** the earlier single turn asked for the
figures and the judgement together; the judgement now has its own turn,
scored as a verdict, with the claims moved to it. The verdict went through
three forms in two days, and the sequence is worth keeping because each
failure named the next problem. Gate C on 2026-09-02: the bool "would a
restriction aimed at that hour cut the PM2.5 it is aimed at" — Flash stored
False with the boundary-layer account, Pro stored True, and Pro was reading
the bool as "would cut it at all", which any restriction does. It became the
enum 'emission' against 'dilution', on which Pro stored 'dilution' and Flash
stored 'emission'. Gate B round 21 then ruled that the enum asks for an
attribution the record cannot support, and the measurements above agree: a
concentration curve and a reanalysis mixing depth do not separate emission
from dilution, and the case had been treating a plausible account as a
computed one. The turn now scores the epistemic verdict instead — the curve
does not identify what a restriction would achieve — which the naive path,
the one that sizes a restriction off the peak, gets wrong.

**A no-data control then showed that verdict is not enough on its own
(2026-09-03, `scripts/controls/no_data_control_r22.py`).** Asked the judgement with
no runtime, no data and only the three figures in the prompt, both DeepSeek
models answered False and gave the right reason — "the data only tells us
averages and a peak hour, not a causal relationship". An epistemic verdict is
recallable from the framing, so a turn carrying nothing else measures a
disposition rather than an analysis, which is the same failure the dust-date
control found in `beijing_dust_column_vs_surface`. The turn now also scores two
hours that cannot be recalled and have to be computed: SO2's winter maximum
(13:00) and NO2's winter minimum (14:00), invariant across all three
constructions of an hour-of-day mean. They are the evidence for the claim as
well as a check that the response went and looked. The figures' turn keeps
only the deliverable.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

_WINTER = (12, 1, 2)
_YEARS = (2020, 2025)
_MORNING = (7, 8, 9)
_EVENING = (17, 18, 19)


def _in_window(frame: pd.DataFrame) -> pd.Series:
    """January, February and December of each year 2020-2025, assigning each
    label to the hour it closes (hour h ends at h:00), so a month runs from its
    1st's 01:00 label to the 00:00 label that opens the next month."""
    ending = pd.to_datetime(frame[["year", "month", "day", "hour"]]) - pd.Timedelta(hours=1)
    return ending.dt.month.isin(_WINTER) & ending.dt.year.between(*_YEARS)


def _diurnal() -> pd.Series:
    """Winter PM2.5 by hour of day: hourly network means, then averaged."""
    aq = pd.read_csv(DATA_DIR / "air_quality.csv")
    winter = aq[_in_window(aq)]
    # Grouped by YEAR as well: an hourly network mean belongs to one actual
    # day, and the curve averages over days. A first version omitted the year,
    # collapsing the six Decembers' 1st-at-07:00 into one figure and weighting
    # calendar slots rather than days; Gate C caught it when both models
    # returned the same 38.81 against that version's 38.48.
    hourly = winter.groupby(["year", "month", "day", "hour"])["PM2.5"].mean()
    return hourly.groupby(level=3).mean()


def _figures() -> Dict[str, object]:
    curve = _diurnal()
    return {
        "morning_rush_pm25": float(curve[list(_MORNING)].mean()),
        "evening_rush_pm25": float(curve[list(_EVENING)].mean()),
        "peak_hour": int(curve.idxmax()),
    }


def validate_rush_hours(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = ("morning_rush_pm25", "evening_rush_pm25", "peak_hour")
    got = {name: runtime.retrieve(name) for name in names}
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)
    for key in ["morning_rush_pm25", "evening_rush_pm25"]:
        if not is_finite_number(got[key]):
            return ValidatorResult(False, f"{key}={got[key]!r} is not a number")
    # `bool` is an `int` subclass; True must not pass as hour 1.
    if not isinstance(got["peak_hour"], int) or isinstance(got["peak_hour"], bool):
        return ValidatorResult(
            False, f"peak_hour={got['peak_hour']!r} is not an integer hour")

    gt = _figures()
    wrong = []
    for key in ["morning_rush_pm25", "evening_rush_pm25"]:
        if not reports_as(got[key], gt[key], decimals=2):
            wrong.append(f"{key}={got[key]}, expected ~{gt[key]:.2f}")
    if got["peak_hour"] != gt["peak_hour"]:
        wrong.append(f"peak_hour={got['peak_hour']}, expected {gt['peak_hour']}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: morning {gt['morning_rush_pm25']:.2f}, evening "
              f"{gt['evening_rush_pm25']:.2f}, peak at {gt['peak_hour']}:00")




def _opposite_phase() -> dict:
    """Winter hour-of-day extremes for two more primary pollutants.

    Both are invariant across the three constructions of an hour-of-day mean
    (station-hours pooled, hourly network means first, station means first):
    SO2 peaks at 13:00 and NO2 bottoms at 14:00, while PM2.5 peaks at 21:00.
    Two primary pollutants in one city with opposite-phase daily curves cannot
    both be tracing when their sources emit, which is the case's point and the
    evidence its claims ask for.
    """
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    df["date"] = pd.to_datetime(df[["year", "month", "day"]])
    winter = df[_in_window(df)]
    builds = {
        "pooled": winter.groupby("hour")[["SO2", "NO2"]].mean(),
        "hourly first": winter.groupby(["date", "hour"])[["SO2", "NO2"]].mean().groupby(level=1).mean(),
        "station first": winter.groupby(["station", "hour"])[["SO2", "NO2"]].mean().groupby(level=1).mean(),
    }
    out = {}
    for key, series in (("so2_peak_hour", "SO2"), ("no2_trough_hour", "NO2")):
        pick = (pd.Series.idxmax if key == "so2_peak_hour" else pd.Series.idxmin)
        hours = {int(pick(frame[series])) for frame in builds.values()}
        if len(hours) != 1:
            raise RuntimeError(f"{key} is not invariant across constructions: {hours}")
        out[key] = hours.pop()
    return out


def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_restriction(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("curve_identifies_what_a_restriction_would_achieve")
    so2 = runtime.retrieve("winter_so2_peak_hour")
    no2 = runtime.retrieve("winter_no2_trough_hour")
    missing = [n for n, v in (("curve_identifies_what_a_restriction_would_achieve", val),
                              ("winter_so2_peak_hour", so2),
                              ("winter_no2_trough_hour", no2)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _opposite_phase()
    errors = []
    for name, got, expected in (("winter_so2_peak_hour", so2, gt["so2_peak_hour"]),
                                ("winter_no2_trough_hour", no2, gt["no2_trough_hour"])):
        if not is_finite_number(got):
            errors.append(f"{name}={got!r} is not a number")
        elif got != expected:
            errors.append(f"{name}={got}, expected {expected}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    # A documented constant, and the docstring argues it: the record holds no
    # traffic count, activity series or emissions inventory, so every series in
    # it is a concentration jointly set by emission and by mixing depth. Gate B
    # round 21 rejected the earlier attribution enum for exactly this reason.
    if not _bool_ok(val, False):
        return ValidatorResult(False,
                               f"curve_identifies_what_a_restriction_would_achieve={val!r}, "
                               "expected False")
    return ValidatorResult(True, f"correct: SO2 peaks at {gt['so2_peak_hour']}:00 while NO2 bottoms "
                                 f"at {gt['no2_trough_hour']}:00, and the curve does not identify "
                                 "what a restriction at the PM2.5 peak would achieve")


tools = []
variables = [
    Variable(
        "morning_rush_pm25",
        None,
        "Store the winter mean PM2.5 over the morning rush hours 07:00, "
        "08:00 and 09:00 as a float in ug/m3, 2 decimal places. Build the "
        "hour-of-day curve by taking each hour's network mean across the "
        "reporting stations first, then averaging those hourly figures over "
        "the days, rather than pooling every station-hour together.",
    ),
    Variable(
        "evening_rush_pm25",
        None,
        "Store the same for the evening rush hours 17:00, 18:00 and 19:00, "
        "on the same construction, as a float in ug/m3, 2 decimal places.",
    ),
    Variable(
        "peak_hour",
        None,
        "Store the hour of day at which that winter curve is highest, as an "
        "integer from 0 to 23.",
    ),
]
validators = {
    "validate_rush_hours": validate_rush_hours,
    "validate_restriction": validate_restriction,
}
variables += [
    Variable("winter_so2_peak_hour", None,
             "Store the hour of the day at which Beijing's winter sulphur "
             "dioxide is highest, as an integer from 0 to 23."),
    Variable("winter_no2_trough_hour", None,
             "Store the hour of the day at which its winter nitrogen dioxide is "
             "lowest, as an integer from 0 to 23."),
    Variable("curve_identifies_what_a_restriction_would_achieve", None,
             "Store True if these records let you say how much a traffic "
             "restriction at that hour would cut the PM2.5 measured then, else "
             "False."),
]
