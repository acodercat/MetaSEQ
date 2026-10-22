"""Beijing dust event — the column product would not have found the worst
surface day (cross_domain_analysis).

TRAP, rebuilt 2026-09-02 on the surface rule (`docs/query_surface_audit.md`).
The runtime offers a CAMS variable literally named `dust_aod550`
(aerosol_df), which is tempting for a "most severe dust event" question. But
AOD is a **column-integrated** optical depth: dust frequently travels in
elevated layers that never reach the ground, so the column maximum is a
different day from the surface maximum.

- correct path: the most severe *surface* dust day is the day with the
  greatest ground-level coarse loading (PM10 minus PM2.5) across the station
  network. That is 2021-03-15, the great March-2021 Mongolian dust storm.
- wrong path: taking the day of maximum `dust_aod550` lands on 2025-05-05,
  an elevated dust layer whose surface coarse loading ranks 1,068th to
  1,318th of 2,192 days, depending on the construction.

**THE DATE ALONE WAS RECALLABLE, AND A NO-DATA CONTROL PROVED IT.** Asked
this case's query with the runtime taken away, `deepseek-v4-flash` and
`deepseek-v4-pro-0813` BOTH answered 2021-03-15 (2026-08-26,
`scratchpad/no_data_control.py`). The March 2021 storm is the best-known
dust event of the decade; a case resting on its date was scoring memory.

**What is scored now.** The date, and two verdicts that cannot be recalled
and that `_figures()` asserts invariant across every construction of the
two rankings — the column product's daily figure as the mean or the maximum
of its 3-hourly values; the surface coarse loading as the difference of the
network means, the mean of the per-row differences, the two-step daily
construction, or PM10 alone:

    the surface peak day among the column product's ten highest   False
        (it ranks 152nd by daily-mean AOD and 55th by daily-max AOD)
    the column peak day among the surface's ten highest            False
        (it ranks 1,068th to 1,318th by surface loading)

The earlier version scored the two ranks exactly (1,271 and 152), which
forced the variables to spell out the difference-of-means construction after
Gate C found a model computing the per-row form (1,279). A rank is a
construction; whether a day is in a top ten is not, here — the nearest any
construction brings either day to a top ten is 55th. Those two ranks were taken
on days read as the labels 0-23; on the hour-ending station day the surface
ranks are 1,068th to 1,318th, and neither verdict nor the date moves.

**The professional consequence.** A colleague proposing the reanalysis
product as a way to find surface dust days in future would have missed the
decade's worst one: the column product does not put it in its top ten under
either daily figure, and the day the column product ranks first was an
ordinary day at the ground. The claim carries the physics — an optical
depth integrates the whole column, so a plume in transit overhead scores
high while contributing little at breathing height.

Ground truth is recomputed from the CSVs at validation time, under eight
constructions at once.
"""

from typing import Dict, List, Tuple

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult

_BJ = DATA_DIR
_START, _END = "2020-01-01", "2025-12-31"
_TOP = 10


def _surface_routes() -> List[Tuple[str, pd.Series]]:
    df = pd.read_csv(_BJ / "air_quality.csv")
    # Hour h is the hour ENDING at h:00: a station day is its hours 1-23 and
    # hour 0 of the next date. The CAMS instants below keep their own dates.
    df["stamp"] = pd.to_datetime(df[["year", "month", "day", "hour"]])
    df["date"] = (df["stamp"] - pd.Timedelta(hours=1)).dt.normalize()
    df = df[(df["date"] >= _START) & (df["date"] <= _END)]
    daily = df.groupby("date").agg(PM10=("PM10", "mean"), PM25=("PM2.5", "mean"))
    hourly = df.groupby(["date", "stamp"]).agg(PM10=("PM10", "mean"), PM25=("PM2.5", "mean"))
    two_step = hourly.groupby(level=0).mean()
    return [
        ("difference of the network means", daily["PM10"] - daily["PM25"]),
        ("mean of the per-row differences", (df["PM10"] - df["PM2.5"]).groupby(df["date"]).mean()),
        ("two-step daily construction", two_step["PM10"] - two_step["PM25"]),
        ("PM10 alone", daily["PM10"]),
    ]


def _column_routes() -> List[Tuple[str, pd.Series]]:
    aer = pd.read_csv(_BJ / "aerosol_cams.csv")
    aer["date"] = pd.to_datetime(aer[["year", "month", "day"]])
    aer = aer[(aer["date"] >= _START) & (aer["date"] <= _END)]
    return [("daily mean dust AOD", aer.groupby("date")["dust_aod550"].mean()),
            ("daily maximum dust AOD", aer.groupby("date")["dust_aod550"].max())]


def _figures() -> Dict[str, object]:
    surface, column = _surface_routes(), _column_routes()
    dates = {s.idxmax() for _, s in surface}
    if len(dates) != 1:
        raise RuntimeError(f"the surface peak day is not invariant: {dates}")
    surface_peak = dates.pop()
    table = []
    for s_name, s in surface:
        s_rank = s.rank(ascending=False, method="min")
        for c_name, c in column:
            c_rank = c.rank(ascending=False, method="min")
            table.append((f"{s_name} / {c_name}", {
                "surface_peak_in_column_top_ten": bool(c_rank.loc[surface_peak] <= _TOP),
                "column_peak_in_surface_top_ten": bool(s_rank.loc[c.idxmax()] <= _TOP),
            }))
    out: Dict[str, object] = {"dust_event_date": f"{surface_peak:%Y-%m-%d}"}
    for key in table[0][1]:
        values = {row[key] for _, row in table}
        if len(values) != 1:
            raise RuntimeError(f"{key} is not invariant across constructions: "
                               + "; ".join(f"{n}={row[key]}" for n, row in table))
        out[key] = values.pop()
    return out


def validate_dust_event_date(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "dust_event_date": runtime.retrieve("dust_event_date"),
        "surface_peak_in_column_top_ten": runtime.retrieve("surface_peak_in_column_top_ten"),
        "column_peak_in_surface_top_ten": runtime.retrieve("column_peak_in_surface_top_ten"),
    }
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    parsed = pd.to_datetime(got["dust_event_date"], errors="coerce")
    if pd.isna(parsed):
        return ValidatorResult(False, f"dust_event_date={got['dust_event_date']!r} is not a date")
    gt = _figures()
    errors = []
    if f"{parsed:%Y-%m-%d}" != gt["dust_event_date"]:
        errors.append(f"dust_event_date={parsed.date()}, expected {gt['dust_event_date']}")
    for name in ["surface_peak_in_column_top_ten", "column_peak_in_surface_top_ten"]:
        val, expected = got[name], gt[name]
        ok = (isinstance(val, bool) and val == expected) or (
            isinstance(val, str) and val.strip().lower() in
            {str(expected).lower(), "yes" if expected else "no"})
        if not ok:
            errors.append(f"{name}={val!r}, expected {expected}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: {gt['dust_event_date']}; neither product's peak "
                                 "day is in the other's top ten")


tools = []
variables = [
    Variable("dust_event_date", None,
             "Store the date of the most severe ground-level dust episode over "
             "2020-2025 as a YYYY-MM-DD string."),
    Variable("surface_peak_in_column_top_ten", None,
             "Store True if that day is among the ten days of 2020-2025 on "
             "which the reanalysis product's dust optical depth over Beijing was "
             "highest, else False."),
    Variable("column_peak_in_surface_top_ten", None,
             "Store True if the day on which that product's dust optical depth "
             "was highest is among the ten days of greatest ground-level coarse "
             "particulate loading across the station network, else False."),
]
validators = {"validate_dust_event_date": validate_dust_event_date}
