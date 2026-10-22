"""US ozone standard in Chinese units — the mixing-ratio trap (regulatory_standards).

Unit conversion is the best-documented LLM failure mode in quantitative
atmospheric work, and this is the field's classic instance: US standards are
volume mixing ratios (ppb), Chinese data are mass concentrations (ug/m3), and
the bridge needs the molar mass of ozone and the molar volume at the stated
conditions.

- Turn 1 (standard_ugm3): 70 ppb at 25 C / 1013.25 hPa -> 70 x 48.0 / 24.465
  = 137.3 ug/m3.
- Turn 2 (exceedance_days_us): days of 2023 whose city-level daily max 8-hour
  ozone (HJ 663 window basis, via the shared implementation) exceeds the
  converted level -> 73.

The query pins temperature and pressure because they are arbitrary conventions,
not the exam: a 20 C convention would defensibly give 139.7 ug/m3 and 71 days.
What remains — knowing the conversion exists, the molar mass, and the right
molar volume — is what the case tests.

WHAT THE 73 IS, and why turn 2 now says so. Beijing is not subject to the US
standard, so a bare count of days over 137.3 reads as a compliance finding it
cannot be. The scenario is a real one — putting a Chinese city on the yardstick
used elsewhere is what a cross-jurisdiction comparison does — and turn 2 now
names it and asks how the number should be described, with a claim scoring the
answer. Two measured anchors sit behind the claim: the same 2023 city record
gives 52 days over China's own Grade II limit of 160 against 73 over the
converted US level, so the count is a property of the threshold as much as of
the air.

The claim's second, optional half stops at "the US standard is not assessed as
a raw count of exceedance days" and deliberately does not describe its form. An
earlier draft of this docstring stated that form from recall. `_shared/mda8.py`
records what this corpus's one real ground-truth error was — a misremembered
regulatory clause — and nothing here verifies 40 CFR against a source, so the
case rests on the two figures above, which are measured, rather than on a
clause that is not.

Turn 2 also carries the round's sharpest evidence for coding detectability on
the REPORTED answer rather than the intermediate. `deepseek-v4-flash` derived
the right factor in a comment and then wrote code dividing 48 g/mol by a molar
volume in m3/mol, reading 137344.4 — absurd on sight. Carried into turn 2 that
threshold produced **0 exceedance days**, which is not absurd at all. The loud
error reached the reader as a quiet one.

Turn 2 inherits the MDA8 window hazard as well as the conversion, and the cost
is worth stating because a live run paid it: with the threshold converted
correctly, admitting all 24 trailing windows instead of the HJ 663 candidate set
gives 85 days against the pinned 73. The supplied `O3_8h` column's daily maximum
is the more tempting route of the two since it looks like the metric already
computed, and it reads 74 over the domain's air-quality day (85 if a day is
taken as its label date's hours 0-23). The query names HJ 663-2013 for this reason,
and 85 is a probe.

Tolerances: +/-0.3 ug/m3 on the Turn 1 threshold, 0 on its hour count, and
0 on Turn 2. The first absorbs the difference between the exact molar volume
(24.465 L/mol) and the textbook 24.45 while excluding both the unconverted 70
and the 0 C conversion (~149.9), and is sized as the paragraph above sets out;
the second was +/-2 until Gate C, and is now 0.

**THE WINDOW VALIDITY RULE WAS UNPINNED AND THE BAND ABSORBED IT, 2026-08-27.**
`deepseek-v4-pro-0813` returned 72 and PASSED at +/-2, having written
`rolling(8, min_periods=8)` — every one of the eight hours required, where
HJ 663 asks for at least six. Measured: 6-of-8 and 7-of-8 both give 73, 8-of-8
gives 72. The case pinned the WINDOW (ends 08:00-24:00) and never the hours
inside it, though its sibling `beijing_aqi_primary_pollutant` pins exactly that
("require each window to contain at least 6 valid hours"), and flash made the
same 8-of-8 error in discovery round 1. So the rule is now pinned on the
variable, which makes 72 a forbidden reading — and a band that admits a
forbidden reading is a P1 failure however it is described, so the band goes to
0. That excludes 72 and keeps excluding the paths further out (231
unconverted, 58 at 0 C, 85 on the all-windows basis, 74 from `O3_8h`). The day count is 73
across the whole +/-0.3 threshold band as well: the nearest daily maxima to
137.34 are 136.125 below and 138.125 above, so the two tolerances agree about
what they permit.

**TURN 1 NEEDED NO DATA, AND A NO-DATA CONTROL PROVED IT.** 137.3 is a molar
arithmetic result, not a property of the record, so asked with the runtime
taken away `deepseek-v4-flash` (137.3) and `deepseek-v4-pro-0813` (137.4) BOTH
produced it and both passed (2026-08-26, `scratchpad/no_data_control.py`). The
turn was scoring a constant.

Turn 1 now also scores the hours of the 2023 city record above the converted
level — 771 of 8,711 reported hours — which cannot be reached without both the
conversion and the data:

    the pinned 137.3 and the textbook 137.4       771 hours
    the level left unconverted at 70            3,244 hours
    the 0 C conversion, 149.9 ug/m3                602 hours
    flash's 1000x slip, 137,344 ug/m3                0 hours

flash's slip now fails turn 1 on the count while still passing on the threshold
it derived correctly in a comment — the divergence this case was already built
to expose, moved one turn earlier.

**THE THRESHOLD BAND HAD TO NARROW TO +/-0.3 TO ADMIT THAT COUNT, and a review
of this fix is what found it.** The city record reports ozone at whole
micrograms, so 771 is the count for any threshold in [137.0, 138.0) and the
pinned 137.3391 sits only 0.3391 above the lower end. The +/-0.5 band that
covered the threshold alone therefore ACCEPTED 136.84 — a defensible reading at
a molar volume of 24.554 — while the count of 782 that follows from it was
rejected by a tolerance of 0. A case that admits a threshold and refuses the
count derived from it is inconsistent with itself, and the direction of the
inconsistency does not matter. +/-0.3 keeps the whole band inside [137.0,
138.0), so every threshold the case accepts yields exactly the count it
requires; it still covers the exact-versus-textbook molar volume spread of
0.0842 nearly four times over, and still excludes 70, 149.9 and 137,344.

The year is the domain's air-quality year, labels 2023-01-01 01:00 to
2024-01-01 00:00, so 31 December keeps its 24:00 window. Selecting by label
year instead moves none of the figures above.

Both ground truths are recomputed here from constants and the CSV.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn
from domains.beijing.mda8 import frame_to_mda8

_CITY, _YEAR = "北京", 2023
_PPB = 70.0
_MW_O3 = 48.0
_MOLAR_VOL_25C = 24.465     # L/mol at 25 C, 1013.25 hPa


def _threshold() -> float:
    return _PPB * _MW_O3 / _MOLAR_VOL_25C


def _year(cities: pd.DataFrame) -> pd.DataFrame:
    """Beijing's air-quality year: hour h ends at h:00, so label 0 belongs to
    the previous date."""
    stamps = pd.to_datetime(cities[["year", "month", "day", "hour"]])
    day = stamps - pd.Timedelta(hours=1)
    return cities[(cities["city"] == _CITY) & (day.dt.year == _YEAR)]


def _counts() -> dict:
    cities = pd.read_csv(DATA_DIR / "region_cities.csv")
    sel = _year(cities)
    mda8 = frame_to_mda8(sel)
    mda8 = mda8[mda8.index.year == _YEAR]
    return {
        "correct": int((mda8 > _threshold()).sum()),
    }


def _hours_above() -> int:
    cities = pd.read_csv(DATA_DIR / "region_cities.csv")
    sel = _year(cities)
    return int((sel["O3"].dropna() > _threshold()).sum())


def validate_standard_ugm3(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("standard_ugm3")
    if val is None:
        return ValidatorResult(
            False, "standard_ugm3 not set", variables_not_set=True
        )
    hours = runtime.retrieve("hours_above_us_level_2023")
    if hours is None:
        return ValidatorResult(
            False, "hours_above_us_level_2023 not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(False, f"standard_ugm3={val!r} is not a number")

    correct = _threshold()
    expected_hours = _hours_above()
    errors = []
    if not reports_as(val, correct, decimals=1):
        errors.append(f"standard_ugm3={val}, expected ~{correct:.1f}")
    try:
        if not is_finite_number(hours) or hours != expected_hours:
            errors.append(
                f"hours_above_us_level_2023={hours}, expected {expected_hours}"
            )
    except (TypeError, ValueError):
        errors.append(f"hours_above_us_level_2023={hours!r} is not an integer")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True, f"correct: {val} ~ {correct:.1f} ug/m3, {expected_hours} hours above"
    )


def validate_exceedance_days_us(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("exceedance_days_us")
    if val is None:
        return ValidatorResult(
            False, "exceedance_days_us not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"exceedance_days_us={val!r} is not a number"
        )

    gt = _counts()
    if compare_numeric(val, gt["correct"], tolerance=0):
        return ValidatorResult(
            True, f"correct: {val} ~ {gt['correct']} days"
        )
    return ValidatorResult(
        False, f"exceedance_days_us={val}, expected ~{gt['correct']}"
    )


tools = []
variables = [
    Variable(
        "standard_ugm3",
        None,
        "Store the US 8-hour ozone standard expressed as a mass concentration at "
        "the stated conditions, as a float in ug/m3, 1 decimal place.",
    ),
    Variable(
        "hours_above_us_level_2023",
        None,
        "Store as an int how many hours of Beijing's 2023 city-level record "
        "reported an ozone concentration above that level. Count reported "
        "hours only, and count the hourly values themselves rather than any "
        "running mean of them.",
    ),
    Variable(
        "exceedance_days_us",
        None,
        "Store the number of 2023 days whose daily maximum 8-hour ozone "
        "exceeded that level, as an integer. A day's maximum 8-hour ozone is "
        "the largest of the 8-hour running means whose window ENDS between "
        "08:00 and 24:00 of that day, per HJ 663-2013, and a window counts "
        "once it holds at least 6 valid hours of the 8.",
    ),
]
validators = {
    "validate_standard_ugm3": validate_standard_ugm3,
    "validate_exceedance_days_us": validate_exceedance_days_us,
}
