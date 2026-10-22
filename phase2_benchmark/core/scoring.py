"""Response Quality: criteria, per-judge scores, aggregation, inter-judge agreement.

A `Criteria` is the pre-registered scoring sheet (ordinal dimensions with
anchored 1-5 levels). A `JudgeScore` is one LLM judge's scoring of one
sample. An `AggregatedScore` is the per-sample aggregate across N judges,
with flagging for follow-up review when judges disagree or scores are extreme.

Inter-judge agreement is reported via Krippendorff's α (interval metric),
implemented directly from Krippendorff (2004) / Hayes & Krippendorff (2007)
with a hand-derived 4-unit textbook case test (tests/test_scoring.py).

The Claim Coverage channel lives in `core/claims.py` and is run
independently by `scripts/verify_claims.py`.
"""

import json
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union


# ---------------------------------------------------------------------------
# Criteria definition (pre-registered, immutable)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Dimension:
    """One ordinal scoring dimension on a 1-5 scale."""
    id: str
    name: str
    description: str
    anchors: Dict[int, str]          # {1..5: anchored description}, all five required
    weight: float = 1.0

    def __post_init__(self) -> None:
        missing = [k for k in (1, 2, 3, 4, 5) if k not in self.anchors]
        if missing:
            raise ValueError(f"Dimension('{self.id}'): missing anchors for {missing}; 1..5 all required.")
        extra = [k for k in self.anchors if k not in (1, 2, 3, 4, 5)]
        if extra:
            raise ValueError(f"Dimension('{self.id}'): anchors outside 1..5 not allowed, got {extra}.")
        if self.weight <= 0:
            raise ValueError(f"Dimension('{self.id}'): weight must be positive, got {self.weight}.")


@dataclass(frozen=True)
class Criteria:
    """Pre-registered scoring criteria. Single global instance loaded from JSON."""
    dimensions: List[Dimension]

    def __post_init__(self) -> None:
        if not self.dimensions:
            raise ValueError("Criteria: at least one Dimension required.")
        ids = [d.id for d in self.dimensions]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Criteria: duplicate dimension ids: {ids}.")

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "Criteria":
        """Load criteria from a JSON file. Anchor keys are converted str -> int."""
        data = json.loads(Path(path).read_text())
        return cls(
            dimensions=[
                Dimension(
                    id=d["id"],
                    name=d["name"],
                    description=d["description"],
                    anchors={int(k): v for k, v in d["anchors"].items()},
                    weight=float(d.get("weight", 1.0)),
                )
                for d in data["dimensions"]
            ],
        )


# ---------------------------------------------------------------------------
# Score records (per-judge and aggregated)
# ---------------------------------------------------------------------------

@dataclass
class JudgeScore:
    """One judge's Response Quality of one (scenario, conversation, turn) sample.

    `judge_id` encodes identity unambiguously, e.g. "llm:claude-opus-4-7".
    """
    judge_id: str
    scores: Dict[str, int]                          # {dimension_id -> 1..5}
    justifications: Dict[str, str] = field(default_factory=dict)
    overall_comment: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JudgeScore":
        return cls(
            judge_id=data["judge_id"],
            scores={k: int(v) for k, v in data["scores"].items()},
            justifications=dict(data.get("justifications", {})),
            overall_comment=data.get("overall_comment", ""),
            timestamp=data["timestamp"],
        )


@dataclass
class AggregatedScore:
    """Per-sample aggregate of N judges' Response Quality.

    Raw scores preserve the judges' independent per-dimension judgment;
    capped scores apply the process-dependency rule deterministically in
    aggregation (see `apply_process_cap`). The headline `overall_score`
    uses CAPPED values (fair ranking — upstream errors can't be papered
    over by fluent downstream prose). `overall_score_raw` and `score_mean`
    preserve the uncapped signal for diagnostic analysis (which of the
    four process steps actually failed independently).
    """
    sample_id: str                                  # "{benchmark}/{conv_id}/{turn_idx}"
    n_judges: int
    score_mean: Dict[str, float]                    # RAW per-dim mean across judges
    score_median: Dict[str, float]
    score_std: Dict[str, float]                     # per-sample dispersion (judge disagreement)
    score_mean_capped: Dict[str, float]             # POST-CAP per-dim mean
    overall_score: float                            # weighted mean over score_mean_capped (ranking)
    overall_score_raw: float                        # weighted mean over score_mean (diagnosis)
    flagged_for_review: bool = False
    flag_reasons: List[str] = field(default_factory=list)
    judges: List[JudgeScore] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AggregatedScore":
        # Strict: missing fields raise KeyError. Silently substituting
        # raw values for missing capped values would mix pre-cap and
        # post-cap numbers in downstream statistics.
        return cls(
            sample_id=data["sample_id"],
            n_judges=int(data["n_judges"]),
            score_mean={k: float(v) for k, v in data["score_mean"].items()},
            score_median={k: float(v) for k, v in data["score_median"].items()},
            score_std={k: float(v) for k, v in data["score_std"].items()},
            score_mean_capped={k: float(v) for k, v in data["score_mean_capped"].items()},
            overall_score=float(data["overall_score"]),
            overall_score_raw=float(data["overall_score_raw"]),
            flagged_for_review=bool(data.get("flagged_for_review", False)),
            flag_reasons=list(data.get("flag_reasons", [])),
            judges=[JudgeScore.from_dict(r) for r in data.get("judges", [])],
        )


# ---------------------------------------------------------------------------
# Krippendorff's alpha (any number of judges, missing data allowed)
# ---------------------------------------------------------------------------

def krippendorff_alpha(
    scores: Sequence[Sequence[Optional[float]]],
    metric: str = "interval",
) -> float:
    """Krippendorff's alpha via the coincidence-matrix algorithm.

    `scores[u]` is the list of ratings for unit u; `None` entries indicate
    missing ratings (units with <2 non-None ratings are dropped). `metric`
    is "interval" (squared difference, appropriate for equally-anchored
    1-5 ordinal) or "nominal" (mismatch = 1). Returns 1.0 if all ratings
    identical (D_e = 0 -> defined as perfect agreement by convention).
    """
    units = [[v for v in u if v is not None] for u in scores]
    units = [u for u in units if len(u) >= 2]
    if not units:
        raise ValueError("no units with >=2 ratings")

    all_values = sorted({v for u in units for v in u})
    idx = {v: i for i, v in enumerate(all_values)}
    K = len(all_values)

    O = [[0.0] * K for _ in range(K)]
    for u in units:
        n_u = len(u)
        cnt = Counter(u)
        for c, n_c in cnt.items():
            for k_, n_k in cnt.items():
                contrib = n_c * (n_k - 1) / (n_u - 1) if c == k_ else n_c * n_k / (n_u - 1)
                O[idx[c]][idx[k_]] += contrib

    n_c = [sum(O[i]) for i in range(K)]
    n_total = sum(n_c)

    if metric == "nominal":
        def delta2(c_val: float, k_val: float) -> float:
            return 0.0 if c_val == k_val else 1.0
    elif metric == "interval":
        def delta2(c_val: float, k_val: float) -> float:
            return (float(c_val) - float(k_val)) ** 2
    else:
        raise ValueError(f"unknown metric: {metric!r}; expected 'nominal' or 'interval'")

    D_o = sum(O[i][j] * delta2(all_values[i], all_values[j])
              for i in range(K) for j in range(K)) / n_total

    D_e_num = sum(n_c[i] * n_c[j] * delta2(all_values[i], all_values[j])
                  for i in range(K) for j in range(K))
    D_e = D_e_num / (n_total * (n_total - 1))

    if D_e == 0:
        return 1.0
    return 1.0 - D_o / D_e


# ---------------------------------------------------------------------------
# Process-dependency cap (deterministic post-hoc; see paper/scoring/design_notes.md)
# ---------------------------------------------------------------------------

PROCESS_CAP_THRESHOLD = 2   # raw score at or below this in a preceding dim triggers the cap
PROCESS_CAP_VALUE = 3       # subsequent dims are capped at this value


def apply_process_cap(
    raw_scores: Dict[str, int],
    dimensions: List["Dimension"],
    cap_threshold: int = PROCESS_CAP_THRESHOLD,
    cap_value: int = PROCESS_CAP_VALUE,
) -> Dict[str, int]:
    """Per-judge process-dependency cap.

    Dimensions form a chain in their declared order. If any **preceding**
    dimension has raw score <= `cap_threshold`, every subsequent
    dimension is capped at `cap_value` (min(raw, cap_value)). The
    triggering dimension itself is not modified. The rule is transitive:
    a low score anywhere upstream caps everything downstream.

    `cap_threshold` and `cap_value` are parameters (default to the
    module constants) so tests can exercise boundary cases without
    monkey-patching globals.

    Examples (with thresholds 2 / 3):
      [5, 5, 5, 5] -> [5, 5, 5, 5]  (no trigger)
      [2, 5, 5, 5] -> [2, 3, 3, 3]  (framing low caps approach/interp/synth)
      [4, 2, 5, 5] -> [4, 2, 3, 3]  (approach is itself low; interp/synth capped)
      [3, 2, 4, 5] -> [3, 2, 3, 3]  (interp cap = min(4, 3) = 3)

    Raises ValueError if `raw_scores` is missing a dimension key (a judge
    that returned an incomplete payload should be rejected upstream in
    `parse_judge_response`, not silently treated as having no scores), or
    if `cap_value <= cap_threshold` (a degenerate parameterization that
    would cap dimensions to a value already considered "low" — almost
    certainly a configuration bug).
    """
    if cap_value <= cap_threshold:
        raise ValueError(
            f"apply_process_cap: cap_value ({cap_value}) must exceed cap_threshold "
            f"({cap_threshold}); otherwise capped scores would themselves trigger "
            "the cap and the rule becomes ill-defined"
        )
    missing = [d.id for d in dimensions if d.id not in raw_scores]
    if missing:
        raise ValueError(
            f"apply_process_cap: raw_scores missing dimensions {missing}; "
            "every judge must score every dimension before the cap is applied"
        )
    capped = dict(raw_scores)
    saw_low = False
    for dim in dimensions:
        if saw_low:
            capped[dim.id] = min(capped[dim.id], cap_value)
        if raw_scores[dim.id] <= cap_threshold:
            saw_low = True
    return capped


# ---------------------------------------------------------------------------
# Aggregation across judges for one sample
# ---------------------------------------------------------------------------

# Flagging thresholds for the per-sample review queue. These are NOT
# pre-registered scoring parameters — they only decide which samples are
# surfaced for human spot-check. The aggregate numbers (score_mean,
# overall_score, etc.) are unchanged by these. Override per-run via the
# `--flag-*` CLI flags on `scripts/score_responses.py` for sensitivity
# analysis. Justifications below assume a 1-5 ordinal scale with weighted
# overall and 3+ judges per sample.
SCORE_STD_FLAG = 1.0
"""Per-dim std across judges that triggers a high-disagreement flag.

On a 5-point scale with N≥3 judges, std=1.0 corresponds to one judge
two anchors off from the rest (e.g., [2, 4, 4] → std≈0.94). Below ~0.7
trips on noise; above ~1.4 misses real splits."""

EXTREME_LOW_FLAG = 2.0
"""Raw overall ≤ this flags as extreme low. Weighted-mean 2.0 means the
panel agrees the response is at or below the "missing a critical
constraint" anchor on most dimensions — typically empty / off-topic
responses or validator-passed-but-unrelated writeups."""

EXTREME_HIGH_FLAG = 4.5
"""Raw overall ≥ this flags as extreme high. Catches responses that look
too good — usually anchor-wording leakage (response echoes anchor 5
phrasing verbatim). Set above 4.0 so genuinely strong responses aren't
flagged just for being good."""


def aggregate_scores(
    sample_id: str,
    scores: List[JudgeScore],
    criteria: Criteria,
    score_std_flag: float = SCORE_STD_FLAG,
    extreme_low: float = EXTREME_LOW_FLAG,
    extreme_high: float = EXTREME_HIGH_FLAG,
    cap_threshold: int = PROCESS_CAP_THRESHOLD,
    cap_value: int = PROCESS_CAP_VALUE,
) -> AggregatedScore:
    """Aggregate per-judge Response Quality.

    Cap is applied **per judge** before averaging (each judge's view of a
    single response carries its own logical-chain consistency); aggregate
    `score_mean_capped` and `overall_score` reflect those capped values.
    Flagging uses **raw** values (independent judge signal — disagreement
    and extreme low/high should reflect actual judgment, not post-cap
    coordination). Threshold defaults are documented above the module
    constants `*_DEFAULT`; override per run for sensitivity studies.

    `cap_threshold` / `cap_value` default to the pre-registered module
    constants and should NEVER differ from those for headline scoring.
    Overrides are exposed only for sensitivity-analysis runs that report
    the (2/3) → {(1/3), (3/4), ...} ablation table alongside headline.
    """
    if not scores:
        raise ValueError(f"aggregate_scores({sample_id!r}): empty score list")

    n = len(scores)
    # Per-judge cap: the logical chain "upstream rot → downstream cannot be
    # sound" is a property of one judge's read, not a cross-judge statistic.
    capped_per_judge = [
        apply_process_cap(s.scores, criteria.dimensions,
                          cap_threshold=cap_threshold, cap_value=cap_value)
        for s in scores
    ]

    score_mean: Dict[str, float] = {}
    score_median: Dict[str, float] = {}
    score_std: Dict[str, float] = {}
    score_mean_capped: Dict[str, float] = {}

    # Per-sample dispersion (std) is the only meaningful within-sample agreement
    # signal. Krippendorff's alpha is a CORPUS statistic (computed once across
    # ALL samples × judges via `compute_corpus_agreement`); computing alpha per
    # sample with one unit gives a degenerate value and was removed.
    for dim in criteria.dimensions:
        raw_vals = [s.scores[dim.id] for s in scores]
        capped_vals = [c[dim.id] for c in capped_per_judge]
        score_mean[dim.id] = sum(raw_vals) / n
        score_median[dim.id] = float(statistics.median(raw_vals))
        score_std[dim.id] = float(statistics.pstdev(raw_vals)) if n > 1 else 0.0
        score_mean_capped[dim.id] = sum(capped_vals) / n

    total_w = sum(d.weight for d in criteria.dimensions)
    overall_capped = sum(d.weight * score_mean_capped[d.id] for d in criteria.dimensions) / total_w
    overall_raw = sum(d.weight * score_mean[d.id] for d in criteria.dimensions) / total_w

    # Flagging uses RAW signal (D5).
    flag_reasons: List[str] = []
    for dim in criteria.dimensions:
        if score_std[dim.id] >= score_std_flag:
            flag_reasons.append(f"high_disagreement:{dim.id}(std={score_std[dim.id]:.2f})")
    if overall_raw <= extreme_low:
        flag_reasons.append(f"extreme_low:overall_raw={overall_raw:.2f}<={extreme_low}")
    if overall_raw >= extreme_high:
        flag_reasons.append(f"extreme_high:overall_raw={overall_raw:.2f}>={extreme_high}")

    return AggregatedScore(
        sample_id=sample_id,
        n_judges=n,
        score_mean=score_mean,
        score_median=score_median,
        score_std=score_std,
        score_mean_capped=score_mean_capped,
        overall_score=overall_capped,
        overall_score_raw=overall_raw,
        flagged_for_review=bool(flag_reasons),
        flag_reasons=flag_reasons,
        judges=list(scores),
    )


# ---------------------------------------------------------------------------
# Corpus-level inter-judge agreement
# ---------------------------------------------------------------------------

def _collect_units(
    samples: List[AggregatedScore],
    dim_id: str,
) -> List[List[float]]:
    """Per-dim list of N-rater rating vectors, one entry per sample.

    Samples with fewer than 2 ratings on the dimension are dropped — alpha
    requires at least two coders per unit to estimate observed disagreement.
    """
    units: List[List[float]] = []
    for sample in samples:
        ratings = [float(j.scores[dim_id]) for j in sample.judges if dim_id in j.scores]
        if len(ratings) >= 2:
            units.append(ratings)
    return units


def compute_corpus_agreement(
    samples: List[AggregatedScore],
    criteria: Criteria,
    metric: str = "interval",
) -> Dict[str, float]:
    """Krippendorff's alpha per dimension over ALL samples × judges in the run.

    Each sample contributes one "unit" per dimension: the list of raw scores
    that the panel's judges gave that sample. Pooling across samples is what
    makes alpha statistically meaningful — alpha on a single unit is
    degenerate (no between-unit variability to estimate the chance baseline).

    `metric` is "interval" (default) or "nominal" — interval treats the 1-5
    scale as equally spaced, nominal treats it as bare categories. Use
    `compute_corpus_agreement_both_metrics` to get both in one call as a
    sensitivity check.

    Returns {dim.id -> alpha}; dimensions with no scorable units (zero samples
    or every sample has <2 ratings) map to NaN.
    """
    out: Dict[str, float] = {}
    for dim in criteria.dimensions:
        units = _collect_units(samples, dim.id)
        out[dim.id] = krippendorff_alpha(units, metric=metric) if units else float("nan")
    return out


def compute_corpus_agreement_both_metrics(
    samples: List[AggregatedScore],
    criteria: Criteria,
) -> Dict[str, Dict[str, float]]:
    """Both interval and nominal corpus alphas, side by side per dimension.

    The interval metric is the headline number when the 1-5 anchors are
    intended as roughly equally-spaced bands; the nominal metric treats
    them as bare categories and serves as a robustness floor. Reporting
    both is the literature-standard defence for ordinal LLM-judge data
    (Hayes & Krippendorff 2007; Artstein & Poesio 2008): a large gap
    between the two suggests the equal-spacing assumption is doing more
    work than the anchor descriptions can defend.

    Returns {dim.id -> {"interval": float, "nominal": float}}.
    """
    out: Dict[str, Dict[str, float]] = {}
    for dim in criteria.dimensions:
        units = _collect_units(samples, dim.id)
        if not units:
            out[dim.id] = {"interval": float("nan"), "nominal": float("nan")}
            continue
        out[dim.id] = {
            "interval": krippendorff_alpha(units, metric="interval"),
            "nominal": krippendorff_alpha(units, metric="nominal"),
        }
    return out
