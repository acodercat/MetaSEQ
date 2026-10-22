"""Beijing 2024 — the sharpest clean-out and the wind that did it
(exceedance_anomaly_detection).

Clearance BASELINE, deliberately not a diagnostic trap. The corpus dissects how
episodes form (`box_model_flux`), how long they last (`dust_recovery`) and whom
they expose (`exceedance_exposure_bias`); nothing until now detects how they
END. Frontal passage over the North China Plain removes a week of accumulation
in a day, and the ventilation coefficient is where that shows up.

- cleanout_date: 2024-10-27. Daily mean PM2.5 fell from 161.36 to 9.30 ug/m3.
- cleanout_drop: -152.07 ug/m3, against a runner-up of -74.49 — a factor of
  2.04, so the date is unambiguous and needs no tie-break.
- the ventilation change, scored as a verdict since 2026-09-02: the daily
  coefficient rose 3.70-fold, from 142.84 to
  528.40 m2/s across the same day boundary: a shallow, still boundary layer
  replaced by a deep, windy one.

Pins, each measured.

- The YEAR, and this one prevents a collision rather than an ambiguity. Over
  the whole record the largest single-day drop is 2021-03-16 at -196.91 ug/m3,
  the decay of the March 2021 dust storm — which is already
  `beijing_dust_recovery`'s subject. An unpinned query would return that event
  and duplicate an existing case; 2024 selects a distinct frontal clearance.
- The VENTILATION BASIS: a day's coefficient is the mean over every station
  record's hourly values. Weighting the five distinct reanalysis series equally
  instead (see `beijing_era5_grid_pseudoreplication`) gives 172.09 to 515.95, a
  ratio of 3.00 — a different number, the same verdict, and one of the
  routes the rebuilt validator checks.
- The daily PM2.5 recipe, which here is insensitive: pooled station-hours
  selects the same date and the same drop to four decimals. Pinned anyway,
  insensitivity stated rather than relied on.
- The DAY. PM2.5 label h is the hour ending at h:00, so a day is labels 1-23
  and label 0 of the next date; the ventilation coefficient is an instant and
  keeps its stamped date. Grouping the PM2.5 calendar labels gives the same
  date but a drop of -149.82 (from 163.18 to 13.36), 2.25 away and well
  outside the band.

What the case may not conclude, and the claim enforces it: a ventilation jump
of this size is CONSISTENT with frontal clearance and is not proof that
ventilation did all the work. This record carries no precipitation, so wet
scavenging cannot be excluded, and reconciling a 150 ug/m3 loss with a
particular removal mechanism is a mass-balance question these three columns
underdetermine.

Tolerances: the date is matched exactly, and no near-miss can arise — the
runner-up drop is 78 ug/m3 smaller. The drop takes +/-0.01, covering
2-decimal reporting; the ratio took the same band until 2026-09-02. The
variable states the sign (the day's mean minus the previous day's), so the
magnitude +152.07 is rejected.

Ground truth is recomputed here from the CSVs.

**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier query told the agent to compute the ventilation ratio; the
rebuilt one asks for the day the air cleared most sharply and an account of
it. The date and the drop stay (the drop is the domain's daily figure, and
pooling reads the same to four decimals); the ratio is replaced by a verdict
on the dispersion change that holds under every construction of the day's
coefficient (3.70 by record, 3.00 by distinct series, 3.15 as mean height
times mean wind — all "more than doubled"). The ventilation coefficient is a
named column of the schema and the variable asks for its change, so reaching
for it is not what the case discriminates on; reading the CHANGE across the
boundary is, and the claim still requires the response to stop short of
crediting ventilation as the whole cause.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_YEAR = 2024
DISPERSION_ROSE = "rose sharply"
DISPERSION_FLAT = "little change"
DISPERSION_FELL = "fell"


def _cleanout() -> dict:
    bj = DATA_DIR
    aq = pd.read_csv(bj / "air_quality.csv")
    met = pd.read_csv(bj / "met_era5.csv")
    # Air-quality label h is the hour ending at h:00, so its day is the label
    # shifted back an hour; ERA5 values are instants and keep their own date.
    aq["ts"] = pd.to_datetime(aq[["year", "month", "day", "hour"]])
    aq["date"] = (aq["ts"] - pd.Timedelta(hours=1)).dt.normalize()
    met["date"] = pd.to_datetime(met[["year", "month", "day"]])

    obs = aq.dropna(subset=["PM2.5"])
    daily = obs.groupby(["date", "ts"])["PM2.5"].mean().groupby(level=0).mean()
    change = (daily - daily.shift(1)).sort_index()
    year = change[change.index.year == _YEAR]
    date = year.idxmin()

    previous = date - pd.Timedelta(days=1)
    # The ventilation change under three constructions of a day's coefficient:
    # the mean over every station record's hours (3.70), the five distinct
    # reanalysis series weighted equally (3.00), the day's mean height times
    # its mean wind (3.15). Every one more than doubles.
    by_record = met.groupby("date")["ventilation_m2s"].mean()
    by_series = met.drop_duplicates(["date", "hour", "ventilation_m2s"]).groupby("date")["ventilation_m2s"].mean()
    product = met.groupby("date")["blh_m"].mean() * met.groupby("date")["wind_speed_ms"].mean()
    ratios = {"by record": by_record[date] / by_record[previous],
              "by distinct series": by_series[date] / by_series[previous],
              "mean height times mean wind": product[date] / product[previous]}
    verdicts = {DISPERSION_ROSE if r > 2.0 else DISPERSION_FELL if r < 0.5 else DISPERSION_FLAT
                for r in ratios.values()}
    if len(verdicts) != 1:
        raise RuntimeError(f"the dispersion verdict is not invariant: {ratios}")
    return {
        "date": date,
        "drop": float(year.min()),
        "dispersion": verdicts.pop(),
    }


def validate_cleanout(response: str, runtime, turn: Turn) -> ValidatorResult:
    raw_date = runtime.retrieve("cleanout_date")
    drop = runtime.retrieve("cleanout_drop")
    dispersion = runtime.retrieve("dispersion_change")
    missing = [n for n, v in (("cleanout_date", raw_date), ("cleanout_drop", drop),
                              ("dispersion_change", dispersion)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    parsed = pd.to_datetime(raw_date, errors="coerce")
    if pd.isna(parsed):
        return ValidatorResult(False, f"cleanout_date={raw_date!r} is not a date")
    if not is_finite_number(drop):
        return ValidatorResult(False, f"cleanout_drop={drop!r} is not a number")
    gt = _cleanout()
    errors = []
    if parsed.date() != gt["date"].date():
        errors.append(f"cleanout_date={parsed.date()}, expected {gt['date'].date()}")
    if not reports_as(drop, gt["drop"], decimals=2):
        errors.append(f"cleanout_drop={drop}, expected ~{gt['drop']:.2f} ug/m3")
    if str(dispersion).strip().lower() != gt["dispersion"]:
        errors.append(f"dispersion_change={dispersion!r}, expected {gt['dispersion']!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True, f"correct: {gt['date'].date()}, drop {gt['drop']:.2f} ug/m3, dispersion {gt['dispersion']}")


tools = []
variables = [
    Variable(
        "cleanout_date",
        None,
        "Store the date as a yyyy-mm-dd string.",
    ),
    Variable(
        "cleanout_drop",
        None,
        "Store the change in daily mean PM2.5, the day's mean minus the "
        "previous day's (negative = a fall), as a float in ug/m3, 2 decimal "
        "places.",
    ),
    Variable(
        "dispersion_change",
        None,
        "Store how the day's dispersion capacity — the ventilation "
        "coefficient, boundary-layer height times wind speed — compared with "
        "the previous day's, as one of exactly these strings: 'rose sharply' "
        "(more than doubled), 'little change', 'fell'.",
    ),
]
validators = {"validate_cleanout": validate_cleanout}
