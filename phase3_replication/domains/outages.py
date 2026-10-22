"""Whether a data source went away while a run was using it.

Agents query the HK database from their own code, so a lost connection reaches them as a
traceback in a cell, and a run that met one was scored as the model's failure (60 runs on
2026-10-09, while the database restarted). The database module records each connection
failure here; the runner takes a turn that met one for an infrastructure failure, which is
retried, instead.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

# The current turn's list, shared by reference with every agent and sub-agent of the turn.
_lost: ContextVar[list[str] | None] = ContextVar("data_source_outages", default=None)


@contextmanager
def watch() -> Iterator[list[str]]:
    lost: list[str] = []
    token = _lost.set(lost)
    try:
        yield lost
    finally:
        _lost.reset(token)


def record(detail: str) -> None:
    lost = _lost.get()
    if lost is not None:
        lost.append(detail)
