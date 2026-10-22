"""Suites: a frozen task set together with the environment it was written for.

    suites/<suite>/
        suite.toml          name, domains, provenance of the port
        environments/<domain>.json
                            per domain: system prompt + runtime variables +
                            functions, verbatim from the source corpus's domain module
        tasks/<category>/<task>.{json,py}
                            each task's JSON names its `domain`

A suite may span several data domains (air_quality: Hong Kong and Beijing);
each task runs in its own domain's environment.

The environment is part of the suite, not of the domain, because a task's
difficulty depends on what the agent is told. Phase 2 tasks were run under the
Phase 2 prompt; AirBench tasks were authored against a later one whose
conventions (e.g. hour-ending timestamps) some validators rely on.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cave_agent import Variable

from domains import Domain
from errors import ConfigurationError, TaskSpecificationError
from settings import settings
from tasks.model import Task


@dataclass(frozen=True)
class VariableSpec:
    name: str
    description: str


@dataclass(frozen=True)
class Environment:
    """What every agent in a suite sees before any task-specific input."""

    system_prompt: str
    variables: tuple[VariableSpec, ...]
    functions: tuple[str, ...]

    def materialise(self, domain: Domain) -> tuple[list[Variable], list]:
        """Bind variable names and function names to live domain objects."""
        try:
            variables = [
                Variable(v.name, domain.handles[v.name](), v.description)
                for v in self.variables
            ]
            functions = [domain.functions[name] for name in self.functions]
        except KeyError as exc:
            raise ConfigurationError(
                f"environment names {exc} which domain {domain.name!r} does not provide"
            ) from exc
        return variables, functions


@dataclass(frozen=True)
class Suite:
    name: str
    description: str
    source: dict[str, Any]
    environments: dict[str, Environment]    # domain -> what agents in it are told
    tasks: dict[str, Task]
    root: Path

    @property
    def domains(self) -> list[str]:
        return list(self.environments)

    def domain_of(self, task: Task) -> str:
        return task.domain

    def environment_of(self, task: Task) -> Environment:
        return self.environments[self.domain_of(task)]

    @classmethod
    def load(cls, name: str, suites_dir: Path | None = None) -> Suite:
        root = (suites_dir or settings.suites_dir) / name
        manifest_path = root / "suite.toml"
        if not manifest_path.exists():
            available = sorted(p.parent.name for p in root.parent.glob("*/suite.toml"))
            raise ConfigurationError(f"no suite {name!r}; available: {available}")
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("name") != name:
            raise ConfigurationError(f"{manifest_path}: name {manifest.get('name')!r} != {name!r}")

        environments = {
            d: _environment(root / "environments" / f"{d}.json") for d in manifest["domains"]
        }

        tasks: dict[str, Task] = {}
        for path in sorted((root / "tasks").glob("*/*.json")):
            task = Task.from_json(path, suite=name)
            if task.name != path.stem:
                raise TaskSpecificationError(f"{path}: name {task.name!r} != file stem")
            if task.category != path.parent.name:
                raise TaskSpecificationError(f"{path}: category {task.category!r} != directory")
            if task.domain not in environments:
                raise TaskSpecificationError(
                    f"{path}: domain {task.domain!r} is not one of {sorted(environments)}"
                )
            tasks[task.name] = task

        return cls(
            name=manifest["name"],
            description=manifest.get("description", ""),
            source=manifest.get("source", {}),
            environments=environments,
            tasks=tasks,
            root=root,
        )

    def select(
        self,
        names: list[str] | None = None,
        categories: list[str] | None = None,
    ) -> list[Task]:
        """Tasks in name order, optionally filtered. Unknown names are an error."""
        if names and (unknown := sorted(set(names) - set(self.tasks))):
            raise ConfigurationError(f"suite {self.name!r} has no tasks {unknown}")
        return [
            task
            for task in self.tasks.values()
            if (not names or task.name in names)
            and (not categories or task.category in categories)
        ]


def _environment(path: Path) -> Environment:
    env = json.loads(path.read_text(encoding="utf-8"))
    return Environment(
        system_prompt=env["system_prompt"],
        variables=tuple(VariableSpec(**v) for v in env["variables"]),
        functions=tuple(env.get("functions", ())),
    )


def available_suites(suites_dir: Path | None = None) -> list[str]:
    root = suites_dir or settings.suites_dir
    return sorted(p.parent.name for p in root.glob("*/suite.toml"))
