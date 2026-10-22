"""April 2025 dust: the event is in the coarse fraction, and a fine-particulate
monitor would have caught it anyway (exceedance_anomaly_detection).

BASELINE, rebuilt 2026-09-02 on the surface rule
(`docs/query_surface_audit.md`). At the hour the coarse fraction peaks, PM10
across the general stations averages 274.10 ug/m3 against PM2.5's 75.55, and
the median station-level PM10 minus PM2.5 reaches 198.7 — about three
quarters of the mass is coarse.

**What this case used to claim about the fine fraction was false, and the
correction is now what the second turn scores.** It said PM2.5 at 75.55 was
"elevated but unremarkable" and that fine-particulate monitoring would have
"registered little". Measured against every hour of 2025 on the general
network, 75.55 is above 99.93 % of them — only 6 hours in the year are
higher. A PM2.5 monitor would have recorded one of the worst hours of the
year. And the published AQHI at that hour reads 6 to 8 across the fifteen
general stations, with the particulate branch taking the PM10 term at every
one of them — so the composite index registered it too.

What fine-only measurement actually loses is not the severity but the SHAPE:
that three quarters of the mass was coarse, which is what points at
wind-blown mineral dust rather than at a combustion or secondary-aerosol
episode, and which changes both the likely source and the depth of
deposition in the airway. Source for the index reading: the `aqhi` column,
EPD's published index.

The window 2025-04-12 22:00 to 2025-04-16 00:00 is the episode Hong Kong's
government announced on 2025-04-13 (info.gov.hk P2025041300395), which
reported a far larger rise in PM10 than in PM2.5. The announcement is
corroboration that the episode happened, not the source of any number here.

**The data this case rests on was recovered, not collected.** 2025-04-09 to
04-15 was one of the network's collection outages: of the 1,350 station-hours
in this window, 1,116 were absent from the database until 2026-08-10 and were
recovered from the data.gov.hk historical archive, and every row at the peak
hour is one of them. The recovery is verified — over the 240k station-hours
held by both sources all six pollutants agree to the last digit.

**What is scored, and what survives every route.** The earlier version
scored the peak HOUR and two concentrations to two decimals, which forced
the query to name the median, the station-first order, the general stations
and the tie-break — the hourly median coarse fraction reads exactly 198.7 at
both 04:00 and 10:00 on 13 April, the hourly mean peaks at 09:00, and the
query had to say which. The rebuilt turns score conclusions that
`_routes()` recomputes under six constructions — the coarse fraction as the
across-station median or mean of each station's PM10 minus PM2.5, or as the
network-mean PM10 minus the network-mean PM2.5; over the general stations or
all eighteen — and refuses to score if any conclusion differs:

    the peak day                             2025-04-13 on every route
    coarse share of PM10 at the peak         about three quarters
                                             (0.72 to 0.75 unrounded)
    PM2.5 at the peak among the year's       True: 6 to 28 of 2025's 8,760
      highest hundredth of hours               general-network hours are higher
    the source settled by these data         False, by construction

    NOT scored: the peak hour, the concentrations.

The coarse share is scored as one of four named fractions rather than a
number because the mean-based routes read 0.746 to 0.750 — on the boundary
at one decimal — while every route is nearer three quarters than half or
nearly all. The fine-fraction rank is scored against the year's highest 1 %
of hours; the weakest route (the mean-based 09:00 peak, PM2.5 68.08) still
sits in the highest 0.4 %.

**The judgement that is scored as a constant.** Whether the data settle
where the particles came from is not computed: PM10, PM2.5 and their ratio
identify a size distribution, and a size distribution is consistent with
wind-blown mineral dust and with other coarse sources — it is not a
composition, a back-trajectory or a source apportionment. The validator
holds that as False; the claims carry the argument.

All ground truths are recomputed here from the database, under six
constructions at once.
"""

from typing import Dict, List, Tuple

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult
from domains.hk.db import read_frame

_WINDOW = {"lo": "2025-04-12 22:00", "hi": "2025-04-16 00:00"}
_YEAR = {"lo": "2025-01-01", "hi": "2026-01-01"}
_TOP_SHARE = 0.01
SHARES = ("about a quarter", "about half", "about three quarters", "nearly all")


def _window_rows(general_only: bool) -> pd.DataFrame:
    kind = "and s.station_type = 'GENERAL'" if general_only else ""
    rows = read_frame(text(f"""
        select q.datetime, q.pm10, q.pm2_5
        from hourly_station_air_quality q
        join air_quality_station s on s.id = q.station_id
        where q.datetime >= :lo and q.datetime <= :hi {kind}
          and q.pm10 is not null and q.pm2_5 is not null
    """), _WINDOW)
    rows["datetime"] = pd.to_datetime(rows["datetime"])
    rows["coarse"] = rows["pm10"] - rows["pm2_5"]
    return rows


def _year_network_pm25() -> pd.Series:
    """Hourly general-network mean PM2.5 over 2025, for ranking the peak."""
    frame = read_frame(text("""
        select q.datetime, avg(q.pm2_5) as pm25
        from hourly_station_air_quality q
        join air_quality_station s on s.id = q.station_id
        where q.datetime > :lo and q.datetime <= :hi
          and s.station_type = 'GENERAL' and q.pm2_5 is not null
        group by 1
    """), _YEAR)
    return frame.set_index(pd.to_datetime(frame["datetime"]))["pm25"]


def _routes() -> List[Tuple[str, pd.Series]]:
    """(name, the row of network means at that construction's peak hour)."""
    routes = []
    for general_only in (True, False):
        rows = _window_rows(general_only)
        by_hour = rows.groupby("datetime").agg(pm10=("pm10", "mean"), pm25=("pm2_5", "mean"),
                                               median=("coarse", "median"), mean=("coarse", "mean"))
        by_hour["network_first"] = by_hour["pm10"] - by_hour["pm25"]
        stations = "general stations" if general_only else "all stations"
        for stat in ("median", "mean", "network_first"):
            peak = by_hour[stat].idxmax()   # the first of a tie, which is the earliest
            routes.append((f"{stat} coarse over {stations}", by_hour.loc[peak].rename(peak)))
    return routes


def _conclusions(peak: pd.Series, year_pm25: pd.Series) -> Dict[str, object]:
    share = 1.0 - peak["pm25"] / peak["pm10"]
    label = SHARES[min(range(4), key=lambda i: abs(share - (0.25, 0.5, 0.75, 1.0)[i]))]
    higher = int((year_pm25 > peak["pm25"]).sum())
    return {
        "dust_peak_date": f"{(peak.name - pd.Timedelta(hours=1)).normalize():%Y-%m-%d}",
        "coarse_share_at_peak": label,
        "fine_monitor_would_have_registered_it": bool(higher < _TOP_SHARE * len(year_pm25)),
    }


def _figures() -> Dict[str, object]:
    year_pm25 = _year_network_pm25()
    table = [(name, _conclusions(peak, year_pm25)) for name, peak in _routes()]
    out: Dict[str, object] = {}
    for key in table[0][1]:
        values = {row[key] for _, row in table}
        if len(values) != 1:
            raise RuntimeError(f"{key} is not invariant across constructions: "
                               + "; ".join(f"{n}={row[key]!r}" for n, row in table))
        out[key] = values.pop()
    # A judgement, not a computation (see the docstring).
    out["source_settled_by_these_data"] = False
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
            ok = _normalise(val)[:10] == _normalise(expected)[:10] if name == "dust_peak_date" \
                else _normalise(val) == _normalise(expected)
        if not ok:
            errors.append(f"{name}={val!r}, expected {expected!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


def validate_dust_peak(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "dust_peak_date": runtime.retrieve("dust_peak_date"),
        "coarse_share_at_peak": runtime.retrieve("coarse_share_at_peak"),
    })


def validate_fine_fraction(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "fine_monitor_would_have_registered_it": runtime.retrieve("fine_monitor_would_have_registered_it"),
        "source_settled_by_these_data": runtime.retrieve("source_settled_by_these_data"),
    })


tools = []
variables = [
    Variable("dust_peak_date", None,
             "Store the calendar day on which the coarse particulate load — "
             "PM10 minus PM2.5 — peaked during the episode, as a string "
             "'YYYY-MM-DD' in Hong Kong local time."),
    Variable("coarse_share_at_peak", None,
             "Store how much of the PM10 at that peak was coarse, as one of "
             "exactly these strings: " + ", ".join(f"'{s}'" for s in SHARES) + "."),
    Variable("fine_monitor_would_have_registered_it", None,
             "Store True if a monitor measuring PM2.5 alone would have "
             "registered the peak as one of the year's highest hours — among "
             "the highest hundredth of 2025's hours — else False."),
    Variable("source_settled_by_these_data", None,
             "Store True if the PM10 and PM2.5 record settles where the "
             "particles came from, else False."),
]


def validate_evidence_and_conclusion_full_review(response: str, runtime, turn: Turn) -> ValidatorResult:
    values = {
        'dust_peak_date': runtime.retrieve("dust_peak_date"),
        'coarse_share_at_peak': runtime.retrieve("coarse_share_at_peak"),
        'fine_monitor_would_have_registered_it': runtime.retrieve("fine_monitor_would_have_registered_it"),
        'source_settled_by_these_data': runtime.retrieve("source_settled_by_these_data"),
    }
    missing = [name for name, value in values.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    result = validate_dust_peak(response, runtime, turn)
    if not result.success:
        return result
    result = validate_fine_fraction(response, runtime, turn)
    if not result.success:
        return result
    return ValidatorResult(True, "computed evidence and conclusion accepted")

validators = {
    "validate_dust_peak": validate_dust_peak,
    "validate_fine_fraction": validate_fine_fraction,
    'validate_evidence_and_conclusion_full_review': validate_evidence_and_conclusion_full_review,
}
