"""The self-consistency baseline G of the pre-registration (§5), from stored runs only: the
single agent run three times with its outputs voted, a compute-matched single-agent point.

    uv run python -m analysis.vote study [ARM]           (ARM: single_agent_bare)

For each model and task, every output of every turn is set to the value most of the
arm's 3 repeats stored: numbers, also inside lists and mappings, are compared after
rounding to 6 significant figures; with no majority, the median when every stored value
is a number, else the first repeat's value. The assembled snapshot is scored by the same
validators. Its verdicts are stored as repeat 1 of the pseudo-arm `<ARM>_vote`: a verdict
file with no run.json beside it, so nothing takes it for a run. Validators read the outputs
only, never the answer text; the first repeat's text stands in. G's tokens are its repeats' sum.
"""

from __future__ import annotations

import asyncio
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any

from domains import get_domain
from evaluation.records import RunRecord
from evaluation.scoring import score_run
from evaluation.store import ResultStore, RunKey
from settings import settings
from tasks import Suite

REPEATS = 3
ABSENT = None   # a repeat whose snapshot lacks the output; stored values are pairs


def _rounded(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float):
        return float(f"{value:.6g}") if math.isfinite(value) else repr(value)
    if isinstance(value, list):
        return [_rounded(v) for v in value]
    if isinstance(value, dict):
        return {k: _rounded(v) for k, v in value.items()}
    return value


def _number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def vote(stored: list[tuple[Any, bool] | None]) -> tuple[Any, bool] | None:
    """One output across the repeats, in repeat order. Each item is (value, stored as a
    type JSON cannot hold) or ABSENT; the result is the chosen item."""
    keys = [item if item is ABSENT else (item[1], json.dumps(_rounded(item[0]), sort_keys=True))
            for item in stored]
    top, count = Counter(keys).most_common(1)[0]
    if count > len(stored) / 2:
        return stored[keys.index(top)]
    present = [item for item in stored if item is not ABSENT]
    if present and all(_number(value) and not unserialisable for value, unserialisable in present):
        return statistics.median(value for value, _ in present), False
    return stored[0]


def voted_run(runs: list[RunRecord]) -> RunRecord:
    """The first repeat's record, each turn's outputs replaced by their vote."""
    conversations = []
    for conversation in runs[0].conversations:
        peers = [{c.id: c for c in run.conversations}[conversation.id].turns for run in runs]
        if len({len(turns) for turns in peers}) != 1:
            raise ValueError(f"{runs[0].task}: repeats differ in the turns of {conversation.id}")
        turns = []
        for index, turn in enumerate(conversation.turns):
            snapshots = [turns_of[index] for turns_of in peers]
            names = list(dict.fromkeys(n for s in snapshots for n in s.runtime_variables))
            values, unserialisable = {}, []
            for name in names:
                chosen = vote([(s.runtime_variables[name], name in s.snapshot_unserialisable)
                               if name in s.runtime_variables else ABSENT for s in snapshots])
                if chosen is not ABSENT:
                    values[name] = chosen[0]
                    if chosen[1]:
                        unserialisable.append(name)
            turns.append(replace(turn, runtime_variables=values,
                                 snapshot_unserialisable=unserialisable))
        conversations.append(replace(conversation, turns=turns))
    return replace(runs[0], conversations=conversations)


async def vote_arm(store: ResultStore, arm: str, *, suites_dir: Path | None = None,
                   progress=print) -> None:
    groups: dict[tuple[str, str], list[RunKey]] = defaultdict(list)
    for key in store.runs():
        if key.arm == arm:
            groups[(key.model, key.task)].append(key)
    suites: dict[str, Suite] = {}
    for n, ((model, task_name), keys) in enumerate(sorted(groups.items()), 1):
        keys.sort(key=lambda k: k.repeat)
        runs = [store.load_run(k) for k in keys]
        label = f"[{n}/{len(groups)}] {arm}_vote {model} {task_name}"
        if len(runs) != REPEATS or not all(run.ok for run in runs):
            progress(f"{label}: not voted ({sum(run.ok for run in runs)} usable repeats)")
            continue
        suite_name = runs[0].suite
        if suite_name not in suites:
            suites[suite_name] = Suite.load(suite_name, suites_dir=suites_dir)
        suite = suites[suite_name]
        task = suite.tasks[task_name]
        for field_name in get_domain(suite.domain_of(task)).required_settings:
            settings.require(field_name)
        card = await score_run(voted_run(runs), task, task.load())
        store.save_scorecard(replace(keys[0], arm=f"{arm}_vote", repeat=1), card)
        passed = sum(v.scored and v.passed for v in card.verdicts)
        progress(f"{label}: {card.outcome} {passed}/{len(card.verdicts)} turns")


def main(argv: list[str]) -> None:
    if len(argv) not in (1, 2):
        raise SystemExit(__doc__)
    arm = argv[1] if len(argv) == 2 else "single_agent_bare"
    asyncio.run(vote_arm(ResultStore(settings.results_dir, argv[0]), arm))


if __name__ == "__main__":
    main(sys.argv[1:])
