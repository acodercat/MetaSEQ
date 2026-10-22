"""Difficulty upgrade — beijing_forecast_skill_floor (2026-10-06).

Forecast reference skill versus high-pollution warning misses.
Professional consequence: Decide whether the better annual-MAE reference is adequate for episode warnings.
Plausible wrong reading: A low annual MAE does not imply good threshold detection; dropping calendar predecessors or training on the target year changes the evaluation.

Source concept: https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/jcffbz/201309/W020250407408679440652.pdf
The paper supports the concept, not these dataset-specific answers. This case
uses its stated data, time conventions and statistical target; no causal or
surface-emission claim is inferred from a column or conditional association.

Independent raw-data results frozen before authoring the advanced helper:
{
  "episode_persistence_mae": 39.51206947798604,
  "episode_climatology_mae": 65.89269074567707,
  "episode_days": 43,
  "persistence_missed_episode_days": 22
}

Numerical answers use the decimal places declared on their variables and
reports_as; counts use tolerance zero and finite-number guards. This excludes
adjacent reported answers, not just gross errors. All sample definitions and
units are visible. Author-selected analysis recipes are marked execution in
the scenario, and are not counted as autonomous method discovery.

The earlier module/validator remains for its original outputs; the current
scenario calls the extended validator requiring those and the added evidence.
The pre-upgrade content is archived in .codex-review/difficulty_20261006/before.
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_TARGET_YEAR = 2023
_CLIM_YEARS = (2020, 2022)


PERSISTENCE = "persistence"
CLIMATOLOGY = "climatology"


def _daily(pooled: bool) -> pd.Series:
    aq = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Hour h is the hour ending at h:00, so a day is its labels 1-23 plus
    # label 0 of the next date.
    stamps = pd.to_datetime(aq[["year", "month", "day", "hour"]])
    aq["date"] = (stamps - pd.Timedelta(hours=1)).dt.normalize()
    obs = aq.dropna(subset=["PM2.5"])
    if pooled:
        return obs.groupby("date")["PM2.5"].mean().sort_index()
    hourly = obs.groupby(["date", "hour"])["PM2.5"].mean()
    return hourly.groupby(level=0).mean().sort_index()


def _errors(daily: pd.Series, full_year: bool, clim_years: tuple) -> dict:
    target = daily[daily.index.year == _TARGET_YEAR]
    persistence = daily.shift(1).reindex(target.index)
    if not full_year:
        persistence = persistence.iloc[1:]
        target = target.iloc[1:]
    train = daily[(daily.index.year >= clim_years[0]) & (daily.index.year <= clim_years[1])]
    monthly = train.groupby(train.index.month).mean()
    climatology = pd.Series(target.index.month.map(monthly), index=target.index)
    return {"persistence": float((target - persistence).abs().mean()),
            "climatology": float((target - climatology).abs().mean())}


def _scores() -> dict:
    """The harder reference and its error to the nearest whole ug/m3, asserted
    across the daily recipe (hourly means first or pooled), the 1 January
    predecessor (365 or 364 days scored) and the climatology window
    (2020-2022 or 2021-2022): persistence 18.89 to 18.93 against climatology
    22.37 to 22.42. Whole units rather than one decimal because the
    station-first and city-point routes (18.87, 19.07) fall either side of
    18.9."""
    table = {}
    for pooled in (False, True):
        daily = _daily(pooled)
        for full_year in (True, False):
            for clim_years in (_CLIM_YEARS, (2021, 2022)):
                e = _errors(daily, full_year, clim_years)
                harder = PERSISTENCE if e["persistence"] < e["climatology"] else CLIMATOLOGY
                table[(pooled, full_year, clim_years)] = (harder, int(round(min(e.values()))))
    verdicts = set(table.values())
    if len(verdicts) != 1:
        raise RuntimeError(f"the reference bar is not invariant: {table}")
    harder, bar = verdicts.pop()
    return {"harder_reference": harder, "bar_mae": bar}


def validate_skill_floor(response: str, runtime, turn: Turn) -> ValidatorResult:
    harder = runtime.retrieve("harder_reference")
    bar = runtime.retrieve("bar_mae")
    missing = [n for n, v in (("harder_reference", harder), ("bar_mae", bar)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    if not is_finite_number(bar):
        return ValidatorResult(False, f"bar_mae={bar!r} is not a number")
    gt = _scores()
    errors = []
    if str(harder).strip().lower() != gt["harder_reference"]:
        errors.append(f"harder_reference={harder!r}, expected {gt['harder_reference']!r}")
    if int(round(float(bar))) != gt["bar_mae"]:
        errors.append(f"bar_mae={bar}, expected ~{gt['bar_mae']} ug/m3")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: {gt['harder_reference']} sets the bar at about {gt['bar_mae']} ug/m3")


tools = []
variables = [
    Variable("harder_reference", None,
             "Store which of the two standard reference forecasts sets the "
             "harder bar for a daily PM2.5 forecast of Beijing over 2023, as one "
             f"of exactly these strings: '{PERSISTENCE}' (yesterday's observed "
             f"value carried forward), '{CLIMATOLOGY}' (the calendar month's mean "
             "over the earlier years of the record). The bar is the reference's "
             "mean absolute error over the days of 2023, and the harder bar is "
             "the LOWER error — the reference a forecast has to beat before it "
             "adds anything."),
    Variable("bar_mae", None,
             "Store that harder reference's mean absolute error over 2023, in "
             "ug/m3 to the nearest whole unit."),
    Variable('episode_persistence_mae', None, "Store persistence's MAE restricted to 2023 observed daily network PM2.5 above 75 µg/m³, in µg/m³ to 2 decimal places. The prediction is the preceding calendar day's daily network mean, reaching into 2022 for the first forecast if necessary."),
    Variable('episode_climatology_mae', None, 'Store MAE on exactly those episode days for the calendar-month daily-PM2.5 climatology trained on 2020-2022 only, in µg/m³ to 2 decimal places.'),
    Variable('episode_days', None, 'Store the exact integer number of 2023 network days with observed daily PM2.5 strictly above 75 µg/m³. This is a reference episode screen, not an official station-level compliance determination.'),
    Variable('persistence_missed_episode_days', None, 'Store the exact integer count of those observed episode days for which the persistence forecast was at or below 75 µg/m³.'),
]

# Difficulty upgrade 2026-10-06: older docstring magnitudes describe the
# earlier scoring surface. Added metrics below are recomputed from source data.
# Their single declared decimal report is checked by reports_as; counts are
# exact. The independent raw-data maps were frozen before these helpers.

def _advanced_metrics():
    daily = _daily(pooled=False)
    target = daily[daily.index.year == 2023]
    prior = daily.reindex(target.index-pd.Timedelta(days=1))
    prior.index = target.index
    monthly = daily.loc["2020":"2022"].groupby(daily.loc["2020":"2022"].index.month).mean()
    clim = pd.Series(target.index.month.map(monthly), index=target.index)
    episode = target > 75
    if prior[episode].isna().any():
        raise LookupError("An episode day lacks its calendar-day predecessor")
    return {"episode_persistence_mae": float((target[episode]-prior[episode]).abs().mean()),
            "episode_climatology_mae": float((target[episode]-clim[episode]).abs().mean()),
            "episode_days": int(episode.sum()),
            "persistence_missed_episode_days": int((prior[episode] <= 75).sum())}






def validate_harder_turn_1(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "harder_reference": runtime.retrieve("harder_reference"),
        "bar_mae": runtime.retrieve("bar_mae"),
        "episode_persistence_mae": runtime.retrieve("episode_persistence_mae"),
        "episode_climatology_mae": runtime.retrieve("episode_climatology_mae"),
        "episode_days": runtime.retrieve("episode_days"),
        "persistence_missed_episode_days": runtime.retrieve("persistence_missed_episode_days"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_skill_floor(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["episode_persistence_mae"]) or not reports_as(got["episode_persistence_mae"], gt["episode_persistence_mae"], decimals=2):
        errors.append(f"episode_persistence_mae={got["episode_persistence_mae"]!r}, expected {gt["episode_persistence_mae"]!r}")
    if not is_finite_number(got["episode_climatology_mae"]) or not reports_as(got["episode_climatology_mae"], gt["episode_climatology_mae"], decimals=2):
        errors.append(f"episode_climatology_mae={got["episode_climatology_mae"]!r}, expected {gt["episode_climatology_mae"]!r}")
    if not is_finite_number(got["episode_days"]) or not compare_numeric(got["episode_days"], gt["episode_days"], tolerance=0):
        errors.append(f"episode_days={got["episode_days"]!r}, expected {gt["episode_days"]!r}")
    if not is_finite_number(got["persistence_missed_episode_days"]) or not compare_numeric(got["persistence_missed_episode_days"], gt["persistence_missed_episode_days"], tolerance=0):
        errors.append(f"persistence_missed_episode_days={got["persistence_missed_episode_days"]!r}, expected {gt["persistence_missed_episode_days"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


validators = {
    "validate_skill_floor": validate_skill_floor,
    "validate_harder_turn_1": validate_harder_turn_1,
}
