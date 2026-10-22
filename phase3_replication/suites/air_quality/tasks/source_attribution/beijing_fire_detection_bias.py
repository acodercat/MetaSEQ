"""Beijing fires — detection is not emission (source_attribution).

Classified a multi-turn BASELINE. Both correlations are unique, well-defined
computations with no plausible naive method that lands on a different number,
so §4's trap contract does not apply: the diagnostic value lives entirely in
the CC channel and in the contrast between the two turns.

Two programmatic turns plus claim-coverage checks. The scientific point is that
raw satellite fire detections mislead: the *all-detections* correlation comes
out negative, and it flips positive once restricted to fires the wind could
actually have carried into the city.

What this data does and does not show. The measured sign change is real. The
usual explanation for the negative raw correlation — cloud cover suppressing
detections on the humid, stagnant days when PM2.5 peaks — is a plausible
mechanism from the remote-sensing literature, but nothing here measures cloud,
humidity, or overpass timing, so this case cannot test it. An earlier version
of this docstring asserted the mechanism outright; it is stated as a hypothesis
because that is all the data supports.

- Turn 1 (fire_pm25_corr_all): r(all detections within 300 km, PM2.5) ~ -0.25.
- Turn 2 (fire_pm25_corr_upwind): r(upwind detections, PM2.5) ~ +0.10.

Both correlations are unique, well-defined computations (P1-clean); the
diagnostic value lives across the two turns and in the claims.

Report each correlation to two decimals. The domain's daily city-value
convention is the mean of hourly network means, using hour-ending observation
days. This gives -0.2452 (reported -0.25) and +0.1044 (reported +0.10).
Pooling station-hours instead gives -0.2449 (reported -0.24); averaging station
daily means gives -0.2451. These are sensitivity comparisons, not alternative
answer keys. The former +/-0.01 band hid the rounding difference. The October
2026 full review fixed the reference recipe and now checks the declared report
with reports_as.

An earlier version of this paragraph claimed the aggregation was "pinned in the
query" and that the band "covers only the 2-decimal reporting the variable asks
for, which needs 0.005". Neither survived the 2026-09-06 restoration, which took
the aggregation back out of the query precisely because the three recipes agree
within the band, and both sentences were still here on 2026-10-06. What found
them was a live run: the first case checked under the tool harness stored
**-0.25** for `fire_pm25_corr_all` and passed, which is correct by design and
flatly contradicted the sentence above it. A stored value a reader would call
wrong, that the validator calls right, is the cheapest way to find a tolerance
whose rationale has drifted.

An earlier version carried +/-0.06 — thirty times the measured spread, justified
from memory as "NaN-handling variance" on a table with no NaNs. Both defects
were in the same line, and only the arithmetic one was visible from inside.

Both ground truths are recomputed here from the CSVs.

**Rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier second turn told the agent to recompute "using only the upwind
detections" — the conditioning the case exists to test. The rebuilt turns
ask whether regional fires drive Beijing's autumn PM2.5 and then relay a
colleague's reading of the negative sign; turn 1 scores the sign (invariant
across the three daily recipes) and a verdict, turn 2 the verdict on the
colleague alone. The upwind correlation (+0.10, invariant too) is computed
in `_corrs()` but NOT scored: naming it on a variable would hand over the
conditioning that the claims `sign_change` and `sign_change_magnitude`
exist to score, and a review on 2026-09-02 found the first rebuild doing
exactly that. Finding the upwind detections in the record is the agent's
move.

**That paragraph no longer describes the file, and the trade it names is
real.** The 2026-09-06 restoration below put the upwind correlation back on a
variable and the words "the detections the wind could actually have carried"
back in turn 2's query, which is exactly the leak the rebuild removed. A
verification pass on 2026-09-07 caught it. The conditioning cannot be both
scored and hidden: restricting by upwind sector, by back-trajectory, or by
distance-weighted plume all answer the same question and give different
coefficients, so a unique number needs the sector pinned, and a pinned sector
is on a surface the agent reads. The resolution is to stop claiming turn 2 is a
discovery turn. **Turn 1 is the open question** — "what does the record tell
you about regional fires" names no method, and its correlation is a real
programmatic quantity at two decimals. **Turn 2 is execution plus
interpretation**: the conditioning is handed over, and what is scored beyond
the arithmetic is whether the agent refuses the colleague's inference. The
claims were rewritten to match, dropping the half that asked the response to
notice a sign change the query had already announced.


**Gate A review 2026-09-06 restored the two magnitudes, because the corpus-wide
no-data control showed this case was measuring nothing.** Asked with the runtime
removed, both DeepSeek models produced every scored quantity of both turns
correctly: a sign, a bool and a bool are all guessable, and a case whose entire
PV surface is guessable has no programmatic content at all
(`scripts/controls/no_data_control.py`).

Historical September 2026 measurements compared three daily recipes over the
same 345 days. Their all-detection correlations differed by only 0.0003 but
straddled the two-decimal rounding boundary. That small numerical difference
cannot establish unique reporting digits. The current answer uses the domain's
hourly-first recipe. PM2.5 days contain hours ending 01:00 through 24:00;
detection dates retain their own daily labels. Calendar-label correlations
(-0.2417 and +0.0982) are also sensitivity results, not scored answer keys.

"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_MONTHS = [10, 11]
_YEARS = range(2020, 2026)
POSITIVE = "positive"
NEGATIVE = "negative"


def _corrs() -> dict:
    """The two correlations, the day count they rest on, and their signs,
    asserted invariant in the historical sensitivity precision across the three daily PM2.5
    recipes (pooled station-hours, hourly network means first, per-station daily
    means). Measured: 345 days under all three, r = -0.2449 / -0.2452 / -0.2451
    for every detection and +0.1041 / +0.1044 / +0.1039 for the upwind ones — a
    spread of 0.0003 and 0.0005, far inside the +/-0.01 the case scores."""
    bj_dir = DATA_DIR
    df = pd.read_csv(bj_dir / "air_quality.csv").dropna(subset=["PM2.5"])
    # Label h is the hour ending at h:00, so a day of air quality is a date's
    # labels 1-23 and label 0 of the next date. FIRMS is daily and keeps its own.
    df["date"] = (pd.to_datetime(df[["year", "month", "day", "hour"]])
                  - pd.Timedelta(hours=1)).dt.normalize()
    recipes = {
        "pooled": df.groupby("date")["PM2.5"].mean(),
        "hourly first": df.groupby(["date", "hour"])["PM2.5"].mean().groupby(level=0).mean(),
        "station first": df.groupby(["date", "station"])["PM2.5"].mean().groupby(level=0).mean(),
    }
    fire = pd.read_csv(bj_dir / "fire_firms.csv")
    fire["date"] = pd.to_datetime(fire[["year", "month", "day"]])
    fire = fire[fire["month"].isin(_MONTHS) & fire["year"].isin(list(_YEARS))]
    readings = {}
    for name, pm in recipes.items():
        merged = fire.merge(pm.rename("pm").reset_index(), on="date", how="inner")
        readings[name] = {
            "days": len(merged),
            "all": float(merged["fires_within_radius"].corr(merged["pm"])),
            "upwind": float(merged["fires_upwind"].corr(merged["pm"])),
        }
    reference = readings["hourly first"]
    # The domain defines daily city values by hourly network means first.
    # The other recipes are sensitivity checks, not additional answer keys.
    # Historically, every recipe's 2-decimal report passed a +/-0.01 band
    # around the reference, not that all recipes round to the same digits: the
    # all-detections figure sits at a rounding boundary, -0.2449 pooled against
    # -0.2452 hourly-first, so the recipes report -0.24 and -0.25 and both formerly passed.
    for key in ("days", "all", "upwind"):
        ok = all(r[key] == reference[key] if key == "days"
                 else abs(round(r[key], 2) - reference[key]) <= 0.01
                 for r in readings.values())
        if not ok:
            raise RuntimeError(f"{key} is not invariant across daily recipes in the historical sensitivity "
                               f"precision: {[(n, r[key]) for n, r in readings.items()]}")
    return {"days": reference["days"],
            "corr_all": reference["all"], "corr_upwind": reference["upwind"],
            "all": POSITIVE if reference["all"] > 0 else NEGATIVE,
            "upwind": POSITIVE if reference["upwind"] > 0 else NEGATIVE,
            "readings": readings,
            # Judgements, not computations: a negative raw correlation is not
            # evidence that fires do not contribute, and the colleague is wrong.
            "fires_shown_not_to_matter": False}


def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_fire_corr_all(response: str, runtime, turn: Turn) -> ValidatorResult:
    sign = runtime.retrieve("fire_pm25_corr_sign_all")
    verdict = runtime.retrieve("fires_shown_not_to_matter")
    missing = [n for n, v in (("fire_pm25_corr_sign_all", sign), ("fires_shown_not_to_matter", verdict)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    days = runtime.retrieve("days_compared")
    value = runtime.retrieve("fire_pm25_corr_all")
    if days is None or value is None:
        return ValidatorResult(False, "days_compared, fire_pm25_corr_all not set",
                               variables_not_set=True)
    gt = _corrs()
    errors = []
    if not is_finite_number(days) or days != gt["days"]:
        errors.append(f"days_compared={days!r}, expected {gt['days']}")
    if not is_finite_number(value):
        errors.append(f"fire_pm25_corr_all={value!r} is not a number")
    elif not reports_as(value, gt["corr_all"], decimals=2):
        errors.append(f"fire_pm25_corr_all={value}, expected ~{gt['corr_all']:.2f}")
    if str(sign).strip().lower() != gt["all"]:
        errors.append(f"fire_pm25_corr_sign_all={sign!r}, expected {gt['all']!r}")
    if not _bool_ok(verdict, gt["fires_shown_not_to_matter"]):
        errors.append(f"fires_shown_not_to_matter={verdict!r}, expected {gt['fires_shown_not_to_matter']}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: {gt['corr_all']:.2f} over {gt['days']} days, "
                                 "and it does not show fires do not matter")


def validate_fire_corr_upwind(response: str, runtime, turn: Turn) -> ValidatorResult:
    verdict = runtime.retrieve("colleague_is_right")
    upwind = runtime.retrieve("fire_pm25_corr_upwind")
    if verdict is None or upwind is None:
        return ValidatorResult(False, "colleague_is_right, fire_pm25_corr_upwind not set",
                               variables_not_set=True)
    gt = _corrs()
    errors = []
    if not is_finite_number(upwind):
        errors.append(f"fire_pm25_corr_upwind={upwind!r} is not a number")
    elif not reports_as(upwind, gt["corr_upwind"], decimals=2):
        errors.append(f"fire_pm25_corr_upwind={upwind}, expected ~{gt['corr_upwind']:.2f}")
    if not _bool_ok(verdict, False):
        errors.append(f"colleague_is_right={verdict!r}, expected False")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: the upwind correlation is {gt['corr_upwind']:.2f}, "
                                 "so the colleague is not right")


tools = []
variables = [
    Variable("days_compared", None,
             "Store how many days the correlation in fire_pm25_corr_all rests "
             "on, as an integer."),
    Variable("fire_pm25_corr_all", None,
             "Store the correlation between the daily count of satellite fire "
             "detections within 300 km of Beijing and Beijing's daily mean "
             "PM2.5 over October-November of 2020 to 2025, as a float, 2 "
             "decimal places. Use only days with a detection record; an absent "
             "day is not a zero."),
    Variable("fire_pm25_corr_upwind", None,
             "Store the correlation between the daily count of detections the "
             "wind could have carried to the city and the same daily PM2.5, as "
             "a float, 2 decimal places."),
    Variable("fire_pm25_corr_sign_all", None,
             "Store the sign of the correlation in fire_pm25_corr_all, as one "
             "of exactly these strings: 'positive', 'negative'."),
    Variable("fires_shown_not_to_matter", None,
             "Store True if that correlation shows that regional fires do not "
             "contribute to Beijing's autumn PM2.5, else False."),
    Variable("colleague_is_right", None,
             "Store True if the colleague is right that the sign settles it, "
             "else False."),
]
validators = {
    "validate_fire_corr_all": validate_fire_corr_all,
    "validate_fire_corr_upwind": validate_fire_corr_upwind,
}
