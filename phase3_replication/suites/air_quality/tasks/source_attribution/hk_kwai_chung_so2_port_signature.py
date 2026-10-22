"""Kwai Chung's southerly SO2 is three times its easterly SO2 — and so is
every other station's; what is local is the excess over a less-exposed site
under the same wind (source_attribution).

BASELINE, hard. The Kwai Tsing container port wraps the Kwai Chung
station's southern and western quarters: Container Port Road bears 240
degrees at 0.4 km (the OSM layer in the database), the terminals stand
along it and on Tsing Yi to the west-south-west, and Rambler Channel with
the Stonecutters Island terminals lies to the south. With the wind at Tsing
Yi from the south (157.5-202.5 degrees) Kwai Chung's SO2 averages 6.45 ug/m3
over 2025; from the east, the prevailing direction, 2.11. (The south-west
sector, 202.5-247.5, reads 4.51 on 171 hours — elevated too, on a fifth of
the sample; the case scores the southerly sector because it carries the
hours and the largest excess.) A desk reads "three times higher
with the wind off the port" and writes that the port is Kwai Chung's SO2
source. The attribution is probably right; the reasoning is not, and the
case scores the reasoning.

**Why the sector contrast is not an attribution.** Southerly flow carries
the harbour and Kowloon plume over the whole western New Territories.
Tsuen Wan, 2.2 km to the north-west (bearing 314 degrees) with no terminal
upwind, rises from 1.47 to 3.35 on the same wind (and to 2.91 in the
south-west sector against Kwai Chung's 4.51); Sha Tin and Central/Western rise too. A
sector enhancement that every station shares is the airmass, not the
station's neighbour. What isolates a LOCAL source is the excess over a
control site under the same wind:

    2025, Tsing Yi wind >= 3 km/h,       south        east
    hours both stations report          (932)        (934)
    Kwai Chung SO2                       6.46         2.13
    Tsuen Wan SO2                        3.33         1.48
    Kwai Chung minus Tsuen Wan          +3.13        +0.65
    Kwai Chung NO2 / Tsuen Wan NO2    66.3 / 53.2   31.9 / 31.9

Under easterlies the two stations agree to 0.65 ug/m3 of SO2 and 0.05 of
NO2; under southerlies Kwai Chung carries 3.1 more SO2 and 13 more NO2. The
southerly air reaching Kwai Chung picks up sulphur near that station which
the air reaching Tsuen Wan does not. Tsuen Wan is the LESS EXPOSED site,
not a source-free one — southerly air reaches it from the harbour as well —
so the excess is a lower bound on the local contribution (Gate B round 19).

**What the excess ratio says, and what it cannot.** The excess is
comparatively rich in sulphur: SO2 over NO2 at 3.13 / 13.14 = 0.238,
against 0.098 for Kwai Chung's own southerly means, so whatever the local
southern contribution is, it carries more sulphur per unit of nitrogen than
the mixture the two stations share. That is consistent with harbour and
port activity, vessels on residual fuel included, and it is the sentence
the desk can write. It is NOT a fuel fingerprint, and Gate B round 19 was
right to strike the word: an ambient concentration ratio is not an emission
ratio — dilution, conversion and deposition act on SO2 and NO2 differently,
and the NO2 measured is not the NOx emitted — so the number cannot identify
a fuel, and terminal plant or channel traffic could carry a similar
signature. Consistent with, on a directional analysis; not proven by it.
The bearing itself is not exact: the southerly sector looks down Rambler
Channel towards Stonecutters rather than at the main terminal front, which
lies west-south-west; a directional excess identifies a direction.

**Turn 1** asks how Kwai Chung's SO2 varies with wind direction and scores
the two sector means and their hour counts. **Turn 2** relays the desk's
line and scores whether the southerly rise is the network's and the
attribution verdict; the claims carry the reasoning: a shared sector
enhancement is the airmass; the excess over a less-exposed site bounds the
local southern contribution from below; the ratio says sulphur-rich and is
consistent with shipping without identifying a fuel; the limits stated.

**Pins, and where each one goes** (`case_design_standard.md` §3.1). Wind
is Tsing Yi's — the nearest station carrying wind — paired to the
air-quality row of the same stamp; hours with Tsing Yi wind below 3 km/h
are excluded (the record codes calm as 0 degrees, and 21 calm hours would
otherwise fall into the north sector); sectors are 45-degree bins centred
on south and east; station-hours need both SO2 and NO2 present. All on
the variables. No control station is named anywhere: choosing one that is
genuinely less exposed is part of the exam (see the rebuild note below).

**Readings measured and excluded** (Kwai Chung south / east; hours):

    calm hours included                      6.31 / 2.37   1051 / 1213
    wind read one hour off the stamp         6.33 / 2.13    951 /  966
    speed threshold 1 km/h                   6.37 / 2.33   1032 / 1160

Turn 1's means use `reports_as` at two decimals; hour counts are exact.
The control figures the earlier turn 2 scored (over the shared hours:
3.13 excess, ratio 0.238; over each station's own hours 3.1 and 0.237) are
now the claims' to require. Gate C also found every model
pairing the wind over a calendar-2025 weather window and losing the last
air-quality hour of the year: the year is the air-quality year, and the
variable now says the wind is taken at the same stamp whatever day the
weather rule assigns it to.

**Limits, which the claims ask the response to state.** The wind is
measured at Tsing Yi, not at the station; SO2 is reported to 0.1 ug/m3 and
the absolute levels are a few micrograms after the fuel-sulphur rules; a
directional excess identifies a direction, not a facility.

**Overlap, stated.** `beijing_wind_sector_pm25` is the sector method on
its own; `hk_calm_coded_as_north` is the calm-wind hazard this case pins
against. Neither has a control site or a fuel-ratio fingerprint.

All ground truths are recomputed from the database at validation time.

**Turn 2 rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier turn named the control site and asked for seven figures over
the shared hours — the query carried the control-site method the case
exists to test, and both models reproduced the figures. The rebuilt turn
relays the desk's line and asks whether it can go out; it scores whether
the southerly rise is the network's (True: every general station with a
hundred hours in each sector reads higher under southerlies, at a 3 km/h
floor and at 1) and the attribution verdict ('consistent but not proven').
The excess over a less-exposed neighbour and its sulphur-richness are now
the claims' to require: they are true against Tsuen Wan, Tung Chung, Kwun
Tong, Yuen Long and Eastern, and false against Sham Shui Po, Central/Western,
Sha Tin and Tuen Mun, which carry their own southerly sulphur — so choosing
a control that is genuinely less exposed is part of the exam, and a bool on
the excess ratio would have been a bool on that choice.

**Gate C on the rebuilt turn 2 (2026-09-02, `gate_c_t1c`):** pro exact on
both verdicts. flash computed every station's sector ratio, wrote "every
station shows a higher SO2 under southerly winds than easterly, but the
ratio at Kwai Chung (3.06x) is far larger than any other station", and
stored `southerly_rise_shared_across_the_network` False. The variable had
said "shared by the other stations rather than particular to Kwai Chung",
which reads as being about size as easily as direction; flash's science was
right (the excess over the shared rise is what is local) and its answer to
the question as worded was defensible. The variable now says the direction
of the change, whatever its size. Re-run queued.


**Gate B round 21 (2026-09-03) rejected the hand-picked control.** The claim
required the response to establish a local southern source from the difference
between Kwai Chung and a less-exposed station, listing five that "serve" and
excluding Sham Shui Po and Tuen Mun because they carry their own sulphur. The
reviewer's objection stands: every urban control has source mixtures, the
record designates none of them source-free, the wind is measured at Tsing Yi
rather than along a common parcel path, and against the two excluded sites the
southerly excess is 0.20 and 0.06 ug/m3 rather than 3.1 to 4.4. A control set
chosen after seeing which ones give the wanted answer is not a control set.

What replaces it is a rank across the whole network, which no choice can move:
under southerlies at a 3 km/h floor every one of the eighteen stations reads
higher than under easterlies — that is the airmass — and Kwai Chung's
enhancement is the LARGEST of the eighteen, 4.34 ug/m3 against 2.46 for
Causeway Bay and 1.92 for Southern. The control comparison stays in the claim
as a sensitivity that has to be reported with its dependence on the control.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, is_finite_number, reports_as
from domains.hk.db import read_frame

_TARGET = "Kwai Chung"
_CONTROL = "Tsuen Wan"
_WIND_STATION = "Tsing Yi"
_MIN_SPEED = 3.0
_SOUTH = (157.5, 202.5)
_EAST = (67.5, 112.5)


def _joined() -> pd.DataFrame:
    aq = read_frame(text("""
        select h.datetime, s.name_en as station, h.so2, h.no2
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where s.name_en in (:target, :control)
          and h.so2 is not null and h.no2 is not null
          and h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
    """), {"target": _TARGET, "control": _CONTROL})
    wind = read_frame(text("""
        select h.datetime, h.wind_degree, h.wind_speed
        from hourly_station_weather h
        join weather_station s on s.id = h.station_id
        where s.name_en = :station and h.wind_speed >= :speed
          and h.wind_degree is not null
    """), {"station": _WIND_STATION, "speed": _MIN_SPEED})
    # The year is the air-quality year (hour-ending stamps); the wind is taken
    # at the same stamp whatever day the weather rule would assign it to.
    frame = aq.merge(wind, on="datetime")
    frame["south"] = (frame["wind_degree"] >= _SOUTH[0]) & (frame["wind_degree"] < _SOUTH[1])
    frame["east"] = (frame["wind_degree"] >= _EAST[0]) & (frame["wind_degree"] < _EAST[1])
    return frame


def _sector_means(min_speed: float) -> pd.DataFrame:
    """Every station's mean SO2 by sector on Tsing Yi's wind, at one speed floor."""
    frame = read_frame(text("""
        select s.name_en as station, w.wind_degree, h.so2
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        join hourly_station_weather w on w.datetime = h.datetime
        join weather_station ws on ws.id = w.station_id
        where ws.name_en = :wind and w.wind_speed >= :speed and w.wind_degree is not null
          and h.so2 is not null and h.no2 is not null
          and h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
    """), {"wind": _WIND_STATION, "speed": min_speed})
    south = (frame["wind_degree"] >= _SOUTH[0]) & (frame["wind_degree"] < _SOUTH[1])
    east = (frame["wind_degree"] >= _EAST[0]) & (frame["wind_degree"] < _EAST[1])
    out = pd.DataFrame({
        "south": frame[south].groupby("station")["so2"].mean(),
        "east": frame[east].groupby("station")["so2"].mean(),
        "n_south": frame[south].groupby("station").size(),
        "n_east": frame[east].groupby("station").size(),
    })
    return out[(out["n_south"] >= 100) & (out["n_east"] >= 100)]


def _figures() -> Dict[str, object]:
    frame = _joined()
    kc = frame[frame["station"] == _TARGET].set_index("datetime")
    out = {
        "kc_so2_south": float(kc.loc[kc["south"], "so2"].mean()),
        "kc_so2_east": float(kc.loc[kc["east"], "so2"].mean()),
        "kc_hours_south": int(kc["south"].sum()),
        "kc_hours_east": int(kc["east"].sum()),
    }
    # Is the southerly enhancement Kwai Chung's, or the airmass's? If every
    # station in the network reads higher under southerlies, it is the
    # airmass. Checked at two speed floors; a disagreement refuses to score.
    shared = {speed: bool((table["south"] > table["east"]).all())
              for speed, table in ((_MIN_SPEED, _sector_means(_MIN_SPEED)),
                                   (1.0, _sector_means(1.0)))}
    if len(set(shared.values())) != 1:
        raise RuntimeError(f"the shared-rise verdict is not invariant: {shared}")
    out["southerly_rise_shared_across_the_network"] = shared[_MIN_SPEED]
    # A judgement, not a computation: a directional excess over a less
    # exposed neighbour is consistent with the port and does not prove it.
    out["port_attribution"] = ATTRIBUTION_CONSISTENT
    return out


def _is_int(val) -> bool:
    """`bool` is an `int` subclass; True must not pass as a count of one."""
    return isinstance(val, int) and not isinstance(val, bool)


def _check(got: Dict[str, object], ints=(), decimals: Dict[str, int] = None) -> ValidatorResult:
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    for name, val in got.items():
        if name in ints:
            if not _is_int(val):
                errors.append(f"{name}={val!r} is not an integer")
            elif val != gt[name]:
                errors.append(f"{name}={val}, expected {gt[name]}")
        elif not is_finite_number(val):
            errors.append(f"{name}={val!r} is not a number")
        elif not reports_as(val, gt[name], decimals=(decimals or {}).get(name, 2)):
            errors.append(f"{name}={val}, expected ~{gt[name]:.3f}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(
        f"{n}={gt[n]}" if n in ints else f"{n}={gt[n]:.3f}" for n in got))


def validate_sectors(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "kc_so2_south": runtime.retrieve("kc_so2_south"),
        "kc_so2_east": runtime.retrieve("kc_so2_east"),
        "kc_hours_south": runtime.retrieve("kc_hours_south"),
        "kc_hours_east": runtime.retrieve("kc_hours_east"),
    }, ints=("kc_hours_south", "kc_hours_east"))


def validate_attribution(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "southerly_rise_shared_across_the_network":
            runtime.retrieve("southerly_rise_shared_across_the_network"),
        "port_attribution": runtime.retrieve("port_attribution"),
    }
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    shared, expected = got["southerly_rise_shared_across_the_network"], \
        gt["southerly_rise_shared_across_the_network"]
    if not ((isinstance(shared, bool) and shared == expected) or
            (isinstance(shared, str) and shared.strip().lower() in
             {str(expected).lower(), "yes" if expected else "no"})):
        errors.append(f"southerly_rise_shared_across_the_network={shared!r}, expected {expected}")
    if str(got["port_attribution"]).strip().lower() != gt["port_attribution"]:
        errors.append(f"port_attribution={got['port_attribution']!r}, "
                      f"expected {gt['port_attribution']!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


_WIND = (
    "Wind is the Tsing Yi weather station's, paired to the air-quality row "
    "with the same timestamp — the year is the air-quality year on the "
    "domain's hour-ending convention, and the wind row is taken at that same "
    "stamp whichever day the weather rule assigns it to; use only hours whose "
    "Tsing Yi wind speed is at "
    "least 3 km/h (calm hours are recorded with a bearing of 0 degrees and must "
    "not be counted as northerly). The southerly sector is a wind bearing from "
    "157.5 up to but not including 202.5 degrees; the easterly sector from 67.5 "
    "up to but not including 112.5. Use only station-hours with both SO2 and NO2 present, "
    "over 2025. "
)
ATTRIBUTION_ALONE = "supported by the sector contrast alone"
ATTRIBUTION_CONSISTENT = "consistent but not proven"
ATTRIBUTION_CONTRADICTED = "contradicted"
tools = []
variables = [
    Variable("kc_so2_south", None,
             "Store the mean SO2 at the Kwai Chung station over the 2025 hours "
             "with a southerly wind, as a float in ug/m3, 2 decimal places. " + _WIND),
    Variable("kc_so2_east", None,
             "Store the same for the easterly wind hours, as a float in ug/m3, 2 decimal places."),
    Variable("kc_hours_south", None,
             "Store the number of Kwai Chung station-hours in the southerly sector, as an integer."),
    Variable("kc_hours_east", None,
             "Store the number of Kwai Chung station-hours in the easterly sector, as an integer."),
    Variable("southerly_rise_shared_across_the_network", None,
             "Store True if the other stations of the network also read higher "
             "SO2 under southerly winds than under easterly ones — the "
             "direction of the change, whatever its size at each station — "
             "else False."),
    Variable("port_attribution", None,
             "Store what these data make of the desk's line that the port is "
             "the source, as one of exactly these strings: "
             f"'{ATTRIBUTION_ALONE}', '{ATTRIBUTION_CONSISTENT}', "
             f"'{ATTRIBUTION_CONTRADICTED}'."),
]
validators = {
    "validate_sectors": validate_sectors,
    "validate_attribution": validate_attribution,
}
