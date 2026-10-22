"""Dingling 1000 hPa — the below-ground level probe (data_retrieval).

Silent data-semantics BASELINE whose diagnostic weight sits entirely in the CC
channel, classified per the `fire_detection_bias` precedent. It was registered
as a trap, and a self-review of §4 compliance found it does not meet the
contract: a trap needs a plausible-but-wrong METHOD landing on a specific wrong
answer, and here an agent that never notices the level is underground still
computes -1.55 correctly. The PV number cannot discriminate the deficiency
being probed. The only numeric alternative is a Kelvin slip at 271.6, which is
a unit error rather than a domain one, and it stays as a probe.

The contrast with `beijing_fine_fraction_2020`, which this case was modelled
on, is worth stating because the two look alike: there, an agent that spots the
impossible data and "cleans" it lands on 0.52 or 0.56 depending on how it
cleans, against a scored mass share near 0.67 — noticing the artefact and
acting on it produces a specific wrong number. (That case is registered a
baseline, not a trap, and the two figures quoted here were 0.5545 and 0.656
until a verification pass on 2026-09-07 found both withdrawn.) Here, noticing changes nothing about the arithmetic. Same silent
structure, different §4 status.

The query is an ordinary retrieval, and the capability under test — knowing
that pressure-level reanalysis is extrapolated below the terrain where the
surface pressure is lower than the level — is checked through claims, with no
hint in the query.

Dingling sits at 387.7 m; its January surface pressure averages ~985 hPa, so the
1000 hPa surface (monthly-mean geopotential height ~216 m) lies underground at
this station for 100 % of the month's hours. The retrieved "temperature" is the
model's subsurface extrapolation, not any real air. Every other station's
terrain is low enough that the same level is genuinely in the atmosphere, which
is why turn 2's 925 hPa question — absorbed from the former
`beijing_geopotential_agl` — never meets the below-ground issue itself.

- PV: mean temperature_c at 1000 hPa, Dingling, January 2023 = -1.55 C (744
  hours, no nulls; a plain unique computation). Tolerance +/-0.2 C: it covers
  rounding only, and is nowhere near the 273 that a Kelvin slip would add.
- CC: does the response itself discover and say that the level is below ground
  and the value is an extrapolation?

Both ground truths are recomputed here from the CSV.

**Turn 2 absorbed `beijing_geopotential_agl`** (corpus triage merge pair 4,
executed 2026-08-24): the 925 hPa clearance question is the same vertical-datum
lesson from the other side. Geopotential height is referenced to mean sea
level; how far a pressure surface sits ABOVE THE GROUND is that height minus
the station's terrain elevation. Across the twelve stations the January 2023
mean 925 hPa geopotential height spans just 830.0-833.0 m (the ERA5 grid
barely resolves the city) while terrain spans 31.6-387.7 m, so the terrain
term decides both the value and the winner:

- correct: min over stations of (mean geopotential height - terrain)
  -> 444 m, at Dingling, the highest-sited station.
- wrong path: the minimum raw geopotential height -> 830 m, at Huairou —
  386 m out and the wrong station.

Tolerance +/-3.0 m, matching the 3.1 m cross-station spread of the raw
height: the band deliberately cannot separate stations on that term, because
terrain is what decides. All 744 hourly records present at 925 hPa for every
station. The two turns together are one misread of the vertical datum: turn 1
finds a level that is UNDER the ground and asks what the number means there;
turn 2 asks how far a level is ABOVE the ground and fails anyone who never
subtracts the ground at all.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_STATION, _LEVEL, _YEAR, _MONTH = "Dingling", 1000.0, 2023, 1


def _mean_t() -> float:
    prof = pd.read_csv(DATA_DIR / "profile_era5.csv")
    sel = prof[
        (prof["station"] == _STATION)
        & (prof["pressure_hpa"] == _LEVEL)
        & (prof["year"] == _YEAR)
        & (prof["month"] == _MONTH)
    ]
    return float(sel["temperature_c"].mean())


def validate_mean_t1000(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("mean_t1000_dingling")
    if val is None:
        return ValidatorResult(
            False, "mean_t1000_dingling not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"mean_t1000_dingling={val!r} is not a number"
        )

    correct = _mean_t()
    if reports_as(val, correct, decimals=2):
        return ValidatorResult(
            True, f"correct: {val} ~ {correct:.2f} C"
        )
    return ValidatorResult(
        False, f"mean_t1000_dingling={val}, expected ~{correct:.2f} C"
    )


_LEVEL_HPA = 925.0


def _heights() -> dict:
    bj = DATA_DIR
    prof = pd.read_csv(bj / "profile_era5.csv")
    st = pd.read_csv(bj / "station_metadata.csv").set_index("station")

    sel = prof[
        (prof["pressure_hpa"] == _LEVEL_HPA)
        & (prof["year"] == _YEAR)
        & (prof["month"] == _MONTH)
    ]
    amsl = sel.groupby("station")["geopotential_height_m"].mean()
    agl = amsl - st.loc[amsl.index, "terrain_elevation_m"]
    return {
        "correct": float(agl.min()),
        "correct_station": str(agl.idxmin()),
    }


def validate_min_agl(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("min_925hpa_height_above_ground_m")
    if val is None:
        return ValidatorResult(
            False,
            "min_925hpa_height_above_ground_m not set",
            variables_not_set=True,
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"min_925hpa_height_above_ground_m={val!r} is not a number"
        )

    gt = _heights()
    if reports_as(val, gt["correct"], decimals=1):
        return ValidatorResult(
            True,
            f"correct: {val} ~ {gt['correct']:.0f} m at {gt['correct_station']}",
        )
    return ValidatorResult(
        False,
        f"min_925hpa_height_above_ground_m={val}, expected ~{gt['correct']:.0f} m",
    )


tools = []
variables = [
    Variable(
        "mean_t1000_dingling",
        None,
        "Store the mean temperature at the 1000 hPa level at Dingling over January "
        "2023 as a float in degrees Celsius, 2 decimal places.",
    ),
    Variable(
        "min_925hpa_height_above_ground_m",
        None,
        "Store the smallest across-station distance from the ground up to "
        "the 925 hPa surface, as a float in metres, 1 decimal place.",
    ),
]


validators = {
    "validate_mean_t1000": validate_mean_t1000,
    "validate_min_agl": validate_min_agl,
}
