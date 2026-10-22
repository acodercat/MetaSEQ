"""Difficulty upgrade — beijing_aerosol_compositional_closure (2026-10-06).

Compositional closure and positive-record Aitchison variation.
Professional consequence: Prevent source-competition or common-source claims drawn from a constrained composition.
Plausible wrong reading: A negative Pearson share correlation is not source competition; adding an arbitrary pseudocount changes the logratio estimand and retaining zero records changes the cohort.

Source concept: https://academic.oup.com/jrsssb/article/44/2/139/7027742
The paper supports the concept, not these dataset-specific answers. This case
uses its stated data, time conventions and statistical target; no causal or
surface-emission claim is inferred from a column or conditional association.

Independent raw-data results frozen before authoring the advanced helper:
{
  "dust_bc_amount_r": 0.05601225174140442,
  "dust_bc_share_r": -0.5085017655007197,
  "composition_records": 17534,
  "dust_bc_logratio_variance": 4.068795943243728,
  "positive_logratio_records": 17531
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

import itertools

import numpy as np

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_YEARS = (2020, 2025)
_SPECIES = (
    "dust_aod550",
    "black_carbon_aod550",
    "organic_matter_aod550",
    "sulphate_aod550",
    "sea_salt_aod550",
)


def _records() -> pd.DataFrame:
    cams = pd.read_csv(DATA_DIR / "aerosol_cams.csv")
    return cams[cams["year"].between(*_YEARS)]


POSITIVE = "positive"
NEGATIVE = "negative"


def _signs() -> dict:
    """The dust-black carbon signs, asserted across Pearson and Spearman, the
    3-hourly and daily bases, and both denominators for the shares (+0.056,
    +0.32, +0.045, +0.41 as amounts; -0.51, -0.48, -0.48, -0.51 as shares)."""
    rec = _records()
    daily = rec.groupby(["year", "month", "day"]).mean(numeric_only=True)
    amount_signs, share_signs = set(), set()
    for frame in (rec, daily):
        dust, bc = frame["dust_aod550"], frame["black_carbon_aod550"]
        for method in ("pearson", "spearman"):
            amount_signs.add(POSITIVE if dust.corr(bc, method=method) > 0 else NEGATIVE)
        # Three 3-hourly records carry a dust optical depth of exactly zero;
        # the log route is taken over the positive records.
        positive = (dust > 0) & (bc > 0)
        amount_signs.add(POSITIVE if np.log(dust[positive]).corr(np.log(bc[positive])) > 0 else NEGATIVE)
        for denominator in (frame["total_aod550"], frame[list(_SPECIES)].sum(axis=1)):
            share_signs.add(POSITIVE if (dust / denominator).corr(bc / denominator) > 0 else NEGATIVE)
    if len(amount_signs) != 1 or len(share_signs) != 1:
        raise RuntimeError(f"a sign is not invariant: amounts {amount_signs}, shares {share_signs}")
    return {"dust_bc_amount_sign": amount_signs.pop(), "dust_bc_share_sign": share_signs.pop(),
            # A judgement, not a computation: shares of one total cannot show
            # displacement, and the amounts are nearly independent.
            "colleague_reading_supported": False}


def _correlations() -> dict:
    rec = _records()
    amounts = rec[list(_SPECIES)]
    shares = amounts.div(rec["total_aod550"], axis=0)

    def negatives(frame: pd.DataFrame) -> int:
        return sum(
            1
            for a, b in itertools.combinations(_SPECIES, 2)
            if frame[a].corr(frame[b]) < 0
        )

    return {
        "records_used": int(len(rec)),
        "dust_bc_amount_r": float(
            amounts["dust_aod550"].corr(amounts["black_carbon_aod550"])
        ),
        "dust_bc_share_r": float(
            shares["dust_aod550"].corr(shares["black_carbon_aod550"])
        ),
        "negative_amount_pairs": negatives(amounts),
        "negative_share_pairs": negatives(shares),
    }


def _collect(runtime, names):
    got = {}
    for name in names:
        val = runtime.retrieve(name)
        if val is None:
            return None, ValidatorResult(
                False, f"{name} not set", variables_not_set=True
            )
        if not is_finite_number(val):
            return None, ValidatorResult(False, f"{name}={val!r} is not a number")
        got[name] = val
    return got, None


def _check(runtime, names, tolerances) -> ValidatorResult:
    got, failure = _collect(runtime, names)
    if failure is not None:
        return failure

    gt = _correlations()

    def show(value) -> str:
        # The counts are integers and the correlations are not; one format
        # string for both printed `records_used 17534.00000`.
        return f"{value}" if isinstance(value, int) else f"{value:.5f}"

    errors = [
        f"{name}={got[name]}, expected {show(gt[name])}"
        for name in names
        if not compare_numeric(got[name], gt[name], tolerance=tolerances[name])
    ]
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True, "correct: " + ", ".join(f"{n} {show(gt[n])}" for n in names)
    )


def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_amount_vs_share(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "dust_bc_amount_sign": runtime.retrieve("dust_bc_amount_sign"),
        "dust_bc_share_sign": runtime.retrieve("dust_bc_share_sign"),
        "colleague_reading_supported": runtime.retrieve("colleague_reading_supported"),
    }
    missing = [n for n, v in got.items() if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _signs()
    errors = []
    for name in ["dust_bc_amount_sign", "dust_bc_share_sign"]:
        if str(got[name]).strip().lower() != gt[name]:
            errors.append(f"{name}={got[name]!r}, expected {gt[name]!r}")
    if not _bool_ok(got["colleague_reading_supported"], gt["colleague_reading_supported"]):
        errors.append(f"colleague_reading_supported={got['colleague_reading_supported']!r}, expected False")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: amounts {gt['dust_bc_amount_sign']}, shares "
                                 f"{gt['dust_bc_share_sign']}; the reading is not supported")


def validate_pair_signs(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check(
        runtime,
        ("negative_amount_pairs", "negative_share_pairs"),
        {"negative_amount_pairs": 0, "negative_share_pairs": 0},
    )


tools = []
variables = [
    Variable("dust_bc_amount_sign", None,
             "Store the sign of the correlation between mineral dust and black "
             "carbon over Beijing as amounts — their optical depths — over 2020 "
             "through 2025, as one of exactly these strings: 'positive', "
             "'negative'."),
    Variable("dust_bc_share_sign", None,
             "Store the sign of the correlation between the same two species "
             "expressed as shares of the total, as 'positive' or 'negative'."),
    Variable("colleague_reading_supported", None,
             "Store True if the pair of figures supports the colleague's reading "
             "that the two source types displace one another, else False."),
    Variable(
        "negative_amount_pairs",
        None,
        "Store the number of species pairs whose optical depths correlate "
        "negatively as an integer — Pearson on the composition's native "
        "3-hourly records, no resampling.",
    ),
    Variable(
        "negative_share_pairs",
        None,
        "Store the number of species pairs whose shares of each record's "
        "total_aod550 correlate negatively as an integer.",
    ),
    Variable('dust_bc_amount_r', None, 'Store the Pearson correlation between dust and black-carbon column optical depths over the native three-hourly records in 2020-2025, to 3 decimal places.'),
    Variable('dust_bc_share_r', None, "Store the Pearson correlation between those two species' shares of the reported total column optical depth on the same records, to 3 decimal places. Recompute both shares from species AOD divided by total_aod550; do not use the pre-rounded dust_fraction field or round intermediate shares."),
    Variable('composition_records', None, 'Store the exact integer number of native aerosol records within 2020-2025 used for the amount/share comparison, without daily resampling.'),
    Variable('dust_bc_logratio_variance', None, 'Store the Aitchison variation for the dust/black-carbon pair, the sample variance of their natural logratio, to 3 decimal places. Use only native records in 2020-2025 where both optical depths are strictly positive, with ddof=1 and no replacement of reported zeros.'),
    Variable('positive_logratio_records', None, 'Store the exact integer number of strictly positive dust/black-carbon record pairs used for that logratio variance.'),
]

# Difficulty upgrade 2026-10-06: older docstring magnitudes describe the
# earlier scoring surface. Added metrics below are recomputed from source data.
# Their single declared decimal report is checked by reports_as; counts are
# exact. The independent raw-data maps were frozen before these helpers.

def _advanced_metrics():
    rec = _records()
    dust, bc = rec["dust_aod550"], rec["black_carbon_aod550"]
    positive = (dust > 0) & (bc > 0)
    logratio = np.log(dust[positive])-np.log(bc[positive])
    return {"dust_bc_amount_r": float(dust.corr(bc)),
            "dust_bc_share_r": float((dust/rec["total_aod550"]).corr(bc/rec["total_aod550"])),
            "composition_records": len(rec),
            "dust_bc_logratio_variance": float(logratio.var(ddof=1)),
            "positive_logratio_records": int(positive.sum())}







def validate_harder_turn_1(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "dust_bc_amount_sign": runtime.retrieve("dust_bc_amount_sign"),
        "dust_bc_share_sign": runtime.retrieve("dust_bc_share_sign"),
        "colleague_reading_supported": runtime.retrieve("colleague_reading_supported"),
        "dust_bc_amount_r": runtime.retrieve("dust_bc_amount_r"),
        "dust_bc_share_r": runtime.retrieve("dust_bc_share_r"),
        "composition_records": runtime.retrieve("composition_records"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_amount_vs_share(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["dust_bc_amount_r"]) or not reports_as(got["dust_bc_amount_r"], gt["dust_bc_amount_r"], decimals=3):
        errors.append(f"dust_bc_amount_r={got["dust_bc_amount_r"]!r}, expected {gt["dust_bc_amount_r"]!r}")
    if not is_finite_number(got["dust_bc_share_r"]) or not reports_as(got["dust_bc_share_r"], gt["dust_bc_share_r"], decimals=3):
        errors.append(f"dust_bc_share_r={got["dust_bc_share_r"]!r}, expected {gt["dust_bc_share_r"]!r}")
    if not is_finite_number(got["composition_records"]) or not compare_numeric(got["composition_records"], gt["composition_records"], tolerance=0):
        errors.append(f"composition_records={got["composition_records"]!r}, expected {gt["composition_records"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


def validate_harder_turn_2(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "negative_amount_pairs": runtime.retrieve("negative_amount_pairs"),
        "negative_share_pairs": runtime.retrieve("negative_share_pairs"),
        "dust_bc_logratio_variance": runtime.retrieve("dust_bc_logratio_variance"),
        "positive_logratio_records": runtime.retrieve("positive_logratio_records"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_pair_signs(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["dust_bc_logratio_variance"]) or not reports_as(got["dust_bc_logratio_variance"], gt["dust_bc_logratio_variance"], decimals=3):
        errors.append(f"dust_bc_logratio_variance={got["dust_bc_logratio_variance"]!r}, expected {gt["dust_bc_logratio_variance"]!r}")
    if not is_finite_number(got["positive_logratio_records"]) or not compare_numeric(got["positive_logratio_records"], gt["positive_logratio_records"], tolerance=0):
        errors.append(f"positive_logratio_records={got["positive_logratio_records"]!r}, expected {gt["positive_logratio_records"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


validators = {
    "validate_amount_vs_share": validate_amount_vs_share,
    "validate_pair_signs": validate_pair_signs,
    "validate_harder_turn_2": validate_harder_turn_2,
    "validate_harder_turn_1": validate_harder_turn_1,
}
