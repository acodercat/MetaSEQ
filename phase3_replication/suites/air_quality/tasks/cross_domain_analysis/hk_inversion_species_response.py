"""Hong Kong inversions raise NO2 and leave PM2.5 alone (cross_domain_analysis).

BASELINE, and the label is not a formality — two things that might look like
traps here are not, and both are stated rather than left to inference.

Reading a null inversion field as a missing observation does not produce a wrong
number, it produces no number at all, because the comparison group vanishes.
Under §4 that disqualifies it as a naive path.

More importantly, **the agent is told**. `sounding_index_df`'s own runtime
description says a null inversion field means no elevated inversion was present,
not a missing value. That description documents the data accurately and predates
this case; weakening it to manufacture difficulty would be sabotaging the
documentation. So the case does not test whether an analyst infers the semantics
— it tests whether they read them, then join two sources and compare two groups.
That is a clean capability check, which is what a baseline is for, and the
scientific content sits in the CC claims rather than in the arithmetic.

Difficulty is `hard` on the cross-domain and step-count anchors — turn 2 spans
the sounding file and a million-row table and runs to six or seven steps — and
the case for `medium` is real, since neither turn needs a domain formula and the
one subtlety is handed over. Recorded so a reviewer can overrule it on the
evidence rather than re-derive it.

Hong Kong's only upper-air station launches at 08:00 and 20:00 local. IGRA
reports an elevated inversion only when one exists, so `inversion_height_agl_m`
is null on 79 % of morning launches — those are the mornings WITHOUT an
inversion, and they are the control group.

Which of the three inversion columns defines "reports an elevated inversion" is
not a degree of freedom, and that was checked rather than assumed: across the
2,142 morning launches the pressure, height and temperature-difference fields
are null together on 1,692 and present together on 450, never mixed, so all
three give 0.2939.

The science is that the surface response is species-dependent, and the species
disagree in a way that inverts the headline conclusion. Measured over 2020-2025
on the 2,133 mornings that pair a launch with surface data:

    NO2     45.412 with an inversion vs 38.750 without   +6.662  (+17.2 %)
    PM2.5   14.562                     vs 14.513         +0.049  ( +0.3 %)
    PM10    23.158                     vs 23.881         -0.723  ( -3.0 %)
    AQHI     2.688                     vs  2.812         -0.124  ( -4.4 %)

The reading the case is built on is that an analyst who measures "air quality"
by the composite index concludes that inversions make Hong Kong's air BETTER.
The NO2 difference is significant at p = 7.3e-12 (Welch, n = 448/1685) and
positive in five of the six years; PM2.5's is p = 0.93.

**Why the species differ is an interpretation this comparison cannot settle,
and the CC claim is written to that limit.** The natural reading — NO2 locally
emitted and so responsive to a lid, PM2.5 regionally transported and so not —
is plausible and is not established here: there is no source apportionment, and
no control for season or year. PM2.5's annual contrasts run from -2.505 to
+1.355 and its year-month-demeaned contrast is -0.849, so even its sign is a
property of the pooling. What the data support is that the two species respond
differently, which is enough for the case; the mechanism is offered as
consistent, not demonstrated.

**Why the index falls is NOT the particulate term, and an earlier version of
this docstring said it was.** Gate B decomposed the stored added-risk
components and the claim did not survive: on inversion mornings the ozone term
moves -0.517614 and the nitrogen dioxide term +0.272544, while the particulate
term moves -0.021282. Particulates are the SMALLEST of the three, 15.3 % of mean total
added risk against ozone's 49.4 % and NO2's 34.0 %.

**The `aqhi` column above is EPD's published index, not a computed one, and it
took two attempts to get there.** On 2026-08-12 the derived columns were
recomputed onto EPD's published band table, on the belief that the table had
been using unpublished edges; that moved AQHI here to 2.701/2.827 and was rolled
back the same day, because recomputation from concentrations agrees with EPD's
own published index on only 96.3 % of rows where the stored values already
agreed on 99.3 %. On 2026-08-13 the column was replaced with the published
values themselves, recovered from the `24aqhi_Eng.xml` archive — 18,617 rows
changed, and the figures above are those. **Neither scored answer was ever
affected**: turn 1 reads the sounding file and turn 2 reads NO2 concentrations,
and neither touches the index.

The index falls because its ozone term falls further than its NO2 term rises —
higher surface NO2 with lower surface ozone, the shape titration takes, though
this case measures the association and does not establish the mechanism. The CC
claim was rewritten around what was measured; the version demanding a
particulate explanation was requiring an answer the data contradicts.

**PM2.5 is deliberately not scored, and the measurement is why.** Its difference
moves 5x across defensible aggregation orders — 0.0494 averaging each morning's
stations before comparing groups, 0.2525 forming each station's two group means
and averaging the stations, 0.2538 pooling station-hours outright. NO2's same
three read 6.6619 / 6.6563 / 6.6750, a spread of 0.019. A near-zero difference
is not robust enough to carry a tolerance, so the species contrast is asked for
in the CC claim, which needs the direction and not the digits.

**Turn 2's window had to be spelled out, because turn 1 narrows to three
months.** It used to say "over the same period", which a reader can take either
as the six calendar years or as the December-January-February subset just
established. The DJF reading is not a mistake: it pairs 533 mornings (158 with
an inversion, 375 without) and gives 52.750044 - 44.039508 = **+8.710536**
against the all-month **+6.661865**. A live agent took it and failed, and Gate B
round 3 ruled it a query defect rather than agent error — correctly, since no
tolerance should be asked to separate two readings the query left open. The turn
now names all twelve months.

Turn 1 is the control turn §4 asks for: it needs the null-as-absence reading but
no surface data at all, so failing to join is separable from failing to read.

Tolerances.

Turn 1, `decimals=4`, deriving +/-0.00006. **It was +/-0.001, which did not
absorb "the rounding and nothing else" as this docstring claimed** — the
fraction is 0.293900185, so 0.2949 sits 0.000999815 away and passed, a
numerically wrong four-decimal answer inside a band justified as rounding slop.
Nothing measured needed that width; the count is exact at 159/541. What the
band excludes is
the cross-year winter convention, 0.3133 — December 2020 through February 2025
grouped by winter rather than by calendar year — which is 19 bands out. The
query names the three months and the year span instead of saying "winter", so
that reading is forbidden rather than merely excluded, but the band would catch
it either way. Pooling the 20:00 launches reads 0.2680 and is likewise named out.

**The year window is the one a live agent actually dropped.** `sounding_index_df`
runs to 2026-08, so taking every DJF 08:00 launch in it without the 2020-2025
restriction reads 171/600 = **0.2850** — the query states the span, the agent
filtered month and hour and not year, and the band rejects it by 148 widths.
This is the hazard `CLAUDE.md` calls the 2026 rule, arriving in the most ordinary
way there is.

Turn 2, +/-0.005 ug/m3. **It was +/-0.05 and that was a P1 failure**, found by
Gate B: the domain prompt's TERRITORY FIGURES convention fixes each morning's
territory mean over every reporting station, so the other aggregation orders
are FORBIDDEN readings, not
implementation variance, and the docstring's framing of them as variance was the
error underneath the number. The wide band passed pooled station-hours
(6.674955), station-first group means (6.656263) and a general-stations-only
territory mean (6.625814) alongside the correct 6.661865.

At +/-0.005 the requested two-decimal 6.66 passes and the observably different
readings, 6.67 and 6.63, fail. Station-first fails on its raw value, 6.656263,
which sits 0.0056 out — but it rounds to 6.66, so an agent that reports at the
requested two decimals is indistinguishable from a correct one. That is stated
rather than hidden: no band can separate a reading that collapses onto the
answer at the precision the case asks for. The two readings the query forbids
outright remain far out — pairing each launch with the day's mean reads
4.7573 and admitting the 20:00 launches reads 8.6863, 381 and 405 bands.

Both ground truths are recomputed here from the database and the sounding file.

**Split 2026-09-02 (query length):** turn 2 asked for the NO2 excess and
then an assessment of PM2.5 and the index in the same breath; the
assessment is now a third turn with two scored verdicts — PM2.5 does not
respond like NO2 (+0.3 % against +17 %), and the index moves with ozone
(down 0.12 while ozone falls 10 ug/m3 and NO2 rises) — with the two claims
moved to it. Gate C the same day: Flash first wrote `pm25_diff > 0`, which
+0.05 ug/m3 satisfies, before overriding it by judgement, so the variable
now defines "comparable" as at least half of NO2's relative excess.

**What "the index follows" means is the direction of the change, and the
variable says so.** It used to ask which pollutant the index "moves with on
inversion mornings", which reads just as naturally as a correlation across
those mornings — and there nitrogen dioxide narrowly wins, r = 0.666 against
ozone's 0.654 over the 448 inversion mornings, a margin no reading should
have to carry. That correlation describes day-to-day variation within one
group; the question the turn asks is what the inversion does, which is the
difference between the groups: the index falls 0.12, ozone falls 10.05 ug/m3
and nitrogen dioxide rises 6.66, so ozone is the one that changes the same
way. The variable now names that comparison, and `_species_verdicts()`
refuses to score if both pollutants or neither change with the index.
"""

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

_SPAN = ("2020-01-01", "2026-01-01")
_LAUNCH_HOUR = 8
_WINTER_MONTHS = (12, 1, 2)


def _launches() -> pd.DataFrame:
    df = pd.read_csv(
        DATA_DIR / "sounding_indices.csv",
        parse_dates=["datetime"],
    )
    df = df[(df["datetime"] >= _SPAN[0]) & (df["datetime"] < _SPAN[1])]
    df = df[df["hour"] == _LAUNCH_HOUR].copy()
    # Null is absence, not absence of measurement: IGRA emits the inversion
    # fields only when the warmest level sits above the surface.
    df["inversion"] = df["inversion_height_agl_m"].notna()
    return df


def _winter_rate() -> float:
    df = _launches()
    winter = df[df["month"].isin(_WINTER_MONTHS)]
    return float(winter["inversion"].mean())


def _no2_excess() -> float:
    return _excess("no2")


def _excess(column: str, with_baseline: bool = False):
    """Inversion-morning minus other-morning mean of a territory 08:00 series.

    With `with_baseline`, also returns the non-inversion mean the excess is
    relative to, so a relative comparison never has to freeze a denominator.
    """
    launches = _launches().set_index("datetime")["inversion"]
    # Each morning's network mean is formed IN THE DATABASE, not by pulling the
    # station-hours back and averaging here. That is the order the query pins,
    # and it is also the only version that runs: `domains.HK.db` caps a
    # statement is capped, and once the record was extended back to 2020 the
    # table passed a million rows — returning the ~39,000 08:00 station-hours
    # started timing out where returning 2,190 daily means does not.
    #
    # The hours are enumerated rather than filtered with `extract(hour ...) =
    # 8`, which is not sargable and forces a sequential scan of the whole table
    # however narrow the result. Matching a generated series of the 2,192
    # timestamps lets `idx_hsaq_datetime` serve it: an index scan at 43 ms
    # against a parallel sequential scan at 84 ms warm, and the gap is far wider
    # cold, where the scan has to read all 130 MB. Both forms return the same
    # 2,183 rows with identical values.
    network = read_frame(text(f"""
        select datetime, avg({column}) as value
        from hourly_station_air_quality
        where datetime in (
            select generate_series(
                cast(:lo as timestamp) + make_interval(hours => :h),
                cast(:hi as timestamp),
                interval '1 day')
        ) and {column} is not null
        group by datetime
    """), {"lo": _SPAN[0], "hi": _SPAN[1], "h": _LAUNCH_HOUR})
    network = network.assign(datetime=pd.to_datetime(network["datetime"])) \
        .set_index("datetime")["value"]
    paired = pd.concat([launches, network.rename("value")], axis=1, join="inner").dropna()
    inversion = float(paired.loc[paired["inversion"], "value"].mean())
    other = float(paired.loc[~paired["inversion"], "value"].mean())
    return (inversion - other, other) if with_baseline else inversion - other


def validate_winter_inversion_rate(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("winter_inversion_rate")
    if val is None:
        return ValidatorResult(
            False, "winter_inversion_rate not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(False, f"winter_inversion_rate={val!r} is not a number")

    gt = _winter_rate()
    if reports_as(val, gt, decimals=4):
        return ValidatorResult(True, f"correct: {val} ~ {gt:.4f}")
    return ValidatorResult(False, f"winter_inversion_rate={val}, expected ~{gt:.4f}")


def validate_no2_inversion_excess(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("no2_inversion_excess")
    if val is None:
        return ValidatorResult(
            False, "no2_inversion_excess not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(False, f"no2_inversion_excess={val!r} is not a number")

    gt = _no2_excess()
    if reports_as(val, gt, decimals=2):
        return ValidatorResult(True, f"correct: {val} ~ {gt:.2f} ug/m3")
    return ValidatorResult(False, f"no2_inversion_excess={val}, expected ~{gt:.2f}")




def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def _species_verdicts() -> dict:
    """Whether PM2.5 responds to the inversion as NO2 does, and what the index
    follows. Measured: NO2 +6.66 ug/m3, PM2.5 +0.05, the index -0.12 and ozone
    -10.05 on inversion mornings, against non-inversion baselines of 38.8, 14.5,
    2.81 and 37.7. PM2.5 "responds like NO2" only if its relative excess is at
    least half of NO2's, which the variable states.

    Both the excesses and the baselines they are relative to are recomputed
    here. A Gate A review on 2026-09-06 found the baselines frozen as the
    literals 38.8 and 14.5 — measured once, then hard-coded — which P2 forbids
    for the same reason it forbids a stored ground truth: the database moves and
    a frozen denominator stops describing it. The same review found the SQL's
    null filter hard-coded to `no2` whatever column was being averaged, so
    PM2.5, the index and ozone were all being averaged over the hours NO2
    happened to report rather than their own. Both are fixed; neither moved a
    verdict (PM2.5's excess went from +0.0481 to +0.0494).
    """
    means, baselines = {}, {}
    for column in ("no2", "pm2_5", "aqhi", "o3"):
        means[column], baselines[column] = _excess(column, with_baseline=True)
    same_way = [name for name, column in (("ozone", "o3"), ("nitrogen dioxide", "no2"))
                if (means[column] < 0) == (means["aqhi"] < 0)]
    if len(same_way) != 1:
        raise RuntimeError(f"index_follows is not unique: {same_way} change with the index, "
                           f"excesses {means}")
    return {
        "pm25_responds_like_no2": bool(
            means["pm2_5"] > 0 and means["no2"] > 0
            and means["pm2_5"] / baselines["pm2_5"] >= 0.5 * means["no2"] / baselines["no2"]),
        "index_follows": same_way[0],
        "excess": means,
        "baseline": baselines,
    }


def validate_species(response: str, runtime, turn: Turn) -> ValidatorResult:
    pm = runtime.retrieve("pm25_responds_like_no2")
    follows = runtime.retrieve("index_follows")
    missing = [n for n, v in (("pm25_responds_like_no2", pm), ("index_follows", follows)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _species_verdicts()
    errors = []
    if not _bool_ok(pm, gt["pm25_responds_like_no2"]):
        errors.append(f"pm25_responds_like_no2={pm!r}, expected {gt['pm25_responds_like_no2']}")
    if str(follows).strip().lower() != gt["index_follows"]:
        errors.append(f"index_follows={follows!r}, expected {gt['index_follows']!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: PM2.5 does not respond like NO2; the index follows {gt['index_follows']}")


tools = []
variables = [
    Variable(
        "winter_inversion_rate",
        None,
        "Store the share of the 08:00 King's Park launches in December, January "
        "and February of 2020 through 2025 that report an elevated inversion, as "
        "a float between 0 and 1, 4 decimal places.",
    ),
    Variable(
        "no2_inversion_excess",
        None,
        "Store the difference in mean 08:00 territory NO2 between mornings whose "
        "08:00 launch reports an elevated inversion and mornings whose launch "
        "does not, as a float in ug/m3, 2 decimal places. Positive means higher "
        "with an inversion.",
    ),
]
validators = {
    "validate_winter_inversion_rate": validate_winter_inversion_rate,
    "validate_no2_inversion_excess": validate_no2_inversion_excess,
    "validate_species": validate_species,
}
variables += [
    Variable("pm25_responds_like_no2", None,
             "Store True if the territory's 08:00 PM2.5 carries an "
             "inversion-morning excess comparable to NO2's — at least half of "
             "NO2's excess in relative terms — else False."),
    Variable("index_follows", None,
             "Compare the territory's 08:00 means on inversion mornings with "
             "those on the other mornings, for the composite health index and "
             "for each pollutant. Store the pollutant that changes in the same "
             "direction as the index, as one of exactly these strings: "
             "'ozone', 'nitrogen dioxide'."),
]
