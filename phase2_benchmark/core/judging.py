"""Shared orchestration helpers for the LLM-judge evaluation scripts.

Both `scripts/score_responses.py` (Response Quality) and
`scripts/verify_claims.py` (Claim Coverage) use this module
to pick a judge pool, walk the run results directory, and call the LLM
judges concurrently.
"""

import logging
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Tuple, TypeVar

from core.llm import LLMClient, ModelConfig, ModelRegistry
from core.results import latest_result_file, main_result_files, sanitize_model_id


logger = logging.getLogger("judging")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# Default judge temperature is pinned at the judging layer (not inherited from
# each model's models.toml entry) so the protocol is documented in one place.
JUDGE_TEMPERATURE = 0.1

# Panel used by both `scripts/score_responses.py` and `scripts/verify_claims.py`
# when `--judge` is not passed. Kept as a tuple of registry names, not model IDs,
# so a user can retarget one lab's provider via models.toml without editing here.
DEFAULT_JUDGE_PANEL: Tuple[str, ...] = (
    "claude-sonnet-4-6", "kimi-k2", "deepseek-v4-flash", "qwen3.7-max",
)


def rater_pool(
    agent_lab: Optional[str],
    candidates: List[ModelConfig],
    exclude_same_lab: bool = False,
) -> List[ModelConfig]:
    """Return the judge panel for one sample.

    Default: returns ALL candidates, so every agent is judged by the same
    panel — required for leaderboard comparability, since panel composition
    is itself a source of bias.

    `exclude_same_lab=True` is the opt-in robustness check: drop any
    judge whose foundation lab matches the agent's. The gap between a
    paired (default, exclude) run measures lab-bias sensitivity; with
    exclusion on the panel is agent-specific and headline numbers are not
    directly cross-agent comparable.

    Raises if `exclude_same_lab=True` and either `agent_lab` or any
    candidate's `lab` is None — silently keeping an unlabeled judge would
    defeat the check (a section called e.g. `my-proxy` proxying a same-lab
    provider would sneak through). Set explicit `lab = "..."` in
    `models.toml` to resolve.
    """
    if not exclude_same_lab:
        return list(candidates)
    if agent_lab is None:
        raise ValueError(
            "rater_pool(exclude_same_lab=True): agent_lab is None — the agent's "
            "models.toml entry is unlabeled. Set `lab = \"...\"` on its entry "
            "or omit --exclude-same-lab."
        )
    unlabeled = [c.name for c in candidates if c.lab is None]
    if unlabeled:
        raise ValueError(
            f"rater_pool(exclude_same_lab=True): candidates {unlabeled} have no "
            "`lab` set. Set `lab = \"...\"` on each candidate's models.toml entry."
        )
    pool = [c for c in candidates if c.lab != agent_lab]
    if len(pool) < 2:
        # Both scoring channels need >= 2 judges to aggregate anything;
        # proceeding would silently produce empty sibling files that then
        # read as "already scored" on rerun. Fail upfront instead.
        raise ValueError(
            f"rater_pool(exclude_same_lab=True): only {len(pool)} judge(s) left "
            f"after excluding lab {agent_lab!r} from {[c.name for c in candidates]}. "
            "Add more judges to the panel or omit --exclude-same-lab."
        )
    return pool


def call_judge(model_cfg: ModelConfig, prompt: str) -> Optional[str]:
    """Call one LLM judge and return the JSON body text (or None on failure).

    Temperature is pinned low so the panel's disagreement reflects judgment
    variance, not sampling noise. The reasoning trace (if the judge is a
    reasoning model with `thinking_echo_field` configured) is discarded
    here — the judge protocol grades on the final JSON only.
    """
    result = LLMClient(model_cfg).complete(prompt, json_mode=True, temperature=JUDGE_TEMPERATURE)
    return result.text if result else None


T = TypeVar("T")


class JudgeCallTracker:
    """Per-judge success/failure counters for one scoring run.

    A judge that is systematically broken (bad key, wrong endpoint) fails
    every call; without run-level accounting that only surfaces as one log
    line per sample and the whole run silently degrades to a smaller jury.
    The orchestration scripts print `summary_lines()` at the end of a run.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls: Counter = Counter()
        self.failures: Counter = Counter()

    def record(self, judge_name: str, ok: bool) -> None:
        with self._lock:
            self.calls[judge_name] += 1
            if not ok:
                self.failures[judge_name] += 1

    def summary_lines(self) -> List[str]:
        lines = []
        for name in sorted(self.calls):
            n, f = self.calls[name], self.failures[name]
            mark = " ⚠ SYSTEMATIC FAILURE — check models.toml / provider" if f == n and n >= 3 else ""
            lines.append(f"  judge {name}: {n - f}/{n} calls succeeded{mark}")
        return lines


def judges_concurrent(
    judges: List[ModelConfig],
    fn: Callable[[ModelConfig], Optional[T]],
    max_workers: int,
    tracker: Optional[JudgeCallTracker] = None,
) -> List[T]:
    """Run `fn(judge_cfg)` over all judges concurrently; drop None results.

    Dropped (None) results are recorded per-judge on `tracker` so a
    systematically failing judge is visible at the end of the run, not
    just as scattered per-sample warnings.
    """
    out: List[T] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for cfg, r in zip(judges, pool.map(fn, judges)):
            if tracker is not None:
                tracker.record(cfg.name, r is not None)
            if r is not None:
                out.append(r)
    return out


def infer_agent_lab(result_path: Path, registry: ModelRegistry) -> Optional[str]:
    """Recover the agent's foundation lab from a result file path.

    Result filenames follow `{api_model}_{YYYYmmdd}_{HHMMSS}.json`; we peel
    the two trailing timestamp segments to get the api_model, then look it
    up in the registry. Returns None when the api_model isn't registered,
    which is the correct fallback for `rater_pool` in default (non-strict)
    mode.
    """
    parts = result_path.stem.rsplit("_", 2)
    agent_model_id = parts[0] if len(parts) == 3 else result_path.stem
    cfg = registry.find_by_api_model(agent_model_id)
    if cfg is None:
        # scripts.run sanitizes api_model for filenames (e.g. `org/model` →
        # `org-model`); match on the sanitized form as well.
        for candidate in registry.all():
            if sanitize_model_id(candidate.api_model) == agent_model_id:
                cfg = candidate
                break
    return cfg.lab if cfg else None


def iter_result_files(
    exp_id: str,
    domain: Optional[str],
    category: Optional[str],
    benchmark: Optional[str],
    latest_only: bool = True,
) -> Iterator[Tuple[str, str, str, Path]]:
    """Yield (domain, category, benchmark_name, result_path) for matching result files.

    Skips sibling output files (`*_scores.json`, `*_claims.json`) and any
    directories starting with `_`. Filters narrow the scan; None = no filter.

    `latest_only=True` (the default) yields only the newest main result file
    per benchmark — the same file `scripts.run_stats` reports PV numbers
    from, so all three channels aggregate the SAME execution when a
    benchmark was re-run. Pass `latest_only=False` to walk every historical
    run (e.g. for variance analysis across repeats).
    """
    base = PROJECT_ROOT / "experiments" / exp_id
    if not base.exists():
        return
    for domain_dir in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("_")):
        if domain and domain_dir.name != domain:
            continue
        for cat_dir in sorted(p for p in domain_dir.iterdir() if p.is_dir() and not p.name.startswith("_")):
            if category and cat_dir.name != category:
                continue
            for bench_dir in sorted(p for p in cat_dir.iterdir() if p.is_dir()):
                if benchmark and bench_dir.name != benchmark:
                    continue
                if latest_only:
                    f = latest_result_file(bench_dir)
                    if f is not None:
                        yield domain_dir.name, cat_dir.name, bench_dir.name, f
                else:
                    for f in main_result_files(bench_dir):
                        yield domain_dir.name, cat_dir.name, bench_dir.name, f
