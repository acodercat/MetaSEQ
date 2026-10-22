"""Hong Kong's worst ozone days and its worst PM2.5 days come with opposite
weather, and in 2025 the ozone days were not in autumn (cross_domain_analysis).

BASELINE, hard, rebuilt 2026-09-01 on the surface rule
(`docs/query_surface_audit.md`). The episode days are now defined by the
Air Quality Objectives themselves — a day on which any station exceeded the
8-hour ozone objective (160 ug/m3) or the 24-hour PM2.5 objective (50) — so
the sets need no invented threshold and no chosen N, and the query can name
them as a desk would. PV scores the season each set falls in and the weather
verdicts that every construction reaches; the claims carry the mechanisms.

**The sets, 2025, station-level exceedance days of the two objectives:**

    set                        days   winter  spring  summer  autumn
    ozone, any station > 160     36     10      17       5       4
    PM2.5, any station > 50       9      6       3       0       0
    days in both                  4

    daily means            pressure   RH    temperature  visibility  radiation
    ozone exceedance days    1014.5   66.5     23.4        33.9 km   20.2 MJ/m2
    PM2.5 exceedance days    1017.0   60.8     20.6        14.4      16.5
    all 365 days             1012.9   73.1     24.4        39.3      14.9

**Two mechanisms, and the record carries evidence for each.** Ozone is made
in the air, by sunlight on NOx and VOC over a few hours: the ozone days take
20 MJ/m2 of global solar radiation against the year's 15, the sunniest days
of the year, with visibility near normal. They fall in spring, before the
south-west monsoon brings clean marine air. PM2.5 on an exceedance day is
mostly imported: the winter north-east monsoon brings a cool, dry
continental airmass under a surge of high pressure — 4 hPa above the annual
mean, 4 degrees below it, 12 points of humidity below it — and the haze it
carries cuts visibility to a third of normal. The three spring PM days are
the other regime, the April 2025 coarse-dust intrusion
(`hk_april_2025_coarse_dust_signature`). So "pollution days cluster in the
winter monsoon" is true of PM2.5 and false of ozone.

**The autumn that did not come.** Hong Kong's ozone climatology peaks in
September to November; 2024 had eleven of its thirty territory days above
120 ug/m3 in those months against twelve in March to May. In 2025 four of
the 36 station-level exceedance days fell in autumn against seventeen in
spring, and the territory MDA8 monthly means were 54 in September and 70 in
October against 99 in January and 83 in April. A response that reports the
record's spring maximum and notes the departure is right; one that "corrects"
the record to autumn because that is where ozone episodes belong is the
failure the first claim catches.

**What survives every route.** `_routes()` recomputes the scored conclusions
under four constructions — the AQO sets as defined, and ranked composites of
the territory series with N = 10, 20 and 30 worst ozone days against 10, 10
and 15 worst PM2.5 days — and refuses to score if any scored conclusion
differs. (This paragraph said six until Gate B round 21 counted them: the two
territory-series sets AT THE OBJECTIVES yield 1 and 2 days, far too few to
carry a seasonal verdict, and they are not in the table. The prose described
an intention; the code was right.)

    ozone days fall mainly in spring              every route
    PM2.5 days fall mainly in winter              every route with N >= 9;
                                                  the 5 worst PM days alone are
                                                  3 April dust days, which is
                                                  why a set that small is not
                                                  among the defensible routes
    ozone days sunnier than the average day       20 to 22 MJ/m2 against 15
    PM2.5 days drier than the average day         54 to 63 % against 73
    PM2.5 days under higher pressure              1015 to 1019 against 1013
    the line holds for PM2.5, not for ozone       every route

    NOT scored: the counts (they are the definition), the weather means (they
    move with the set), the overlap.

**Measured and NOT used.** The northerly-quadrant wind share at Waglan Island
(80 % on ozone days against 84 % on PM days) and ERA5's boundary-layer height
(420 m against 409 m) do not separate the two sets; both are stagnant. What
separates them is sunlight and airmass.

**What the earlier versions scored, and why they are gone.** First thresholds
of 120 and 38 ug/m3 that were nobody's (Gate B round 19), then a ranked
composite whose N was the author's, with the query naming the season windows
and the five weather variables. Both models reproduced every number; the
query had told them where to look.

**Overlap, stated.** `hk_sunshine_ozone_scale_reversal` is radiation against
ozone by month; `hk_airmass_origin_ozone` is ozone by 900 hPa wind origin;
`hk_april_2025_coarse_dust_signature` is the April dust;
`hk_ozone_aqo_day_boundary` and `hk_aqo_revision_allowance` apply the same
objectives to compliance counts. None sets the two pollutants' episode
meteorology side by side.

All ground truths are recomputed from the database and `radiation_df` at
validation time, under four constructions at once.


**Gate B round 21 (2026-09-03) narrowed the mechanism claim.** It required the
PM2.5 days' low visibility to be explained by "imported haze", and the record
does not apportion the burden: cool, dry, high-pressure days with poor
visibility are consistent with continental outflow, with local accumulation
under a stagnant winter boundary layer, or with both, and low visibility is an
effect of aerosol load rather than evidence of where the aerosol came from.
There is no chemical tracer and no trajectory in these data. The claim now asks
for the winter monsoon regime and requires transport and accumulation to be
offered as the candidate mechanisms rather than the first as a finding. The
same round found the route count in the paragraph above overstated; both are
corrected.
"""

from typing import Dict, List, Tuple

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult
from domains.hk.db import read_frame

_O3_AQO = 160.0
_PM_AQO = 50.0
_MIN_HOURS = 6
SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
           6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}


def _station_daily() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Per-station daily MDA8 ozone and daily mean PM2.5 for 2025 (hour-ending days)."""
    frame = read_frame(text("""
        select h.datetime, s.name_en as station, h.o3, h.pm2_5
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
    """))
    start = frame["datetime"] - pd.Timedelta(hours=1)
    ozone, pm = [], []
    for station, group in frame.groupby("station"):
        series = group.set_index("datetime")["o3"].asfreq("h")
        rolling = series.rolling(8, min_periods=_MIN_HOURS).mean()
        ending = pd.Series(rolling.values, index=rolling.index - pd.Timedelta(hours=1))
        mda8 = ending.groupby(ending.index.date).max()
        ozone.append(pd.Series(mda8.values, index=pd.DatetimeIndex(mda8.index), name=station))
        daily = group.dropna(subset=["pm2_5"]).groupby(start[group.index].dt.date)["pm2_5"].mean()
        pm.append(pd.Series(daily.values, index=pd.DatetimeIndex(daily.index), name=station))
    return pd.concat(ozone, axis=1), pd.concat(pm, axis=1)


def _territory_daily() -> Tuple[pd.Series, pd.Series]:
    territory = read_frame(text("""
        select datetime, avg(o3) as o3, avg(pm2_5) as pm25
        from hourly_station_air_quality
        where datetime > '2025-01-01' and datetime <= '2026-01-01'
        group by datetime order by datetime
    """)).set_index("datetime")
    rolling = territory["o3"].asfreq("h").rolling(8, min_periods=_MIN_HOURS).mean()
    ending = pd.Series(rolling.values, index=rolling.index - pd.Timedelta(hours=1))
    mda8 = ending.groupby(ending.index.date).max()
    hour_start = territory.index - pd.Timedelta(hours=1)
    pm = territory["pm25"].groupby(hour_start.date).mean()
    return (pd.Series(mda8.values, index=pd.DatetimeIndex(mda8.index)),
            pd.Series(pm.values, index=pd.DatetimeIndex(pm.index)))


def _weather_daily() -> pd.DataFrame:
    frame = read_frame(text("""
        select date(h.datetime - interval '1 hour') as day,
               avg(h.pressure) filter (where s.name_en = 'HK Observatory') as p,
               avg(h.humidity) filter (where s.name_en = 'HK Observatory') as rh,
               avg(h.temperature) filter (where s.name_en = 'HK Observatory') as t,
               avg(h.visibility) filter (where s.name_en = 'Chek Lap Kok') / 1000.0 as vis
        from hourly_station_weather h
        join weather_station s on s.id = h.station_id
        where s.name_en in ('HK Observatory', 'Chek Lap Kok')
          and h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
        group by 1
    """))
    frame["day"] = pd.to_datetime(frame["day"])
    radiation = pd.read_csv(DATA_DIR / "radiation_hko.csv",
                            parse_dates=["date"])[["date", "global_solar_radiation_mj_m2"]]
    radiation.columns = ["day", "rad"]
    return frame.merge(radiation, on="day").set_index("day")


def _routes() -> List[Tuple[str, pd.DatetimeIndex, pd.DatetimeIndex]]:
    """Four constructions of the two day sets: (name, ozone days, PM2.5 days)."""
    station_o3, station_pm = _station_daily()
    territory_o3, territory_pm = _territory_daily()
    routes = [("any station over the objectives",
               station_o3.index[(station_o3 > _O3_AQO).any(axis=1)],
               station_pm.index[(station_pm > _PM_AQO).any(axis=1)])]
    for n_o3, n_pm in ((10, 10), (20, 10), (30, 15)):
        routes.append((f"territory worst {n_o3} / {n_pm}",
                       territory_o3.sort_values(ascending=False).index[:n_o3],
                       territory_pm.sort_values(ascending=False).index[:n_pm]))
    return routes


def _conclusions(o3_days: pd.DatetimeIndex, pm_days: pd.DatetimeIndex,
                 wx: pd.DataFrame) -> Dict[str, object]:
    o3_season = pd.Series([SEASONS[m] for m in o3_days.month]).value_counts().idxmax()
    pm_season = pd.Series([SEASONS[m] for m in pm_days.month]).value_counts().idxmax()
    o3_wx, pm_wx = wx.loc[wx.index.isin(o3_days)], wx.loc[wx.index.isin(pm_days)]
    return {
        "ozone_exceedance_season": o3_season,
        "pm25_exceedance_season": pm_season,
        "line_true_of_pm25": pm_season == "winter",
        "line_true_of_ozone": o3_season == "winter",
        "ozone_days_sunnier_than_average": bool(o3_wx["rad"].mean() > wx["rad"].mean()),
        "pm25_days_drier_than_average": bool(pm_wx["rh"].mean() < wx["rh"].mean()),
        "pm25_days_under_higher_pressure": bool(pm_wx["p"].mean() > wx["p"].mean()),
    }


def _figures() -> Dict[str, object]:
    wx = _weather_daily()
    table = [(name, _conclusions(o3, pm, wx)) for name, o3, pm in _routes()]
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


def validate_episode_calendar(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "ozone_exceedance_season": runtime.retrieve("ozone_exceedance_season"),
        "pm25_exceedance_season": runtime.retrieve("pm25_exceedance_season"),
    })


def validate_episode_weather(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "line_true_of_pm25": runtime.retrieve("line_true_of_pm25"),
        "line_true_of_ozone": runtime.retrieve("line_true_of_ozone"),
        "ozone_days_sunnier_than_average": runtime.retrieve("ozone_days_sunnier_than_average"),
        "pm25_days_drier_than_average": runtime.retrieve("pm25_days_drier_than_average"),
        "pm25_days_under_higher_pressure": runtime.retrieve("pm25_days_under_higher_pressure"),
    })


_SEASON_NOTE = (
    "Seasons are the calendar quarters: winter is December, January and "
    "February; spring March to May; summer June to August; autumn September "
    "to November. "
)
tools = []
variables = [
    Variable("ozone_exceedance_season", None,
             "Store the season in which most of 2025's ozone exceedance days "
             "fell — days on which any station exceeded the 8-hour ozone "
             "objective of 160 ug/m3 on its daily maximum 8-hour mean — as one "
             "of exactly these strings: 'winter', 'spring', 'summer', 'autumn'. "
             + _SEASON_NOTE),
    Variable("pm25_exceedance_season", None,
             "Store the same for 2025's PM2.5 exceedance days — days on which "
             "any station's daily mean PM2.5 exceeded the 24-hour objective of "
             "50 ug/m3 — as one of the same four strings."),
    Variable("line_true_of_pm25", None,
             "Store True if the line 'Hong Kong's pollution days cluster in the "
             "winter monsoon' holds for PM2.5 in 2025, else False."),
    Variable("line_true_of_ozone", None,
             "Store True if that line holds for ozone in 2025, else False."),
    Variable("ozone_days_sunnier_than_average", None,
             "Store True if the ozone exceedance days received more daily global "
             "solar radiation on average than the 2025 average day, else False."),
    Variable("pm25_days_drier_than_average", None,
             "Store True if the PM2.5 exceedance days had lower daily mean "
             "relative humidity at the Observatory on average than the 2025 "
             "average day, else False."),
    Variable("pm25_days_under_higher_pressure", None,
             "Store True if the PM2.5 exceedance days had higher daily mean "
             "Observatory pressure on average than the 2025 average day, else False."),
]
validators = {
    "validate_episode_calendar": validate_episode_calendar,
    "validate_episode_weather": validate_episode_weather,
}
