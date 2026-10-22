"""A Python runtime that stages execute in, plus lab-side access to it.

The runner creates one `Workspace` per conversation; every stage of a turn works in it,
and scoring reads its output variables.

Lab-side access never executes code:

- `values(names)`: registered output variables, numpy scalars as Python numbers;
- `inventory()`: what agents have staged, summarised, for recording what a
  stage changed.

`close()` frees the runtime when its conversation is done (see there).
"""

from __future__ import annotations

import atexit
import copy
import types as pytypes
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from cave_agent import Function, IPythonRuntime, Variable

from agents.security import create_security_checker
from domains import cell_time
from errors import ConfigurationError

_IPYTHON_NAMES = {"In", "Out", "exit", "quit", "get_ipython"}
_SCALAR_REPR_CHARS = 160


@dataclass(frozen=True)
class Entry:
    """One staged variable, as the next stage is told about it."""

    name: str
    summary: str
    token: tuple[int, str]   # (identity, summary): changes when the value is rebound or edited

    def __str__(self) -> str:
        return f"{self.name}: {self.summary}"


Inventory = dict[str, Entry]


class _TimedRuntime(IPythonRuntime):
    """Each cell of agent code runs under the time per cell (`domains.cell_time`)."""

    async def execute(self, code: str) -> Any:
        with cell_time.cell():
            return await super().execute(code)


class Workspace:
    def __init__(
        self,
        functions: Iterable[Callable],
        variables: Iterable[Variable],
        types: Iterable[Any] = (),
    ):
        self._functions = list(functions)
        self._types = list(types)
        variables = list(variables)
        self.runtime = _TimedRuntime(
            functions=[Function(f) for f in self._functions],
            variables=variables,
            types=self._types,
            security_checker=create_security_checker(),
        )
        # Environment handles (engine, frames) are described in the system
        # prompt already; the inventory lists only what agents produced.
        self._environment = [v for v in variables if v.value is not None]
        self._provided = {v.name for v in self._environment}
        self._descriptions = {v.name: v.description for v in variables}

    @property
    def environment_names(self) -> set[str]:
        """Names the environment binds (data frames, handles, functions)."""
        return self._provided | {getattr(f, "__name__", "") for f in self._functions}

    async def _land(self, names: Iterable[str]) -> None:
        """Land what the runtime has queued: any read through it does."""
        for name in names:
            try:
                await self.runtime.retrieve(name)
                return
            except KeyError:        # unbound by an agent's `del`; try the next one
                continue

    def register(self, variables: Iterable[Variable]) -> None:
        """Register output variables when the turn that asks for them begins.

        Registration binds the name to its initial value (None), which also
        discards anything a model wrote to it speculatively in an earlier turn.
        """
        for variable in variables:
            self.runtime.inject_variable(variable)
            self._descriptions[variable.name] = variable.description

    @property
    def registered(self) -> set[str]:
        return set(self._descriptions)

    async def values(self, names: Iterable[str]) -> dict[str, Any]:
        """Current values of registered variables, numpy scalars as Python numbers.

        `df["x"].sum()` hands back np.float64; a model that stores one has
        stored the float its variable asked for. One the agent's code deleted
        (`del name`) reads as None, not set, as a validator scores it.
        """
        out = {}
        for name in names:
            if name not in self._descriptions:
                continue
            try:
                value = await self.runtime.retrieve(name)
            except KeyError:                    # registered, but no longer bound
                value = None
            out[name] = value.item() if isinstance(value, np.generic) else value
        return out

    def namespace(self) -> dict[str, Any]:
        """The live user namespace, read without executing code. Do not modify it."""
        return _user_namespace(self.runtime)

    def inventory(self) -> Inventory:
        namespace = _user_namespace(self.runtime)
        entries = {}
        for name, value in list(namespace.items()):
            if (
                name.startswith("_")
                or name in _IPYTHON_NAMES
                or name in self._provided
                or value is None
                or isinstance(value, pytypes.ModuleType)
                or callable(value)
            ):
                continue
            summary = _summarise(name, value)
            entries[name] = Entry(name, summary, (id(value), summary))
        return entries

    def close(self) -> None:
        """Free the runtime and whatever its agents loaded into it.

        IPython registers every shell's `atexit_operations` when the shell is
        built and cave-agent never unregisters it, so without this each
        workspace -- frames and all -- lived until the process exited: a
        three-slice run of the air_quality suite grew to ~50 GB.
        """
        shell = _shell(self.runtime)
        atexit.unregister(shell.atexit_operations)
        shell.user_ns.clear()


def private_copy(variable: Variable) -> Variable:
    """A variable whose data frame is the holder's own.

    Environment frames are cached process-wide and validators read the same
    cache (`load_population()`), so an agent editing `pop_df` in place would
    otherwise corrupt ground truth and every later run.
    """
    value = variable.value
    if isinstance(value, pd.DataFrame):
        value = value.copy(deep=True)
    return Variable(variable.name, value, variable.description)


def own_copy(value: Any) -> Any:
    """A copy another agent can edit in place without changing the original."""
    if isinstance(value, (pd.DataFrame, pd.Series)):
        return value.copy(deep=True)
    try:
        return copy.deepcopy(value)
    except Exception:     # handles such as an engine cannot be copied; they are shared
        return value


def changed(before: Inventory, after: Inventory) -> list[str]:
    """Names created or modified between two inventories."""
    return sorted(n for n, e in after.items() if n not in before or before[n].token != e.token)


def _summarise(name: str, value: Any) -> str:
    if isinstance(value, pd.DataFrame):
        cols = ", ".join(map(str, value.columns[:20]))
        more = f", ... (+{len(value.columns) - 20})" if len(value.columns) > 20 else ""
        return f"DataFrame {value.shape[0]}x{value.shape[1]} [{cols}{more}]"
    if isinstance(value, pd.Series):
        return f"Series len={len(value)} dtype={value.dtype} name={value.name!r}"
    if isinstance(value, np.ndarray):
        return f"ndarray shape={value.shape} dtype={value.dtype}"
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, (str, int, float, bool, list, tuple, dict, set)):
        text = repr(value)
        kind = type(value).__name__
        if len(text) > _SCALAR_REPR_CHARS:
            size = f" len={len(value)}" if hasattr(value, "__len__") else ""
            return f"{kind}{size} {text[:_SCALAR_REPR_CHARS]}..."
        return f"{kind} {text}"
    return f"<{type(value).__name__}>"


def _user_namespace(runtime: IPythonRuntime) -> dict[str, Any]:
    """The live IPython user namespace, read without executing code.

    cave-agent exposes no public enumeration, and executing a probe would both
    go through the security checker (which forbids `locals()`) and leave
    traces in the agent's history.
    """
    return _shell(runtime).user_ns


def _shell(runtime: IPythonRuntime) -> Any:
    """The runtime's IPython shell: the one cave-agent internal the lab touches
    (for the namespace and for `close`); the dependency is pinned for it."""
    try:
        return runtime._executor._shell
    except AttributeError as exc:  # pragma: no cover - guards a cave-agent upgrade
        raise ConfigurationError(
            "cave-agent internals changed: IPythonRuntime._executor._shell "
            "is gone; update agents.workspace._shell"
        ) from exc
