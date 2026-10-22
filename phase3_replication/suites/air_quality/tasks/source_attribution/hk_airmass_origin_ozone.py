"""Where the air came from decides Hong Kong's ozone (source_attribution).

BASELINE. Two wrong paths exist and both are ruled out by what the agent is
already told, so neither is a naive path in the Round 9 sense and the case is
not dressed up as a trap.

- Reading `wind_dir_deg` as the direction the wind blows TOWARDS would swap the
  two sectors and return -52.24. The runtime variable's own description says it
  is the direction the wind blows FROM.
- Averaging several levels' directions arithmetically breaks across north: 350
  and 10 degrees average to 180, due south. A single level is specified, so no
  averaging arises. Measured anyway, since the case would otherwise rest on an
  assumption: over the 875-925 hPa band the arithmetic mean reads +50.61 and the
  vector mean +51.92 — a real defect with, here, a modest effect, because most
  launches report only one or two levels in that band.

The phenomenon is Hong Kong's defining air-quality pattern and it is large.
Classifying each 08:00 launch by the wind direction nearest 900 hPa over
2020-2025 and pairing it with that day's maximum territory ozone:

    northerly (315-45)   264 days   110.8643 ug/m3
    southerly (135-225)  593 days    58.6238 ug/m3
    difference                       +52.2405

Continental outflow arrives with ozone and its precursors already in it;
maritime air from the South China Sea does not. The contrast is present in
every year, from +39.7 in 2025 to +67.5 in 2020, so the pooled figure is not
carried by one episode or one season's worth of days.

The 900 hPa level is chosen because it sits above the marine boundary layer and
the harbour's own circulation while still describing the air that reaches the
surface. Levels are as launched rather than interpolated, so "nearest 900 hPa"
lands on 925 hPa more often than not — median offset 25 hPa, and only 8 of 2,142
launches are further than 25 hPa away. Two mornings have levels equidistant from
900. Nothing the agent is told says which way to break that tie, and the sweep
is what
licenses the omission: under the pinned level selection both directions give
the same answer to every digit.

**The selection order is pinned, and an earlier version of this docstring got
the reason exactly backwards.** It said the order could not matter because
"all 2,142 mornings carry wind at the level nearest 900 hPa". That is false.
Taking the nearest level by pressure and then reading its wind leaves **1,279 of
2,142 mornings (59.7 %) with no direction at all**, because these soundings
report many levels for height and temperature and only some of them for wind —
the 900 hPa level itself appears on just 44 mornings and reports wind on none of
them. Selecting among wind-reporting levels instead, which is what
`northerly_mornings` now specifies, keeps 2,135 paired mornings and reads
+52.240456; the literal order keeps 862 and reads **+64.328438**, a difference
of 12.09 ug/m3 and of 1,273 mornings.

That false claim survived because of how it was checked. The helper grouped by
date and called `.first()`, which in pandas returns the first NON-NULL value in
each column independently — so it can never see a missing wind at the nearest
level, and neither could the measurement that used it. The method could not
detect the thing it was asserting. `drop_duplicates` is used below instead,
which keeps the row rather than the first surviving value of each column.

**The sector bounds are the delicate part, and both ends of both sectors are
closed for a measured reason.** Reported directions cluster on 45-degree
increments, so the bounds themselves are heavily populated: 36 mornings read
exactly 45, 40 read 135, 46 read 225 and 3 read 315. Half-opening the upper end
of each sector drops 36 northerly and 46 southerly mornings and reads +53.2490;
half-opening only the north sector reads +54.2331. The closed reading, the
90-degree sector centred on each cardinal, is +52.2405 and is what
`northerly_mornings` specifies. This
was found by cross-checking the validator against the independent exploratory
measurement,
which had used a closed interval on one side and a half-open one on the other.

Tolerance `decimals=2`, the repo's idiom for "must round to this two-decimal
number", deriving +/-0.006. The previous +/-0.1 was 20x wider than two-decimal
reporting needs and it absorbed a class of reading the case forbids. A
territory hour is the mean over the stations reporting in it; requiring a
minimum of 11, 12, 13, 14, 15 or 17 of them first reads 52.262132, 52.262132,
52.268322, 52.263971, 52.252743 and 52.371938, and rounding each hourly mean to
an integer reads 52.216497 half-even or 52.220285 half-up — every one of them
inside the old band. Under `decimals=2` all of them are out, but **not by
much, and this paragraph used to claim otherwise**: the closest, the min-15
screen at 52.252743, is 2.5 band widths away, and the furthest of the family
26.3. (The figures here were 52.122650 and a "closest at 23.3 band widths"
until a verification pass on 2026-09-07 re-measured them. They had been
recorded under the day-of-stamp reading and were never updated when
`_daily_max_ozone()` moved to the hour-ending day; the pinned value and the
sector swap, the two figures a day-boundary shift leaves alone, are why the
staleness was invisible.) The rest of that family is measured rather than
assumed: a minimum of ten reporting stations or fewer reproduces the pinned
value to every digit, because no hour that thin ever carries a day's maximum.
A minimum of 16 reads 52.690919 and of 18 reads 49.593025.

Further out: taking each station's own daily maximum and averaging the stations
instead of forming the territory mean hour by hour reads +57.4099; the two
sector boundary variants read +53.2490 and +54.2331; the band-averaging
variants +50.7696 and +52.0691; the literal level-selection order +64.3284; and
the sector swap -52.2405.

The band-averaging pair is the one family whose recipe this docstring does not
fully specify — the 875-925 hPa band read inclusively, over levels reporting a
direction, with the vector mean taken as atan2 of the mean sine and cosine.
Read a different way those two rows move. Every other row above is unambiguous.

**The query used to be 160 words and almost all of them were pseudocode.** It
dictated which levels to consider, how to break a tie, how to form each hour's
territory figure and that no minimum station count applies — a specification,
not a question anyone would ask. It is now 59 words and asks the thing a person
would actually want to know. Nothing about the estimand changed; the
specification moved, in three directions:

- into the HK domain prompt, as the standing TERRITORY FIGURES convention:
  a territory hour is the equal-weighted mean over whichever sites report, and
  a daily peak is the highest hourly territory figure rather than the highest
  reading any one site recorded. This is shared across the domain and belongs
  there rather than in eight separate queries;
- into the variable descriptions, which carry what is specific to this
  question — the level selection and the sector bounds. An analyst is given a
  question and a reporting format, and the format is where the house
  conventions live; `northerly_mornings` is that format;
- out of the case entirely, for the tie-break, which the sweep measures as
  immaterial under the pinned level selection.

**Two group sizes became scored variables in the same change, and they are not
decoration.** The specification is now somewhere the agent must read but that
no longer restates itself in the question, so it needs an enforcement that does
not depend on a tolerance. The level selection reads 111 and 296 mornings where
the pinned one reads 264 and 593; half-opening a sector drops 36 or 46. Those
are exact integers. The contrast separates the same readings by 11.84 and by
1.0 to 2.0, which is comfortable but is a band argument; a group size is not.
This is the lesson this corpus keeps relearning: where a convention changes the
SIZE of the sample, score the size.

They earned their place on the first live run after they were added, and
against their own author. The counts were described as the mornings classified
northerly and southerly, while ground truth counts the mornings that ALSO carry
a territory ozone figure — 264 and 593 rather than 265 and 595, eight of the
2,142 launches falling on days the network reported no ozone. A run stored 265
and 595, the counts of every launch rather than of the launches whose day
carries an ozone figure. Measured 2026-09-06: those two extra northerly and two
extra southerly mornings have no ozone to contribute, so the contrast is
52.2405 either way and the counts were the only thing that could reject the
run. The description was the thing at fault, and both now say that a morning belongs to
a side of the comparison only if its day has an ozone figure to compare.

**What the intermediate state cost, recorded because it is the argument for the
sweep.** Between dropping the recipe from the query and writing the domain
convention, a live run read **+78.242684** — each station's own daily maximum,
then the highest of those. That is the sibling of the +57.11 already listed, it
is 4,357 bands out, and it was in neither the docstring nor the probe table
until a model produced it. It is in both now. A convention removed from a query
has to land somewhere, and until it does the reading it used to exclude is
live.

**Convention sweep — four axes, sixty combinations, all computed.**
`levels` is whether
the nearest level is chosen among those reporting wind or by pressure alone;
`sector` is which sector ends are closed; `ozone` is the daily recipe, carrying
the minimum-station screen and the hourly rounding as recipes of their own so
that every combination is applicable. `tie` is in the sweep because the query
stopped stating it, and the sweep answers a sharper question than the one the
docstring used to answer by assertion: the tie is immaterial ONLY under the
pinned level selection. All fifteen `wind_reporting` pairs agree to every
digit, while all fifteen `nearest_any` pairs differ, by up to 1.7 — because
there the tie falls between a level that reports wind and one that does not, so
it decides whether the morning is classified at all. Dropping the tie-break
from the query is safe because the level selection stayed in it.

Ground truth is recomputed here from the database and the sounding file.


**Gate A review 2026-09-06 reconciled the group means with the contrast.** The
northerly mean read 110.724 in this docstring against a difference of +52.240,
and the two could not both be right: recomputed, the northerly mean is
**110.8643** over 264 mornings and the southerly **58.6238** over 593, giving
**+52.2405**, which is what `_figures()` returns and what the probe table
records as correct. The mean was the stale figure, not the contrast. Three
derived numbers followed it and are corrected with it — the literal-order gap
(11.84, not 11.98) and the sector swap (-52.24, not -52.10).
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

_SPAN = ("2020-01-01", "2026-01-01")
_LAUNCH_HOUR = 8
_TARGET_HPA = 900
_NORTH = (315, 45)
_SOUTH = (135, 225)


def _wind_at_900() -> pd.Series:
    """Each morning's wind, from the wind-reporting level closest to 900 hPa.

    Levels without a direction are discarded BEFORE the nearest is chosen,
    which is what `northerly_mornings` specifies and is not a detail: on 59.7 %
    of mornings the nearest level by pressure alone reports no wind.
    """
    levels = pd.read_csv(
        DATA_DIR / "profile_sounding.csv",
        parse_dates=["datetime"],
        usecols=["datetime", "hour", "pressure_hpa", "wind_dir_deg"],
    )
    levels = levels[(levels["datetime"] >= _SPAN[0]) & (levels["datetime"] < _SPAN[1])]
    levels = levels[levels["hour"] == _LAUNCH_HOUR].dropna(subset=["wind_dir_deg"])
    levels = levels.copy()
    levels["date"] = levels["datetime"].dt.normalize()
    levels["offset"] = (levels["pressure_hpa"] - _TARGET_HPA).abs()
    # Ties broken towards the lower level, i.e. the higher pressure. Nothing
    # the agent is told states this, because the sweep measures both directions
    # as identical under the pinned level selection; it is fixed here so that
    # ground truth is a value rather than a coin.
    #
    # `drop_duplicates`, never `groupby(...).first()`: the latter returns the
    # first non-null value of each column independently, so it silently reaches
    # past the selected row for any column that is missing there. That is how
    # this file came to assert, wrongly, that no morning lacks a wind at the
    # nearest level.
    nearest = levels.sort_values(
        ["date", "offset", "pressure_hpa"], ascending=[True, True, False]
    ).drop_duplicates("date").set_index("date")
    return nearest["wind_dir_deg"]


def _daily_max_ozone() -> pd.Series:
    # Aggregated server-side: the table passed a million station-hours when the
    # record was extended back to 2020, and `domains.HK.db` caps a statement at
    # thirty seconds. Pulling the hourly rows to average them here times out.
    daily = read_frame(text("""
        select date_trunc('day', h.datetime - interval '1 hour') as date, max(h.territory_o3) as o3
        from (
            select datetime, avg(o3) as territory_o3
            from hourly_station_air_quality
            where datetime > :lo and datetime <= :hi and o3 is not null
            group by datetime
        ) h
        group by 1
    """), {"lo": _SPAN[0], "hi": _SPAN[1]})
    return daily.assign(date=pd.to_datetime(daily["date"])).set_index("date")["o3"]


def _figures() -> Dict[str, object]:
    """The three scored quantities: both group sizes and the contrast."""
    paired = pd.concat(
        [_wind_at_900().rename("wind"), _daily_max_ozone().rename("o3")],
        axis=1, join="inner",
    ).dropna()
    # Both sectors CLOSED at both ends — the 90-degree sector centred on north
    # and on south. Not cosmetic: the reported directions cluster on 45-degree
    # increments, so 36 mornings sit exactly on 45, 40 on 135, 46 on 225 and 3
    # on 315, and half-opening the ends moves the answer by up to 2.0.
    north = (paired["wind"] >= _NORTH[0]) | (paired["wind"] <= _NORTH[1])
    south = (paired["wind"] >= _SOUTH[0]) & (paired["wind"] <= _SOUTH[1])
    return {
        "northerly_mornings": int(north.sum()),
        "southerly_mornings": int(south.sum()),
        "airmass_ozone_contrast": float(
            paired.loc[north, "o3"].mean() - paired.loc[south, "o3"].mean()),
    }


def validate_airmass_ozone_contrast(response: str, runtime, turn: Turn) -> ValidatorResult:
    contrast = runtime.retrieve("airmass_ozone_contrast")
    counts = {"northerly_mornings": runtime.retrieve("northerly_mornings"),
              "southerly_mornings": runtime.retrieve("southerly_mornings")}

    if contrast is None:
        return ValidatorResult(
            False, "airmass_ozone_contrast not set", variables_not_set=True
        )
    if not is_finite_number(contrast):
        return ValidatorResult(
            False, f"airmass_ozone_contrast={contrast!r} is not a number")
    for name, val in counts.items():
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not isinstance(val, int) or isinstance(val, bool):
            return ValidatorResult(False, f"{name}={val!r} is not an integer")

    gt = _figures()
    # The counts are matched exactly, and they carry the specification the
    # query no longer states. Reading the nearest level by pressure and taking
    # its wind — rather than choosing among the levels that report one — is
    # 111 and 296 against 264 and 593, and half-opening either sector moves a
    # count by 36 or 46. The contrast alone separates those readings too, but
    # only by 11.84 and by 1.0 to 2.0; a group size separates them by
    # construction.
    wrong = [f"{name}={val}, expected {gt[name]}" for name, val in counts.items()
             if val != gt[name]]
    if not reports_as(contrast, gt["airmass_ozone_contrast"], decimals=2):
        wrong.append(f"airmass_ozone_contrast={contrast}, "
                     f"expected ~{gt['airmass_ozone_contrast']:.2f}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {contrast} ug/m3 over {counts['northerly_mornings']} "
              f"northerly and {counts['southerly_mornings']} southerly mornings")


tools = []
variables = [
    Variable(
        "northerly_mornings",
        None,
        "Store how many mornings the northerly side of the comparison "
        "contains, as an integer — 08:00 King's Park launches in the window "
        "classified as northerly whose day also carries a territory ozone "
        "figure. Classify a morning by the wind direction at the sounding "
        "level nearest 900 hPa AMONG THE LEVELS THAT REPORT A DIRECTION — "
        "these soundings report height and temperature at many levels where "
        "they report no wind. Northerly is the 90-degree sector centred on "
        "north, and a direction lying exactly on either bound is inside it.",
    ),
    Variable(
        "southerly_mornings",
        None,
        "Store the size of the southerly side of the same comparison — the "
        "90-degree sector centred on south, under the same level-selection, "
        "bound and ozone-availability rules — as an integer.",
    ),
    Variable(
        "airmass_ozone_contrast",
        None,
        "Store the mean daily peak territory ozone over the northerly mornings "
        "minus the mean over the southerly mornings, as a float in ug/m3 to 2 "
        "decimal places. Positive means the northerly mornings are the higher "
        "of the two.",
    ),
]
validators = {
    "validate_airmass_ozone_contrast": validate_airmass_ozone_contrast,
}
