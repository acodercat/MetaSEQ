"""The pre-registered primary model (docs/preregistration.md §5), on the frozen outcomes.

    uv run --isolated --no-project --python 3.12 --with bambi==0.21.0 --with pymc==6.3.2 \\
        --with arviz==1.3.0 --with numpy==2.5.3 --with pandas==3.0.6 \\
        python analysis/bayes.py results/report/study_outcomes.csv

bambi and PyMC stay out of the project's environment, whose numerical libraries the
validators run on; this script imports nothing from the lab and reads the outcomes
`analysis.study` wrote. A Bayesian mixed-effects logistic regression on the four core arms'
scored runs with bambi's default weakly informative priors:

    correct ~ decomposition * verification + (1 | task) + (1 | backbone) + (1 | task:backbone)

and with one backbone the backbone terms drop out. Reported on the probability scale, averaged
over the tasks (and, pooled, over the backbones; per backbone, over its tasks): both main
effects, the interaction, H2's test and the core contrasts, as posterior means with 95%
equal-tailed intervals. Written beside the CSV as study_bayes.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import arviz as az
import bambi as bmb
import numpy as np
import pandas as pd
import pymc

# (decomposition, verification)
ARMS = {"single_agent_bare": (0, 0), "single_agent_verified": (0, 1),
        "neuroair_no_verification": (1, 0), "neuroair": (1, 1)}
SEED = 20260929
# Above bambi's default 0.8: with few backbones the backbone variance sits near zero, where
# smaller steps avoid the divergences the default produces.
TARGET_ACCEPT = 0.99


def _estimates(cells: np.ndarray) -> dict[str, np.ndarray]:
    """Draws x 4 cell probabilities (A, B, C, D) -> the reported quantities."""
    a, b, c, d = (cells[:, i] for i in range(len(ARMS)))
    return {
        "verification (main effect)": ((b - a) + (d - c)) / 2,
        "decomposition (main effect)": ((c - a) + (d - b)) / 2,
        "interaction": (d - c) - (b - a),
        "H2: verification − decomposition (= B − C)": b - c,
        "H1 D − A": d - a, "H2a B − A": b - a, "H2b C − A": c - a, "H2c D − B": d - b,
    }


def _fit_one(data: pd.DataFrame, formula: str) -> tuple[dict[str, np.ndarray], dict]:
    """Fit `formula`; the quantities averaged over every (task, backbone) the data holds,
    and the fit's convergence figures."""
    model = bmb.Model(formula, data, family="bernoulli")
    idata = model.fit(draws=2000, tune=2000, chains=4, target_accept=TARGET_ACCEPT,
                      random_seed=SEED, progressbar=False)
    pairs = data[["task", "backbone"]].drop_duplicates().sort_values(["backbone", "task"])
    grid = pd.DataFrame([{"task": row.task, "backbone": row.backbone, "decomposition": d,
                          "verification": v}
                         for row in pairs.itertuples() for d, v in ARMS.values()])
    predicted = model.predict(idata, data=grid, kind="response_params", inplace=False)
    parent = model.family.likelihood.parent
    p = predicted.posterior[parent].stack(sample=("chain", "draw")).transpose("sample", ...)
    cells = p.to_numpy().reshape(p.shape[0], len(pairs), len(ARMS)).mean(axis=1)
    sigmas = [name for name in idata.posterior.data_vars if name.endswith("_sigma")]
    summary = az.summary(idata, var_names=["Intercept", "decomposition", "verification",
                                           "decomposition:verification", *sigmas])
    return _estimates(cells), {
        "formula": formula, "runs": len(data), "r_hat": float(summary.r_hat.max()),
        "ess_bulk": float(summary.ess_bulk.min()), "ess_tail": float(summary.ess_tail.min()),
        "divergent": int(idata.sample_stats["diverging"].sum())}


def fit(outcomes: pd.DataFrame) -> list[tuple[str, dict[str, np.ndarray], dict]]:
    """The pooled model over every backbone (the primary analysis) and, as the
    pre-registration's stratification by backbone, each backbone on its own."""
    data = outcomes[outcomes.arm.isin(list(ARMS)) & (outcomes.status == "scored")].copy()
    data["correct"] = data.passed.astype(str).str.lower().eq("true").astype(int)
    data["decomposition"] = data.arm.map(lambda arm: ARMS[arm][0])
    data["verification"] = data.arm.map(lambda arm: ARMS[arm][1])
    data["backbone"] = data.model
    backbones = sorted(data.backbone.unique())
    single = "correct ~ decomposition * verification + (1|task)"
    fits = []
    if len(backbones) > 1:
        fits.append(("pooled over backbones",
                     *_fit_one(data, single + " + (1|backbone) + (1|task:backbone)")))
    for backbone in backbones:
        fits.append((backbone, *_fit_one(data[data.backbone == backbone], single)))
    return fits


def render(fits: list[tuple[str, dict[str, np.ndarray], dict]]) -> str:
    lines = ["# Primary model (pre-registration §5)", "",
             "Bayesian logistic regressions on the four core arms' scored runs, bambi default"
             f" priors, 4 chains × 2,000 draws (seed {SEED}, target accept {TARGET_ACCEPT})."
             " Probability scale, averaged over the tasks (and backbones) the fit holds.", ""]
    for scope, quantities, diag in fits:
        lines += [f"## {scope}", "", f"`{diag['formula']}`; {diag['runs']} runs. Convergence:"
                  f" max r̂ {diag['r_hat']:.3f}, min bulk ESS {diag['ess_bulk']:,.0f}, min tail"
                  f" ESS {diag['ess_tail']:,.0f}, divergent transitions {diag['divergent']}.", "",
                  "| quantity | posterior mean (pp) | 95% interval (pp) | P(> 0) |",
                  "|---|---|---|---|"]
        for name, draws in quantities.items():
            lo, hi = np.percentile(draws, [2.5, 97.5])
            lines.append(f"| {name} | {100 * draws.mean():+.1f} |"
                         f" [{100 * lo:+.1f}, {100 * hi:+.1f}] | {(draws > 0).mean():.3f} |")
        lines.append("")
    lines += [f"Versions: bambi {bmb.__version__}, PyMC {pymc.__version__}, ArviZ {az.__version__},"
              f" NumPy {np.__version__}, pandas {pd.__version__}.", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    if len(argv) != 1:
        raise SystemExit(__doc__)
    path = Path(argv[0])
    markdown = render(fit(pd.read_csv(path)))
    (path.parent / "study_bayes.md").write_text(markdown, encoding="utf-8")
    print(markdown)


if __name__ == "__main__":
    main(sys.argv[1:])
