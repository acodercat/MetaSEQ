"""Beijing 2020 lockdown — the primary tracer fell and PM2.5 rose
(comparative_assessment).

Natural-experiment BASELINE, classified per the `fire_detection_bias`
precedent: both computations are plain, pinned and unique, so §4's trap
contract does not apply — the diagnostic value lives in the CC channel, where
the naive EXPECTATION is that shutting down a city cleans its air.

- no2_lockdown_change_pct: -36.60 %. NO2, the traffic tracer, fell from 42.44
  to 26.91 ug/m3 between the pre-lockdown window (2020-01-01 to 01-22) and the
  lockdown window (2020-01-25 to 02-29).
- pm25_lockdown_change_pct: +76.80 %. PM2.5 rose from 40.82 to 72.17 over the
  same two windows, with daily means reaching 184.2, 209.4 and 201.1 ug/m3 on
  February 11-13, in line with the published record of this event (the
  literature reports 181-208 ug/m3 for those days; grouping by label date
  reproduces its 181.8, 208.3 and 203.8 to the digit, so those sources read
  hour 0 as the first hour of its date).

The windows are the domain's air-quality days: 1 January 2020 starts after
label 00:00, and 29 February ends with label 00:00 of 1 March. Taking each
date's labels 0-23 instead reads -36.63/+77.39, outside the band on both.

This is the documented COVID air-quality paradox: emissions of NOx fell by
roughly half across the region, yet severe haze formed anyway. The published
explanations — enhanced secondary formation under unchanged oxidant levels,
and stagnant, humid meteorology — are what this record cannot SETTLE: the
corpus holds no observed surface aerosol composition and no humidity. Stated
that precisely because Gate B corrected a looser draft: the runtime does carry
CAMS column-integrated aerosol composition, but a modelled column speciation
over an 80 km cell is not the surface measurement these hypotheses need, and
the corpus's own CAMS manifest forbids treating it as one. The claims
therefore require the sign contrast to be computed and stated, and the
explanation bounded as a literature hypothesis rather than asserted.

Two confounds are stated rather than hidden. The lockdown began at Chinese New
Year, so part of any January-February NO2 drop is the holiday itself — the
case reports the contrast between the two windows, never a lockdown-only
attribution. And the windows are a convention: extending the lockdown window
to March 31 dilutes the PM2.5 rise to +34.0 % as the episodes end, which is
why both windows are pinned to the day in the query and the diluted reading
is a probe.

Tolerances: +/-0.01 percentage points on each change, covering 2-decimal
reporting. The basis is pinned on the variables (hourly network means, then
the period mean, hours weighted equally) because the domain prompt's DAILY
FIGURES convention speaks of days and a window is not a day: the
daily-then-period reading is -36.68/+75.91 and the pooled reading
-36.16/+78.24, both outside the band on both sides.

Both ground truths are recomputed here from the CSV.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_PRE = ("2020-01-01", "2020-01-22")
_LOCK = ("2020-01-25", "2020-02-29")


def _period_mean(df: pd.DataFrame, pollutant: str, span: tuple) -> float:
    sel = df[(df["date"] >= span[0]) & (df["date"] <= span[1])]
    sel = sel.dropna(subset=[pollutant])
    return float(sel.groupby(["date", "hour"])[pollutant].mean().mean())


def _changes() -> dict:
    aq = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Hour h ends at h:00, so label 0 belongs to the previous date.
    stamps = pd.to_datetime(aq[["year", "month", "day", "hour"]])
    aq["date"] = (stamps - pd.Timedelta(hours=1)).dt.normalize()
    out = {}
    for pollutant, key in (("NO2", "no2"), ("PM2.5", "pm25")):
        pre = _period_mean(aq, pollutant, _PRE)
        lock = _period_mean(aq, pollutant, _LOCK)
        out[key] = 100.0 * (lock / pre - 1.0)
    return out


def validate_lockdown_changes(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {}
    for name in ("no2_lockdown_change_pct", "pm25_lockdown_change_pct"):
        val = runtime.retrieve(name)
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")
        got[name] = val

    gt = _changes()
    errors = []
    if not reports_as(got["no2_lockdown_change_pct"], gt["no2"], decimals=2):
        errors.append(
            f"no2_lockdown_change_pct={got['no2_lockdown_change_pct']}, "
            f"expected ~{gt['no2']:+.2f} %"
        )
    if not reports_as(got["pm25_lockdown_change_pct"], gt["pm25"], decimals=2):
        errors.append(
            f"pm25_lockdown_change_pct={got['pm25_lockdown_change_pct']}, "
            f"expected ~{gt['pm25']:+.2f} %"
        )
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True, f"correct: NO2 {gt['no2']:+.2f} %, PM2.5 {gt['pm25']:+.2f} %"
    )


tools = []
variables = [
    Variable(
        "no2_lockdown_change_pct",
        None,
        "Store the NO2 change as a signed float percentage, 2 decimal places "
        "(e.g. -12.34 for a 12.34 % fall). Take each window's mean over its "
        "hourly network means directly — every hour weighted equally, not "
        "built from daily values first: the windows' days carry unequal hour "
        "counts, so the two weightings differ.",
    ),
    Variable(
        "pm25_lockdown_change_pct",
        None,
        "Store the PM2.5 change as a signed float percentage, 2 decimal "
        "places, on the same hour-weighted window means.",
    ),
]
validators = {"validate_lockdown_changes": validate_lockdown_changes}
