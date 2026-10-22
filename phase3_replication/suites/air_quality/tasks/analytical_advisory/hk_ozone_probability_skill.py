"""hk_ozone_probability_skill — hard baseline.

Decision: Choose an honest probability reference for rare pollution-event warnings.
Source concept: https://www.cawcr.gov.au/projects/verification/Mason/IntegratedVerificationProcedures.pdf
Plausible wrong paths: Calling the no-alert classifier useful because its accuracy is high, replacing the historical reference with the test-year frequency, or calculating skill from rounded scores.

Raw-data values were frozen before authoring in
.codex-review/new_cases_20261006/frozen_answers.json.
Reported answers: {'probability_training_days': 1460, 'probability_test_days': 365, 'observed_ozone_alert_days': 33, 'never_alert_accuracy_pct': 90.96, 'seasonal_brier_score': 0.0875, 'annual_climatology_brier_score': 0.0824, 'never_alert_brier_score': 0.0904, 'seasonal_brier_skill': -0.0622}

Each declared numeric precision rejects adjacent reported answers; all integer
counts use tolerance zero and finite-number guards. Runtime ground truth is
recomputed from the source files/database. No causal judgement is PV-scored.
Author-selected quadrature/cohort conventions make this an execution turn.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

def _ground_truth():
    from sqlalchemy import text
    from domains.hk.db import read_frame
    frame = read_frame(text("""SELECT a.datetime, a.o3 FROM hourly_station_air_quality a
        JOIN air_quality_station s ON s.id=a.station_id
        WHERE s.name_en=:site AND a.datetime>:lo AND a.datetime<=:hi ORDER BY a.datetime"""),
        {"site":"Tap Mun","lo":"2020-12-31 17:00","hi":"2026-01-01"})
    ozone = frame.set_index("datetime").o3.asfreq("h")
    rolling = ozone.rolling(8,min_periods=6).mean()
    daily = rolling.groupby((rolling.index-pd.Timedelta(hours=1)).normalize()).max().loc["2021":"2025"].dropna()
    events = daily.gt(160).astype(float)
    train,test = events.loc["2021":"2024"],events.loc["2025"]
    climatology = train.groupby(train.index.month).mean()
    predicted = climatology.reindex(test.index.month).to_numpy()
    observed = test.to_numpy()
    annual_score = float(np.mean((observed-float(train.mean()))**2))
    seasonal_score = float(np.mean((observed-predicted)**2))
    return dict(probability_training_days=len(train), probability_test_days=len(test), observed_ozone_alert_days=int(test.sum()), never_alert_accuracy_pct=float(100*np.mean(observed==0)), seasonal_brier_score=seasonal_score, annual_climatology_brier_score=annual_score, never_alert_brier_score=float(np.mean(observed**2)), seasonal_brier_skill=float(1-seasonal_score/annual_score))


tools = []
variables = [
    Variable('probability_training_days', None, 'Store the exact integer number of valid Tap Mun daily ozone-alert observations in 2021-2024 used to train both probability references. Define an alert as daily maximum trailing-eight-clock-hour O3 strictly above 160 µg/m³, taking all 24 ending hours with at least six valid hourly readings per window and the domain hour-ending day. Retain days with a valid maximum, with no additional daily coverage rule; absent observations are not no-alert days. This is a fixed diagnostic alert screen, not an AQO compliance assessment.'),
    Variable('probability_test_days', None, 'Store the exact integer number of valid 2025 test days under the same alert definition.'),
    Variable('observed_ozone_alert_days', None, 'Store the exact integer number of observed alert days in that 2025 test cohort.'),
    Variable('never_alert_accuracy_pct', None, 'Store percentage classification accuracy on those test days for always predicting no alert, to 2 decimal places.'),
    Variable('seasonal_brier_score', None, "Store the 2025 Brier score of month-of-year alert probabilities estimated as each month's observed event fraction in 2021-2024, to 4 decimal places. Fit no probability on the test year; use raw unsmoothed fractions and the binary-event, mean squared probability-error Brier convention."),
    Variable('annual_climatology_brier_score', None, 'Store the 2025 Brier score of the single all-training-days alert probability, to 4 decimal places, using the same test days and binary-event convention.'),
    Variable('never_alert_brier_score', None, 'Store the 2025 Brier score for probability zero on every test day, to 4 decimal places.'),
    Variable('seasonal_brier_skill', None, 'Store the monthly-probability Brier skill score against the historical annual-probability reference, to 4 decimal places, calculated from unrounded Brier scores.'),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "probability_training_days": runtime.retrieve("probability_training_days"),
        "probability_test_days": runtime.retrieve("probability_test_days"),
        "observed_ozone_alert_days": runtime.retrieve("observed_ozone_alert_days"),
        "never_alert_accuracy_pct": runtime.retrieve("never_alert_accuracy_pct"),
        "seasonal_brier_score": runtime.retrieve("seasonal_brier_score"),
        "annual_climatology_brier_score": runtime.retrieve("annual_climatology_brier_score"),
        "never_alert_brier_score": runtime.retrieve("never_alert_brier_score"),
        "seasonal_brier_skill": runtime.retrieve("seasonal_brier_skill"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    if not (is_finite_number(got["probability_training_days"]) and compare_numeric(got["probability_training_days"], expected["probability_training_days"], tolerance=0)):
        errors.append("probability_training_days="+repr(got["probability_training_days"])+", expected "+repr(expected["probability_training_days"]))
    if not (is_finite_number(got["probability_test_days"]) and compare_numeric(got["probability_test_days"], expected["probability_test_days"], tolerance=0)):
        errors.append("probability_test_days="+repr(got["probability_test_days"])+", expected "+repr(expected["probability_test_days"]))
    if not (is_finite_number(got["observed_ozone_alert_days"]) and compare_numeric(got["observed_ozone_alert_days"], expected["observed_ozone_alert_days"], tolerance=0)):
        errors.append("observed_ozone_alert_days="+repr(got["observed_ozone_alert_days"])+", expected "+repr(expected["observed_ozone_alert_days"]))
    if not (is_finite_number(got["never_alert_accuracy_pct"]) and reports_as(got["never_alert_accuracy_pct"], expected["never_alert_accuracy_pct"], decimals=2)):
        errors.append("never_alert_accuracy_pct="+repr(got["never_alert_accuracy_pct"])+", expected "+repr(expected["never_alert_accuracy_pct"]))
    if not (is_finite_number(got["seasonal_brier_score"]) and reports_as(got["seasonal_brier_score"], expected["seasonal_brier_score"], decimals=4)):
        errors.append("seasonal_brier_score="+repr(got["seasonal_brier_score"])+", expected "+repr(expected["seasonal_brier_score"]))
    if not (is_finite_number(got["annual_climatology_brier_score"]) and reports_as(got["annual_climatology_brier_score"], expected["annual_climatology_brier_score"], decimals=4)):
        errors.append("annual_climatology_brier_score="+repr(got["annual_climatology_brier_score"])+", expected "+repr(expected["annual_climatology_brier_score"]))
    if not (is_finite_number(got["never_alert_brier_score"]) and reports_as(got["never_alert_brier_score"], expected["never_alert_brier_score"], decimals=4)):
        errors.append("never_alert_brier_score="+repr(got["never_alert_brier_score"])+", expected "+repr(expected["never_alert_brier_score"]))
    if not (is_finite_number(got["seasonal_brier_skill"]) and reports_as(got["seasonal_brier_skill"], expected["seasonal_brier_skill"], decimals=4)):
        errors.append("seasonal_brier_skill="+repr(got["seasonal_brier_skill"])+", expected "+repr(expected["seasonal_brier_skill"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
