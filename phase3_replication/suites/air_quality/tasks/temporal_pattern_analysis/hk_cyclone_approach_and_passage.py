"""A fall this large has two ends, and only one of them is clean
(temporal_pattern_analysis).

BASELINE with an unnamed concept at its centre. Nothing here says cyclone,
subsidence, scavenging, periphery or washout: the query asks for the largest
day-to-day fall in the summer's fine particulate and then for where the day
before it sits in its own month, and knowing that an account of the clean end
alone is not an account of the event — and going to the meteorological record
to see what spans both days — IS the exam.

**The condition in the record.** Over June to August 2025, territory PM2.5
falls between consecutive days by more than 6 ug/m3 five times. One of them is
not like the others:

    2025-07-19 -> 2025-07-20     18.4345 -> 4.6344     fall 13.8001
    2025-07-07 -> 2025-07-08     15.8914 -> 6.6044     fall  9.2870
    2025-06-03 -> 2025-06-04     14.1305 -> 7.4354     fall  6.6951
    2025-07-30 -> 2025-07-31     16.3669 -> 9.7948     fall  6.5720
    2025-08-09 -> 2025-08-10     12.4882 -> 6.0575     fall  6.4306

The largest is half again the next, and the two days it spans sit near opposite
ends of their month: of July's 31 days exactly TWO are dirtier than 19 July,
and exactly ONE is cleaner than 20 July.

**This table read 18.8860 -> 4.6068 and a fall of 14.2792 until a Gate A review
on 2026-09-06, and those are the day-of-stamp figures the corpus abandoned on
2026-08-30.** The verdict baseline has carried 18.89 / 4.61 as a WRONG path ever
since, so the docstring was quoting as its headline the reading the case exists
to reject; the closing note claiming the figures had been re-measured under the
hour-ending convention was not true of this table. Every row above is now the
hour-ending reading `_daily()` computes, and the third and fourth rows swap
under it.

**What the record says happened, without leaving the database.** The lowest
station pressure of the whole record — 975.1 hPa — was recorded on 20 July
2025, and the highest gust that day reached 234 km/h. On 19 July the pressure
had already fallen to 991.2 and the gust reached 92. The system was approaching
through 19 July and over the territory on 20 July.

Externally, and recorded here for the docstring rather than for the agent: this
is Typhoon Wipha (2506), for which the Hong Kong Observatory hoisted Hurricane
Signal No. 10 on the morning of 20 July 2025, its first since 2023. HKO's
report gives maximum gusts of 234 km/h at Ngong Ping, 173 at Cheung Chau Beach
and 156 at Waglan Island. The database's 234 km/h for that day matches HKO's
Ngong Ping figure exactly, which is a useful check on the record and not
something the case asks the agent to know.

**Why the naive account is incomplete, and how far the record lets the case
go.** A desk that looks at 20 July alone sees the second-cleanest day of the
month and writes that the weather cleared the air. That is true, and it omits
that 19 July was the second-DIRTIEST day of the month. Both days sit inside one
exceptional synoptic transition, and an account that reports only the clean end
is an account of half an event.

**What the case must NOT ask for, which Gate B round 11 established.** That the
system PRODUCED the preceding load. The textbook account — an approaching
cyclone subsides ahead of itself, suppresses mixing, stalls the wind and the
load builds under it — is plausible, and HKO's own report confirms Wipha's
outer subsiding air reached Hong Kong on 19 July. But two daily means do not
separate subsidence from regional transport, local emission or reduced
ventilation, and regional transport is not refuted by anything in the record.
The first version of this case required that attribution and both Gate C models
failed it; round 11 ruled the claim, not the models. The claim now asks for the
association and for restraint about the source, and a response that reports the
transition and declines to attribute the build-up satisfies it.

Ozone moves with it — the territory peak falls from 114.5 to 56.5 across the
same two days — which is corroboration a response may reach for. It is not
scored because neither turn asks for an ozone number. It is NOT unscored
because the population is open: the domain prompt defines a territory value
over whichever sites report THAT quantity, so 56.5 is the figure and the 56.0
this docstring first carried came from restricting ozone to hours that also
reported PM2.5, which the convention forbids. Round 11 caught both the number
and the false reason given for leaving it out.

**The professional consequence.** Hong Kong issues health advice on the index,
and the record shows where the burden fell: on 19 July the stored AQHI spans 2
to 8 with five HIGH and three VERY HIGH station-hours, while on 20 July it
spans 1 to 3 and every station-hour is LOW. The health load was on the day
before the clean one, and an account built on the clean end alone loses it.

An earlier version of this paragraph said the advice was needed "the day before
the signal went up". That is wrong and round 11 corrected it: HKO issued Signal
No. 1 at 02:20 on 19 July and No. 3 at 14:20 the same day, so warnings were
already up. Only the higher signals came on 20 July. The point survives the
correction — the health burden and the storm warning peaked on different days —
but the sentence as written asserted something the record contradicts.

**Pins, and where each one goes** (`case_design_standard.md` §3.1). The daily
territory figure is the domain prompt's TERRITORY FIGURES convention — the
hourly mean across whichever sites report, then the mean of those hourly
figures — and is not restated in the query. June to August 2025 is stated in
the query because the window is arbitrary rather than the exam. Everything else
the case needs, it needs the agent to find.

**Readings measured and excluded.**

    scored, the domain's hourly-then-daily figure       18.4345 / 4.6344
    pooling every station-hour into the day            18.5843 / 4.7291
    each station's own daily mean, then averaged       18.6056 / 4.6346

Both alternatives preserve the ranking, the date pair and the count. On the day
the fall came FROM they are out by 0.150 and 0.171, comfortably past the
+/-0.02 band; on the day it fell TO the pooled reading is out by 0.095 and the
per-station reading by 0.0002, which is well INSIDE the band. So the
per-station reading is separated on one of the two scored means and not the
other — both are scored, so it is refused, but it is refused by a single figure
and that is worth stating rather than claiming a margin the case does not have.

These three rows were re-measured under the hour-ending day on 2026-09-06,
with the headline table above; the figures they replace (19.0093 / 4.6949 and
19.0269 / 4.5969) were day-of-stamp readings, and the deltas derived from them
described a separation the case did not have. The date and the count are exact and no
convention moves them, so what the case actually rests on is finding the right
pair of days; the means confirm the reader found them the way the domain asks.

**Overlap with `hk_extreme_wind_corroboration`, and it is larger than this
docstring first claimed.** That case scores the 975.1 hPa minimum, its date,
and how many stations exceeded 80 km/h on it against the separate 319 km/h gust
day; its subject is that a local squall and a territory-wide cyclone are
different things. This case scores no meteorological quantity, so there is no
overlap in PV. There IS overlap in CC: the claim here sends the response to the
same 20 July meteorology and asks it to read the same territory-wide system,
which the older case scores and explains. Round 11 ruled the two are not
duplicates — the PM2.5 day pair and the editorial decision are distinct — but
"they ask nothing in common" was an overstatement and is withdrawn.

All ground truths are recomputed from the database at validation time.


Figures re-measured 2026-08-30 under the hour-ending timestamp convention
(see the prompt's TIMESTAMPS section and `hk_ozone_aqo_day_boundary`).
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

_SPAN = ("2025-06-01", "2025-09-01")
_BAND = 0.02


def _daily() -> pd.Series:
    """Territory PM2.5 by day: the hourly mean across reporting sites, then the
    mean of those hourly figures, per the domain prompt's TERRITORY FIGURES."""
    frame = read_frame(text("""
        select datetime, pm2_5
        from hourly_station_air_quality
        where datetime > :lo and datetime <= :hi and pm2_5 is not null
    """), {"lo": _SPAN[0], "hi": _SPAN[1]})
    hourly = frame.groupby("datetime")["pm2_5"].mean()
    daily = hourly.groupby((hourly.index - pd.Timedelta(hours=1)).normalize()).mean()
    return daily


def _figures() -> Dict[str, object]:
    daily = _daily()
    fall = daily.shift(1) - daily
    end = fall.idxmax()
    july = daily[(daily.index >= "2025-07-01") & (daily.index < "2025-08-01")]
    before = daily.loc[end - pd.Timedelta(days=1)]
    return {
        "largest_fall_end_date": str(end.date()),
        "pm25_day_before": float(before),
        "pm25_fall_day": float(daily.loc[end]),
        "summer_fall_magnitude": float(fall.loc[end]),
        "july_days_dirtier_than_day_before": int((july > before).sum()),
    }


def _read(runtime, names):
    got = {name: runtime.retrieve(name) for name in names}
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return got, ValidatorResult(
            False, f"{', '.join(missing)} not set", variables_not_set=True)
    return got, None


def _is_int(val) -> bool:
    """`bool` is an `int` subclass; True must not pass as a count of one."""
    return isinstance(val, int) and not isinstance(val, bool)


def validate_largest_fall(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = ("largest_fall_end_date", "pm25_day_before", "pm25_fall_day")
    got, failure = _read(runtime, names)
    if failure is not None:
        return failure
    for key in ("pm25_day_before", "pm25_fall_day"):
        if not is_finite_number(got[key]):
            return ValidatorResult(False, f"{key}={got[key]!r} is not a number")

    gt = _figures()
    wrong = []
    if str(got["largest_fall_end_date"])[:10] != gt["largest_fall_end_date"]:
        wrong.append(f"largest_fall_end_date={got['largest_fall_end_date']!r}, "
                     f"expected {gt['largest_fall_end_date']}")
    wrong += [f"{key}={got[key]}, expected ~{gt[key]:.2f}"
              for key in ("pm25_day_before", "pm25_fall_day")
              if not reports_as(got[key], gt[key], decimals=2)]
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {gt['pm25_day_before']:.2f} to {gt['pm25_fall_day']:.2f} "
              f"ug/m3 into {gt['largest_fall_end_date']}")


def validate_where_it_sits(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = ("summer_fall_magnitude", "july_days_dirtier_than_day_before",
             "pm25_day_before", "pm25_fall_day")
    got, failure = _read(runtime, names)
    if failure is not None:
        return failure
    if not is_finite_number(got["summer_fall_magnitude"]):
        return ValidatorResult(
            False, f"summer_fall_magnitude={got['summer_fall_magnitude']!r} "
                   f"is not a number")
    if not _is_int(got["july_days_dirtier_than_day_before"]):
        return ValidatorResult(
            False, f"july_days_dirtier_than_day_before="
                   f"{got['july_days_dirtier_than_day_before']!r} is not an integer")

    gt = _figures()
    wrong = []
    if not reports_as(got["summer_fall_magnitude"], gt["summer_fall_magnitude"], decimals=2):
        wrong.append(f"summer_fall_magnitude={got['summer_fall_magnitude']}, "
                     f"expected ~{gt['summer_fall_magnitude']:.2f}")
    if got["july_days_dirtier_than_day_before"] != gt["july_days_dirtier_than_day_before"]:
        wrong.append(f"july_days_dirtier_than_day_before="
                     f"{got['july_days_dirtier_than_day_before']}, "
                     f"expected {gt['july_days_dirtier_than_day_before']}")
    # R5: the magnitude is the difference between the two levels turn 1 stored.
    # Scored because a fall reported without reference to the levels it spans is
    # the shape of answer this case exists to refuse.
    both = (is_finite_number(got["pm25_day_before"])
            and is_finite_number(got["pm25_fall_day"]))
    if both:
        implied = got["pm25_day_before"] - got["pm25_fall_day"]
        if not compare_numeric(got["summer_fall_magnitude"], implied, tolerance=2 * _BAND):
            wrong.append(
                f"the fall of {got['summer_fall_magnitude']} does not match the "
                f"{got['pm25_day_before']} and {got['pm25_fall_day']} reported "
                f"for the two days, which differ by {implied:.2f}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: a fall of {gt['summer_fall_magnitude']:.2f} ug/m3, and "
              f"{gt['july_days_dirtier_than_day_before']} July day was dirtier "
              f"than the day it fell from")


tools = []
variables = [
    Variable(
        "largest_fall_end_date",
        None,
        "Store the date on which territory PM2.5 fell furthest from the day "
        "before it, anywhere in June, July and August 2025, as a string in "
        "YYYY-MM-DD form — the LATER of the two days.",
    ),
    Variable(
        "pm25_day_before",
        None,
        "Store the territory PM2.5 of the day that fall came from, as a float "
        "in ug/m3, 2 decimal places.",
    ),
    Variable(
        "pm25_fall_day",
        None,
        "Store the territory PM2.5 of the day it fell to, as a float in "
        "ug/m3, 2 decimal places.",
    ),
    Variable(
        "summer_fall_magnitude",
        None,
        "Store how far it fell, as a float in ug/m3, 2 decimal places.",
    ),
    Variable(
        "july_days_dirtier_than_day_before",
        None,
        "Store how many days in July 2025 carried a higher territory PM2.5 "
        "than the day the fall came from, as an integer.",
    ),
]
validators = {
    "validate_largest_fall": validate_largest_fall,
    "validate_where_it_sits": validate_where_it_sits,
}
