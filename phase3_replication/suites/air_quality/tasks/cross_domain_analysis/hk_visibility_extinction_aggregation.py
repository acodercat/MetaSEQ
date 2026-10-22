"""Averaging visibility is not averaging what visibility measures
(cross_domain_analysis).

DIAGNOSTIC TRAP.

**The naive path and what it produces.** Extinction is inversely proportional
to visibility, so the mean extinction over a set of hours is the mean of the
reciprocals, not the reciprocal of the mean. Taking the group's mean visibility
first and converting once reads **0.22776 km^-1** against the correct
**0.37238**, a 38.8 % understatement. This is Jensen's inequality, not a
convention: for a strictly convex transform the mean of the function exceeds
the function of the mean, always and in that direction.

The query therefore does not forbid the shortcut. It names the target — the
mean extinction coefficient of the group, under Koschmieder at the 2 %
threshold — and stops there. That is bucket-A specification: the estimand is
identified uniquely, while working out that it is a mean of reciprocals is the
exam. The error survives P1 because "average the visibilities and convert" is a
wrong computation of the named quantity, not a second defensible reading of it.

**Gate B round 7 blocked the first version for saying exactly what this
paragraph claims it does not.** That query asked for the mean "converting each
hour's visibility", which is the operation that separates the two paths, and it
opened by announcing that the exercise was about finding when particulate mass
"stops working" as a stand-in — the interpretive motive that turn 2's own claim
then scores. Both are gone. The docstring asserting that the query left the
shortcut open, while the query closed it, is the shape of error this file is
now careful about.

**The science, said no more strongly than the design supports.** Restricting
to a narrow particulate band and splitting on humidity produces a contrast
consistent with hygroscopic growth: the same dry aerosol mass scatters far
more light once it takes up water. Over 2025, pairing the airport's hourly
visibility and humidity with Tung Chung's PM2.5 and keeping the hours whose
PM2.5 lies in [10, 15) ug/m3:

    humid, relative humidity 90 % or more      0.37238 km^-1    42 hours
    dry, relative humidity below 75 %          0.08293          1035 hours

An earlier version of the required claim said the band holds particulate mass
"fixed by construction" and that humidity "has to enter any such estimate".
Gate B round 8 rejected both, correctly: a band restricts the range, it does
not fix the loading, and the near-equality of the two groups' PM2.5 means —
12.404762 humid against 12.427053 dry — is an empirical fact of this sample,
not a property of binning. It is a measured fact, though, and it carries the
comparison: the contrast also holds in every 1 ug/m3 sub-band (humid over dry
reads 0.318/0.080, 0.217/0.081, 0.371/0.083, 0.609/0.084 and 0.383/0.087 from
[10,11) to [14,15), Gate B's own recomputation). What the observational split
cannot do is establish the mechanism or make humidity necessary; the claim now
asks that mass alone does not predict the contrast, and explicitly permits a
response that notes the residual confounding — the wording that used to risk
rejecting the most careful answers. EPD's own visibility study attributes Hong
Kong's visibility reduction to particulates AND humidity together, which is
the association this measures.

**The dry figure is a bound, not an estimate, and the case says so rather than
hiding it.** The airport's visibility sensor reports at most 50,000 m, and
**573 of the 1,035 dry hours — 55.4 % — sit exactly at that ceiling**; the dry
group's median visibility IS the ceiling. HKO's convention is that a 50 km
report means visibility of 50 km OR MORE, so 0.08293 is an upper bound on the
true dry mean extinction and the humid-to-dry ratio of 4.4901 is a lower bound
on the real contrast. Both bounds are non-strict: an underlying visibility may
equal 50 km exactly, so the record does not establish that the true values
differ from the computed ones by any positive amount. An earlier draft said the
true mean was "lower by an unknown amount", which overstated it.
Across all 8,173 paired hours 36.3 % are censored this way, and 38.7 % of
the 1,781 inside the particulate band.

That is also why the trap lives in the humid group. Censoring compresses the
visibility distribution and Jensen's gap scales with its spread, so the
shortcut understates the dry group by only 1.4 % against 38.8 % for the humid
one. A case built on the dry hours would have had almost no trap to fall into,
and the author's first design did exactly that before the ceiling was measured.

**Convention sweep — four axes, sixteen combinations, all computed.**

    K       endpoint    band     RH     humid_ext   n    dry_ext   ceiling
    3.912   exclusive   [10,15)  >=90     0.37238   42   0.08293       573  <- pinned
    3.912   exclusive   [10,15]  >=90     0.37238   42   0.08314       579
    3.912   exclusive   [10,15)  >=95     0.61187    4   0.08293       573
    3.0     (any)       (any)    (any)    0.28556   42   0.06360       573

`K` is the Koschmieder constant: 3.912 is the 2 % contrast threshold and 3.0
the 5 % one used in some aviation practice. The query names the threshold
rather than the formula, which is bucket-A specification — Koschmieder is a
named method, so naming it is not leakage, and leaving the constant open would
be a P1 failure. `RH` at 95 % leaves four hours and is degenerate. `endpoint`
changes nothing at all: no paired hour falls at 2026-01-01 00:00.

`band` — whether 15 ug/m3 belongs to the band — moves only the dry outputs, and
by 0.00021, which is INSIDE a three-decimal tolerance. The dry hour count
excludes it exactly, because the band decides which hours are dry hours.
Where a convention changes which readings are in the sample, score the size
of the sample.

**Tolerances.** Both extinction figures use `decimals=3`, deriving +/-0.0006.
The naive path is 0.14462 out on the humid figure, 241 bands; the 3.0 constant
is 0.08682 out, 145 bands. The two counts are integers matched exactly.

**Forty-two hours is a small sample and the case scores the number so it cannot
be quoted without it.** One CC claim requires the response to say so. The
narrowness is not a defect to be widened away: relaxing the band to [10, 20)
buys 55 hours and relaxing humidity to 85 % changes what is being isolated.

Ground truth is recomputed from the database at validation time.

**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`)
as a Tier 2 case: the band, the humidity split and the pairing are a
colleague's screening design, handed over as such in the query, and the
Koschmieder relation at 2 % is the standard. What the rebuilt query no
longer says is what the earlier one said in its second turn — that some dry
hours sit at the instrument's ceiling. That is the observation the second
claim exists to score, and naming it on a surface dissolved it; the dry
turn now scores the dry mean and its hour count, and the ceiling stays in
the claim. The trap itself, the mean of reciprocals, is untouched by the
framing: the colleague's design says which hours, not how to average them.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, is_finite_number, reports_as
from domains.hk.db import read_frame

_SPAN = ("2025-01-01", "2026-01-01")
_KOSCHMIEDER = 3.912          # 2 % contrast threshold
_PM25_BAND = (10.0, 15.0)     # closed below, open above
_HUMID_RH = 90.0
_DRY_RH = 75.0


def _paired() -> pd.DataFrame:
    """Airport visibility and humidity against Tung Chung PM2.5, hour by hour.

    The airport is the only site carrying both visibility and humidity with
    full coverage — Waglan Island is the sole other candidate — and Tung Chung
    is the air quality station nearest to it.
    """
    span = {"lo": _SPAN[0], "hi": _SPAN[1]}
    weather = read_frame(text("""
        select h.datetime, h.visibility as vis, h.humidity as rh
        from hourly_station_weather h
        join weather_station w on w.id = h.station_id
        where w.station_code = 'HKA'
          and h.datetime > :lo and h.datetime <= :hi
          and h.visibility is not null and h.humidity is not null
    """), span)
    pm = read_frame(text("""
        select a.datetime, a.pm2_5 as pm25
        from hourly_station_air_quality a
        join air_quality_station s on s.id = a.station_id
        where s.name_en = 'Tung Chung'
          and a.datetime > :lo and a.datetime <= :hi
          and a.pm2_5 is not null
    """), span)
    paired = weather.merge(pm, on="datetime")
    return paired[(paired["pm25"] >= _PM25_BAND[0])
                  & (paired["pm25"] < _PM25_BAND[1])]


def _figures() -> Dict[str, object]:
    """The four scored quantities."""
    band = _paired()
    humid = band[band["rh"] >= _HUMID_RH]
    dry = band[band["rh"] < _DRY_RH]

    def extinction(rows: pd.DataFrame) -> float:
        # Per hour, then averaged. The reverse order is the trap.
        return float((_KOSCHMIEDER / (rows["vis"] / 1000.0)).mean())

    return {
        "humid_extinction_km": extinction(humid),
        "humid_hours": int(len(humid)),
        "dry_extinction_km": extinction(dry),
        "dry_hours": int(len(dry)),
    }


def _unusable(name: str, val) -> ValidatorResult:
    """The failure for a variable that is missing or not a number, else None.

    `runtime.retrieve` stays in the validators: `tests/test_turn_stores.py`
    reads the names out of the validator source to check them against the
    turn's `stores`, and hiding the call here would take that check away.
    """
    if val is None:
        return ValidatorResult(False, f"{name} not set", variables_not_set=True)
    if not is_finite_number(val):
        return ValidatorResult(False, f"{name}={val!r} is not a number")
    return None


def _not_an_integer(name: str, val) -> ValidatorResult:
    """A count must be an int; `bool` is excluded as an `int` subclass."""
    if val is None:
        return ValidatorResult(False, f"{name} not set", variables_not_set=True)
    if not isinstance(val, int) or isinstance(val, bool):
        return ValidatorResult(False, f"{name}={val!r} is not an integer")
    return None


def validate_humid_extinction(response: str, runtime, turn: Turn) -> ValidatorResult:
    extinction = runtime.retrieve("humid_extinction_km")
    hours = runtime.retrieve("humid_hours")

    failure = _unusable("humid_extinction_km", extinction)
    if failure is not None:
        return failure
    failure = _not_an_integer("humid_hours", hours)
    if failure is not None:
        return failure

    gt = _figures()
    wrong = []
    if not reports_as(extinction, gt["humid_extinction_km"], decimals=3):
        wrong.append(f"humid_extinction_km={extinction}, "
                     f"expected ~{gt['humid_extinction_km']:.3f}")
    if hours != gt["humid_hours"]:
        wrong.append(f"humid_hours={hours}, expected {gt['humid_hours']}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {extinction} km-1 over {hours} humid hours")


def validate_dry_extinction(response: str, runtime, turn: Turn) -> ValidatorResult:
    extinction = runtime.retrieve("dry_extinction_km")
    hours = runtime.retrieve("dry_hours")

    failure = _unusable("dry_extinction_km", extinction)
    if failure is not None:
        return failure
    failure = _not_an_integer("dry_hours", hours)
    if failure is not None:
        return failure

    gt = _figures()
    wrong = []
    if not reports_as(extinction, gt["dry_extinction_km"], decimals=3):
        wrong.append(f"dry_extinction_km={extinction}, "
                     f"expected ~{gt['dry_extinction_km']:.3f}")
    # Exact: the hour count is what rejects a band that includes 15 ug/m3,
    # which moves the dry extinction by less than a tolerance band could see.
    if hours != gt["dry_hours"]:
        wrong.append(f"dry_hours={hours}, expected {gt['dry_hours']}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {extinction} km-1 over {hours} dry hours")


tools = []
variables = [
    Variable(
        "humid_extinction_km",
        None,
        "Store the mean atmospheric extinction coefficient over the humid "
        "hours of the selected particulate band, as a float in km^-1 to 3 "
        "decimal places.",
    ),
    Variable(
        "humid_hours",
        None,
        "Store how many hours that mean was taken over, as an integer.",
    ),
    Variable(
        "dry_extinction_km",
        None,
        "Store the same mean over the dry hours of the same band, as a float "
        "in km^-1 to 3 decimal places.",
    ),
    Variable(
        "dry_hours",
        None,
        "Store how many dry hours that mean was taken over, as an integer.",
    ),
]
validators = {
    "validate_humid_extinction": validate_humid_extinction,
    "validate_dry_extinction": validate_dry_extinction,
}
