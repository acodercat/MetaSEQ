"""Does the winter sector predictor survive spring? — the mean and the
median of the same hours disagree (source_attribution).

BASELINE with an unnamed concept at its centre. Nothing in this case says dust,
coarse fraction, skew, tail or episode: the query asks whether a screening rule
holds, and knowing that a mean and a median can answer that question in
opposite directions — and why these do — IS the exam.

**The prior this case tests, and where the corpus teaches it.**
`beijing_wind_sector_pm25` conditions winter PM2.5 on the same sectors by the
same per-row rule and finds southerly 47.90 against northerly 32.47: southerly
flow arrives over the industrialised plain, northerly flow descends from the
plateau and clears the city. That is the textbook account and in winter it is
right. This case is its SPRING ARM — same convention, same sector bounds,
disjoint months — and Gate B should rule on the two together.

Measured over the March, April and May station-hours of 2020 through 2025,
each observation classified by the wind direction of its own station's
meteorology row for the same hour (50,196 northerly and 48,464 southerly
station-hours; spring is the hour-ending hours of March to May, 1 March 01:00
to 1 June 00:00):

    PM2.5   mean     northerly 37.17    southerly 42.85    southerly +5.68
    PM10    mean     northerly 95.79    southerly 84.05    NORTHERLY +11.75
    PM10    median   northerly 55       southerly 73       southerly +18

The rule holds on fine particles, fails on coarse particles, and holds again on
coarse particles the moment the statistic changes. All three readings are
correct and they are taken over the same hours.

**Why.** A typical northerly spring hour is cleaner than a typical southerly
one — that is the median, and it is negative in all six springs and in both
pollutants. The northerly mean is nevertheless higher in PM10 because the
northerly distribution carries a tail the southerly one does not: spring dust
intrusions arrive on exactly that flow, and a handful of them carries enough
mass to move a 50,000-hour mean by 12 ug/m3. The seasonal mean and the typical
hour are answering different questions, and a screening rule is a question
about hours.

**The professional consequence, and it is turn 2.** Over the same six springs
the network daily PM10 exceeded the Grade II 24-hour level of 150 ug/m3 on 53
days of 552. Turn 2 puts a colleague's PROPOSAL to a test — carry the
southerly-flow premise into a spring trigger for coarse particles — and states the trigger
exactly, because an operational consequence cannot be read off a statistic that
does not define one. Gate B round 9 rejected the earlier framing for precisely
that: the case asserted a screening rule Beijing was said to run without
evidence any such rule exists, and scored "more northerly hours than southerly"
while the claim spoke of days a rule fails to flag. Five defensible day-level
rules gave 8, 34, 39, 42 or 43 misses over the 52 days the label-day reading
found, so the consequence was not identified by the number.

Stated exactly — fire when a day's southerly station-hours strictly outnumber
its northerly ones, a tie not firing — the proposal fails in both directions at
once:

    exceedance days                                53 of 552
    days the trigger fires on                      21
    exceedance days it misses                      32    (all northerly, no tie)
    spring days it fires on at all                274 of 552

It misses three coarse exceedance days in five while flagging half the season.
The same split for PM2.5 above 75 ug/m3 is 29 caught against 28 missed — the
sector is uninformative there rather than inverted, which is why the case scores the
PM10 determination and not the PM2.5 one.

**Robustness, measured, including what cuts against the finding.**

- *The instrument artefact.* 5.3 % of these station-hours report PM2.5 above
  PM10, and `datasets/README.md` names dust-versus-haze discrimination as what
  that artefact invalidates. Excluding those hours moves the PM10 contrast to
  +12.03 and the PM2.5 contrast to -5.51. The artefact therefore biases
  AGAINST this case's finding — it can only shrink a northerly PM10 excess —
  so the reported +11.75 is the conservative reading. This was measured
  because the artefact's presence is a reason to distrust the case, not a
  footnote.
- *Per-year spread, which is the reason the window is six springs.* The PM10
  mean difference reads +89.06 (2021), +37.64 (2023), +5.52 (2024), -26.79
  (2020), -2.57 (2022), -15.88 (2025). The MEDIAN difference is negative in
  all six. So the divergence between the two statistics is the structural
  fact, while the mean's own sign counts how many intrusions a window caught.
  A three-spring window is not enough for a quantity that counts events: over
  2023-2025 the PM10 mean difference is +9.64 and dropping 2023 alone takes it
  to -5.67. Turn 2's determination does not inherit that fragility — 32 missed
  against 21 caught is a count over the whole window, and the exceedance-day
  split stays northerly-majority in every leave-one-year-out sample (20 to 32
  northerly against 15 to 19 southerly).

**Windows rejected by measurement, recorded so they are not retried.**

- *March 2021 alone.* The largest reversal in the record, +28.40 on PM2.5 and
  +256.29 on PM10 — and 41.3 % of that month's station-hours report PM2.5
  above PM10. The month cannot carry a size-fraction reading.
- *March 2023 alone.* +65.39 on PM10, and dropping 2023-03-22 alone takes it
  to +27.62 while flipping PM2.5 from +2.12 to -5.27. One day.

**Pins, and where each one goes** (`docs/case_design_standard.md` §3.1). The
sector bounds and the per-row conditioning are specific to this question and
live in the Variable descriptions; the daily figure is the domain prompt's
DAILY FIGURES convention and is not restated. The six springs are stated
because a "2020 onward" filter would annex spring 2026 — the contamination
this corpus has hit four times — and that reading is measured below rather
than assumed harmless. The met file covers every spring station-hour of the
air-quality file (151,760 rows in, 151,760 after the inner join), so the join
drops nothing the air-quality record holds.

**IT IS NOT SYMMETRIC, AND A GATE C RUN PAID FOR THAT.** The met file carries
158,976 spring station-hours against the air-quality file's 151,760 — 7,216
hours where the meteorology reports and the pollutant record has no row at
all. The hour counts therefore have two populations, and the variables used
to say only "including any whose pollutant columns are missing", which reads
more naturally as the met-side population than as the air-quality rows whose
values happen to be null. `deepseek-v4-pro-0813` took it that way, wrote
"preserve every station-hour, including ones whose df pollutants are missing",
and returned 52,743 / 50,280 — with all four of its means EXACT. The
population is now named on the variables and the met-side reading is in the
probe table. The combination sweep carried it as a sixth axis, `population`,
which is where the shape of the hole is easiest to see: under the met-side
reading every mean and both turn-2 quantities are IDENTICAL to a digit, and
only the two exact counts move. No tolerance on a mean could ever have caught
it, and the counts are scored exactly for precisely the reason §3.1 gives.

**What the same run says about the claim layer, which is what the case is
for.** Turn 1's claim was covered by both models: each reported the split and
refused to give the rule a single verdict. Turn 2 separated them.
`episodes_not_a_dirtier_airstream` scored 1.00 for flash, which wrote that
"the northerly mean was inflated by a relatively small number of very high
readings ... while the typical day is actually dirtier under southerly flow" —
the median set against the mean, which is the whole of the case. It scored
**0.00 for pro**, from both judges: pro reported both medians, observed that
the typical hour is consistent with the southerly premise, and then explained
the exceedances by "northerly-flow dust events" without once setting that
median against the mean it had itself computed one turn earlier. Its two
numbers never met.

That is the second case in this corpus where the model with the stronger
grasp leaves its own figures unreconciled while the weaker one joins them:
`hk_roadside_night_cleanliness` recorded the first, on a different mechanism,
with the same two models the same way round. The shared feature of the two is
that the concept has to ORGANISE the answer rather than gate a step.

**Wrong paths pinned.**

    counted on the met file          52,743 / 50,280 hours, means exact
    per-station-first averaging      37.52 / 42.75 / 96.97 / 84.06
    linear mean of the network's
      directions, then sectoring     29.68 / 44.97 / 104.31 / 86.48
    springs 2020 through 2026        36.52 / 42.72 / 91.68 / 82.66

The second is the circular-mean error `beijing_wind_circular_mean` exists for —
a linear mean of 350 and 10 degrees is 180 — and here it does not merely shift
the means, it reduces the sample from 98,660 station-hours to 7,776 hourly
figures and moves the PM2.5 contrast from -5.68 to -15.29.

**Tolerance note, stated as what it excludes.** The band is +/-0.01 on each
mean, covering 2-decimal reporting. Three of the four wrong paths above fall
outside it on every mean they touch. The fourth does not and cannot: counting
the sector on the met file leaves every mean EXACT, so no tolerance on a mean
could ever reject it and only the exact hour counts do. That is the case for
scoring the counts at all, and it was found by a live run rather than by
reasoning about the tolerance. The one reading it cannot separate is the sector
bounds taken as exclusive rather than inclusive: 37.1772 / 42.8509 / 95.8356 /
84.0395, which is outside the band on the two northerly means and inside it on
the two southerly ones. The bounds are pinned inclusive on the surface the
agent reads, and the scored signs are identical under both readings (PM10
+11.80 exclusive against +11.75 inclusive), so nothing the case asks turns on
it.

**The combination sweep** covered the five axes these surfaces pin — bounds,
pooling, direction source, window, and the daily construction — over 48
combinations. Two land inside the band:
the pinned one, and the same combination with the day's PM10 figure pooled
from its station-hours instead of built by the domain prompt's DAILY FIGURES
recipe. That equivalence is measured rather than assumed — both reach 53 days
and 32 missed by the trigger — so the determination does not rest on the daily
construction at all. Averaging each station's own day first does move it,
to 52 days, and is left outside the band. (The sweep was run on days read as
the labels 0-23; the three daily constructions are remeasured here on the
hour-ending day.) The exceedance count is exact and two days sit close to the
line, 4 April 2020 at 150.12 and 9 March 2025 at 150.43. The hour-ending day
lifts 4 April 2020 over it (148.15 on the labels) and moves a dust episode's
peak day from 11 to 10 May 2024, which is why the label-day reading's 52 days
and 34 misses fail.

Ground truth is recomputed from the CSVs on every validation.

**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
Turn 1's query no longer dictates the per-row classification (the
variables carry it). Turn 2 no longer asks for the medians by name — the
mean-against-median reading was the exam and the query was handing it
over; it asks which sector is dirtier on a typical hour, scored as a
verdict that holds for the pooled median, the mean of per-station medians
and every spring alone, in both pollutants. The trigger counts stay: the
proposal is the colleague's and its rule is stated as a colleague would.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_MONTHS = (3, 4, 5)
_YEARS = tuple(range(2020, 2026))
_PM10_DAILY_LIMIT = 150.0
NORTHERLY = "northerly"
SOUTHERLY = "southerly"


def _spring() -> pd.DataFrame:
    """Spring station-hours with each one's own wind direction attached."""
    bj = DATA_DIR
    aq = pd.read_csv(bj / "air_quality.csv")
    met = pd.read_csv(bj / "met_era5.csv")
    met["datetime"] = pd.to_datetime(met["datetime"])
    for part in ("year", "month", "day", "hour"):
        met[part] = getattr(met["datetime"].dt, part)

    # Hour h of the air-quality record is the hour ENDING at h:00, so spring's
    # hours run from 1 March 01:00 to 1 June 00:00, and a day is its hours 1-23
    # plus hour 0 of the next date. Each hour still takes the wind of the
    # meteorology row stamped with the same label.
    stamp = pd.to_datetime(aq[["year", "month", "day", "hour"]])
    owner = stamp - pd.Timedelta(hours=1)
    aq = aq.assign(_ts=stamp, _date=owner.dt.normalize())
    aq = aq[owner.dt.month.isin(_MONTHS) & owner.dt.year.isin(_YEARS)]
    joined = aq.merge(
        met[["year", "month", "day", "hour", "station", "wind_dir_deg"]],
        on=["year", "month", "day", "hour", "station"],
        how="inner",
    )
    wd = joined["wind_dir_deg"]
    joined["sector"] = "other"
    joined.loc[(wd >= 135) & (wd <= 225), "sector"] = "southerly"
    joined.loc[(wd >= 315) | (wd <= 45), "sector"] = "northerly"
    return joined


def _sector_stats() -> dict:
    spring = _spring()
    north = spring[spring["sector"] == "northerly"]
    south = spring[spring["sector"] == "southerly"]
    return {
        "northerly_hours": int(len(north)),
        "southerly_hours": int(len(south)),
        "northerly_mean_pm25": float(north["PM2.5"].mean()),
        "southerly_mean_pm25": float(south["PM2.5"].mean()),
        "northerly_mean_pm10": float(north["PM10"].mean()),
        "southerly_mean_pm10": float(south["PM10"].mean()),
    }


def _typical_hour() -> dict:
    """Which sector is dirtier on a typical hour, asserted across the median of
    pooled station-hours, the mean of per-station medians, and every spring
    taken alone, for PM10 and for PM2.5 alike (all six springs' medians are
    higher under southerly flow in both pollutants)."""
    spring = _spring()
    verdicts = set()
    for pollutant in ("PM10", "PM2.5"):
        rows = spring.dropna(subset=[pollutant])
        north, south = rows[rows["sector"] == "northerly"], rows[rows["sector"] == "southerly"]
        verdicts.add(SOUTHERLY if south[pollutant].median() > north[pollutant].median() else NORTHERLY)
        by_station = rows.groupby(["sector", "station"])[pollutant].median().groupby("sector").mean()
        verdicts.add(SOUTHERLY if by_station["southerly"] > by_station["northerly"] else NORTHERLY)
        for _, year_rows in rows.groupby(rows["_date"].dt.year):
            n, so = year_rows[year_rows["sector"] == "northerly"], year_rows[year_rows["sector"] == "southerly"]
            verdicts.add(SOUTHERLY if so[pollutant].median() > n[pollutant].median() else NORTHERLY)
    if len(verdicts) != 1:
        raise RuntimeError(f"the typical-hour verdict is not invariant: {verdicts}")
    return {"typical_hour_dirtier_sector": verdicts.pop()}


def _exceedance_stats() -> dict:
    spring = _spring()

    # DAILY FIGURES: hourly network mean, then the mean of those hourly figures,
    # each hour on the day it belongs to.
    hourly = spring.groupby(["_date", "_ts"])["PM10"].mean()
    daily = hourly.groupby(level="_date").mean()
    exceeded = daily[daily > _PM10_DAILY_LIMIT]

    counts = spring.groupby(["_date", "sector"]).size().unstack(fill_value=0)
    for sector in ("northerly", "southerly"):
        if sector not in counts.columns:
            counts[sector] = 0
    on_exceeded = counts.loc[exceeded.index]
    # The proposed trigger, stated in the query: a day is flagged when its
    # southerly station-hours STRICTLY outnumber its northerly ones, so a tie
    # is not flagged. Scored as the days the trigger misses rather than the
    # days it catches, because that is the quantity the decision turns on.
    # Gate B round 9 required this: "more northerly hours than southerly" was
    # scored while the claim spoke of days the rule fails to flag, and five
    # defensible day rules give 8, 34, 39, 42 or 43 misses.
    flagged = on_exceeded["southerly"] > on_exceeded["northerly"]
    return {
        "spring_pm10_exceedance_days": int(len(exceeded)),
        "rule_missed_exceedance_days": int((~flagged).sum()),
    }


def _read(runtime, names) -> tuple:
    got = {}
    for name in names:
        val = runtime.retrieve(name)
        if val is None:
            return None, ValidatorResult(
                False, f"{name} not set", variables_not_set=True
            )
        if not is_finite_number(val):
            return None, ValidatorResult(False, f"{name}={val!r} is not a number")
        got[name] = val
    return got, None


def _is_int(val) -> bool:
    """A day or hour count must be an int. `bool` is an int subclass; True
    must not pass as a count of one."""
    return isinstance(val, int) and not isinstance(val, bool)


def validate_sector_contrast(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = (
        "northerly_hours",
        "southerly_hours",
        "northerly_mean_pm25",
        "southerly_mean_pm25",
        "northerly_mean_pm10",
        "southerly_mean_pm10",
    )
    got, failure = _read(runtime, names)
    if failure is not None:
        return failure

    gt = _sector_stats()
    errors = []
    for key in ("northerly_hours", "southerly_hours"):
        # int() would truncate: 50212.9 passed as 50212 until Gate B round 9
        # read these two guards. A count is an integer or it is not a count.
        if not _is_int(got[key]) or got[key] != gt[key]:
            errors.append(f"{key}={got[key]!r}, expected {gt[key]}")
    for key in names[2:]:
        if not reports_as(got[key], gt[key], decimals=2):
            errors.append(f"{key}={got[key]}, expected ~{gt[key]:.2f}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True,
        "correct: PM2.5 northerly {northerly_mean_pm25:.2f} vs southerly "
        "{southerly_mean_pm25:.2f}, PM10 northerly {northerly_mean_pm10:.2f} vs "
        "southerly {southerly_mean_pm10:.2f} ug/m3".format(**gt),
    )


def validate_tail_and_determination(
    response: str, runtime, turn: Turn
) -> ValidatorResult:
    got = {
        "spring_pm10_exceedance_days": runtime.retrieve("spring_pm10_exceedance_days"),
        "rule_missed_exceedance_days": runtime.retrieve("rule_missed_exceedance_days"),
    }
    missing = [n for n, v in got.items() if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    sector = runtime.retrieve("typical_hour_dirtier_sector")
    if sector is None:
        return ValidatorResult(False, "typical_hour_dirtier_sector not set", variables_not_set=True)
    gt = {**_typical_hour(), **_exceedance_stats()}
    errors = []
    if str(sector).strip().lower() != gt["typical_hour_dirtier_sector"]:
        errors.append(f"typical_hour_dirtier_sector={sector!r}, expected {gt['typical_hour_dirtier_sector']!r}")
    for key in ["spring_pm10_exceedance_days", "rule_missed_exceedance_days"]:
        if not _is_int(got[key]) or got[key] != gt[key]:
            errors.append(f"{key}={got[key]!r}, expected {gt[key]}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True,
        "correct: the typical hour is dirtier under {typical_hour_dirtier_sector} flow; the proposed "
        "trigger misses {rule_missed_exceedance_days} of {spring_pm10_exceedance_days} exceedance "
        "days".format(**gt),
    )


tools = []
variables = [
    Variable(
        "northerly_hours",
        None,
        "Store the number of northerly station-hours as an int. A station-hour "
        "is northerly when the wind direction on that same station's "
        "meteorology row for that same hour is 315 degrees or more, or 45 "
        "degrees or less, both bounds inclusive. Count the station-hours THE "
        "AIR-QUALITY RECORD REPORTS, whether or not their pollutant values "
        "are present; the meteorology file covers hours the air-quality file "
        "does not, and those are not counted.",
    ),
    Variable(
        "southerly_hours",
        None,
        "Store the number of southerly station-hours as an int, on the same "
        "counting rule and the same population, where southerly is 135 to "
        "225 degrees inclusive.",
    ),
    Variable(
        "northerly_mean_pm25",
        None,
        "Store the mean PM2.5 over the northerly station-hours as a float in "
        "ug/m3, 2 decimal places. Give every station-hour equal weight — pool "
        "the observations themselves rather than averaging each station first "
        "and then the stations — and take the mean over the hours that report "
        "PM2.5.",
    ),
    Variable(
        "southerly_mean_pm25",
        None,
        "Store the mean PM2.5 over the southerly station-hours as a float in "
        "ug/m3, 2 decimal places, on the same equal-weight pooling.",
    ),
    Variable(
        "northerly_mean_pm10",
        None,
        "Store the mean PM10 over the northerly station-hours as a float in "
        "ug/m3, 2 decimal places, on the same equal-weight pooling, over the "
        "hours that report PM10.",
    ),
    Variable(
        "southerly_mean_pm10",
        None,
        "Store the mean PM10 over the southerly station-hours as a float in "
        "ug/m3, 2 decimal places, on the same equal-weight pooling.",
    ),
    Variable(
        "typical_hour_dirtier_sector",
        None,
        "Store which of the two sectors carries the dirtier air on a typical "
        "spring hour — the hour in the middle of each sector's distribution "
        "rather than its average — as one of exactly these strings: "
        "'northerly', 'southerly'.",
    ),
    Variable(
        "spring_pm10_exceedance_days",
        None,
        "Store as an int the number of days in these six springs whose "
        "city-wide daily PM10 figure was above 150 ug/m3.",
    ),
    Variable(
        "rule_missed_exceedance_days",
        None,
        "Store as an int how many of those exceedance days the proposed "
        "trigger would NOT have flagged. The trigger fires on a day when that "
        "day holds strictly more southerly station-hours than northerly ones, "
        "under the same sector bounds; a day holding equal numbers of each "
        "does not fire it, and so counts as missed.",
    ),
]
validators = {
    "validate_sector_contrast": validate_sector_contrast,
    "validate_tail_and_determination": validate_tail_and_determination,
}
