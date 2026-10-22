"""CAMS PM2.5 against the Beijing network — and where the product stops working
(cross_domain_analysis).

Product-validation BASELINE, not a diagnostic trap. A reanalysis product is only
usable where its error is characterised, and the error here is neither small nor
uniform.

- Turn 1 (the pre-rebuild figures cams_obs_pairs_2023, cams_pm25_bias_2023 and
cams_pm25_rmse_2023, which the claims now carry): 2897
  matched records in 2023, a mean CAMS-minus-network difference of +56.82 ug/m3,
  and a root-mean-square difference of 76.70. The product averages 92.1 ug/m3
  against the network's 35.3 over the same hours — 2.6 times as much, an excess
  of 1.6 times the observed level — and it is high nearly always rather than on
  average: 91 % of the 2897 differences are positive.
- Turn 2 (low_dust_decile_r, high_dust_decile_r): over 2020-2025 the
  CAMS-network correlation is 0.687 in the tenth of hours the product itself
  scores lowest for dust and 0.422 in the tenth it scores highest. Agreement is
  not merely poor, it is conditionally poor, and it is worst in the regime the
  product's own composition diagnostic singles out.

Why this is a baseline and not a trap. It was registered as a trap against
aggregation before comparison, and Gate B was right to reject that: the
earlier query pinned "the network mean of the identical hour", so
collapsing to daily means was explicit non-compliance rather than a
plausible reading of the estimand; since the 2026-09-02 rebuild the daily
comparison is one of the routes the verdicts are asserted over, and it
reaches the same verdicts. The reclassification also explains the live result —
6 turns of 6 on the first model — better than the model's competence does. The
`hard` label stays: two files, five outputs, a percentile-conditioned
correlation and a substitution judgement is not an easy task, and one model's
clean sweep is not evidence that it is.

The aggregation readings are still worth recording as excluded values, and one
of them is instructive. Collapsing both series to daily means gives an RMSE of
66.06, a seventh lower than the exact-hour figure. What that hides is worth
stating precisely, because the obvious explanation is wrong.

Averaging does NOT cancel errors of opposite sign: 91 % of the differences are
positive and the daily bias, +57.08, is if anything larger than the 3-hourly
+56.82. What collapses is the scatter. Since a mean square error is the bias
squared plus the variance, and the standard deviation of the difference falls
from 51.5 to 33.3 once the eight sub-daily values are averaged, daily
aggregation conceals the timing mismatch while leaving the offset untouched. It
makes the product look more precise, never less biased. (Taking the observed
daily mean over all 24 hours rather than the eight matched ones gives 66.06 with
a spread of 33.3; over the matched hours only, 66.01 and 33.2. Both readings are
the same mistake.)

Two related slips: matching CAMS hours against the daily observed mean gives
78.52, and comparing against individual station rows rather than the network
mean gives 77.49. Only the exact-hour comparison against the network mean
answers the question asked.

What the case may NOT say, taken from the dataset's own manifest rather than
from judgement. `datasets/Beijing/cams.sources.json` lists six known limitations
and an earlier version of the required claims broke two of them:

- The fields "must never be compared to station values as if measuring the same
  quantity". CAMS PM2.5 is a model surface field on a 0.75 degree grid, roughly
  80 km, while the network is twelve point sites, eight urban and four suburban.
  Same units, different spatial support. A claim requiring the response to call
  them two estimates of the same quantity contradicted the manifest outright,
  and it also miscounted the network as twelve urban sites.
- "Never use dust_aod550 or dust_fraction to identify ground-level dust
  episodes." The manifest measures why: dust AOD correlates with station PM10 at
  only r = +0.32, the record's strongest surface dust event ranks 152nd of 2193
  days by dust AOD, and the coarse-fraction ratio is identical between the 30
  highest and 30 lowest dust-AOD days. Column aerosol travels in elevated layers
  that never reach the ground. The upper stratum here is therefore hours CAMS
  DIAGNOSES as dust-rich, never observed coarse-particle episodes, and a claim
  that called them the latter asked for a statement the data refutes.

That constraint does not weaken the case, because the stratification never
needed real dust. Splitting on the product's own composition diagnostic
partitions the record by what the model thinks is happening rather than by
season or concentration, and it borrows no information from the observations it
is being scored against. The finding stands on its own terms: where CAMS
attributes more of the column to dust, its surface PM2.5 agrees with the network
markedly less well.

Tolerances.

(Until 2026-09-02; the rebuilt turns score verdicts.)

- Turn 1: the pair count took 0, and the two error statistics +/-0.01 ug/m3.
  With the join pinned to the exact hour and the observed value to the network
  mean there was no implementation variance, so the band covered only 2-decimal
  reporting. The daily-aggregation reading at 66.06 is ten units away.
- Turn 2: +/-0.005 on each correlation, reported to 3 decimals. The decile
  boundary is the only free choice and it barely registers: across linear,
  lower, higher, nearest and midpoint interpolation, and inclusive against
  strict comparison, the low-dust correlation is 0.6874 every time and the
  high-dust one spans 0.4211 to 0.4217. Twenty-six records sit exactly on the
  low boundary, which is why inclusive is pinned rather than left open. The band
  is a fiftieth of the 0.265 gap the case is about.

Turn 2 applies its 2020-2025 window in code as well as in the query, and that
is not belt-and-braces. The CAMS file carries two rows dated 2026 — the manifest
says coverage ends 2025-12, and the local-time conversion pushes a sliver past
it — and an unfiltered helper swept them in, moving the low-dust correlation
from 0.68739 to 0.68682 and shifting two records across the decile boundary.
Both readings round to 0.687 so no score ever changed, but the validator was
answering a question the query had not asked. Gate B found it. This is the third
time in two days a partial 2026 has contaminated a statistic in this corpus, the
others being an author robustness check and an evaluated model's pooled ozone
figure, so any window that stops before the end of the record should be enforced
in code and not left to the file's current extent.

Ground truth is recomputed here from the CSVs.

**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier turns dictated the exact-hour join and the decile split and
scored five figures to two or three decimals. The rebuilt turns ask the
colleague's question and the regime question and score four verdicts: the
model reads higher (True under exact-hour, daily and station-row
comparisons), by about 60 ug/m3 (56.8 to 57.1), it cannot substitute for the
network, and its agreement is worse where it diagnoses dust (True under
3, 4, 5 and 10 groups and the decile edges, on 3-hourly records and on
daily means). The correlations themselves (0.687 against 0.422 at the
deciles) are now the claims' to require.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn

_YEAR = 2023
_SPAN = (2020, 2025)
_DECILE = 0.1


def _matched() -> pd.DataFrame:
    """CAMS records joined to the network mean of the very same hour."""
    bj = DATA_DIR
    cams = pd.read_csv(bj / "aerosol_cams.csv")
    obs = pd.read_csv(bj / "air_quality.csv").dropna(subset=["PM2.5"])
    network = (
        obs.groupby(["year", "month", "day", "hour"])["PM2.5"]
        .mean()
        .rename("observed")
        .reset_index()
    )
    return cams.merge(network, on=["year", "month", "day", "hour"], how="inner")


def _year_error() -> dict:
    """The 2023 offset under three comparisons; its sign and its size to the
    nearest 10 ug/m3 are asserted invariant (+56.8 exact-hour, +57.1 daily,
    +56.9 against station rows)."""
    df = _matched()
    df = df[df["year"] == _YEAR]
    exact = float((df["cams_pm2p5_ugm3"] - df["observed"]).mean())
    daily = df.groupby(["month", "day"])[["cams_pm2p5_ugm3", "observed"]].mean()
    by_day = float((daily["cams_pm2p5_ugm3"] - daily["observed"]).mean())
    obs = pd.read_csv(DATA_DIR / "air_quality.csv").dropna(subset=["PM2.5"])
    rows = obs[obs["year"] == _YEAR].merge(df[["year", "month", "day", "hour", "cams_pm2p5_ugm3"]],
                                           on=["year", "month", "day", "hour"])
    by_row = float((rows["cams_pm2p5_ugm3"] - rows["PM2.5"]).mean())
    readings = {"exact hour": exact, "daily": by_day, "station rows": by_row}
    verdicts = {(r > 0, int(10 * round(r / 10))) for r in readings.values()}
    if len(verdicts) != 1:
        raise RuntimeError(f"the offset verdict is not invariant: {readings}")
    higher, nearest_ten = verdicts.pop()
    return {"model_reads_higher": higher, "bias_nearest_10": nearest_ten,
            # A judgement, not a computation: a field on an 80 km grid with a
            # +57 ug/m3 offset and conditionally poor agreement is not a
            # substitute for twelve point sites.
            "field_can_substitute": False}


def _dust_skill() -> dict:
    """Agreement in the hours the product scores lowest and highest for dust,
    asserted invariant across the split (3, 4, 5 and 10 groups; the decile
    edges inclusive) and the basis (3-hourly records or daily means)."""
    df = _matched()
    df = df[df["year"].between(*_SPAN)]
    daily = df.groupby(["year", "month", "day"])[["cams_pm2p5_ugm3", "observed", "dust_fraction"]].mean()
    verdicts = {}
    for basis, frame in (("records", df), ("daily", daily)):
        for groups in (3, 4, 5, 10):
            label = pd.qcut(frame["dust_fraction"], groups, labels=False, duplicates="drop")
            corr = frame.groupby(label).apply(lambda g: g["cams_pm2p5_ugm3"].corr(g["observed"]))
            verdicts[f"{basis}, {groups} groups"] = bool(corr.iloc[-1] < corr.iloc[0])
        low = frame[frame["dust_fraction"] <= frame["dust_fraction"].quantile(_DECILE)]
        high = frame[frame["dust_fraction"] >= frame["dust_fraction"].quantile(1 - _DECILE)]
        verdicts[f"{basis}, decile edges"] = bool(
            high["cams_pm2p5_ugm3"].corr(high["observed"]) < low["cams_pm2p5_ugm3"].corr(low["observed"]))
    if len(set(verdicts.values())) != 1:
        raise RuntimeError(f"the dust-regime verdict is not invariant: {verdicts}")
    return {"agreement_worse_where_model_sees_dust": verdicts["records, decile edges"]}


def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_year_error(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "model_reads_higher": runtime.retrieve("model_reads_higher"),
        "cams_pm25_bias_nearest_10": runtime.retrieve("cams_pm25_bias_nearest_10"),
        "field_can_substitute": runtime.retrieve("field_can_substitute"),
    }
    missing = [n for n, v in got.items() if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _year_error()
    errors = []
    if not _bool_ok(got["model_reads_higher"], gt["model_reads_higher"]):
        errors.append(f"model_reads_higher={got['model_reads_higher']!r}, expected {gt['model_reads_higher']}")
    bias = got["cams_pm25_bias_nearest_10"]
    if not is_finite_number(bias) or int(10 * round(float(bias) / 10)) != gt["bias_nearest_10"]:
        errors.append(f"cams_pm25_bias_nearest_10={bias!r}, expected {gt['bias_nearest_10']}")
    if not _bool_ok(got["field_can_substitute"], gt["field_can_substitute"]):
        errors.append(f"field_can_substitute={got['field_can_substitute']!r}, expected {gt['field_can_substitute']}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: the model reads higher by about {gt['bias_nearest_10']} ug/m3; "
                                 "not a substitute")


def validate_dust_skill(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("agreement_worse_where_model_sees_dust")
    if val is None:
        return ValidatorResult(False, "agreement_worse_where_model_sees_dust not set", variables_not_set=True)
    gt = _dust_skill()
    if not _bool_ok(val, gt["agreement_worse_where_model_sees_dust"]):
        return ValidatorResult(False, f"agreement_worse_where_model_sees_dust={val!r}, "
                                      f"expected {gt['agreement_worse_where_model_sees_dust']}")
    return ValidatorResult(True, "correct: agreement is worse in the hours the product scores dust-rich")


tools = []
variables = [
    Variable("model_reads_higher", None,
             "Store True if the modelled PM2.5 field reads higher than the "
             "network over 2023 on average, else False."),
    Variable("cams_pm25_bias_nearest_10", None,
             "Store the mean modelled-minus-observed difference over 2023 as a "
             "signed number in ug/m3 to the nearest 10."),
    Variable("field_can_substitute", None,
             "Store True if the field can be used in place of the network as it "
             "stands, else False."),
    Variable("agreement_worse_where_model_sees_dust", None,
             "Store True if, over 2020 to 2025, the modelled and observed PM2.5 "
             "agree less well in the hours the product itself scores highest for "
             "dust than in the hours it scores lowest, else False."),
]
validators = {
    "validate_year_error": validate_year_error,
    "validate_dust_skill": validate_dust_skill,
}
