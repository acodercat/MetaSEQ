"""Claim Coverage: per-turn claims, per-judge coverage, aggregation.

A `Claim` is a specific knowledge point a turn's response is expected to
address. A `JudgeCoverage` is one LLM judge's true/false verdict on each
claim. An `AggregatedCoverage` is the per-sample aggregate across N judges
with flagging when a required claim is majority-missed.

Claims live in each benchmark's spec JSON (per-turn, not per-module):

    "turns": [{
        "query":     "...",
        "validator": "...",
        "claims": [{"id": "...", "description": "...", "required": true}, ...]
    }]

This module owns only the data structures and aggregation math. The
orchestration script that actually calls the judges is
`scripts/verify_claims.py`; shared infrastructure (judge-pool selection,
result-file traversal) lives in `core/judging.py`.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Claim:
    """A per-turn knowledge point the response is expected to address.

    Required claims that fewer than `coverage_threshold` of judges mark as
    covered flag the sample for review. Optional claims contribute coverage
    rate but never flag.
    """
    id: str
    description: str
    required: bool = True


@dataclass
class JudgeCoverage:
    """One judge's coverage verdict over a list of claims."""
    judge_id: str                                       # e.g. "llm:claude-opus-4-7"
    coverage: Dict[str, bool]                           # {claim_id -> covered (True/False)}
    justifications: Dict[str, str] = field(default_factory=dict)
    overall_comment: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JudgeCoverage":
        return cls(
            judge_id=data["judge_id"],
            coverage={k: bool(v) for k, v in data["coverage"].items()},
            justifications=dict(data.get("justifications", {})),
            overall_comment=data.get("overall_comment", ""),
            timestamp=data["timestamp"],
        )


@dataclass
class AggregatedCoverage:
    """Per-sample aggregate of N judges' claim coverage verdicts."""
    sample_id: str                                      # "{benchmark}/{conv_id}/{turn_idx}"
    n_judges: int
    coverage_rate: Dict[str, float]                     # {claim_id -> [0.0, 1.0]}
    flagged_for_review: bool = False
    flag_reasons: List[str] = field(default_factory=list)
    judges: List[JudgeCoverage] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AggregatedCoverage":
        return cls(
            sample_id=data["sample_id"],
            n_judges=int(data["n_judges"]),
            coverage_rate={k: float(v) for k, v in data["coverage_rate"].items()},
            flagged_for_review=bool(data.get("flagged_for_review", False)),
            flag_reasons=list(data.get("flag_reasons", [])),
            judges=[JudgeCoverage.from_dict(j) for j in data.get("judges", [])],
        )


def aggregate_coverage(
    sample_id: str,
    coverages: List[JudgeCoverage],
    claims: List[Claim],
    coverage_threshold: float = 0.5,
) -> AggregatedCoverage:
    """Aggregate per-judge coverage; flag if any required claim is majority-missed."""
    if not coverages:
        raise ValueError(f"aggregate_coverage({sample_id!r}): empty judge list")

    n = len(coverages)
    coverage_rate: Dict[str, float] = {}
    for claim in claims:
        votes = [1 if c.coverage.get(claim.id, False) else 0 for c in coverages]
        coverage_rate[claim.id] = sum(votes) / n

    # "Majority-missed" (< threshold) flags; an exact tie (== threshold,
    # possible with an even panel, e.g. 2/2 on the default 4-judge panel)
    # is neither covered nor missed by majority — flag it explicitly rather
    # than silently counting it as covered.
    flag_reasons = []
    for claim in claims:
        if not claim.required:
            continue
        rate = coverage_rate[claim.id]
        if rate < coverage_threshold:
            flag_reasons.append(f"required_claim_missed:{claim.id}(coverage={rate:.2f})")
        elif rate == coverage_threshold:
            flag_reasons.append(f"required_claim_tie:{claim.id}(coverage={rate:.2f})")

    return AggregatedCoverage(
        sample_id=sample_id,
        n_judges=n,
        coverage_rate=coverage_rate,
        flagged_for_review=bool(flag_reasons),
        flag_reasons=flag_reasons,
        judges=list(coverages),
    )


def load_claims(category: str, domain: str, benchmark: str) -> Dict[Tuple[str, str, int], List[Claim]]:
    """Load per-turn claims from `evals/<category>/<domain>/<benchmark>.json`.

    Returns a dict keyed by (scenario_name, conversation_id, turn_index) —
    ALL cases in the spec are read, not just the first, and the scenario
    name disambiguates conversations with the same id across cases. Turns
    without a `claims` field map to an empty list; missing JSON returns {}.
    """
    spec_path = PROJECT_ROOT / "evals" / category / domain / f"{benchmark}.json"
    if not spec_path.exists():
        return {}
    spec = json.loads(spec_path.read_text())
    out: Dict[Tuple[str, str, int], List[Claim]] = {}
    for case in spec:
        scenario_name = case.get("name", "unknown")
        for conv in case.get("conversations", []):
            conv_id = conv["id"]
            for turn_idx, turn in enumerate(conv.get("turns", [])):
                out[(scenario_name, conv_id, turn_idx)] = [
                    Claim(id=c["id"], description=c["description"], required=bool(c.get("required", True)))
                    for c in turn.get("claims", [])
                ]
    return out
