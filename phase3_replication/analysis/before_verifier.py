"""Score every D turn on the outputs it held before the verifier ran.

    uv run python -m analysis.before_verifier study [hk|beijing]

The fixed-roles topology records, for every turn, the required outputs as the synthesis
worker left them (`coordination.before_verification`) before the verifier recomputed and
possibly overwrote them. This scores that snapshot with the same validators that scored the
final outputs, and stores the verdicts as repeat r<k> of the pseudo-arm
`multi_agent_fixed_roles_verified_before`: a verdict file with no run.json beside it, so
nothing takes it for a run. The audit itself is `before_verifier_audit()` below, which pairs
each before-verdict with the stored final verdict: corrected (failed before, passed after),
broken (passed before, failed after), or unchanged.

Hong Kong validators need the database; the Beijing ones read files only.
"""

from __future__ import annotations

import asyncio
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

from domains import get_domain
from evaluation.records import RunRecord
from evaluation.scoring import score_run
from evaluation.store import ResultStore, RunKey
from settings import settings
from tasks import Suite

ARM = "multi_agent_fixed_roles_verified"
BEFORE = f"{ARM}_before"


def before_run(run: RunRecord) -> RunRecord:
    """The record with each turn's outputs replaced by its pre-verifier snapshot."""
    conversations = []
    for conversation in run.conversations:
        turns = []
        for turn in conversation.turns:
            before = (turn.coordination or {}).get("before_verification")
            if before is None:
                raise ValueError(f"{run.task} turn {turn.turn}: no before_verification snapshot")
            turns.append(replace(turn, runtime_variables=dict(before), snapshot_unserialisable=[]))
        conversations.append(replace(conversation, turns=turns))
    return replace(run, conversations=conversations)


async def score_before(store: ResultStore, domain: str | None = None, *, progress=print) -> None:
    keys = sorted((k for k in store.runs() if k.arm == ARM and (domain is None or k.domain == domain)),
                  key=lambda k: (k.domain, k.task, k.model, k.repeat))
    suites: dict[str, Suite] = {}
    done = 0
    for n, key in enumerate(keys, 1):
        target = replace(key, arm=BEFORE)
        if store.load_scorecard(target) is not None:
            done += 1
            continue
        run = store.load_run(key)
        if not run.ok:
            progress(f"[{n}/{len(keys)}] {key.task} {key.model} r{key.repeat}: run not ok, skipped")
            continue
        if run.suite not in suites:
            suites[run.suite] = Suite.load(run.suite)
        suite = suites[run.suite]
        task = suite.tasks[key.task]
        for field_name in get_domain(suite.domain_of(task)).required_settings:
            settings.require(field_name)
        card = await score_run(before_run(run), task, task.load())
        store.save_scorecard(target, card)
        if n % 100 == 0:
            progress(f"[{n}/{len(keys)}] scored")
    progress(f"{len(keys)} runs; {done} already scored")


def before_verifier_audit(results: Path) -> dict:
    """Pair every D turn's pre-verifier verdict with its final verdict."""
    import json

    tally: Counter = Counter()
    by_model: dict[str, Counter] = {}
    rows = []
    for final_path in results.glob(f"*/*/*/{ARM}/*/r*/programmatic_verification.json"):
        before_path = Path(str(final_path).replace(f"/{ARM}/", f"/{BEFORE}/"))
        if not before_path.exists():
            tally["missing_before_card"] += 1
            continue
        final = json.loads(final_path.read_text())
        before = json.loads(before_path.read_text())
        task, model = final_path.parts[-5], final_path.parts[-3]
        repeat = int(final_path.parts[-2][1:])
        fb = {(c["id"], t["turn"]): t for c in before["conversations"] for t in c["turns"]}
        for c in final["conversations"]:
            for t in c["turns"]:
                b = fb.get((c["id"], t["turn"]))
                if b is None or b.get("status") != "scored" or t.get("status") != "scored":
                    tally["unjudged"] += 1
                    continue
                pb, pa = bool(b["success"]), bool(t["success"])
                kind = ("unchanged_pass" if pa else "unchanged_fail") if pb == pa else ("corrected" if pa else "broken")
                tally[kind] += 1
                by_model.setdefault(model, Counter())[kind] += 1
                rows.append(dict(domain=final_path.parts[-7], task=task, model=model, repeat=repeat,
                                 conversation=c["id"], turn=t["turn"], before=pb, after=pa, kind=kind,
                                 before_message=b.get("message", ""), after_message=t.get("message", "")))
    return {"tally": dict(tally), "by_model": {m: dict(c) for m, c in by_model.items()}, "rows": rows}


def main(argv: list[str]) -> None:
    if len(argv) not in (1, 2):
        raise SystemExit(__doc__)
    domain = argv[1] if len(argv) == 2 else None
    asyncio.run(score_before(ResultStore(settings.results_dir, argv[0]), domain))


if __name__ == "__main__":
    main(sys.argv[1:])
