"""Beijing 2023 ozone — equal by day, split by night (comparative_assessment).

Chemistry-contrast BASELINE, deliberately not a diagnostic trap: all four
quantities are pinned means, and the content is the counterintuitive shape
they form. By day the urban class and the background site see essentially the
SAME ozone; by night they diverge, and it is the clean background site that
stays high.

- Day (12:00-16:00 inclusive): day_urban_o3 94.7453, day_background_o3
  95.0947 — 0.35 apart, indistinguishable in practice.
- Night (02:00-05:00 inclusive): night_urban_o3 39.9667, night_background_o3
  51.4947 — 11.5 apart, the background site 29 % HIGHER.

The standard account is NO titration, the textbook nocturnal reaction NO + O3
-> NO2 + O2: urban traffic supplies fresh NO all night, which eats ozone where
it is emitted; the background site has no local NO source, so its overnight
ozone survives. What this record can and cannot say about that account is
drawn carefully, because the first version of the claim overdrew it and Gate B
corrected the boundary: the record holds NO2 but not NO, and NO2 is the
reaction's PRODUCT — the far higher nighttime urban NO2 (40.50 against 10.90
at the background site) is consistent with titration, not proof of it. Field
studies that diagnose titration in Beijing measure NO directly. At least one
alternative is alive in this data's own metadata: the background site stands
at 387.7 m terrain elevation against 42-76 m for the eight urban sites, high
enough to decouple from the shallow nocturnal surface layer and ride the
residual layer where ozone survives the night for reasons that have nothing to
do with local NO. Deposition and mixing differences are likewise unexcluded.
The claim therefore requires the account to be offered as the standard
explanation, the NO2 contrast as corroboration, and at least one alternative
left standing; daytime equality is read as regional photochemistry over a
well-mixed boundary layer, not as evidence the sites are alike.

Groupings are pinned by SHAPE, per the Gate B ruling that "official" wording
fails P1: the urban class is the station table's two-way urban/suburban
field's eight-site side, and the background site is the single site whose
functional role names it a background/control station. Only one field is
two-way and only one site carries that role, so both descriptions resolve
uniquely without naming a column.

Tolerances: +/-0.01 on all four means, covering 2-decimal reporting. Measured
exclusions: the urban basis is station-then-class (pooling station-hours reads
39.8788 at night, 0.088 away, excluded); the night window is 02:00-05:00
(01-05 reads 41.98/52.78 and 00-05 reads 44.32/54.05, both far outside); the
year is 2023, stated.

All four ground truths are recomputed here from the CSVs.


**Gate A review 2026-09-06: this is a Tier 2 case and now says so.** The four
means are unique only because `day_urban_o3` tells the agent to compute each
station's mean before averaging the stations, which is an aggregation order and
therefore a recipe on an agent surface. The review asked whether a coarser
precision would let the pin go, and measured that it does not: on the night
window the urban mean reads 39.9667 station-first, 39.8788 pooled and **37.3992**
with the hourly network means taken first, so whole numbers give 40 / 40 / 37
and the third route is still excluded. Only at the nearest ten do all three
agree, which is too coarse to say anything about ozone.

So the recipe stays and the label changes, which is what
`docs/case_design_standard.md` requires of a case whose uniqueness is bought
that way: it is a Tier 2 execution test, alongside `beijing_multiple_comparisons`
and `hk_visibility_extinction_aggregation`, and it is reported as one rather
than counted as evidence about method selection. The titration science is
unaffected — background ozone exceeds urban ozone by some 11 ug/m3 at night and
the two are level by day on every route — and that contrast is what the claims
score.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_YEAR = 2023
_DAY = (12, 16)
_NIGHT = (2, 5)


def _window_means(aq: pd.DataFrame, urban: list, background: str, hours: tuple) -> dict:
    sel = aq[aq["hour"].between(*hours)].dropna(subset=["O3"])
    per_station = sel.groupby("station")["O3"].mean()
    return {
        "urban": float(per_station[urban].mean()),
        "background": float(per_station[background]),
    }


def _contrast() -> dict:
    bj = DATA_DIR
    aq = pd.read_csv(bj / "air_quality.csv")
    st = pd.read_csv(bj / "station_metadata.csv", dtype={"station_code": "string"})
    aq = aq[aq["year"] == _YEAR]

    urban = st[st["network_class_2013"] == "urban"]["station"].tolist()
    background = st[st["functional_role_2013"] == "background"]["station"].iloc[0]

    day = _window_means(aq, urban, background, _DAY)
    night = _window_means(aq, urban, background, _NIGHT)
    return {
        "day_urban": day["urban"], "day_background": day["background"],
        "night_urban": night["urban"], "night_background": night["background"],
    }


def validate_titration_contrast(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = ("day_urban_o3", "day_background_o3", "night_urban_o3",
             "night_background_o3")
    got = {}
    for name in names:
        val = runtime.retrieve(name)
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")
        got[name] = val

    gt = _contrast()
    keys = ("day_urban", "day_background", "night_urban", "night_background")
    errors = [
        f"{name}={got[name]}, expected ~{gt[key]:.2f}"
        for name, key in zip(names, keys)
        if not reports_as(got[name], gt[key], decimals=2)
    ]
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True,
        f"correct: day {gt['day_urban']:.2f}/{gt['day_background']:.2f}, "
        f"night {gt['night_urban']:.2f}/{gt['night_background']:.2f} ug/m3",
    )


tools = []
variables = [
    Variable(
        "day_urban_o3",
        None,
        "Store the daytime urban-class mean as a float in ug/m3, 2 decimal "
        "places. Urban is the eight-site side of the station table's two-way "
        "urban/suburban classification; compute each station's mean first, "
        "then average the stations.",
    ),
    Variable(
        "day_background_o3",
        None,
        "Store the daytime background-site mean as a float in ug/m3, 2 "
        "decimal places — the single station whose functional role designates "
        "it a background station.",
    ),
    Variable(
        "night_urban_o3",
        None,
        "Store the nighttime urban-class mean as a float in ug/m3, 2 decimal "
        "places.",
    ),
    Variable(
        "night_background_o3",
        None,
        "Store the nighttime background-site mean as a float in ug/m3, "
        "2 decimal places.",
    ),
]
validators = {"validate_titration_contrast": validate_titration_contrast}
