"""Task data model.

A task is a pair of files in `suites/<suite>/tasks/<category>/`:

    <name>.json   what is asked: conversations of turns, each naming its validator
    <name>.py     how it is checked: `variables`, `validators`, optional `tools`,
                  `hooks`, `types`

The JSON is read eagerly (listing and filtering need nothing else); the module
is imported only when a task is run or scored, because validators bind the
database engine at import.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cave_agent import Variable

from errors import TaskSpecificationError

# Task modules are imported under this package name. The agent runtime's
# security checker forbids importing it, so an agent cannot read a validator.
TASK_MODULE_PACKAGE = "metaseq_suites"


@dataclass(frozen=True)
class Turn:
    query: str
    validator: str
    # Variables this turn asks for. None means every variable the task
    # declares, registered up front (single-turn and Phase 2 tasks). When set,
    # a variable is registered only when the turn that stores it begins, so an
    # earlier turn never advertises a later turn's outputs.
    stores: tuple[str, ...] | None = None
    pre_turn_hook: str | None = None
    # Claim-coverage rubric items, kept for judge-based channels; unused by PV.
    claims: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Turn:
        if not data.get("validator"):
            raise TaskSpecificationError(f"turn has no validator: {data.get('query', '')[:80]!r}")
        stores = data.get("stores")
        return cls(
            query=data.get("query", ""),
            validator=data["validator"],
            stores=tuple(stores) if stores is not None else None,
            pre_turn_hook=data.get("pre_turn_hook"),
            claims=tuple(data.get("claims", ())),
        )


@dataclass(frozen=True)
class Conversation:
    id: str
    turns: tuple[Turn, ...]

    @property
    def scoped(self) -> bool:
        """Whether variables are registered turn by turn (see `Turn.stores`)."""
        return any(turn.stores is not None for turn in self.turns)


@dataclass
class TaskModule:
    """What a task's `.py` file provides."""

    variables: list[Variable]
    validators: dict[str, Callable]
    tools: list[Callable] = field(default_factory=list)
    hooks: dict[str, Callable] = field(default_factory=dict)
    types: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class Task:
    name: str
    suite: str
    category: str
    difficulty: str | None
    conversations: tuple[Conversation, ...]
    json_path: Path
    # Scenario text given to every agent stage (AirBench `description`).
    description: str | None = None
    # Phase 2 tasks state their required outputs in prose; kept verbatim
    # because the single agent was given it in the archived runs.
    requirements: str | None = None
    case_type: str | None = None
    domain: str | None = None     # the data domain the task runs in (its JSON's `domain`)

    @classmethod
    def from_json(cls, path: Path, suite: str) -> Task:
        data = json.loads(path.read_text(encoding="utf-8"))
        try:
            conversations = tuple(
                Conversation(
                    id=conv["id"],
                    turns=tuple(Turn.from_dict(t) for t in conv["turns"]),
                )
                for conv in data["conversations"]
            )
            return cls(
                name=data["name"],
                suite=suite,
                category=data["category"],
                difficulty=data.get("difficulty"),
                conversations=conversations,
                json_path=path,
                description=data.get("description"),
                requirements=data.get("requirements"),
                case_type=data.get("case_type"),
                domain=data.get("domain"),
            )
        except (KeyError, TypeError) as exc:
            raise TaskSpecificationError(f"{path}: malformed task ({exc})") from exc

    @property
    def module_path(self) -> Path:
        return self.json_path.with_suffix(".py")

    @property
    def n_turns(self) -> int:
        return sum(len(c.turns) for c in self.conversations)

    def load(self) -> TaskModule:
        """Import the task module and check it against the JSON."""
        name = f"{TASK_MODULE_PACKAGE}.{self.suite}.{self.name}"
        module = sys.modules.get(name)
        if module is None:
            spec = importlib.util.spec_from_file_location(name, self.module_path)
            if spec is None or spec.loader is None:
                raise TaskSpecificationError(f"cannot import {self.module_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            try:
                spec.loader.exec_module(module)
            except Exception:
                del sys.modules[name]
                raise
        loaded = TaskModule(
            variables=list(getattr(module, "variables", [])),
            validators=dict(getattr(module, "validators", {})),
            tools=list(getattr(module, "tools", [])),
            hooks=dict(getattr(module, "hooks", {})),
            types=list(getattr(module, "types", [])),
        )
        self._check(loaded)
        return loaded

    def _check(self, module: TaskModule) -> None:
        declared = {v.name for v in module.variables}
        for conv in self.conversations:
            for turn in conv.turns:
                if turn.validator not in module.validators:
                    raise TaskSpecificationError(
                        f"{self.name}: validator {turn.validator!r} is not defined"
                    )
                if turn.pre_turn_hook and turn.pre_turn_hook not in module.hooks:
                    raise TaskSpecificationError(
                        f"{self.name}: hook {turn.pre_turn_hook!r} is not defined"
                    )
            if conv.scoped:
                stored = [n for t in conv.turns for n in (t.stores or ())]
                if unknown := sorted(set(stored) - declared):
                    raise TaskSpecificationError(
                        f"{self.name}/{conv.id}: stores undeclared variables {unknown}"
                    )
                if unclaimed := sorted(declared - set(stored)):
                    raise TaskSpecificationError(
                        f"{self.name}/{conv.id}: no turn stores {unclaimed}"
                    )
