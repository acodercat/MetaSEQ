"""Beijing monitor catchments — how unevenly the network carries the city
(spatial_analysis).

Catchment BASELINE, deliberately not a diagnostic trap. The query states the
operation; what it tests is whether an agent can carry a 100 m population grid
through a nearest-station assignment and summarise the result two ways without
losing the denominator.

- largest_catchment_population_share_pct: 13.70, scored to the nearest whole
  per cent. Tiantan is nearest for
  2,448,121 of the grid's 17,870,621 residents.
- the ratio, 19.27, no longer scored: Tiantan carries that many times the load
  of Dingling, which is nearest for 127,025.

Why it is a baseline rather than a trap. "Largest catchment" is ambiguous
between residents, grid cells and area, so P1 forces the query to pin
population weighting — and pinning it is exactly what removes the trap. Two
unpinned readings are still worth recording as probes:

- Counting CELLS instead of residents makes Shunyi the largest catchment at
  19.89 % with a ratio of 15.95. The suburban catchments really are vast and
  nearly empty — Dingling holds 8.8 residents per cell and Huairou 16.8, against
  205 for Guanyuan and 199 for Dongsi — so the two rankings barely resemble each
  other.
- Measuring distance in the plane of raw degrees, rather than on the sphere the
  query names, moves 38,597 of the 329,384 cells — nearly one in eight — and
  makes Nongzhanguan the largest catchment at 15.03 % with a ratio of 20.56. At
  40 degrees north a degree of longitude spans only 0.766 of a degree of
  latitude, so treating the two as interchangeable stretches the east-west axis.
  The reassignments do not favour one direction: 47 % of them hand the cell to a
  station displaced mainly north-south and 53 % to one displaced mainly
  east-west, which is worth stating because the tidy story — that the distortion
  systematically favours one axis — is not what the data shows.

THE ACCESS DISTANCE IS NOW SCORED HERE. `beijing_monitor_access_population_weighted`
asked for the population-weighted mean distance to the nearest monitor, 7.55 km,
off the same grid and the same assignment; a corpus triage found the two were
one network-siting audit split across two scenarios and this case is the
survivor. 10.80 km — the UNWEIGHTED mean over cells, which counts an empty
mountain cell like a tower block — came across with it as a probe.

AND THE RATIO POINTS AT THE WRONG END OF THE NETWORK, which is what the case
now asks about and what it previously left unsaid. The 19.27x denominator is
Dingling, and `station_metadata.csv` records Dingling as the network's
`background` site, the only one — sited away from population on purpose and
excluded from the city aggregate for the same reason. Its 127 thousand
residents against Tiantan's 2.45 million is the design working, not a coverage
gap. Measured: drop the background site and the imbalance across the eleven
assessment stations falls from 19.27x to **4.74x** (Tiantan against Huairou).
Four fifths of the headline ratio is an artefact of including a station that is
not meant to serve anyone.

A response that reads 19x as the network's imbalance, or that recommends action
on the smallest catchment, has been misled by a number this case computes
correctly. That is the claim, and it is why the two station identities are
scored rather than left to prose: without the names, nothing distinguishes an
answer that knows which site sits at each end from one that does not. A nineteen-fold spread means the twelve stations are not twelve
comparable samples of the city's exposure, which is the assumption every
station-average in this corpus quietly makes.

Tolerances (both +/-0.01 until 2026-09-02), and the invariance behind them is
unusually strong.
A nearest-neighbour assignment does not depend on the Earth radius at all —
6367, 6371 and 6378.137 km give the identical assignment, maximum, minimum and
ratio — and substituting the secondary registry coordinate set changes nothing
either, despite the 3.5 km Gucheng discrepancy that
`beijing_station_coordinate_audit` is about. Nothing is left but the 2-decimal
reporting the variables ask for. The band has to stay tight because the
runner-up share, Nongzhanguan at 13.47, sits only 0.23 pp below the answer.

Ties were checked rather than assumed, because 0.01 is a narrow band to hang on
an argmin. No cell is exactly equidistant from two stations; the closest call is
1.2e-06 km, and 52 cells holding 3808 residents sit within a metre of a
boundary — 0.021 % of the grid, which is twice the band and so would matter if
those cells were genuinely unstable. They are not: three independent
great-circle implementations (a full distance matrix, the sequential minimum
this validator uses, and a KD-tree over 3-D unit-sphere coordinates) assign all
329,384 cells identically and agree to six decimals on both answers.

The query pins the coordinate set even so. Gate B ruled in an earlier round that
P1 may not be secured by an instruction in the domain schema rather than in the
query, and that ruling does not bend for a case where the choice happens to be
harmless — a reviewer should not have to measure the invariance to know the
question is well posed.

Both ground truths are recomputed here from the CSVs.

**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier query dictated the assignment and asked for five figures; the
rebuilt one asks how unevenly the network carries the city and where a
review should look. The assignment rule moves to the first variable, the
share is scored to the nearest whole per cent (14) and the access distance
to the nearest half kilometre (7.5: the value is 7.55, and whole
kilometres would have put it 0.05 from an edge), both identical under
either coordinate set; the two station names stay, the
ratio goes, and the review verdict is scored — the heavily loaded end,
because the smallest catchment is the background site by design.


**Gate B round 21 (2026-09-03):** the review enum offered "the heavily loaded
stations", "the background site" or "nothing", and the reviewer pointed out
that a coverage review can defensibly look at the sparse edge as well as the
high-leverage core — the catchments settle which stations sit at each end, not
which end a review should care about. A fourth option, "both ends of the
distribution", was added. It is accepted alongside "the heavily loaded
stations", not instead of it: the loaded end is the reading this docstring
argues for, so scoring only "both ends" would fail it, and an option worded as
the loaded stations plus the background site would ask the agent to treat the
background site as a gap. The both-ends option is therefore worded as the
loaded core and the sparse edge together, and the claim requires a response
that looks at the sparse edge to say why the smallest catchment is not a
fault. The trap is unchanged: reading
Dingling's small catchment as a siting failure still lands on "the background
site", and a site chosen to measure background air is meant to have few people
near it.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn

_R_EARTH_KM = 6371.0
REVIEW_LOADED = "the heavily loaded stations"
REVIEW_BACKGROUND = "the background site"
REVIEW_BOTH_ENDS = "both ends of the distribution"
REVIEW_NOTHING = "nothing"


def _haversine_km(lat1, lon1, lat2, lon2):
    p = np.pi / 180.0
    a = (
        np.sin((lat2 - lat1) * p / 2) ** 2
        + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    )
    return 2 * _R_EARTH_KM * np.arcsin(np.sqrt(a))


def _catchments() -> dict:
    bj = DATA_DIR
    pop = pd.read_csv(bj / "population_100m.csv")
    st = pd.read_csv(bj / "station_metadata.csv", dtype={"station_code": "string"})

    lat, lon, weight = (
        pop["latitude"].values, pop["longitude"].values, pop["population"].values
    )
    nearest = np.full(len(pop), np.inf)
    assigned = np.zeros(len(pop), dtype=int)
    for i, s in enumerate(st.itertuples()):
        d = _haversine_km(lat, lon, s.latitude, s.longitude)
        closer = d < nearest
        nearest[closer] = d[closer]
        assigned[closer] = i

    loads = np.bincount(assigned, weights=weight, minlength=len(st))
    names = st["station"].tolist()
    return {
        "share": 100.0 * float(loads.max()) / float(weight.sum()),
        "ratio": float(loads.max()) / float(loads.min()),
        "largest": names[int(loads.argmax())],
        "smallest": names[int(loads.argmin())],
        "access_km": float(np.average(nearest, weights=weight)),
        # A judgement, not a computation: the smallest catchment is the
        # background site by design; the heavily loaded end is the review's.
        # A review may also look over the sparse edge (Gate B round 21), so
        # either answer that includes the loaded end is accepted; one that
        # sends the review to the background site alone, or nowhere, is not.
        "review_targets": (REVIEW_LOADED, REVIEW_BOTH_ENDS),
    }


def validate_catchment_imbalance(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {name: runtime.retrieve(name) for name in (
        "largest_catchment_population_share_pct", "mean_distance_to_monitor_km",
        "largest_catchment_station", "smallest_catchment_station")}
    missing = [n for n, v in got.items() if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    for name in ["largest_catchment_population_share_pct", "mean_distance_to_monitor_km"]:
        if not is_finite_number(got[name]):
            return ValidatorResult(False, f"{name}={got[name]!r} is not a number")
    gt = _catchments()
    errors = []
    if round(float(got["largest_catchment_population_share_pct"])) != round(gt["share"]):
        errors.append(f"largest_catchment_population_share_pct={got['largest_catchment_population_share_pct']}, "
                      f"expected ~{gt['share']:.0f} %")
    if round(2 * float(got["mean_distance_to_monitor_km"])) != round(2 * gt["access_km"]):
        errors.append(f"mean_distance_to_monitor_km={got['mean_distance_to_monitor_km']}, "
                      f"expected ~{round(2 * gt['access_km']) / 2:.1f} km")
    for name, expected in (("largest_catchment_station", gt["largest"]),
                           ("smallest_catchment_station", gt["smallest"])):
        if str(got[name]).strip().casefold() != expected.casefold():
            errors.append(f"{name}={got[name]!r}, expected {expected!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: {gt['largest']} carries about {gt['share']:.0f} % of residents, "
                                 f"{gt['smallest']} the fewest; access about {round(2 * gt['access_km']) / 2:.1f} km; "
                                 "interpret coverage in light of station roles")


tools = []
_ASSIGNMENT = (
    "Assign every cell of Beijing's population grid to whichever monitoring "
    "station is nearest by great-circle distance, locating the stations by "
    "their benchmark-reproduction coordinates rather than their secondary "
    "registry references, and total the residents assigned to each station. "
)
variables = [
    Variable("largest_catchment_population_share_pct", None,
             "Store the largest station catchment's share of the grid's total "
             "population as a percentage to the nearest whole number. " + _ASSIGNMENT),
    Variable("largest_catchment_station", None,
             "Store the name of the station with the largest assigned "
             "population, as the string the station metadata uses."),
    Variable("smallest_catchment_station", None,
             "Store the name of the station with the smallest assigned "
             "population, spelled the same way."),
    Variable("mean_distance_to_monitor_km", None,
             "Store how far the average resident lives from their nearest "
             "station — the population-weighted mean distance from a grid cell "
             "to its nearest station — as a float in km to the nearest half "
             "kilometre."),
]
validators = {"validate_catchment_imbalance": validate_catchment_imbalance}
