"""Roadside ozone is 45 % lower and the oxidant is not (comparative_assessment).

BASELINE, rebuilt 2026-09-02 on the surface rule
(`docs/query_surface_audit.md`). The error this case is about — reading low
roadside ozone as less oxidising air — is an interpretation. The first turn
asks how much ozone a roadside loses to the road; the second asks whether
the air there is less oxidising, and the odd-oxygen sum that answers it is
named as the standard quantity it is.

Pairing each of Hong Kong's three roadside stations with its nearest general
station over 2025, on the 24,386 hours where both report ozone and nitrogen
dioxide, and working in ppb at 25 C and 1 atm:

    ozone            roadside minus general   -13.8545 ppb   (17.18 vs 31.03)
    nitrogen dioxide                          +15.9148
    Ox = O3 + NO2                              +2.0596       (51.59 vs 49.53)

Roadside ozone is 45 % lower. The odd-oxygen sum is 4 % HIGHER. The nitrogen
dioxide gain recovers 115 % of the ozone deficit, which is the shape
titration by fresh nitric oxide takes — the reading being that the ozone is
not absent so much as converted.

**That reading is what the data is consistent with, not what it shows, and
the CC claim says so.** Gate B round 3 found the required claim concluding
that the ozone "has been chemically converted" while the next claim said the
mechanism had not been demonstrated. Two averaged concentration differences
are not a chemical budget: the nitrogen dioxide surplus at a kerb also
contains NO2 emitted directly, which this comparison cannot separate from
NO2 made by titrating ozone.

**The pairs do not agree, and the case scores that rather than averaging it
away.**

    Causeway Bay / Eastern           dO3 -19.06   dOx -0.50   ozone 55 % lower
    Central / Central-Western        dO3 -15.81   dOx +1.49   49 %
    Mong Kok / Sham Shui Po          dO3  -6.69   dOx +5.19   26 %

One of the three has LOWER oxidant at the roadside. So "Ox is conserved" is
the mechanism's expectation, not this data's finding; what the data supports
is that the ozone deficit is largely or wholly offset, with a residual that
varies by pair and is not explained here. Nearest-general pairing is a proxy
for a control, not a control: Causeway Bay's partner is 3.5 km away and Mong
Kok's 1.3 km.

**What is scored, and what survives every route.** The earlier version
scored the two differences to three decimals, which forced the query to
state the pairing, the weighting and three conversion constants (a live run
had used 24.465 L/mol and an audit had found 47.997 g/mol open) — the
query was the recipe. The rebuilt turns score three conclusions that
`_routes()` recomputes under the constructions an analyst could defensibly
choose — the three pairs weighted equally or their station-hours pooled;
every roadside hour against every general hour with no pairing at all; the
conversion at 24.45, 24.465 or 22.414 L/mol — and refuses to score if any
conclusion differs:

    roadside ozone deficit                        "about half lower" on every
                                                  route (42.9 to 44.8 %; an
                                                  ozone-only-hours reading
                                                  gives 42.5, which is why a
                                                  percentage to the nearest 5
                                                  was replaced by the fraction)
    the roadside air is less oxidising            False on every route
                                                  (Ox +1.9 to +4.3 ppb)
    the pairs agree on the oxidant's sign         False (-0.5 / +1.5 / +5.2)

    NOT scored: the differences themselves.

The deficit is a ratio of ozone to ozone, so the conversion cancels out of
it; the oxidant sign needs the conversion and survives every value of it.
The pairs' disagreement is a property of the pairing and is computed on it.

**Pins, and where each one goes** (`case_design_standard.md` §3.1). The
pairing — nearest general station, hours where both report both gases,
2025 — is on the first variable; the conversion constants the standards use
are on the second. Neither is the exam; the exam is the reading.

Ground truth is recomputed from the database at validation time, under six
constructions at once.


**Gate A review 2026-09-06 dropped the both-gases filter from the variable.** It
read "over the hours where both report ozone and nitrogen dioxide", which is a
validity filter of ours on an agent surface. It can go without costing
uniqueness, because `_routes()` already recomputes the scored enum over an
unpaired construction as well as the paired one and refuses to score if they
disagree; the pairing itself stays, because it is the estimand the query asks
for rather than a route to it.
"""

from typing import Dict, List, Tuple

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult
from domains.hk.db import read_frame

_YEAR = {"lo": "2025-01-01", "hi": "2026-01-01"}
_MOLAR_VOLUMES = (24.45, 24.465, 22.414)   # L/mol: the standards' value, R*T/P at 25 C, and 0 C
_M_O3, _M_NO2 = 48.0, 46.0
DEFICITS = ("about a quarter lower", "about half lower", "about three quarters lower")


def _per_pair() -> pd.DataFrame:
    """Per roadside station: hours, and the sums of the differences and levels
    against its nearest general station, on the hours both report both gases."""
    return read_frame(text("""
        with roadside as (
            select id, coordinate::geography as g from air_quality_station
            where station_type = 'ROADSIDE'
        ), general as (
            select id, coordinate::geography as g from air_quality_station
            where station_type = 'GENERAL'
        ), pairs as (
            select roadside.id as roadside_id,
                   (array_agg(general.id order by st_distance(roadside.g, general.g)))[1]
                       as general_id
            from roadside cross join general
            group by roadside.id
        )
        select p.roadside_id, count(*) as n,
               sum(r.o3) as r_o3, sum(g.o3) as g_o3,
               sum(r.no2) as r_no2, sum(g.no2) as g_no2
        from pairs p
        join hourly_station_air_quality r
          on r.station_id = p.roadside_id
         and r.datetime > :lo and r.datetime <= :hi
         and r.o3 is not null and r.no2 is not null
        join hourly_station_air_quality g
          on g.station_id = p.general_id and g.datetime = r.datetime
         and g.o3 is not null and g.no2 is not null
        group by 1
    """), _YEAR)


def _unpaired() -> pd.DataFrame:
    """Every roadside and every general station-hour of the year, by type."""
    return read_frame(text("""
        select s.station_type::text as kind, avg(a.o3) as o3, avg(a.no2) as no2
        from hourly_station_air_quality a
        join air_quality_station s on s.id = a.station_id
        where a.datetime > :lo and a.datetime <= :hi
          and a.o3 is not null and a.no2 is not null
        group by 1
    """), _YEAR).set_index("kind")


def _routes() -> List[Tuple[str, Dict[str, object]]]:
    """(name, {o3_roadside, o3_general, d_o3, d_no2, pair_d_ox}) in ug/m3."""
    pairs = _per_pair()
    means = pairs[["r_o3", "g_o3", "r_no2", "g_no2"]].div(pairs["n"], axis=0)
    routes = []
    for label, weight in (("three pairs, equal weight", None), ("three pairs, pooled hours", pairs["n"])):
        m = means.mean() if weight is None else means.mul(weight, axis=0).sum() / weight.sum()
        routes.append((label, {
            "o3_roadside": float(m["r_o3"]), "o3_general": float(m["g_o3"]),
            "d_o3": float(m["r_o3"] - m["g_o3"]), "d_no2": float(m["r_no2"] - m["g_no2"]),
            "pair_d_o3": (means["r_o3"] - means["g_o3"]).to_numpy(),
            "pair_d_no2": (means["r_no2"] - means["g_no2"]).to_numpy(),
        }))
    kinds = _unpaired()
    r, g = kinds.loc["ROADSIDE"], kinds.loc["GENERAL"]
    routes.append(("every roadside hour against every general hour", {
        "o3_roadside": float(r["o3"]), "o3_general": float(g["o3"]),
        "d_o3": float(r["o3"] - g["o3"]), "d_no2": float(r["no2"] - g["no2"]),
        "pair_d_o3": (means["r_o3"] - means["g_o3"]).to_numpy(),
        "pair_d_no2": (means["r_no2"] - means["g_no2"]).to_numpy(),
    }))
    return routes


def _conclusions(route: Dict[str, object], molar_volume: float) -> Dict[str, object]:
    ppb_o3, ppb_no2 = molar_volume / _M_O3, molar_volume / _M_NO2
    d_ox = route["d_o3"] * ppb_o3 + route["d_no2"] * ppb_no2
    pair_d_ox = route["pair_d_o3"] * ppb_o3 + route["pair_d_no2"] * ppb_no2
    deficit = 1.0 - route["o3_roadside"] / route["o3_general"]
    return {
        "roadside_ozone_deficit": DEFICITS[min(range(3), key=lambda i: abs(deficit - (0.25, 0.5, 0.75)[i]))],
        "roadside_air_less_oxidising": bool(d_ox < 0),
        "pairs_agree_on_oxidant_sign": bool(len({d > 0 for d in pair_d_ox}) == 1),
    }


def _figures() -> Dict[str, object]:
    table = [(f"{name}, {mv} L/mol", _conclusions(route, mv))
             for name, route in _routes() for mv in _MOLAR_VOLUMES]
    out: Dict[str, object] = {}
    for key in table[0][1]:
        values = {row[key] for _, row in table}
        if len(values) != 1:
            raise RuntimeError(f"{key} is not invariant across constructions: "
                               + "; ".join(f"{n}={row[key]!r}" for n, row in table))
        out[key] = values.pop()
    return out


def _normalise(value) -> str:
    return str(value).strip().lower()


def _check(got: Dict[str, object]) -> ValidatorResult:
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    for name, val in got.items():
        expected = gt[name]
        if isinstance(expected, bool):
            ok = (isinstance(val, bool) and val == expected) or (
                isinstance(val, str) and _normalise(val) in {str(expected).lower(),
                                                              "yes" if expected else "no"})
        else:
            ok = _normalise(val) == _normalise(expected)
        if not ok:
            errors.append(f"{name}={val!r}, expected {expected!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


def validate_ozone_deficit(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({"roadside_ozone_deficit": runtime.retrieve("roadside_ozone_deficit")})


def validate_oxidant_reading(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "roadside_air_less_oxidising": runtime.retrieve("roadside_air_less_oxidising"),
        "pairs_agree_on_oxidant_sign": runtime.retrieve("pairs_agree_on_oxidant_sign"),
    })


tools = []
variables = [
    Variable("roadside_ozone_deficit", None,
             "Store how much lower ozone is at the roadside stations than at "
             "the general stations nearest them over 2025, as one of exactly "
             "these strings: " + ", ".join(f"'{x}'" for x in DEFICITS) + ". "
             "Pair each roadside station with the general station nearest to it."),
    Variable("roadside_air_less_oxidising", None,
             "Store True if the air at the roadside is less oxidising than at "
             "the paired general stations — lower in odd oxygen, ozone plus "
             "nitrogen dioxide, in ppb — else False. Convert with a molar "
             "volume of 24.45 L/mol, the value the air quality standards use at "
             "25 C and 1 atm, and molar masses of 48 g/mol for ozone and 46 for "
             "nitrogen dioxide."),
    Variable("pairs_agree_on_oxidant_sign", None,
             "Store True if the three pairs agree on whether the roadside's odd "
             "oxygen is above or below its partner's, else False."),
]
validators = {
    "validate_ozone_deficit": validate_ozone_deficit,
    "validate_oxidant_reading": validate_oxidant_reading,
}
