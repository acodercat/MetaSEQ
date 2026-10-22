"""Current classification: BASELINE. The variable contract explicitly excludes
calm zero-direction rows, so this tests execution rather than discovery of the
calm-code hazard. Historical rationale follows.

Hours of north wind at Wetland Park, December 2025 — calm is spelled north
(statistical_characterization).

DIAGNOSTIC TRAP, and the premise kind: the quantity asked for has a correct
value only once a property of the record has been noticed, and the naive
count is 3.8 times the true one.

`hourly_station_weather` stores a calm hour — wind speed zero — with
`wind_degree = 0` and `wind_direction = 'N'`. Of the 4,554 zero-speed
station-hours in 2025, 4,537 carry exactly that pair. Direction is undefined at
zero speed; the stored north is a code, not an observation, and any count of
"north" that reads the direction column alone inherits every calm hour.

Wetland Park is the site where it bites hardest. Over December 2025, 743
reported hours:

    calm hours (stored speed zero)                       241
    hours whose direction column reads N                 326
    hours with a wind from the north                      85   <- the answer

**The naive path and what it produces.** `wind_direction == 'N'` gives 326.
The query asks for hours the wind BLEW from the north, and a calm hour is not
an hour the wind blew from anywhere — so 326 is a wrong computation of the
named quantity, not a second reading of it. That is the same bucket-A
specification `hk_visibility_extinction_aggregation` rests on: the estimand is
identified by plain meaning, and working out that the direction column cannot
answer it alone is the exam.

**Why the domain prompt does NOT carry a wind convention, and the first
version of this case did.** A WIND block was written into the HK prompt —
"a calm hour has no direction; directional statistics are taken over hours
with a wind" — on the §3.1 argument that it is meteorological practice. Gate C
then ran the case on two models. Both excluded calm because the prompt told
them to, both returned the right figure, and **neither noticed or mentioned
that the calm hours are filed under N** — under that convention the coding no
longer affected anything they were asked for, so nothing made them look. The
case had become a test of reading the prompt, the claim was asking for a fact
with no consequence, and the triage standard for "a groupby with an
interpretation in the docstring" applied in full. The block is gone; this
docstring is where the lesson lives.

**This is a decision about this case, not an amendment to §3.1**, and Gate B
round 9 was right to insist on the difference. §3.1 stands: a stable external
convention belongs in the domain prompt, and "a calm hour has no direction" is
exactly such a convention. What makes it inadmissible HERE is not that it is
the question in general — it is that stating it in the prompt discloses the
premise this particular case tests, which the first Gate C run demonstrated by
running it. Another case that needed the same convention as background, and did
not test whether an agent arrives at it, would be entitled to have it in the
prompt. The justification is specific and has to be re-argued each time; it is
not a rule that can be cited.

Pins, each measured, on the variables rather than the query.

- THE EIGHT-POINT COMPASS POINT N, stated on `northerly_hours`. The degree
  field offers other norths: the 16-point sector (337.5–22.5) over windy
  hours also reads 85, so that reading is harmless, but a 90-degree quadrant
  (315–45) reads 154 and is foreclosed by naming the compass point.
- A CALM HOUR IS NOT A NORTH-WIND HOUR, stated on `northerly_hours` and tied
  to the calm definition on `calm_hours`. See the resolution below for why
  this pin is on the variable after all.
- CALM IS A STORED SPEED OF ZERO, stated on `calm_hours`. Some practice calls
  anything under 0.5 m/s calm; that reading gives 67 northerly hours. The
  pin sits on the calm count, not on the northerly count — a model that reads
  it there and still counts north from the direction column alone has made
  the connection the case is about fail to happen, which is the trap.
- DECEMBER 2025, half-open per TIME WINDOWS: 743 hours, one short of the
  month (2025-12-18 16:00 is absent).

Tolerance 0 on both counts. The naive 326 is 241 away; the quadrant 154 and
the threshold 67 are 69 and 18 away; nothing measured lands within a day.

**Gate C, third round, with the convention gone and the variable
disambiguated: both models stored 326 and both wrote 85.** flash: "If the
intent is to count hours with an actual north wind, the figure should be 85,
not 326." pro: "only 85 hours had both a north direction and a non-zero wind
speed." Each computed `wind_direction == 'N'` first, then found the coding,
then reported the correction in prose and left the stored variable as the
first computation. The right answer is in the response; the scored artefact —
the number a downstream consumer would take — is the naive one. pro did the
same in the round before, when the variable's wording could still be read as
a column filter; the wording was fixed and the behaviour did not change.

Whether that was a model failure or a residual ambiguity in "the wind blew
from the north" was left open for Gate B. It was ambiguity, and the variable
caused it (resolved below).

Both ground truths are recomputed here from the database.


**Gate A review 2026-09-06:** `northerly_hours` named the database column
outright, which P3's lexicon forbids on any agent surface. The pin itself is
load-bearing and stays — a 90-degree quadrant reads 154 against the coded
value's 326 — so only the column name is gone.


**Resolved: the variable asks for wind, not for a code.** The 2026-09-06
wording defined north as "the record's eight-point compass code N". Read
literally that is a column filter, and the filter returns 326 with every calm
hour in it, so a model that stored 326 had followed the definition it was
given while the key said 85. The ambiguity was not in "blew from the north",
which nobody reads as including still air; it was in defining north by what
the record writes. A case cannot score a model for obeying its own variable.

The variable now defines north as the compass point a wind blows from and
says that a calm hour, calm as `calm_hours` defines it, has no direction and
is not one of them. That is meteorological practice, not a disclosure, and it
leaves 85 as the only reading: N excluding calm is 85, and the 16-point
sector over windy hours is 85 too. What it does not say is the thing the case
tests, that this record files those directionless hours under N. An agent
that counts the N hours and trusts that calm must be stored some other way
still stores 326; the 326 is now wrong by the variable's own words rather
than by an argument from plain meaning.

This is close to the WIND block the first version put in the domain prompt,
and the cost of that block applies in part: an agent that excludes zero-speed
hours by habit gets 85 without ever seeing the coding. Two things differ. The
rule sits on the one variable it governs, so it is not a domain convention
the agent applies without looking; and the claim `calm_is_filed_as_north`
still scores whether the response saw the coding and says what it does to a
naive count, so the habitual 85 earns PV and not CC.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult
from domains.hk.db import read_frame

_STATION = "Wetland Park"
_SPAN = ("2025-12-01", "2026-01-01")


def _hours() -> pd.DataFrame:
    return read_frame(text("""
        select h.wind_speed, h.wind_direction
        from hourly_station_weather h
        join weather_station s on s.id = h.station_id
        where s.name_en = :station
          and h.datetime > :lo and h.datetime <= :hi
          and h.wind_speed is not null
    """), {"station": _STATION, "lo": _SPAN[0], "hi": _SPAN[1]})


def _figures() -> Dict[str, int]:
    hours = _hours()
    calm = hours["wind_speed"] == 0
    north = hours["wind_direction"] == "N"
    return {
        "northerly_hours": int((north & ~calm).sum()),
        "calm_hours": int(calm.sum()),
    }


def validate_northerly_hours(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = ("northerly_hours", "calm_hours")
    got = {name: runtime.retrieve(name) for name in names}
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)
    # `bool` is an `int` subclass; True must not pass as 1.
    for name, val in got.items():
        if not isinstance(val, int) or isinstance(val, bool):
            return ValidatorResult(False, f"{name}={val!r} is not an integer")

    gt = _figures()
    wrong = [f"{name}={val}, expected {gt[name]}"
             for name, val in got.items() if val != gt[name]]
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {gt['northerly_hours']} hours of north wind, "
              f"{gt['calm_hours']} calm")


tools = []
variables = [
    Variable(
        "northerly_hours",
        None,
        "Store how many hours of December 2025 the wind at Wetland Park blew "
        "from the north, as an integer: hours with a wind blowing from the "
        "eight-point compass point N, not from a range of degrees. A calm "
        "hour, as defined for calm_hours, has no wind direction and is not "
        "one of them.",
    ),
    Variable(
        "calm_hours",
        None,
        "Store how many hours of the month were calm, as an integer; an hour "
        "is calm when its stored wind speed is exactly zero.",
    ),
]
validators = {
    "validate_northerly_hours": validate_northerly_hours,
}
