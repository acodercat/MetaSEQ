"""The record's PM2.5 is the real-time feed, and it cannot adjudicate an
annual objective decided in the tenths (regulatory_standards).

BASELINE, hard. The April 2025 revision set the annual PM2.5 objective at
15 ug/m3. EPD's 2025 annual report (Table C3) gives Sham Shui Po an annual
mean of 15.0 — on the objective, compliant. This record gives 15.23:
non-compliant by two tenths. The gap is not a computation choice, and the
case is about knowing that.

**What reproduces and what does not.** The record's hourly means for 2025
reproduce the report's annual figures for the gases at every station to
within 1 ug/m3 — to the printed integer at seventeen of eighteen for NO2
(Sham Shui Po 42.54 against 43; Tai Po 28.48 against 29 is the exception)
and sixteen of eighteen for ozone (50.94 against 51) — with no sign to the
residue. For PM2.5 the record is HIGHER than the report
at all eighteen stations, by 0.03 (Tseung Kwan O) to 1.00 (Central), mean
0.27. No construction closes it: the mean of all hourly values, the mean of
daily means (with or without an 18-hour validity rule, on either reading of
the midnight stamp), the mean of twelve monthly means — every one of them
puts Sham Shui Po between 15.11 and 15.23, and every station above its
published figure.

    Sham Shui Po, 2025            record   report
    NO2, annual mean              42.54    43
    O3, annual mean               50.94    51
    PM2.5, mean of hours          15.23    15.0
    PM2.5, mean of daily means    15.21
    PM2.5, mean of monthly means  15.20

**Why.** `datasets/EXTERNAL_DATA_SOURCES.md` records where the
concentrations come from: hourly snapshots of EPD's real-time 24-hour feed,
kept by the data.gov.hk historical archive. That feed is provisional. The
annual report is built on validated data. That validation moves the
particulate figures down and leaves the gases where they were is an
inference from the eighteen-for-eighteen sign of the gap and the gas
agreement, not something the record states; the mechanism (calibration or
blank corrections applied on validation, an instrument change, a data
edit) is not in the record and the case does not ask for it. What the
record shows is that the gap is systematic, particulate-specific, and
beyond any averaging choice.

**What follows for the desk.** Sham Shui Po's compliance with the annual
objective is decided by two tenths, and the record is biased the wrong way
by more than that at most stations. The verdict is the report's. The
record's 15.23 is not wrong — it is the real-time value — but it is not
the number the objective is assessed on, and a response that reports Sham
Shui Po as non-compliant on its strength has mistaken its record for the
authority's.

**Turn 1** scores the record's annual PM2.5 at Sham Shui Po (15.23) —
computed the plain way, the mean of the hourly values — and, as a control
the desk will use in turn 2, its NO2 and ozone annual means (42.54, 50.94).
**Turn 2**, after the desk quotes the report's three figures, scores the
mean of daily means (15.21), the construction an analyst tries first to
close the gap, and the claims carry the reasoning: gases reproduce and PM
does not; no averaging closes it; the record is provisional; publish the
report's verdict and hold the record's.

**Pins, and where each one goes** (`case_design_standard.md` §3.1). The
three annual means are the plain hourly means over the calendar year, on
the domain's TIME WINDOWS convention; the daily-means construction is
defined on its variable (calendar days on the same convention, every day
with at least eighteen hourly values, then the mean of the daily means).
The identity of the two data products — the report from validated data,
this database an archive of the real-time feed — is stated in turn 2's
desk note since Gate B round 18: four Gate C runs before that had treated
the record as authoritative, because nothing an agent reads said
otherwise (the provenance note lived in `datasets/`), and a product
identity is a premise, not a method. What the case still tests is what
follows from it: which figures the record can reproduce, and which
verdict to print.

**Readings measured and excluded** (Sham Shui Po PM2.5 annual):

    mean of hours, hour-ending stamps      15.23 (same to two decimals)
    daily means, any number of hours       15.11
    daily means, hour-ending stamps        15.21 (same to two decimals)
    monthly means, then annual             15.20

Means use `reports_as` at two decimals; the daily-means figure at 15.21 is
separated from the any-hours reading (15.11) and from the monthly reading
(15.20) — the latter by 0.01, which is why the validity rule is pinned.

**Overlap, stated.** `hk_aqhi_not_reproducible` is about the published
index not being a function of the published components; this case is
about the published concentrations not being the record's. The ozone
cases on the 8-hour and peak-season objectives reproduce the report from
this record because ozone survives validation nearly unchanged — the
contrast is the point.

All ground truths are recomputed from the database at validation time. The
published figures appear only in the docstring and the desk's note.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, is_finite_number, reports_as
from domains.hk.db import read_frame

_STATION = "Sham Shui Po"
_MIN_HOURS_PER_DAY = 18


def _hourly() -> pd.DataFrame:
    return read_frame(text("""
        select h.datetime, h.pm2_5, h.no2, h.o3
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where s.name_en = :station
          and h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
    """), {"station": _STATION})


def _figures() -> Dict[str, float]:
    frame = _hourly()
    days = frame.dropna(subset=["pm2_5"]).groupby((frame["datetime"] - pd.Timedelta(hours=1)).dt.date)["pm2_5"].agg(["mean", "count"])
    valid = days[days["count"] >= _MIN_HOURS_PER_DAY]
    return {
        "ssp_pm25_annual_2025": float(frame["pm2_5"].mean()),
        "ssp_no2_annual_2025": float(frame["no2"].mean()),
        "ssp_o3_annual_2025": float(frame["o3"].mean()),
        "ssp_pm25_annual_of_daily_means_2025": float(valid["mean"].mean()),
    }


def validate_annual_means(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "ssp_pm25_annual_2025": runtime.retrieve("ssp_pm25_annual_2025"),
        "ssp_no2_annual_2025": runtime.retrieve("ssp_no2_annual_2025"),
        "ssp_o3_annual_2025": runtime.retrieve("ssp_o3_annual_2025"),
    }
    return _check_values(got)


def validate_daily_construction(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {"ssp_pm25_annual_of_daily_means_2025": runtime.retrieve("ssp_pm25_annual_of_daily_means_2025")}
    return _check_values(got)


def _check_values(got: Dict[str, object]) -> ValidatorResult:
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    for name, val in got.items():
        if not is_finite_number(val):
            errors.append(f"{name}={val!r} is not a number")
        elif not reports_as(val, gt[name], decimals=2):
            errors.append(f"{name}={val}, expected ~{gt[name]:.2f}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]:.2f}" for n in got))


tools = []
variables = [
    Variable(
        "ssp_pm25_annual_2025",
        None,
        "Store the Sham Shui Po station's 2025 annual mean PM2.5 — the mean "
        "of every hourly PM2.5 value belonging to 2025 on the domain's "
        "hour-ending convention — as a float in ug/m3, "
        "2 decimal places.",
    ),
    Variable(
        "ssp_no2_annual_2025",
        None,
        "Store the same station's 2025 annual mean NO2, built the same way, "
        "as a float in ug/m3, 2 decimal places.",
    ),
    Variable(
        "ssp_o3_annual_2025",
        None,
        "Store the same station's 2025 annual mean ozone, built the same "
        "way, as a float in ug/m3, 2 decimal places.",
    ),
    Variable(
        "ssp_pm25_annual_of_daily_means_2025",
        None,
        "Store the Sham Shui Po station's 2025 annual PM2.5 built as the "
        "mean of daily means: for each calendar day of 2025 with at least "
        "eighteen hourly PM2.5 values, the mean of those values; then the "
        "mean of those daily figures over the year, as a float in ug/m3, 2 "
        "decimal places.",
    ),
]
validators = {
    "validate_annual_means": validate_annual_means,
    "validate_daily_construction": validate_daily_construction,
}
