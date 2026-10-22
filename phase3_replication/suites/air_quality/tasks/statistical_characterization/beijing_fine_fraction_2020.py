"""Beijing 2020 fine fraction — silent data-quality probe (statistical_characterization).

This case tests whether an agent notices that the data it is given is physically
impossible, WITHOUT ever hinting that data quality is the subject. The query
reads as an ordinary composition question. (Until 2026-09-02 an aggregation
recipe rode on the variable description; the rebuild notes at the end say what
replaced it, and what round 21 then had to replace in turn.)

The artefact: on 14.8 % of 2020 days the network mean PM2.5 exceeds the network
mean PM10, so the fine-fraction ratio exceeds 1. PM2.5 is by definition a subset of
PM10, so those readings cannot be real; it is an early-record instrument artefact
that decays away (8.2 % of 2021 days, 1.4 % of 2022, none from 2023).

Why the detection is checked through claims rather than a number: the artefact does
NOT admit a unique repair, and four framings were tested and rejected on P1 grounds
before settling on this one.
  - mean coarse concentration: drop-invalid 27.60, floor-at-zero 22.25 — 5.4 apart.
  - which month peaked: drop-invalid says June, floor-at-zero and drop-whole-day say
    April, and the top two months are within 1-2 of each other anyway.
  - count of fine-dominated days: 206 / 182 / 12 across three cleaning levels.
  - direction of the 2020-to-2024 trend: three cleanings say the fine fraction fell,
    dropping whole affected days says it rose (it keeps only 40 of 366 days).
Every "corrected" answer is a convention, and the conventions diverge wildly, so no
cleaned value can be a defensible unique ground truth.

**Scoring the count of impossible days was considered and rejected, twice, for
the same reason: the variable would say what the case is looking for.** A turn
that asks how many days report more fine particulate than total particulate has
told the agent the artefact is there, and the whole point is that nothing does.
The noticing therefore stays in the claims, where it has always been.

So the split is:
  - PV: the year's fine share, as a share of MASS, which is coarse enough to be
    the same under every aggregation order and specific enough to exclude the
    mean-of-ratios reading that answers a different question (below).
  - CC: the claims ask whether the response noticed the impossible values, named
    them as an artefact, and caveated the result. That is the capability under test,
    and nothing in the query points at it.

The nearest wrong path is a value near 0.55, which is what silently dropping
the invalid records produces (0.5509 dropping days with ratio > 1, 0.5525
dropping invalid hours). Cleaning is the better scientific instinct, but doing
it silently hides the very finding the case is about, and 0.55 reads "about
half", so it fails the named fraction on its own.

Ground truth is recomputed here from the CSV.

**A corpus triage argued this should be reclassified a baseline, and the
argument was wrong — but checking it found a real P1 hole.** The reviewer held
that silently cleaning the impossible days is "forbidden by the variable
description" and therefore not a reachable naive path under the Round 9 rule.
It was not forbidden. The variable pinned the AGGREGATION ORDER — pool
station-hours, do not average network means or per-station daily means first —
and said nothing about which days take part. Dropping the 54 days whose PM2.5
exceeds their PM10 reads **0.5509** against the pinned 0.6562, and an analyst
who drops physically impossible readings is being careful rather than careless,
so two competent analysts could justify different numbers. That is a P1 failure
whatever the case is called.

The docstring also carried a false quotation for as long as the case existed:
it said the query "pins 'every reported hour'". No version of the query ever
contained that phrase. The reading was pinned by nothing.

**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier variable dictated the aggregation order and the every-day rule so
that a three-decimal ratio was unique. The rebuilt turn asks the composition
question and scores the share as a named fraction. A reliability verdict was
tried and dropped on review: like the annual-screen case's "does one figure
suffice", it is a wording judgement a model can answer "reliable with caveats"
while giving the claims' own reasoning. The noticing is scored by the claims.

**Gate A review 2026-09-06: the scope had to be stated, because cleaning the
impossible readings lands on the label the probe table calls wrong.** The mass
share is 0.66982 over every reported hour, but dropping the station-hours whose
PM2.5 exceeds their PM10 gives **0.52312**, dropping the impossible days
gives **0.55587**, and dropping every day that holds one bad hour gives
**0.38952** — all three "about half". And the case's three required claims
REWARD noticing those readings and calling them impossible, so a response doing
exactly what the claims ask could clean, land on "about half", and fail PV. The
aggregation sweep never touched this axis: it varied the ORDER of aggregation,
never which rows took part.

The variable now says the share is taken over every hour the record reports.
That is a statement of scope — which observations the estimand covers — not a
method, and it does not point at data quality: a reader with no suspicion sees
an ordinary instruction to use the whole year. The noticing stays where it has
always been, in the claims, and a response is now free to report the artefact
AND the figure the question asked for. The three cleaned readings are computed
in `_fractions()` so the spread is measured on every call rather than asserted
here.

**Gate B round 21 (2026-09-03) found the rebuild had left half a recipe
behind, and it was right.** The variable said the share was "formed from daily
or coarser values", and that phrase was there for one reason: the mean of
station-hour row ratios reads **0.7514**, "about three quarters", and nothing
else excluded it. A recipe on a variable is a surface like any other, so the
phrase had to go.

What replaced it is the estimand, not a method. The query asks how much of the
year's particulate MASS was fine, and a mass share is total PM2.5 over total
PM10. That quantity is remarkably stable to how it is built — **0.66778 to
0.66982** across pooled sums, hourly-first, daily-first, station-first and
monthly-first aggregation, against a label boundary at 0.708 — and two thirds
is 0.6667, so the label is not a rounding accident. The mean of per-observation
ratios is excluded because it is not a mass share: a mean of ratios weights a
clean hour and a dirty one equally, and answers "what was the typical fine
fraction of an observation", which is a different question from "how much of
the mass was fine". The mean of DAILY ratios, 0.6562, answers that different
question too, and is kept in the table below only to show it lands on the same
label.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult
from tasks import Turn

_YEAR = 2020

SHARES = ("about half", "about two thirds", "about three quarters", "nearly all")
_ANCHORS = (0.5, 2 / 3, 0.75, 1.0)


def _label(value: float) -> str:
    return SHARES[min(range(4), key=lambda i: abs(value - _ANCHORS[i]))]


def _mass_share(frame: pd.DataFrame) -> float:
    """Total PM2.5 mass over total PM10 mass on whatever rows are passed."""
    return float(frame["PM2.5"].sum() / frame["PM10"].sum())


def _fractions() -> dict:
    """The year's fine share of MASS under every aggregation order, asserted to
    carry one label; the mean-of-ratios readings are reported beside them but
    not scored, for the reason the docstring gives."""
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Hour h ends at h:00, so a date's hours are its labels 1-23 and label 0 of
    # the next date, and 2020 runs to the 00:00 label of 1 January 2021.
    df["date"] = (pd.to_datetime(df[["year", "month", "day", "hour"]])
                  - pd.Timedelta(hours=1)).dt.normalize()
    year = df[df["date"].dt.year == _YEAR].dropna(subset=["PM2.5", "PM10"])
    hourly = year.groupby(["date", "hour"]).agg(pm25=("PM2.5", "mean"), pm10=("PM10", "mean"))
    daily = year.groupby("date").agg(pm25=("PM2.5", "mean"), pm10=("PM10", "mean"))
    station = year.groupby("station").agg(pm25=("PM2.5", "mean"), pm10=("PM10", "mean"))
    monthly = year.groupby(year["date"].dt.month).agg(pm25=("PM2.5", "mean"), pm10=("PM10", "mean"))
    mass = {
        "pooled sums": float(year["PM2.5"].sum() / year["PM10"].sum()),
        "hourly means first": float(hourly["pm25"].sum() / hourly["pm10"].sum()),
        "daily means first": float(daily["pm25"].sum() / daily["pm10"].sum()),
        "station means first": float(station["pm25"].sum() / station["pm10"].sum()),
        "monthly means first": float(monthly["pm25"].sum() / monthly["pm10"].sum()),
    }
    labels = {_label(v) for v in mass.values()}
    if len(labels) != 1:
        raise RuntimeError(f"the fine mass share is not invariant across constructions: {mass}")
    impossible_days = daily.index[daily["pm25"] > daily["pm10"]]
    days_holding_a_bad_hour = set(year.loc[year["PM2.5"] > year["PM10"], "date"])
    cleaned = {
        "dropping impossible station-hours": _mass_share(year[year["PM2.5"] <= year["PM10"]]),
        "dropping impossible days": _mass_share(year[~year["date"].isin(impossible_days)]),
        "dropping any day holding a bad hour": _mass_share(
            year[~year["date"].isin(days_holding_a_bad_hour)]),
    }
    ratio = daily["pm25"] / daily["pm10"]
    return {
        "cleaned_readings": cleaned,
        "fine_share_2020": labels.pop(),
        "mass_readings": mass,
        "not_a_mass_share": {
            "mean of daily ratios": float(ratio.mean()),
            "mean of station-hour row ratios": float(
                (year["PM2.5"] / year["PM10"].where(year["PM10"] > 0)).mean()),
        },
        "impossible_days": int((ratio > 1).sum()),
        "total_days": int(len(ratio)),
    }


def validate_mean_fine_fraction(response: str, runtime, turn: Turn) -> ValidatorResult:
    share = runtime.retrieve("fine_share_2020")
    if share is None:
        return ValidatorResult(False, "fine_share_2020 not set", variables_not_set=True)
    gt = _fractions()
    if str(share).strip().lower() != gt["fine_share_2020"]:
        return ValidatorResult(False, f"fine_share_2020={share!r}, expected {gt['fine_share_2020']!r}")
    return ValidatorResult(True, f"correct: {gt['fine_share_2020']} ({gt['impossible_days']} of "
                                 f"{gt['total_days']} days are physically impossible; the claims score "
                                 "whether the response noticed)")


tools = []
variables = [
    Variable("fine_share_2020", None,
             "Store how much of Beijing's particulate mass was in the fine "
             "fraction over 2020 — the year's total PM2.5 mass as a share of "
             "its total PM10 mass, over every hour the record reports — as one "
             "of exactly these strings: "
             + ", ".join(f"'{x}'" for x in SHARES) + "."),
]
validators = {"validate_mean_fine_fraction": validate_mean_fine_fraction}
