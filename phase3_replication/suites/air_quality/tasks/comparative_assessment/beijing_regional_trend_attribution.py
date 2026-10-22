"""Beijing winter trend — the regional confounder (comparative_assessment).

A two-step attribution problem of the kind that decides whether a city's air
quality policy is credited with an improvement. Beijing's winter mean PM2.5 fell
8.82 ug/m3 between winter 2022 and winter 2025, which reads as a local success.
But the surrounding transmission-channel cities fell 13.79 ug/m3 over the same two
winters, so relative to its own airshed Beijing did NOT improve — it lagged by
4.98 ug/m3.

- Turn 1 (beijing_winter_change): -8.82 ug/m3, the raw local change. Uniquely
  defined once the query pins pooling of station-hours.
- Turn 2 (the verdict): +4.98 ug/m3 = Beijing's change minus the regional
  change on the pinned construction, scored as "fell by less than the region". The nearest documented wrong path is -8.82 — reporting the
  raw local change again, never netting out the shared regional trend. The two
  differ in SIGN, so the scientific conclusion inverts.

BASELINE, reclassified from trap on two grounds that arrived together. The
first is the reviewer's: after a query that says in as many words "Beijing's
change minus that regional figure", answering -8.82 is a failure to execute an
instruction, not an atmospheric misconception, and P5 asks a trap for the
latter.

The second is measured. In discovery round 1 NEITHER model took that path.
flash answered 5.64, and the reason is worth more than the label: it recomputed
Beijing from the CITY-LEVEL record in turn 2 (-8.1709) after answering turn 1
from the twelve-station network (-8.8583), which is the domain
prompt's WHICH BEIJING default. Its two turns therefore contradict each other
by 0.69 ug/m3 and **nothing reports that** — PV scores turns independently, so
turn 1 passed on one definition while turn 2 failed on another and the pair was
never compared. A cross-turn consistency check on shared quantities would catch
it; the corpus has none, and this is the case that shows why one is worth
building.

The turn-2 ask was also narrowed. It used to end "say what the result tells you
about Beijing's own performance", which invites exactly the attribution the
design cannot support: the regional series mixes those cities' own controls
with the meteorology the whole airshed shared, and nothing here separates them.
It now asks what the comparison does and does NOT establish, and the second
claim scores the second half — otherwise the limit would have lived only in
this docstring, which P4b names as its own failure mode.

The sign inversion is robust to aggregation choice (per-station-then-average gives
-9.68 and +4.12), but the exact values are not, which is why the query pins pooling.

**The turn-2 sign convention was itself ambiguous, and an external audit was
right about it.** The query used to say the difference is "signed positive when
Beijing's change is the larger of the two". Both changes are NEGATIVE — Beijing
-8.816022, the region -13.794197 — so "larger" reads either as the larger
number (-8.82 > -13.79, giving +4.98) or as the larger reduction (13.79 > 8.82,
giving -4.98), and no +/-0.05 band survives a sign flip. Worse, the case's whole
point is that the sign carries the conclusion. The query now just says
"Beijing's change minus that regional figure" and the variable states the
subtraction order and what a positive value means, so the direction is
arithmetic rather than adjectival.

Two further audit findings on the same case were checked and only one held. The
regional membership WAS underspecified and the variable now names it: every city
of the regional file except Beijing. The panel-completeness worry does NOT hold
— both winters carry all 30 non-Beijing cities with 2,102 to 2,146 hours each,
no city absent from either window, and restricting to cities present in both
reproduces -13.794197 to every digit. Measured, not assumed.

Tolerance +/-0.01 ug/m3 on turn 1, covering 2-decimal reporting. With pooling
pinned the values are exact to rounding, so the band absorbs nothing
methodological; it was +/-0.5, which left the per-station-then-average variant
the query rules out (-9.68) only 1.7 bands away, and then +/-0.05, which
accepted the winters taken as label months (-8.86, 0.042 from the answer). A
winter is the domain's air-quality months: December starts after label
1 December 00:00 and February ends with label 1 March 00:00, the hour that
closes 28 February. That reading moves no verdict.

Both ground truths are recomputed here from the CSVs.

**Turn 2 rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier turn dictated the regional construction and scored the
difference to two decimals; the rebuilt one asks whether Beijing's
improvement is its own and scores the verdict — fell by less than the
region, under every recipe, roster and weighting measured — and whether
the comparison establishes cause. Turn 1 keeps its pooled figure.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_EARLY, _LATE = 2022, 2025
_BEIJING_CITY = "北京"
FELL_BY_LESS = "fell by less than the region"
FELL_BY_MORE = "fell by more than the region"
SAME = "about the same as the region"


def _winter(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """December of year-1 plus January and February of `year`. Hour h ends
    at h:00, so label 0 belongs to the previous date and its month."""
    t = pd.to_datetime(df[["year", "month", "day", "hour"]]) - pd.Timedelta(hours=1)
    return df[
        ((t.dt.year == year) & (t.dt.month.isin([1, 2])))
        | ((t.dt.year == year - 1) & (t.dt.month == 12))
    ]


def _changes() -> dict:
    bj_dir = DATA_DIR
    df = pd.read_csv(bj_dir / "air_quality.csv")
    cities = pd.read_csv(bj_dir / "region_cities.csv")

    # Beijing: pooled station-hours, as the query specifies.
    beijing = _winter(df, _LATE)["PM2.5"].mean() - _winter(df, _EARLY)["PM2.5"].mean()

    # Region: each city's own window mean, then averaged across cities.
    def regional(year: int) -> float:
        w = _winter(cities, year)
        return w[w["city"] != _BEIJING_CITY].groupby("city")["PM2.5"].mean().mean()

    region = regional(_LATE) - regional(_EARLY)
    # The verdict, asserted across Beijing's recipe (pooled -8.82, two-step
    # -8.08), the regional roster (30 non-Beijing cities -13.79; the 27
    # channel cities without northern Hebei -14.59) and the regional
    # weighting (per city or pooled, identical to two decimals).
    two_step = (_winter(df, _LATE).groupby(["year", "month", "day", "hour"])["PM2.5"].mean().mean()
                - _winter(df, _EARLY).groupby(["year", "month", "day", "hour"])["PM2.5"].mean().mean())
    northern = {"张家口", "承德", "秦皇岛"}

    def regional_pooled(year: int, roster) -> float:
        w = _winter(cities, year)
        return w[w["city"].isin(roster)]["PM2.5"].mean()

    rosters = {"all": [c for c in cities["city"].unique() if c != _BEIJING_CITY],
               "channel": [c for c in cities["city"].unique() if c != _BEIJING_CITY and c not in northern]}
    verdicts = set()
    for local in (beijing, two_step):
        for roster in rosters.values():
            for reg in (region, regional_pooled(_LATE, roster) - regional_pooled(_EARLY, roster)):
                verdicts.add(FELL_BY_LESS if local - reg > 0.5 else FELL_BY_MORE if local - reg < -0.5 else SAME)
    if len(verdicts) != 1:
        raise RuntimeError(f"the regional verdict is not invariant: {verdicts}")
    return {
        "beijing_change": float(beijing),
        "adjusted": float(beijing - region),
        "relative": verdicts.pop(),
        # A judgement, not a computation: the regional figure mixes those
        # cities' controls with the airshed's meteorology.
        "comparison_establishes_cause": False,
    }


def validate_beijing_winter_change(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("beijing_winter_change")
    if val is None:
        return ValidatorResult(
            False, "beijing_winter_change not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"beijing_winter_change={val!r} is not a number"
        )

    gt = _changes()
    if reports_as(val, gt["beijing_change"], decimals=2):
        return ValidatorResult(
            True, f"correct: {val} ~ {gt['beijing_change']:.2f} ug/m3"
        )
    return ValidatorResult(
        False,
        f"beijing_winter_change={val}, expected ~{gt['beijing_change']:.2f}",
    )


def validate_regional_adjusted_change(response: str, runtime, turn: Turn) -> ValidatorResult:
    relative = runtime.retrieve("beijing_relative_to_region")
    cause = runtime.retrieve("comparison_establishes_cause")
    missing = [n for n, v in (("beijing_relative_to_region", relative),
                              ("comparison_establishes_cause", cause)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _changes()
    errors = []
    if str(relative).strip().lower() != gt["relative"]:
        errors.append(f"beijing_relative_to_region={relative!r}, expected {gt['relative']!r}")
    ok = (isinstance(cause, bool) and cause == gt["comparison_establishes_cause"]) or (
        isinstance(cause, str) and cause.strip().lower() in {"false", "no"})
    if not ok:
        errors.append(f"comparison_establishes_cause={cause!r}, expected False")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: Beijing {gt['relative']} ({gt['adjusted']:+.2f} ug/m3 on the "
                                 "pinned construction); the comparison establishes no cause")


tools = []
variables = [
    Variable(
        "beijing_winter_change",
        None,
        "Store the change in Beijing's winter mean PM2.5 from the earlier winter to "
        "the later one as a float in ug/m3, 2 decimal places (negative = a decrease).",
    ),
    Variable("beijing_relative_to_region", None,
             "Store how Beijing's change between the two winters compares with "
             "the other channel cities' — every city of `cities_df` except "
             "Beijing — as one of exactly these strings: "
             f"'{FELL_BY_LESS}', '{FELL_BY_MORE}', '{SAME}'."),
    Variable("comparison_establishes_cause", None,
             "Store True if that comparison establishes why Beijing's winter "
             "PM2.5 moved, else False."),
]


def validate_evidence_and_conclusion_full_review(response: str, runtime, turn: Turn) -> ValidatorResult:
    values = {
        'beijing_winter_change': runtime.retrieve("beijing_winter_change"),
        'beijing_relative_to_region': runtime.retrieve("beijing_relative_to_region"),
        'comparison_establishes_cause': runtime.retrieve("comparison_establishes_cause"),
    }
    missing = [name for name, value in values.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    result = validate_beijing_winter_change(response, runtime, turn)
    if not result.success:
        return result
    result = validate_regional_adjusted_change(response, runtime, turn)
    if not result.success:
        return result
    return ValidatorResult(True, "computed evidence and conclusion accepted")

validators = {
    "validate_beijing_winter_change": validate_beijing_winter_change,
    "validate_regional_adjusted_change": validate_regional_adjusted_change,
    'validate_evidence_and_conclusion_full_review': validate_evidence_and_conclusion_full_review,
}
