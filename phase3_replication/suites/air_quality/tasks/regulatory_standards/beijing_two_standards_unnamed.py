"""Which standard does Beijing's ozone breach more often — 70 ppb or 160
ug/m3? (regulatory_standards)

DIAGNOSTIC TRAP, the unnamed-application kind. The corpus already has the
NAMED version of this concept: `beijing_ozone_ppb_standard` opens by telling
the agent to express 70 ppb "in the concentration units this dataset uses",
so the conversion is pointed at before any work starts, and in discovery
round 1 flash still botched it (137,344 ug/m3, then "0 exceedance days").
This case removes the pointer. The two limits arrive as a working analyst
meets them — one in each jurisdiction's native unit — and nothing anywhere
says "convert". Noticing that 70 and 160 are not on the same scale IS the
exam.

The three-layer probes of 2026-08-23 (`docs/v2_measurements.md` §4) are why
this case exists: both models state the conversion correctly when asked
plainly, and flash even catches its own 1000x slip in a pure-text answer
("That result is wrong — I misapplied units") while sailing past the same
number in an agentic run. Prediction, recorded before the first Gate C run:
pro passes, flash is the model at risk.

Measured on the 2023 city-level record, MDA8 per the shared HJ 663
implementation:

    days over 137.3 ug/m3 (70 ppb converted at 25 C, 1013.25 hPa)   73
    days over 160 ug/m3 (China's Grade II limit)                    52
    days over 70 READ AS ug/m3 — the unconverted naive path        231

The naive path does not merely move the number; it reverses the comparison's
meaning. Unconverted, the US standard looks nearly twice as strict again as
it is (231 vs 52); converted, the true contrast is 73 vs 52. An analyst who
never converts reports that Beijing spends most of the ozone season above
the US level, which is false by a factor of three.

Pins, each measured.

- CONVERSION CONDITIONS 25 C / 1013.25 hPa, stated in `domains/Beijing/
  prompts.py` under GAS UNITS — they are an arbitrary convention, not the exam
  (a 20 C convention defensibly gives 139.7 and a slightly different count),
  and they hold across the domain, which under §3.1 is what puts them in the
  prompt rather than on a variable. They were on the variable until 2026-09-06;
  `beijing_ozone_ppb_standard` reads them from the same place.
- THE CITY-LEVEL RECORD, named in the query: the WHICH BEIJING default would
  otherwise send this to the twelve-station network.
- THE MDA8 WINDOW per HJ 663-2013, stated on the variable the same way the
  sibling case states it (largest 8-hour running mean whose window ENDS
  08:00-24:00). The window convention is the sibling's exam, not this one's.
- EVERY DAY of 2023, whatever number of hours it reports.

Tolerances: 0 on both counts. The converted count carried +/-2 until
2026-10, copied from the sibling for the exact-molar-volume choice, but that
choice moves nothing (24.45 and 24.465 L/mol both give 73: the nearest daily
maxima are 136.125 and 138.125), the sibling itself went to 0 after its band
passed a forbidden 8-of-8 reading, and the same band here admitted 72 (all 8
hours required, which the variable forbids), 74 (the daily maximum of the
supplied `O3_8h` over the domain's day) and 71 (a 20 C conversion, which the
prompt forbids). At 0 those fail while the naive 231 and 52 misplaced into
the US slot stay far out.

The year is the domain's air-quality year, labels 2023-01-01 01:00 to
2024-01-01 00:00, so 31 December keeps its 24:00 window; selecting by label
year instead gives the same 73 and 52.

Both ground truths are recomputed here from the CSV through the shared
implementation.


**Gate A review 2026-09-06 closed a P1 hole and moved a P3 leak.** Two pins
this docstring lists as measured were on no agent surface: the every-day rule
and HJ 663's own 6-of-8 window minimum, against counts scored at tolerance 0.
`evals/_shared/mda8.py` is explicit that those spreads "have to be named in the
query rather than left to the agent", and the sibling
`beijing_ozone_ppb_standard` had to add the 6-of-8 rule after Gate C read 72
for the same quantity. Both are now on the variable, where HJ 663's own
validity rules belong.

The same variable used to end "taking that standard at 25 degrees Celsius and
1013.25 hPa", and that sentence announced the very thing this case exists to
test: temperature and pressure are meaningless to an agent reading 70 as a mass
concentration, so naming them flags a molar-volume conversion. The reference
conditions are a property of the domain, not of this question, and they now sit
in `domains/Beijing/prompts.py` under GAS UNITS with the other conventions,
where the sibling case can use them too and where they do not point at any one
question.

A verification pass on 2026-09-07 trimmed that block. It had gone in stating
the conversion factor as well — one part per billion of ozone as a number of
ug/m3 — which hands `beijing_ozone_ppb_standard` its turn 1 outright, that
case's whole deliverable being the conversion, and its tolerance being set wide
enough to accept either 24.45 or 24.465 L/mol precisely because choosing a
molar volume is the agent's move. The block now states the reference
conditions and stops there, which is the convention; the arithmetic is not a
convention.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number
from domains.beijing.mda8 import frame_to_mda8

_YEAR = 2023
_US_LIMIT_UGM3 = 70 * 48.0 / 24.465   # 137.3 at 25 C / 1013.25 hPa
_CN_LIMIT_UGM3 = 160.0


def _counts() -> dict:
    cities = pd.read_csv(DATA_DIR / "region_cities.csv")
    # Hour h ends at h:00, so label 0 belongs to the previous date.
    day = pd.to_datetime(cities[["year", "month", "day", "hour"]]) - pd.Timedelta(hours=1)
    bj = cities[(cities["city"] == "北京") & (day.dt.year == _YEAR)]
    mda8 = frame_to_mda8(bj)
    mda8 = mda8[mda8.index.year == _YEAR]
    return {
        "days_over_us_standard": int((mda8 > _US_LIMIT_UGM3).sum()),
        "days_over_cn_standard": int((mda8 > _CN_LIMIT_UGM3).sum()),
    }


def validate_two_standards(response: str, runtime, turn: Turn) -> ValidatorResult:
    us = runtime.retrieve("days_over_us_standard")
    cn = runtime.retrieve("days_over_cn_standard")
    missing = [n for n, v in (("days_over_us_standard", us),
                              ("days_over_cn_standard", cn)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)
    for name, val in (("days_over_us_standard", us), ("days_over_cn_standard", cn)):
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")

    gt = _counts()
    wrong = []
    if not compare_numeric(us, gt["days_over_us_standard"], tolerance=0):
        wrong.append(f"days_over_us_standard={us}, "
                     f"expected {gt['days_over_us_standard']}")
    if not compare_numeric(cn, gt["days_over_cn_standard"], tolerance=0):
        wrong.append(f"days_over_cn_standard={cn}, "
                     f"expected {gt['days_over_cn_standard']}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {gt['days_over_us_standard']} days over the US level, "
              f"{gt['days_over_cn_standard']} over the Chinese limit")


tools = []
variables = [
    Variable(
        "days_over_us_standard",
        None,
        "Store the number of 2023 days whose daily maximum 8-hour ozone "
        "exceeded the United States standard, as an integer. A day's maximum "
        "8-hour ozone is the largest of the 8-hour running means whose "
        "window ENDS between 08:00 and 24:00 of that day, per HJ 663-2013, a "
        "window counting once it holds at least 6 valid hours of the 8, and "
        "every day of the year is considered whatever number of hours it "
        "reports.",
    ),
    Variable(
        "days_over_cn_standard",
        None,
        "Store the number of 2023 days whose daily maximum 8-hour ozone, on "
        "the same construction, exceeded China's Grade II limit, as an "
        "integer.",
    ),
]
validators = {
    "validate_two_standards": validate_two_standards,
}
