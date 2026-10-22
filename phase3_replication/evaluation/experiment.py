"""Experiment specs (`configs/experiments/<name>.toml`) and their execution.

An experiment is the grid  arms x models x tasks x repeats  over one suite,
plus the contrasts its report tests. The spec is the unit of reproducibility:
results live under `results/` (the study) or `results/<name>/`, and the report is a function of the
spec and the stored verdicts.
"""

from __future__ import annotations

import hashlib
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agents import Arm, instructions, load_arms
from agents.arm import REMOVED_FIELDS
from agents.harness import Harness, HarnessName, build_harness, harness_type
from domains import get_domain
from errors import ConfigurationError, InfrastructureError
from evaluation.protocol import protocol_fingerprint
from evaluation.records import Scorecard
from evaluation.runner import RunContext, run_task
from evaluation.scoring import score_run
from evaluation.store import ResultStore, RunKey
from llm import ModelRegistry
from settings import settings
from tasks import Suite, Task, TaskModule

# Attempts a run gets before it is left as an error (`ResultStore.attempts`).
MAX_ATTEMPTS = 3
# Consecutive failed runs after which a process stops: past this, it is an outage.
FAILURES_IN_A_ROW = 5


class Contrast(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    treatment: str
    control: str
    question: str = ""


class ExperimentSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str = ""
    suite: str
    arms: list[str] = Field(min_length=1)
    models: list[str] = Field(min_length=1)
    repeats: int = Field(1, ge=1)
    # How code reaches the runtime (`agents.harness`).
    harness: HarnessName = "tool"
    tasks: list[str] = Field(default_factory=list)        # empty: the whole suite
    categories: list[str] = Field(default_factory=list)
    contrasts: list[Contrast] = Field(default_factory=list)

    @model_validator(mode="after")
    def _contrasts_use_listed_arms(self) -> ExperimentSpec:
        for c in self.contrasts:
            if missing := {c.treatment, c.control} - set(self.arms):
                raise ValueError(f"contrast {c.name!r} uses arms not in `arms`: {missing}")
        return self

    @classmethod
    def load(cls, name_or_path: str) -> ExperimentSpec:
        path = Path(name_or_path)
        if not path.suffix:
            path = settings.configs_dir / "experiments" / f"{name_or_path}.toml"
        if not path.exists():
            raise ConfigurationError(f"experiment config {path} not found")
        try:
            return cls(**tomllib.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            raise ConfigurationError(f"{path}: {exc}") from exc

    def resolve_arms(self) -> list[Arm]:
        catalogue = load_arms()
        if unknown := [a for a in self.arms if a not in catalogue]:
            raise ConfigurationError(f"unknown arms {unknown}; see configs/arms.toml")
        return [catalogue[a] for a in self.arms]

    def select_tasks(self, suite: Suite) -> list[Task]:
        return suite.select(self.tasks or None, self.categories or None)

    def covers(self, key: RunKey) -> bool:
        """Whether a stored run belongs to this spec's grid (arms and models may shrink)."""
        return key.arm in self.arms and key.model in self.models


@dataclass(frozen=True)
class Selection:
    """Command-line narrowing of an experiment; never widens it."""

    arms: list[str] | None = None
    models: list[str] | None = None
    tasks: list[str] | None = None
    shard: tuple[int, int] | None = None     # (index, count), 0-based

    def keep(self, key: RunKey) -> bool:
        if self.arms and key.arm not in self.arms:
            return False
        if self.models and key.model not in self.models:
            return False
        if self.tasks and key.task not in self.tasks:
            return False
        if self.shard:
            index, count = self.shard
            # Stable across processes (unlike hash()), so shards never overlap; a
            # cryptographic digest, because crc32 is affine and sent a task's repeats to
            # fixed residues, leaving the shards 98/69/97/69 runs.
            digest = hashlib.blake2b(f"{key.task}/{key.repeat}".encode(), digest_size=4)
            return int.from_bytes(digest.digest(), "big") % count == index
        return True


def grid(spec: ExperimentSpec, suite: Suite, tasks: list[Task]) -> list[RunKey]:
    """Every run, in the order they are made: each repeat of each task across every model
    and arm before the next, so that arms share the conditions of the hours they run in
    (database load, provider latency) and a study stopped early leaves whole repeats."""
    return [
        RunKey(arm, model, task.name, repeat,
               domain=suite.domain_of(task), category=task.category)
        for repeat in range(1, spec.repeats + 1)
        for task in tasks
        for model in spec.models
        for arm in spec.arms
    ]


async def run_experiment(
    spec: ExperimentSpec,
    selection: Selection,
    *,
    rerun: bool = False,
    score: bool = True,
    dry_run: bool = False,
    progress: Callable[[str], None] = print,
) -> None:
    """Run every selected cell that has no completed run; score as it goes.

    Completed runs left unscored (scoring was off, or the process stopped
    between saving and scoring) are scored first, so `run` alone converges.
    `dry_run` reports what would run, and stops there.
    """
    suite = Suite.load(spec.suite)
    arms = {a.name: a for a in spec.resolve_arms()}
    tasks = {t.name: t for t in spec.select_tasks(suite)}
    registry = ModelRegistry.load(settings.models_toml)
    store = ResultStore(settings.results_dir, spec.name)
    modules = _ModuleCache()

    keys = [k for k in grid(spec, suite, list(tasks.values())) if selection.keep(k)]
    _require_settings(suite, [tasks[k.task] for k in keys])
    protocols = {d: protocol_fingerprint(suite.environments[d], spec.harness)
                 for d in suite.domains}
    # The suite prompt as the experiment's harness has its agents read it.
    system_prompts = {d: harness_type(spec.harness).system_prompt(
        suite.environments[d].system_prompt) for d in suite.domains}
    instructions.load_prompts()        # read now, with the code the fingerprint covers
    done = [k for k in keys if not rerun and store.status(k) == "ok"]
    # A completed run made under other code, prompts, arm settings or model
    # configuration (endpoint, temperature, ...) is rerun, never mixed with
    # runs made under the current ones.
    configs = {m: registry.get(m).fingerprint() for m in {k.model for k in done}}
    stale = [k for k in done if not _made_under_current(
        store.made_under(k), protocols[k.domain], arms[k.arm], configs[k.model])]
    # A run that has failed MAX_ATTEMPTS times is not tried again: it stays an error and
    # is reported, rather than retried until it happens to succeed.
    exhausted = [k for k in keys if k not in done and store.attempts(k) >= MAX_ATTEMPTS]
    todo = [k for k in keys if (k not in done or k in stale) and k not in exhausted]
    unscored = [k for k in keys if k not in todo and k not in exhausted
                and not store.is_scored(k)] if score else []
    progress(f"{spec.name}: {len(keys)} runs selected, {len(todo)} to run"
             + (f" ({len(stale)} stale)" if stale else "")
             + (f", {len(exhausted)} given up after {MAX_ATTEMPTS} failed attempts"
                if exhausted else "")
             + (f", {len(unscored)} to score" if unscored else ""))
    if dry_run:
        return

    for key in unscored:
        task = tasks[key.task]
        store.save_scorecard(key, await score_run(store.load_run(key), task, modules.get(task)))

    environments: dict[str, tuple] = {}     # domain -> (variables, functions), bound once
    harnesses: dict[str, tuple[Harness, dict[str, Any]]] = {}   # model -> harness, its record
    failed_in_a_row = 0
    for n, key in enumerate(todo, 1):
        if key.model not in harnesses:
            config = registry.get(key.model)
            harnesses[key.model] = (build_harness(spec.harness, config), config.fingerprint())
        harness, fingerprint = harnesses[key.model]
        task = tasks[key.task]
        domain = suite.domain_of(task)
        if domain not in environments:
            environments[domain] = suite.environments[domain].materialise(get_domain(domain))
        env_variables, env_functions = environments[domain]
        ctx = RunContext(
            experiment=spec.name,
            domain=domain,
            protocol=protocols[domain],
            arm=arms[key.arm],
            harness=harness,
            model_fingerprint=fingerprint,
            system_prompt=system_prompts[domain],
            environment_variables=env_variables,
            environment_functions=env_functions,
        )
        result = await run_task(ctx, task, modules.get(task), key.repeat)
        if result.record.error:
            store.record_attempt(key, result.record)
        store.save_run(key, result.record, result.transcripts)
        failed_in_a_row = failed_in_a_row + 1 if result.record.error else 0
        if failed_in_a_row == FAILURES_IN_A_ROW:
            # An outage, not bad luck: stop before it spends every remaining run's
            # attempts (and, with the database down, a whole turn of tokens each).
            raise InfrastructureError(
                f"{spec.name}: {FAILURES_IN_A_ROW} runs in a row failed, the last with "
                f"{result.record.error}; stopping", kind="outage")

        if result.record.error:
            verdict = f"ERROR {result.record.error}"
        elif score:
            scorecard = await score_run(result.record, task, modules.get(task))
            store.save_scorecard(key, scorecard)
            verdict = _describe(scorecard)
        else:
            verdict = "done"
        cost = result.record.cost
        progress(f"[{n}/{len(todo)}] {key.arm} {key.model} {key.task} r{key.repeat}: "
                 f"{verdict}  steps={cost.steps} tokens={cost.total_tokens}")


async def rescore_experiment(
    spec: ExperimentSpec,
    selection: Selection,
    *,
    progress: Callable[[str], None] = print,
) -> None:
    """Re-judge this spec's stored runs with today's validators. No model calls."""
    suite = Suite.load(spec.suite)
    store = ResultStore(settings.results_dir, spec.name)
    modules = _ModuleCache()
    keys = [
        k for k in store.runs()
        if spec.covers(k) and selection.keep(k) and k.task in suite.tasks
    ]
    _require_settings(suite, [suite.tasks[k.task] for k in keys])
    for n, key in enumerate(keys, 1):
        task = suite.tasks[key.task]
        scorecard = await score_run(store.load_run(key), task, modules.get(task))
        store.save_scorecard(key, scorecard)
        progress(f"[{n}/{len(keys)}] {key.arm} {key.model} {key.task} r{key.repeat}: "
                 f"{_describe(scorecard)}")


def _made_under_current(made_under: tuple[str | None, dict, dict], protocol: str, arm: Arm,
                        model_config: dict) -> bool:
    """Whether a stored run was made under the current protocol, arm and model configuration.

    A field added to `Arm` after the run was made is absent from its record; the
    run behaved as that field's default, the only behaviour that existed then. A field
    since removed with the code it configured (`agents.arm.REMOVED_FIELDS`) counts only
    at the one value whose behaviour remains. The description is documentation, not
    behaviour, and is not compared.
    """
    made_protocol, made_arm, made_config = made_under
    current = arm.model_dump(exclude={"description"})
    made_arm = {k: v for k, v in made_arm.items() if k != "description"}
    removed = {k: made_arm.pop(k) for k in list(made_arm) if k in REMOVED_FIELDS}
    if any(REMOVED_FIELDS[k] != v for k, v in removed.items()):
        return False
    same_arm = set(made_arm) <= set(current) and all(
        made_arm.get(field, Arm.model_fields[field].default) == value
        for field, value in current.items())
    return made_protocol == protocol and same_arm and made_config == model_config


def _require_settings(suite: Suite, tasks: list[Task]) -> None:
    """Fail before any model call if a domain these tasks run in lacks its settings
    (the HK database URL); a Beijing-only selection needs none."""
    for domain in sorted({suite.domain_of(t) for t in tasks}):
        for field_name in get_domain(domain).required_settings:
            settings.require(field_name)


class _ModuleCache:
    """Task modules, imported once per process."""

    def __init__(self) -> None:
        self._loaded: dict[str, TaskModule] = {}

    def get(self, task: Task) -> TaskModule:
        if task.name not in self._loaded:
            self._loaded[task.name] = task.load()
        return self._loaded[task.name]


def _describe(scorecard: Scorecard) -> str:
    if scorecard.status != "ok":
        return f"UNSCORED ({scorecard.status}: {scorecard.reason})"
    passed = sum(v.scored and v.passed for v in scorecard.verdicts)
    label = {"passed": "PASS", "failed": "FAIL", "refused": "UNSCORED"}[scorecard.outcome]
    return f"{label} {passed}/{len(scorecard.verdicts)} turns"
