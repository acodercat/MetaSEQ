"""One dark day is provable from the station alone, the other is not
(exceedance_anomaly_detection).

BASELINE. Turn 1 screens for the anomaly and turn 2 asks what settles it; the
discrimination the case is about — a broken sensor against a genuinely sunless
day — is the interpretation, and it lives in the CC claims.

Screening 2025's hourly radiation record for **station-days whose global solar
radiation is zero at every recorded hour** returns exactly **2**, both at Kau Sai
Chau, on 14 and 15 January. They are the only two in the whole file, which runs
2024-12-01 to 2026-08-08.

Neither is a dark day, but only one of them says so by itself:

    2025-01-15  Kau Sai Chau   global 0 at all 24 hours, diffuse 0 at all 24,
                               direct 148 293 654 764 786 771 416 692 565 342
                               through the daytime hours — a full clear-sky beam
                King's Park    global peaks 772, direct 874: a sunny day

    2025-01-14  Kau Sai Chau   global 0, diffuse 0, direct never above 5 —
                               every channel silent
                King's Park    global peaks 393 of which 367 is diffuse,
                               direct never above 4: a bright overcast day

On the 15th the station contradicts itself: its own direct channel records
several hundred watts of beam for ten consecutive hours while its global and
diffuse channels hold exact zeros. That is decidable from one station's record
and needs no neighbour. On the 14th every channel reads zero together, which is
what an instrument that has stopped reporting looks like, and nothing in that
day's own record contradicts it. It is not what a sunless site looks like
either: across the other 1,230 station-days in the file no hour from 08:00 to
16:00 reads a global of exactly zero, the dimmest midday peak is 27 W/m2 (Kau
Sai Chau, 4 August 2025) and the dimmest winter one 96. But that is
an argument from physics and from other days, and the day itself is judged on
external evidence — King's Park, 20 km west, reading 393 W/m2 of mostly diffuse
light. The 15th needs neither.

**What this case used to score, and why it was wrong.** Turn 2 counted
"station-days carrying at least one hour where global reads zero and direct
reads above it", which returns **67**, and the docstring built a six-week
degradation narrative on it. Gate B round 3 took the count apart: of the 238
qualifying rows, **225 have direct equal to exactly 1 W/m2**. Requiring direct
above 1 leaves **2** station-days; above 100 leaves **1**. Only 17 of the 67 have
any hit between 07:00 and 18:00. The 67 was a count of the pyranometer's thermal
offset, which the dataset manifest documents as a known feature and explicitly
declines to zero out — so the case had turned documented instrument noise into
evidence of an intermittent fault.

Two further claims went with it, and both were false:

- The old docstring said "a working radiometer does not report 0.00 even in
  darkness", citing the thermal offset. Measured on this file's 2025 rows,
  **6,929 of 7,292 night-time readings — 95.02 % — have global exactly zero**,
  and only 321 sit in the 1-12 W/m2 offset band. An exact zero at night is the
  norm, not a tell.
- It used the manifest's closure statistic, median (direct + diffuse) / global
  = 1.000, as evidence that a station reporting beam with zero global is
  internally inconsistent. The manifest's `known_limits` says the opposite in
  as many words: the direct column's reference plane is not established, and
  **"Do NOT build a case that treats direct + diffuse as a decomposition of
  global; it does not reliably close."** It licenses the direct/diffuse pair
  "only as a qualitative clear-versus-overcast indicator", which is all the
  rebuilt case uses it for: 786 W/m2 of beam means the sun was out, whatever
  plane it is referenced to. No arithmetic combines the channels anywhere here.

Measured degrees of freedom:

- **Which channel, pinned, and the counts are not what they look like.**
  Requiring global AND diffuse to be zero all day returns **2**, the same answer,
  because both channels are flat on both days. But requiring all three, or
  global and direct together, returns **0** — direct is never zero across either
  day, reaching 5 W/m2 on the 14th and 786 on the 15th, which is the whole point
  of the second turn. So the screen must name the global channel; naming "the
  radiation channels" would empty it.
- **The window does not matter.** 2025 gives 2 and the whole file gives 2.
- **Turn 2's margin is not delicate.** The two candidate days' peak direct
  readings are 786 and 5, a factor of 157. No threshold between them changes
  which day is identified.
- **Do NOT use a record-count criterion, which is where this case began.** The
  original proposal screened for days carrying "24 complete records", and both
  anomalies have 24 rows — but the archive samples at HH:00 and HH:50 and both
  land in the same hour, so 14 January has 24 rows spanning only 22 distinct
  hours and 15 January 23. Requiring 24 DISTINCT hours drops turn 1's answer
  from 2 to **0**. That the case's own completeness criterion fell to "a row
  count is not an hour count" is a lesson it kept.

**Turn 2, rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier turn told the agent that exactly one day was contradicted by its
own station and asked for that day and its peak direct reading — the query
carried the discrimination the case exists to test. The rebuilt turn asks the
agent to settle what was going on and scores two figures: the day the
station settles alone (2025-01-15, the 786 W/m2 beam) and what the sky was
doing at the other site on the other day ('bright overcast': on 14 January
King's Park peaks at 393 W/m2 with a direct beam never above 4). The sky
verdict is computed from the other site's channels with a direct threshold
for 'clear' and a global threshold for 'bright'; at 50, 100 or 200 W/m2 the
verdict is the same, because 393 of global against 4 of direct is not near
any of them. The count in turn 1 and the day in turn 2 are matched exactly.

Relationship to `hk_april_2025_coarse_dust_signature`, the other case in this
category: that one detects a real atmospheric event that must not be read as an
instrument problem; this one detects an instrument problem that must not be read
as weather. They are the two halves of the same discrimination.

All three ground truths are recomputed here from the radiation file.


**Gate B round 21 (2026-09-03) rejected the verdict on the second day, and the
case's own words were the evidence against it.** This docstring then said the
silent local record was equally consistent with an outage and a genuinely sunless
local observation (the all-zero midday is not, as above; the round's point about
the verdict stands regardless); `other_day_verdict` nonetheless refused the 'cannot be settled'
option it offered, whenever the OTHER site — 20 km away across water — was
brighter than an author-chosen threshold. Irradiance at two sites that far
apart can differ by everything under cloud or fog, and the record holds no
colocated instrument, status flag or maintenance log. The scored verdict is now
'cannot be settled', which is the option the query asks the agent to weigh, and
the claims carry what a working analyst would actually write: a fault is
strongly suspected, and here is what would settle it.

**Then Gate C rejected the replacement too, and the verdict came out
altogether (2026-09-03).** Pro stored 'instrument fault' against the new key
of 'cannot be settled' — and that answer is as defensible as the one it
failed, which is the original defect with its sign reversed. The variable was
asking the analyst to grade their own certainty, and P4a's test disposes of
it: name the measurement that would change the answer. There is none. No
maintenance log, no quality flag, no second instrument at Kau Sai Chau.

What the turn scores now is what the record settles: the day the station's own
contradiction settles (15 January), and what the sky was doing at the second
site (bright overcast). The certainty judgement lives in
`instrument_not_weather`, which requires the response to say how firmly it can
speak for each day — established for the 15th, a working diagnosis for the
14th.

The sky variable was also renamed. It read `other_day_sky`, "what the sky over
the territory was doing", and one station's three channels do not establish
that; it now names the site it describes.

Gate C on 2026-09-03 then had flash store 'clear' for King's Park on 14
January, where the global channel reads 393 W/m2 and the direct channel 4. A
direct beam of 4 W/m2 means the sun's disc was blocked, which is what overcast
IS, so the answer is wrong on the physics rather than on a convention — but the
enum named three states without saying what separated them, and a bright
January day at 393 W/m2 invites the word "clear". The three values now carry
their meanings, in the same form every other enum in this corpus uses.

What the record does settle is unchanged and is the sharper half of the case:
on 15 January the Kau Sai Chau instrument reports a direct beam of 786 W/m2
while its global channel reads zero all day, and no sky produces that. The
station contradicts itself.


**Gate A review 2026-09-06: the sky variable said "that day", whose nearest
antecedent was the day the OTHER variable had just stored.** Ground truth is the
sky on the silent day, 14 January, where King's Park reads a global 393 with a
direct beam of 4 — bright overcast. Under the grammatical reading the variable
invited, 15 January, King's Park reads global 772 and direct 874, which is
'clear', a value the probe table carries as a wrong path. Only the variable's
name pointed at the intended day; its text pointed at the other one. It now
names the day it means.

**Gate C review: neither variable said WHAT the station's record settles.** 6
of 24 runs read "the day the station's own record settles" as "settles what the
sky was doing", chose 14 January — every channel near zero, so the record
looks unambiguous about a dark sky — and then stored 'clear' for King's Park on
the 15th. On that reading both answers are coherent, so the pin was missing.
What the station settles is that its zeros are not the sky, and how it settles
it is that one of its own channels records sunlight while its global channel
reads zero; the variable now says both. The sky variable no longer leans on
"the OTHER of the two days": it names King's Park and identifies the day by the
property that defines it (none of Kau Sai Chau's channels records sunlight),
not by its date, which would hand over the first variable by elimination.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable

from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number

SKY_CLEAR = "clear"
SKY_BRIGHT_OVERCAST = "bright overcast"
SKY_DARK = "dark"

_YEAR = ("2025-01-01", "2026-01-01")


def _hourly() -> pd.DataFrame:
    df = pd.read_csv(
        DATA_DIR / "radiation_1min_hko.csv",
        parse_dates=["observed"],
    )
    df = df[(df["observed"] >= _YEAR[0]) & (df["observed"] < _YEAR[1])].copy()
    df["day"] = df["observed"].dt.normalize()
    return df


def _all_zero_station_days() -> int:
    """Station-days whose global radiation is zero at every recorded hour."""
    peak = _hourly().groupby(["station", "day"])["global_radiation_wm2"].max()
    return int((peak == 0).sum())


def _station_days() -> pd.DataFrame:
    """Per station-day peaks of the three channels."""
    return _hourly().groupby(["station", "day"]).agg(
        global_peak=("global_radiation_wm2", "max"),
        diffuse_peak=("diffuse_radiation_wm2", "max"),
        direct_peak=("direct_radiation_wm2", "max"),
    )


def _sky(row: pd.Series) -> str:
    """What a working station's channels say the sky was doing."""
    if row["direct_peak"] > 100:
        return SKY_CLEAR
    if row["global_peak"] > 100:
        return SKY_BRIGHT_OVERCAST
    return SKY_DARK


def _verdicts() -> Dict[str, object]:
    """The two dark days, settled: one by its own station, one by the other site.

    Asserted rather than assumed: exactly one all-zero-global day carries a
    direct beam (786 W/m2 against 5), and exactly one does not; if the record
    ever changed that, "the day" would not be a well-formed answer.
    """
    peaks = _station_days()
    dark = peaks[peaks["global_peak"] == 0]
    lit = dark[dark["direct_peak"] > 100]
    silent = dark[dark["direct_peak"] <= 100]
    if len(lit) != 1 or len(silent) != 1:
        raise AssertionError(
            f"expected one all-zero-global day carrying a direct beam and one "
            f"without, found {list(lit.index)} and {list(silent.index)}")
    (silent_station, silent_day), _ = next(silent.iterrows())
    elsewhere = peaks.xs(silent_day, level="day").drop(index=silent_station)
    if len(elsewhere) != 1:
        raise AssertionError(f"expected one other site on {silent_day:%Y-%m-%d}, "
                             f"found {list(elsewhere.index)}")
    other_sky = _sky(elsewhere.iloc[0])
    return {
        "day_settled_by_the_station_alone": f"{lit.index[0][1]:%Y-%m-%d}",
        "other_day_sky_at_the_second_site": other_sky,
    }


def _normalise(value) -> str:
    return str(value).strip().lower()


def validate_zero_days(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("zero_global_station_days")
    if val is None:
        return ValidatorResult(
            False, "zero_global_station_days not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"zero_global_station_days={val!r} is not a number"
        )

    gt = _all_zero_station_days()
    if compare_numeric(val, gt, tolerance=0):
        return ValidatorResult(True, f"correct: {val} station-days")
    return ValidatorResult(False, f"zero_global_station_days={val}, expected {gt}")


def validate_settlement(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "day_settled_by_the_station_alone": runtime.retrieve("day_settled_by_the_station_alone"),
        "other_day_sky_at_the_second_site": runtime.retrieve("other_day_sky_at_the_second_site"),
    }
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)
    gt = _verdicts()
    wrong = []
    # A date, a string and a Timestamp are all reasonable things to have
    # stored; what is scored is the day.
    day = got["day_settled_by_the_station_alone"]
    try:
        parsed = pd.Timestamp(day)
        if parsed.tz is not None:
            parsed = parsed.tz_localize(None)
    except (TypeError, ValueError):
        parsed = None
    if parsed is None or pd.isna(parsed):
        wrong.append(f"day_settled_by_the_station_alone={day!r} is not a date")
    elif f"{parsed.normalize():%Y-%m-%d}" != gt["day_settled_by_the_station_alone"]:
        wrong.append(f"day_settled_by_the_station_alone={day!r}, "
                     f"expected {gt['day_settled_by_the_station_alone']}")
    wrong += [f"{name}={got[name]!r}, expected {gt[name]!r}"
              for name in ["other_day_sky_at_the_second_site"]
              if _normalise(got[name]) != _normalise(gt[name])]
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


tools = []
variables = [
    Variable(
        "zero_global_station_days",
        None,
        "Store how many station-days in 2025 have a global solar radiation "
        "reading of zero at every hour recorded, as an integer.",
    ),
]
variables += [
    Variable("earlier_day_peak_direct_wm2", None, "Store Kau Sai Chau's peak direct radiation on the earlier flagged all-zero-global day, as a float in W/m2 to 1 decimal place."),
    Variable("later_day_peak_direct_wm2", None, "Store the same on the later flagged day, as a float in W/m2 to 1 decimal place."),
    Variable("earlier_day_peer_peak_global_wm2", None, "Store King's Park's peak global radiation on the earlier flagged Kau Sai Chau day, as a float in W/m2 to 1 decimal place."),
    Variable("earlier_day_peer_peak_direct_wm2", None, "Store King's Park's peak direct radiation on that same earlier day, as a float in W/m2 to 1 decimal place."),
]


def validate_channel_peaks(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "earlier_day_peak_direct_wm2": runtime.retrieve("earlier_day_peak_direct_wm2"),
        "later_day_peak_direct_wm2": runtime.retrieve("later_day_peak_direct_wm2"),
        "earlier_day_peer_peak_global_wm2": runtime.retrieve("earlier_day_peer_peak_global_wm2"),
        "earlier_day_peer_peak_direct_wm2": runtime.retrieve("earlier_day_peer_peak_direct_wm2"),
    }
    missing = [n for n,v in got.items() if v is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    peaks = _station_days()
    zero = peaks[peaks.global_peak.eq(0)].sort_index(level="day")
    if len(zero) != 2:
        raise AssertionError("two flagged station-days required")
    earlier, later = zero.index[0], zero.index[1]
    peer = peaks.loc[("King's Park", earlier[1])]
    gt = {"earlier_day_peak_direct_wm2":zero.loc[earlier,"direct_peak"], "later_day_peak_direct_wm2":zero.loc[later,"direct_peak"], "earlier_day_peer_peak_global_wm2":peer.global_peak, "earlier_day_peer_peak_direct_wm2":peer.direct_peak}
    if not all(compare_numeric(got[n], v, tolerance=0) for n,v in gt.items()):
        return ValidatorResult(False, "incorrect channel peak(s)")
    return ValidatorResult(True, "channel measurements accepted")

validators = {
    "validate_zero_days": validate_zero_days,
    "validate_settlement": validate_settlement,
    "validate_channel_peaks": validate_channel_peaks,
}
