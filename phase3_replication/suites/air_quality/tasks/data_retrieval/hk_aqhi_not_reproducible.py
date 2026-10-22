"""Banding the component sum cannot reproduce the published AQHI
(data_retrieval).

BASELINE. The premise-check kind: a colleague proposes to rebuild each hour's
index by adding the four added-risk components and banding the total, so that
the index can be attributed to a pollutant. The case asks whether that plan can
work, and the data says it cannot. The refusal is the answer, and it is provable
from the table the agent is querying.

**What the data proves, and what it does not.** This case claimed more than it
could until Gate B round 9, and the correction is worth stating first because
the earlier framing is the natural one to reach for. Over 2025 the 155,478
station-hours carrying an index and all four components contain 155,478
DISTINCT four-component vectors — no vector repeats. A sample in which every
input is unique cannot contradict any function of those inputs, so "the index
is not a function of the components" is not merely unproven here; it is
unprovable from this table. What IS provable is narrower and is what the
colleague actually proposed: the SUM does not determine the index.

    distinct component totals, rounded to one decimal        209
    totals carrying more than one published index             99    47 %
    station-hours whose total is one of those                146,395    94 %

Ninety-four per cent of hours carry a total that, on its own, does not settle
which index was published. No rule mapping a total to a band returns the
published number for every hour, and that is the whole of what the counts show.

**Why the earlier statistic was replaced.** The case scored the number of
adjacent index values whose min-max ranges of the total overlap: 8 of 9. Gate B
established that overlap does not carry the inference the case drew from it —
two ranges can overlap without sharing a single total, and here bands 8 and 9
do exactly that. The count above is the direct form: it counts totals that
actually appear under more than one index.

**Rounding to one decimal is load-bearing, not tidying.** The exact float total
is not a well-defined quantity. Summing the four columns in different orders
gives 22,613 / 22,855 / 21,215 / 19,581 distinct totals and 722 / 713 / 720 /
691 ambiguous ones, because the last bit depends on association order. Rounded
to one decimal all four orders agree exactly at 209 and 99. The ROW count is
not equally safe — 146,395 under half-up against 146,421 under half-to-even —
so it is stated here and in the claims but is NOT scored; only the two counts
that survive both rounding modes are.

**The example the docstring used to give was false.** "A component sum of 5.0
was published as a 2, a 3 and a 4" is not true of exact stored totals: an exact
5.0 occurs only under index 3. It becomes true only after rounding to one
decimal, where 2,185 rows round to 5.0 and carry indices 2, 3 and 4. Gate B
caught it.

**What the case must not ask for.** That the two columns have different
provenance. `datasets/EXTERNAL_DATA_SOURCES.md` records that `aqhi` is EPD's
published value and the `*_ar` columns are computed, but nothing an agent can
query establishes it, and the claims no longer require it. The practical
conclusion the counts do support is an operational one: read the issued value
where the official index is required.

**And what the failure does NOT condemn.** The components themselves. An
attribution asking which of the four carried the most added risk in a given
hour reads them directly and is untouched by whether their total reproduces the
band. The earlier claim told the colleague their whole analysis rested on a
relationship the data refutes; that was too broad, and the third claim now says
so explicitly.

Pins, as measured for the count the earlier version scored — kept as the
record of what moved it; the rebuilt verdict below holds under every one.

    2025, all stations, four components present   99 of 209    155,478 hours
    2024 instead                                  93 of 199    156,195
    missing components filled with zero          119 of 218    156,953
    one station alone (18)                        26 of 129      8,717
    the total rounded to two decimals            330 of 1,598  155,478

- 2025, half-open, per the domain prompt's TIME WINDOWS. Under the statistic
  this case scored BEFORE Gate B round 9 the year did not matter — 2024 also
  read 8 of 9 — and the pin rested entirely on `hours_checked`. It now moves
  the scored count as well, so both figures reject it.
- EVERY STATION pooled. One station reads 26 of 129: the ambiguity is a
  property of the published index over the whole network, and a single site
  understates it by a factor of four.
- ROWS CARRYING ALL FOUR COMPONENTS, stated on `hours_checked`. Treating a
  missing component as zero invents a total, and it shows: 119 of 218.
- ONE DECIMAL PLACE on the total, which the earlier variable stated. Two
  decimals reads 330 of 1,598 — the same conclusion, a different number — and
  the exact float total has no stable value at all, which is why the count
  had to pin a rounding and the verdict does not.

Ground truth is recomputed from the database at validation time.

**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier turn told the agent to add the four components, round to one
decimal and count the distinct totals carrying more than one index — the
recipe was the query, and the count (99) was a property of the rounding.
The rebuilt turn hands over the colleague's plan and asks whether it works;
it scores the hours checked (exact, the join's size) and the verdict, which
is the same under one-decimal, three-decimal and unrounded sums: 99, 620
and 721 sums carry more than one index, and adjacent indices' raw-sum
ranges overlap at every one of the eight boundaries from 1/2 to 9/10. No
banding of the sum can reproduce the stored index on more than 98.4 % of
hours at one decimal or 99.2 % at three, and the claims carry that limit.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult
from domains.hk.db import read_frame

_SPAN = ("2025-01-01", "2026-01-01")
_COMPONENTS = ("no2_ar", "so2_ar", "o3_ar", "pm_ar")


def _component_sums() -> pd.DataFrame:
    """Every 2025 station-hour with a stored index and all four components,
    with the components summed."""
    frame = read_frame(text(f"""
        select aqhi, {', '.join(_COMPONENTS)}
        from hourly_station_air_quality
        where datetime > :lo and datetime <= :hi
          and aqhi is not null
          and {' and '.join(f'{c} is not null' for c in _COMPONENTS)}
    """), {"lo": _SPAN[0], "hi": _SPAN[1]})
    # Rounded to one decimal, and that is load-bearing rather than tidy: the
    # EXACT float sum is not a well-defined quantity here. Summing the four
    # columns in different orders gives 22,613 / 22,855 / 21,215 / 19,581
    # distinct sums and 721 / 713 / 720 / 691 ambiguous ones, because the last
    # bit depends on association. Rounded to one decimal every order agrees
    # exactly, which is what makes the scored counts an estimand at all.
    frame["component_sum"] = frame[list(_COMPONENTS)].sum(axis=1).round(1)
    return frame


def _figures() -> Dict[str, object]:
    frame = _component_sums()
    frame["raw"] = frame[list(_COMPONENTS)].sum(axis=1)
    # A function of the sum would give every sum one index. Checked on the
    # sum rounded to one decimal, to three, and unrounded; the three agree
    # (99, 620 and 721 sums carry more than one index) and a disagreement
    # would refuse to score rather than pick one.
    verdicts = {
        f"{label}": bool((frame.groupby(key)["aqhi"].nunique() > 1).any())
        for label, key in (("one decimal", frame["component_sum"]),
                           ("three decimals", frame["raw"].round(3)),
                           ("unrounded", frame["raw"]))
    }
    if len(set(verdicts.values())) != 1:
        raise RuntimeError(f"ambiguity is not invariant across roundings: {verdicts}")
    return {
        "hours_checked": int(len(frame)),
        "index_is_a_function_of_the_component_sum": not verdicts["one decimal"],
    }


def validate_band_overlap(response: str, runtime, turn: Turn) -> ValidatorResult:
    hours = runtime.retrieve("hours_checked")
    verdict = runtime.retrieve("index_is_a_function_of_the_component_sum")
    missing = [n for n, v in (("hours_checked", hours),
                              ("index_is_a_function_of_the_component_sum", verdict))
               if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)
    # `bool` is an `int` subclass; True must not pass as 1.
    if not isinstance(hours, int) or isinstance(hours, bool):
        return ValidatorResult(False, f"hours_checked={hours!r} is not an integer")
    gt = _figures()
    wrong = []
    if hours != gt["hours_checked"]:
        wrong.append(f"hours_checked={hours}, expected {gt['hours_checked']}")
    expected = gt["index_is_a_function_of_the_component_sum"]
    ok = (isinstance(verdict, bool) and verdict == expected) or (
        isinstance(verdict, str) and verdict.strip().lower() in
        {str(expected).lower(), "yes" if expected else "no"})
    if not ok:
        wrong.append(f"index_is_a_function_of_the_component_sum={verdict!r}, "
                     f"expected {expected}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: the index is not a function of the component sum over "
              f"{gt['hours_checked']} hours")


tools = []
variables = [
    Variable(
        "hours_checked",
        None,
        "Store how many station-hours of 2025 carry a stored AQHI together "
        "with all four added-risk components, as an integer — every station "
        "pooled, and only hours where none of the four is missing.",
    ),
    Variable(
        "index_is_a_function_of_the_component_sum",
        None,
        "Store True if, over those hours, the stored index can be obtained "
        "from the sum of the four added-risk components — the same sum "
        "always carrying the same index — else False.",
    ),
]
validators = {
    "validate_band_overlap": validate_band_overlap,
}
