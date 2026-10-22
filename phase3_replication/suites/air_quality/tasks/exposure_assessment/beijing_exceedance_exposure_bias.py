"""Summer 2023 ozone exceedance — spatial averaging biases exposure toward the
null (exposure_assessment).

The exposure-epidemiology literature's central measurement-error result, made
computable: averaging monitors BEFORE applying a threshold smooths away local
peaks, so a citywide series understates how often anyone in the city actually
faced an exceedance. Summer 2023 makes the bias large because the station
field is genuinely heterogeneous at the tail (28 to 42 exceedance days across
the twelve stations) even though annual means are nearly uniform.

- Turn 1 (citywide_exceedance_days): the city MDA8 series above 160 on 31 days.
- Turn 2 (anywhere_exceedance_days): at least one station above the limit on 47
  days — half again the citywide figure.
- Turn 3 (population_over_40_days): nearest-station assignment of the 100 m
  population grid; only Dongsi (42 days) clears "more than 40", and 818,533
  residents live nearest to it.

The case names HJ 663-2013 on all three turns — turn 1 on its variable, turns
2 and 3 in their queries — because the candidate-window set
drives every number here. Admitting all 24 trailing windows instead gives 37 and
55 days, lifts four stations over the 40-day line instead of one, and reports
7,021,985 residents against 818,533 — an eightfold error. An earlier version
pinned only the six-hour minimum and left the endpoints open; the first model
evaluated on this case produced exactly the unrestricted figures, and Gate B
confirmed the case, not the model, was at fault.

**The two counts differ on TWO axes, not one, and an external audit caught
that the required claim named only the first.** Decomposed here before the
claim was rewritten: citywide (11 city assessment points, averaged then
thresholded) gives 31; anywhere on those same 11 points gives 45; anywhere on
all 12 stations gives 47. So the 16-day gap is **14 days of
averaging-before-thresholding and 2 days of the station set widening** —
averaging dominates at 87.5 %, but it is not the whole of it, and the claim
used to demand that it was. It now asks for averaging as the DOMINANT
mechanism and accepts either naming the station-set difference or isolating
the two by recounting on a common set.

Turn 1 also pins "every day of the period, whatever number of valid windows it
yields", and what that pin guards against needs stating precisely, because the
first version of this paragraph got it wrong and Gate B corrected it. HJ
663-2013's data-validity table requires at least 14 valid 8-hour means per day —
but its section 6.1.2 then PRESERVES an under-sampled day whose maximum exceeds
the limit. Dongsi's two short summer days (2023-06-16 and 2023-06-17, nine
windows each, at 235.67 and 272.12) both exceed 160, so the complete standard
keeps them and lands on the same 42 days and 818,533 residents the pin
specifies. What the pin excludes is the plausible INCOMPLETE application — the
14-window rule remembered without its exceedance-preservation clause — which
drops Dongsi to 40, empties the "more than 40 days" set, and flips the
population answer to ZERO. That half-remembered-standard reading is a wrong
path, not a defensible alternative, and 0 is its permanent probe. An earlier
docstring claimed the 40-day line was "insensitive to MDA8 implementation
detail"; that had been measured against min_periods 6 vs 8 only.

Tolerance: 0 on Turns 1 and 2, because both are counts of days and nothing
legitimate moves them. The +/-2 band they used to carry was justified as
absorbing "rolling min_periods 6 vs 8", but 6 is not an implementation choice:
GB 3095-2012 Table 4 prescribes it — "臭氧8小时平均：每8小时至少有6小时平均浓度值" —
so the 8-hour variant is a forbidden reading. The band was admitting it, and a
zero band excludes it on Turn 2, where it reads 46 against the correct 47.

What a zero band does NOT do is separate it on Turn 1, and that has to be stated
rather than left implied by the sentence above. Since A.2 (below) restricted the
city series to 城市点, the 8-hour variant reads 31 there — the same as the
correct answer. It is excluded by the stated pin, not by the band, and Turn
1's
probe against it can only ever pass. The measured values under A.2 are:

    min_periods 6 (prescribed)    Turn 1: 31    Turn 2: 47
    min_periods 8 (forbidden)     Turn 1: 31    Turn 2: 46

Turn 1 lost that discrimination as a side effect of the A.2 correction; the
correction was still right, and Turn 2 still carries the probe.
Turn 3 scores the population to the nearest hundred thousand (it used +/-2 %
until 2026-09-02); 0, the reading produced by the
14-window rule applied without its 6.1.2 exception, is a permanent probe.

The station table carries a second, secondary coordinate set. Substituting it
moves this answer by nothing at all — the assignment is identical — so the query
does not pin which set to use — the domain schema already directs the agent to the
benchmark coordinates. Measured, not assumed; see
`beijing_station_coordinate_audit`, where the 3.5 km discrepancy behind it is
the subject.

All three ground truths are recomputed here from the CSVs.

HJ 663-2013 A.2 admits only 城市点: its footnote reads "点位指城市点，不包括
区域点、背景点、污染监控点和路边交通点", and it sits under every row of Table A.2,
so it governs the particulate and gas statistics as well as ozone. Dingling is
the network's background site; `station_metadata.csv` has carried the flag in
`included_in_city_aggregate` since the dataset was built, and until Gate B read
the footnote only `beijing_product_provenance` was using it. Excluding Dingling
is what moved this case's figures.


**Turn 3 rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier query dictated the nearest-station assignment; the rebuilt one
asks how many residents live where the limit was exceeded on more than 40
days. The station is scored by name alongside the count — as a set, because
the variable does not tell the agent whether one station or several clear the
line, so it has to accept a bare name and a list alike and judge them on
whether they name exactly the stations over 40 days.

**Gate B round 21 (2026-09-03) ruled the rebuild had moved the recipe rather
than removed it**, and it had: the nearest-station assignment had come off the
query and gone onto the variable, which under round 21's own rule is a surface
like any other. The fix is not to drop the exposure model — without one there
is no question — but to hand it over where a desk would hand it over. The
query now states the study's design in the study's words: each resident is
treated as exposed to the air at their nearest station. That is a real and
common exposure surrogate, and it is the thing being asked about rather than a
route to a number.

Great-circle stays on the variable as the distance convention, in the same
role it has in `hk_population_weighted_background_no2` and
`beijing_monitor_catchment_imbalance`, both of which round 21 passed clean with
it. It is not a choice between two defensible methods: nearest by planar
degrees compares a degree of longitude with a degree of latitude, which at
Beijing's latitude are 0.77 apart, and it reads 747,497 against 818,533 —
a wrong answer produced by a wrong metric, not a second convention.


**Gate A review 2026-09-06 pinned HJ 663's 6-of-8 window rule on turn 2's
variable.** The rule was enforced by `evals/_shared/mda8.py` and stated on no
surface, against a count scored at tolerance 0 — and this docstring already
records the consequence, that the +/-2 band was dropped because a reading of 46
against the correct 47 was getting through. The sibling
`beijing_o3_mda8_exceedance` pins it in the query and
`beijing_ozone_ppb_standard` had to add it on the variable after Gate C read 72
for the same quantity; this case was the one left without it. It is HJ 663's own
validity rule, so it belongs on the surface as the standard it is.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn
from domains.beijing.mda8 import frame_to_mda8

_YEAR, _MONTHS, _LIMIT = 2023, (6, 7, 8), 160.0
_DAYS_LINE = 40
_R_EARTH_KM = 6371.0


def _year() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Hour h ends at h:00, so 2023 runs from 1 January 01:00 to 1 January 2024
    # 00:00; only summer is scored, so the edges never reach a counted day.
    stamp = pd.to_datetime(df[["year", "month", "day", "hour"]])
    return df[(stamp - pd.Timedelta(hours=1)).dt.year == _YEAR]


def _counts() -> dict:
    year = _year()

    # HJ 663 A.2: each city point's own daily maximum, averaged over the points; the whole year feeds
    # the rolling window so 1 June keeps its 31 May history.
    network = frame_to_mda8(year)
    citywide = int((network[network.index.month.isin(_MONTHS)] > _LIMIT).sum())

    per_station = {
        station: frame_to_mda8(g)
        for station, g in year.groupby("station")
    }
    summer_days = sorted({
        d for s in per_station.values() for d in s.index if d.month in _MONTHS
    })
    per_station_days: dict = {}
    anywhere = 0
    for day in summer_days:
        exceeding = {
            station for station, s in per_station.items()
            if pd.notna(s.get(day)) and s.get(day) > _LIMIT
        }
        for station in exceeding:
            per_station_days[station] = per_station_days.get(station, 0) + 1
        if exceeding:
            anywhere += 1

    return {
        "citywide": citywide,
        "anywhere": anywhere,
        "per_station": per_station_days,
    }


def _population_over_line(per_station: dict | None = None) -> float:
    """Residents whose nearest station exceeded on more than `_DAYS_LINE` days.

    `per_station` is accepted so a caller that already has the exceedance
    counts does not pay for a second pass over the year's hourly record.
    """
    bj = DATA_DIR
    pop = pd.read_csv(bj / "population_100m.csv")
    st = pd.read_csv(bj / "station_metadata.csv", dtype={"station_code": "string"})

    if per_station is None:
        per_station = _counts()["per_station"]
    hot = {s for s, n in per_station.items() if n > _DAYS_LINE}

    lat, lon, weight = (
        pop["latitude"].values, pop["longitude"].values, pop["population"].values
    )
    p = np.pi / 180.0
    nearest = np.full(len(pop), np.inf)
    assigned = np.empty(len(pop), dtype=object)
    for _, s in st.iterrows():
        a = (
            np.sin((s["latitude"] - lat) * p / 2) ** 2
            + np.cos(lat * p) * np.cos(s["latitude"] * p)
            * np.sin((s["longitude"] - lon) * p / 2) ** 2
        )
        d = 2 * _R_EARTH_KM * np.arcsin(np.sqrt(a))
        closer = d < nearest
        nearest[closer] = d[closer]
        assigned[closer] = s["station"]
    mask = np.isin(assigned, list(hot))
    return float(weight[mask].sum())


def validate_citywide_days(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("citywide_exceedance_days")
    if val is None:
        return ValidatorResult(
            False, "citywide_exceedance_days not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"citywide_exceedance_days={val!r} is not a number"
        )
    gt = _counts()
    if compare_numeric(val, gt["citywide"], tolerance=0):
        return ValidatorResult(True, f"correct: {val} ~ {gt['citywide']}")
    return ValidatorResult(
        False, f"citywide_exceedance_days={val}, expected ~{gt['citywide']}"
    )


def validate_anywhere_days(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("anywhere_exceedance_days")
    if val is None:
        return ValidatorResult(
            False, "anywhere_exceedance_days not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"anywhere_exceedance_days={val!r} is not a number"
        )
    gt = _counts()
    if compare_numeric(val, gt["anywhere"], tolerance=0):
        return ValidatorResult(True, f"correct: {val} ~ {gt['anywhere']}")
    return ValidatorResult(
        False, f"anywhere_exceedance_days={val}, expected ~{gt['anywhere']}"
    )


def validate_population_over_40(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("population_over_40_days")
    station = runtime.retrieve("station_over_40_days")
    missing = [n for n, v in (("population_over_40_days", val), ("station_over_40_days", station)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    if not is_finite_number(val):
        return ValidatorResult(False, f"population_over_40_days={val!r} is not a number")
    counts = _counts()
    hot = sorted(s for s, n in counts["per_station"].items() if n > _DAYS_LINE)
    gt = _population_over_line(counts["per_station"])
    errors = []
    # To the nearest hundred thousand: 818,533 under both coordinate sets by
    # great-circle distance; the unrestricted-window reading (7.0 million)
    # and the half-remembered validity rule (0) round elsewhere.
    if round(float(val) / 100000) != round(gt / 100000):
        errors.append(f"population_over_40_days={val}, expected ~{gt:.0f}")
    # The variable asks for "the station, or the stations", so a bare name and
    # a list of names are the same answer; what is scored is the SET, so a
    # list that misses a hot station or adds a cool one fails either way.
    names = [station] if isinstance(station, str) else station
    if not isinstance(names, (list, tuple)) or not all(isinstance(n, str) for n in names):
        errors.append(f"station_over_40_days={station!r} is not a station name or a list of them")
    elif {n.strip().casefold() for n in names} != {h.casefold() for h in hot}:
        errors.append(f"station_over_40_days={station!r}, expected {hot}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: about {gt:.0f} residents nearest {', '.join(hot)}")


tools = []
variables = [
    Variable(
        "citywide_exceedance_days",
        None,
        "Store the number of summer-2023 days whose citywide daily maximum "
        "8-hour ozone exceeded the limit, as an integer. Form the city daily "
        "value as HJ 663-2013 defines it: each city assessment point's own "
        "daily maximum 8-hour mean, averaged over the eleven stations flagged "
        "as included in the city aggregate, background site out. A day's "
        "maximum 8-hour mean is the largest of the 8-hour running means whose "
        "window ends between 08:00 and 24:00 of that day, a window counting "
        "once it holds at least 6 valid hours of the 8, and every day of the "
        "period is scored whatever number of valid windows it yields.",
    ),
    Variable(
        "anywhere_exceedance_days",
        None,
        "Store the number of summer-2023 days on which at least one station "
        "exceeded the limit, as an integer, each station judged on its own "
        "hourly record. A day's maximum 8-hour ozone is the largest of the "
        "8-hour running means whose window ends between 08:00 and 24:00 of "
        "that day, a window counting once it holds at least 6 valid hours of "
        "the 8, and every day of the period is scored whatever number of "
        "valid windows it yields.",
    ),
    Variable(
        "population_over_40_days",
        None,
        "Store the number of residents the study would count, to the nearest "
        "hundred thousand, counting a station's days on the same basis as "
        "above. Nearest is by great-circle distance.",
    ),
    Variable(
        "station_over_40_days",
        None,
        "Store the name of the station, or the stations, that exceeded the "
        "limit on more than 40 days, as the string the station metadata uses.",
    ),
]
validators = {
    "validate_citywide_days": validate_citywide_days,
    "validate_anywhere_days": validate_anywhere_days,
    "validate_population_over_40": validate_population_over_40,
}
