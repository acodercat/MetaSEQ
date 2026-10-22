"""Beijing 2024 PM2.5 — a detector that cannot be run on the day it scores
(exceedance_anomaly_detection).

Anomaly-detection BASELINE, declared one from the start: the desk's own
detector is specified as a desk would specify it, and the colleague's
version is relayed as the colleague would describe it (the rebuild note at
the end). The diagnostic weight sits in the CC channel, where the naive
move is to read the second turn's smaller count as a cleaner, less trigger-happy
detector.

Flagging a day when its PM2.5 sits more than three standard deviations above
the 30 days before it:

- Turn 1 (realtime_alert_days, max_realtime_z): 8 days of 2024, the strongest
  4.2034 on 26 October.
- Turn 2 (centered_alert_days): 1 day, when the same rule is computed on a
  30-day window CENTRED on the day being scored.

The centred window is the standard implementation shortcut — `center=True` on a
rolling mean — and it needs the fifteen days after the day it is scoring, so it
cannot be evaluated until they have happened. On a series being watched for
public warnings that is not a detail: none of the eight alerts is among the
centred detector's, and its single alert, 12 April, is a day the trailing
detector scores at 2.9842, just under the line.

The direction of the error is the part worth having, because it is the opposite
of the intuition that peeking makes a detector sharper. A centred window
contains the very day it is scoring, so a large value inflates the mean AND the
standard deviation of its own reference distribution and partly hides itself.
Leakage here does not manufacture a crop of false alarms; it SUPPRESSES all
eight of the trailing detector's.

Robustness, swept as 32 COMBINATIONS rather than one convention at a time.
Crossing window 30 or 31, population or sample standard deviation, scoring only
days with 30 days of 2024 history or reaching back into 2023, hourly network
means or pooled station-hours, and a threshold of strictly above 3 or at least
3, the centred count is 1 in all 32 and the trailing count is 8 in the eight
that take a 30-day window and the sample divisor, 9 where one of those two
changes and 10 where both do. Both are pinned on `realtime_alert_days`, so 9
and 10 are forbidden readings, and the three conventions left unpinned —
history, recipe, threshold form — never move it.

THE MARGIN IS THIN and is recorded rather than hidden. The eighth trailing z is
3.0017 (4 September) and the ninth 2.9842 (12 April). Per-station daily means
averaged, a recipe the domain convention excludes, swap the two (2.9838 and
3.0083) and still count 8; rounding the daily means to one decimal or the
hourly figures to whole units keeps 8 too. So the count has held under every
perturbation tried, but which days make it is not stable, and nothing that
scores membership should be built on it. On the centred side the first z is
3.1048 and the second 2.8814.

These figures are on the record's own day: label h is the hour ending at h:00,
so a day is labels 1-23 and label 0 of the next date. Grouping the calendar
labels instead gave 9 alerts and a maximum of 4.3305, with 12 April among the
nine — the figures this case scored until the day convention was fixed
corpus-wide, now forbidden readings like any other wrong day.

Pins, each measured.

- THE STANDARD DEVIATION AND THE WINDOW LENGTH, which move the count and the
  maximum both: a population divisor reads 9 and 4.2753, a 31-day window 9 and
  4.2790, against 8 and 4.2034 for the sample divisor on 30 days. Compounded,
  the two read 10 and 4.3498. `realtime_alert_days` names both the window
  length and the sample convention.
- ALL 366 DAYS SCORED, the first thirty drawing their reference from the end of
  2023. Restricting to 2024's own history leaves 336 days scored; both give 8
  alerts and the same maximum, so this pin buys reproducibility rather than a
  different answer, and the docstring says which.
- The window EXCLUDES the day being scored in turn 1 and INCLUDES it in turn 2.
  That is the whole comparison, and both variables state it: turn 1's says
  the day itself is excluded, turn 2's that the day is one of the 30.

- THE DAILY RECIPE, which the domain prompt's DAILY FIGURES convention pins
  and which an earlier revision of this
  paragraph wrongly called measured-indifferent. Pooling station-hours leaves
  both counts at 8 and 1, so it is indifferent for them, but it moves the
  maximum to 4.2028 — 0.0006 from the correct 4.2034 (on calendar labels the
  gap was 0.0003, which the +/-0.001 band this case originally carried
  ACCEPTED). Gate B was right: a band must not absorb a method the case
  forbids. The band is 0.0001, which still covers the 0.00005 that 4-decimal
  reporting needs and puts the pooled reading six bands out.

Measured indifferent, so stated rather than pinned: the alignment of an
even-length centred window. Windows of 30 and 31 both give 1, so the case does
not depend on how a library splits a 30-day window around its centre.

Excluded readings in the probe table: the centred count reported for the
trailing turn and the reverse; 4.2753 and 4.2790 for the maximum; 8 (the
trailing count stored for the centred one) and 3, which came from a live run
and is worth its own paragraph. A Gate C run on the rebuilt turn (2026-09-02)
stored 0 for the colleague's detector; none of the four alignments of a
30-day window around the day (14/15, 15/14, 15/15, 14/14) reproduces it —
all give 1 — so its construction is unrecorded and 0 stays a wrong path
without an explanation.

That model, before turn 2 asked for anything, built a symmetric window of the
30 days either side of each day that EXCLUDED the day itself, and got 3 alerts.
The reading is instructive rather than merely wrong: leaving the scored day out
of its own reference distribution flags 3 where the centred window flags 1, and
narrowing the same leave-one-out window to +/-15 days flags 4. (On calendar
labels, where that run worked, the two read 3 and 5.) That is direct evidence for the mechanism this case rests on — the
suppression comes from self-inclusion, not from the mere presence of future
days. It remains an excluded reading here because turn 2 names a window that
contains the day, and because a leave-one-out symmetric window still cannot be
computed in real time.

It is also why the turn-2 variable has to say so (below): +/-15 days with the
day left out is exactly what "the same detector, centred" means if "the same"
is taken to carry over turn 1's exclusion, and it gives 4.

Distinct from `beijing_sharpest_cleanout`, which reads the same October
episode: that case dates the sharpest CLEAN-OUT, 27 October, and measures the
drop and the ventilation that caused it. This one never asks for a date. They
share an episode because the year has one dominant one, not a question.

Tolerances: 0 on the two counts — the only conventions that move them are the
window length and the divisor, both pinned. +/-0.0001 on the maximum, against
4-decimal reporting, which needs 0.00005. The nearest excluded reading is the
pooled recipe at six bands, then the population divisor at 0.072.

Observed live behaviour, AGAINST AN EARLIER REVISION carrying a +/-0.001
maximum band: the first model to run this case passed both turns at the first
attempt, in six steps and three, on calendar-label days. It got both counts
right, but it formed its
daily means by POOLING station-hours and reported 4.3302 — the reading the
case
forbids and that band absorbed. Under the band this case now carries it fails
turn 1, which is the correct outcome. The pass was the band's fault, not the
model's competence, and it is the clearest evidence in this corpus for the rule
that a band absorbs implementation variance and never a method the case names.
The same run also filled `centered_alert_days` speculatively during turn 1,
before the question was asked, with the leave-one-out reading described above;
turn 2 replaced it with the correct 1.

All three ground truths are recomputed here from the CSV.

**Turn 2 rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier query said the centred window "contains the day itself and the
days following it" — the reveal. The rebuilt query relays a colleague's
detector as the colleague would describe it (scored against the 30 days
around the day, far less trigger-happy) and asks which to run; the count
stays (1 under all 32 conventions swept) and
the choice is scored as a variable. The claims still carry the two reasons.


**Gate A review 2026-09-06 finished the job the 2026-09-02 rebuild started.**
That rebuild took "contains the day itself and the days following it" out of the
query, calling it the reveal — and the same clause was sitting on
`centered_alert_days` as "so that it holds the day itself and the days around
it". Both required claims turn on exactly that: that the window contains the day
being scored and days after it. Saying it on a variable is saying it. The clause
is gone; "centred on the day being scored" is the definition of the window and
what it contains is the agent's to work out.

**That left the self-inclusion unpinned, and it is a pin, not a reveal.** Turn
1's variable says its window excludes the day; turn 2 asked for "the same rule"
centred on the day, and the query spoke of "the 30 days around it". Carrying
the exclusion across — fifteen days either side, the day out — is the literal
reading of both, and it flags 5, so a model that read carefully had a
defensible wrong answer and the key could only be reached by guessing at
`center=True`. The variable now says the day is one of the 30, and the query
speaks of a window centred on the day rather than the days around it. What
stays the agent's to work out is everything the claims score: that the window
reaches fifteen days past the day it scores and so cannot run in real time,
and that self-inclusion is why it flags FEWER days — knowing the day is in the
window is not knowing what that does to the score. That reading (4 on the record's own day) is now excluded alongside the
trailing count and 3.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_YEAR = 2024
_WINDOW = 30
_THRESHOLD = 3.0
DETECTOR_TRAILING = "the trailing detector"
DETECTOR_CENTRED = "the colleague's detector"
DETECTOR_EITHER = "either"


def _daily() -> pd.Series:
    aq = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Label h is the hour ending at h:00: a day is its labels 1-23 and label 0
    # of the next date, so the label shifted back one hour carries the date.
    aq["ts"] = pd.to_datetime(aq[["year", "month", "day", "hour"]])
    aq["date"] = (aq["ts"] - pd.Timedelta(hours=1)).dt.normalize()
    obs = aq.dropna(subset=["PM2.5"])
    hourly = obs.groupby(["date", "ts"])["PM2.5"].mean()
    return hourly.groupby(level=0).mean().sort_index()


def _scores() -> dict:
    daily = _daily()

    # Real time: the 30 days strictly before the day being scored. The shift
    # runs on the whole record, so January 2024 draws on the end of 2023.
    prior = daily.shift(1).rolling(_WINDOW, min_periods=_WINDOW)
    trailing = (daily - prior.mean()) / prior.std(ddof=1)

    # Lookahead: a window centred on the day, which contains it and the days
    # after it.
    centred_window = daily.rolling(_WINDOW, center=True, min_periods=_WINDOW)
    centred = (daily - centred_window.mean()) / centred_window.std(ddof=1)

    year = daily.index.year == _YEAR
    return {
        "realtime_alert_days": int((trailing[year] > _THRESHOLD).sum()),
        "max_realtime_z": float(trailing[year].max()),
        "centered_alert_days": int((centred[year] > _THRESHOLD).sum()),
        # A judgement, not a computation: a detector whose window contains
        # days that have not happened yet cannot be run on the day it scores.
        "detector_to_run": DETECTOR_TRAILING,
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

    gt = _scores()
    errors = [
        f"{name}={got[name]}, expected {gt[name]:.4f}"
        for name in names
        if not (reports_as(got[name], gt[name], decimals=4) if name == "max_realtime_z" else compare_numeric(got[name], gt[name], tolerance=0))
    ]
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True, "correct: " + ", ".join(f"{n} {gt[n]:.4f}" for n in names)
    )


def validate_realtime_detector(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check(
        runtime,
        ("realtime_alert_days", "max_realtime_z"),
        {"realtime_alert_days": 0, "max_realtime_z": 0.0001},
    )


def validate_lookahead_detector(response: str, runtime, turn: Turn) -> ValidatorResult:
    count = runtime.retrieve("centered_alert_days")
    choice = runtime.retrieve("detector_to_run")
    missing = [n for n, v in (("centered_alert_days", count), ("detector_to_run", choice)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    if not is_finite_number(count):
        return ValidatorResult(False, f"centered_alert_days={count!r} is not a number")
    gt = _scores()
    errors = []
    if not compare_numeric(count, gt["centered_alert_days"], tolerance=0):
        errors.append(f"centered_alert_days={count}, expected {gt['centered_alert_days']}")
    if str(choice).strip().lower() != gt["detector_to_run"]:
        errors.append(f"detector_to_run={choice!r}, expected {gt['detector_to_run']!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: {gt['centered_alert_days']} day flagged; run {gt['detector_to_run']}")


tools = []
variables = [
    Variable(
        "realtime_alert_days",
        None,
        "Store the number of days of 2024 flagged by the trailing-window "
        "detector as an integer, working on the daily series. A day's "
        "score is its distance above the mean of the 30 calendar days "
        "immediately before it — the day itself excluded — in units of their "
        "sample standard deviation (n-1 divisor), reaching back into the end "
        "of 2023 so that January is scored too; a day is flagged when the "
        "score exceeds 3.",
    ),
    Variable(
        "max_realtime_z",
        None,
        "Store the largest trailing-window score of 2024 as a float, 4 "
        "decimal places.",
    ),
    Variable(
        "centered_alert_days",
        None,
        "Store the number of days of 2024 flagged by the colleague's "
        "detector as an integer — the same rule, but with the 30-day window "
        "centred on the day being scored and counting that day itself as "
        "one of the 30.",
    ),
    Variable(
        "detector_to_run",
        None,
        "Store which detector the desk should run, as one of exactly these "
        f"strings: '{DETECTOR_TRAILING}', '{DETECTOR_CENTRED}', '{DETECTOR_EITHER}'.",
    ),
]
validators = {
    "validate_realtime_detector": validate_realtime_detector,
    "validate_lookahead_detector": validate_lookahead_detector,
}
