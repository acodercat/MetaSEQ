"""Beijing 2023 annual PM2.5 — station screen versus network figure
(regulatory_standards).

Screening BASELINE, deliberately not a diagnostic trap. Both turns are stated
operations; the case exists because the two answers disagree about the same year.

- Turn 1 (stations_at_or_below_limit): 3 of the twelve stations have a 2023
  annual mean at or below the GB 3095-2012 Grade II limit of 35 ug/m3 —
  Dingling 30.20, Huairou 31.29, Changping 32.16.
- Turn 2 (network_annual_mean_pm25): pooling every station's hourly values gives
  35.51 ug/m3, which is ABOVE the same limit.

The contrast is the content. Three sites clear the annual limit while the
network as a whole does not, so "did Beijing meet the annual standard in 2023"
has no answer until someone says whether the question is per-station or
network-wide.

The site class does not cleanly predict the outcome, which is worth stating
because it is the obvious shortcut. All eight urban sites fail, but so does
Shunyi, a suburban assessment site, at 35.37 — and the urban site immediately
above it, Wanliu, is only 0.05 higher at 35.42. Three of the four suburban and
background sites pass; the fourth does not, and the pass/fail line does not sit
on the urban/suburban boundary.

Called a threshold SCREEN, never an attainment determination, and completeness
is one of the things separating the two — an earlier version of this paragraph
claimed the opposite and Gate B corrected it. All twelve stations clear the
annual >=324-valid-day floor, but HJ 663's monthly floors fail at exactly two of
the three stations this screen passes: Changping reports 23 valid days in both
September and November against a floor of 27, and Dingling 20 in January and 18
in February against 27 and 25. A completeness-qualified screen would therefore
pass only Huairou — 1 of 12, not 3. The query pins "over every hour it reports"
precisely so that 3 is the unique answer to the question actually asked; 1 is
the qualified reading's permanent probe. A formal determination additionally
runs on the designated evaluation network with post-hoc audit, which this
twelve-station mirror is not. The query says "screen" for all of these reasons.

On recall versus computation. Beijing publishes a city-wide annual PM2.5 from
the full designated network, which is larger than this twelve-station mirror and
weighted differently, so the published figure is not 35.51 and an agent that
reproduces it from memory has not answered this question. The exact published
value is deliberately NOT quoted here: it cannot be verified from anything in
this repository, and an unsourced number in a case file is the kind of thing a
reviewer should not have to take on trust. What matters is enforced by the band
rather than by the prose — `scripts/verdict_baseline.json` probes 32, a
plausible recalled value, and the 0.05 tolerance rejects it. A neighbouring case
in this corpus once carried a band wide enough to accept a published headline
instead of the computed answer; that is the failure this narrow band prevents.

Tolerances, both measured.

- Turn 1 takes 0. The three-station set is identical under all three averaging
  bases — hourly arithmetic, daily-then-annual, and daily-with-at-least-20-hours
  — and the 35 line falls inside a 3.21 ug/m3 gap between Changping at 32.16 and
  Shunyi at 35.37, so no convention moves the count.
- Turn 2 takes +/-0.01. Four aggregation conventions span 0.1543 (pooled
  35.5089, station-then-mean 35.4845, daily-then-annual 35.4322,
  daily network means over days with 20 hours 35.3546) and the variable pins pooling, so the band has to
  reject the other three rather than average over them. An earlier +/-0.05
  accepted station-then-mean at 0.0244 away — a value this docstring itself
  listed as excluded, checked against the daily-then-annual reading and never
  against the nearer one. Gate B invoked the validator with 35.4837 and it
  returned success. 2-decimal reporting needs 0.005; 0.01 leaves margin without
  reaching 35.4845.

  One reading survives that the query does not ask for: equal-weighting eligible
  station-days gives 35.5001, 0.0088 from the pooled answer. It reports as 35.50
  against 35.51, so a band of 0.005 could separate the two, but only by a
  thousandth of a unit at the edge of rounding; on the label-date day the same
  reading sat 0.0023 away and reported identically, and a pin whose separation
  depends on which side of midnight one hour falls is not one to build on.

Both ground truths are recomputed here from the CSV.

**Turn 2 rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`):
the query asks the desk's question — can the year be described with one
figure? — and scores the pooled figure (its construction on the variable),
whether it is above the limit (True under all four constructions the code
checks: pooled 35.51, station means averaged 35.48, daily-then-annual
35.43, daily means over days with at least 20 hourly figures 35.35). A third variable, "does one figure suffice", was dropped
after the first Gate C run: flash answered "a valid shorthand, but it masks
a spatial pattern in which the violation is widespread" — the claim's own
content — and stored True. Whether that is "suffices" is wording, not
analysis, so the claim carries it and no variable does.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_YEAR = 2023
_ANNUAL_LIMIT = 35.0


def _annual() -> dict:
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Hour h is the hour ending at h:00, so 2023 runs from the 01:00 label of
    # 1 January to the 00:00 label of 1 January 2024.
    date = (pd.to_datetime(df[["year", "month", "day", "hour"]])
            - pd.Timedelta(hours=1)).dt.normalize()
    df["date"] = date
    year = df[date.dt.year == _YEAR]
    per_station = year.groupby("station")["PM2.5"].mean()
    network = float(year["PM2.5"].mean())
    # Four defensible constructions of the citywide figure (pooled, station
    # means averaged, daily-then-annual, daily with a 20-hour floor) read 35.43
    # to 35.51: all above the limit, so the verdict is asserted on all four.
    hourly = year.groupby(["date", "hour"])["PM2.5"].mean()
    daily = hourly.groupby(level=0).mean()
    hours_per_day = hourly.groupby(level=0).size()
    readings = [network, float(per_station.mean()), float(daily.mean()),
                float(daily[hours_per_day >= 20].mean())]
    verdicts = {r > _ANNUAL_LIMIT for r in readings}
    if len(verdicts) != 1:
        raise RuntimeError(f"the network verdict is not invariant: {readings}")
    return {
        "n_at_or_below": int((per_station <= _ANNUAL_LIMIT).sum()),
        "network_mean": network,
        "network_above_limit": verdicts.pop(),
    }


def validate_station_screen(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("stations_at_or_below_limit")
    if val is None:
        return ValidatorResult(
            False, "stations_at_or_below_limit not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"stations_at_or_below_limit={val!r} is not a number"
        )

    gt = _annual()
    if compare_numeric(val, gt["n_at_or_below"], tolerance=0):
        return ValidatorResult(True, f"correct: {val} stations at or below the limit")
    return ValidatorResult(
        False,
        f"stations_at_or_below_limit={val}, expected {gt['n_at_or_below']}",
    )


def validate_network_mean(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("network_annual_mean_pm25")
    above = runtime.retrieve("network_above_limit")
    missing = [n for n, v in (("network_annual_mean_pm25", val), ("network_above_limit", above)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    if not is_finite_number(val):
        return ValidatorResult(False, f"network_annual_mean_pm25={val!r} is not a number")
    gt = _annual()
    wrong = []
    if not reports_as(val, gt["network_mean"], decimals=2):
        wrong.append(f"network_annual_mean_pm25={val}, expected ~{gt['network_mean']:.2f} ug/m3")
    for name, got in (("network_above_limit", above),):
        expected = gt[name]
        ok = (isinstance(got, bool) and got == expected) or (
            isinstance(got, str) and got.strip().lower() in
            {str(expected).lower(), "yes" if expected else "no"})
        if not ok:
            wrong.append(f"{name}={got!r}, expected {expected}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(True, f"correct: {val} ~ {gt['network_mean']:.2f} ug/m3, above the limit")


tools = []
variables = [
    Variable(
        "stations_at_or_below_limit",
        None,
        "Store how many monitoring stations had a 2023 annual mean PM2.5 at or "
        "below the limit, as an integer.",
    ),
    Variable(
        "network_annual_mean_pm25",
        None,
        "Store the 2023 annual mean PM2.5 over all stations' hourly values pooled "
        "together, as a float in ug/m3, 2 decimal places.",
    ),
    Variable(
        "network_above_limit",
        None,
        "Store True if the citywide 2023 figure is above the Grade II annual "
        "limit, else False.",
    ),
]
validators = {
    "validate_station_screen": validate_station_screen,
    "validate_network_mean": validate_network_mean,
}
