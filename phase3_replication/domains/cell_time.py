"""How long one cell of agent code may run without yielding.

The runtime runs agent code in the event loop's thread, and nothing bounded a cell: one that
loops over thousands of hourly queries, each inside the database's 30 s statement timeout, or
that computes without end, held its run for hours (2026-10-09), starved the streams of every
other agent in the process, and was found only by the watcher, whose restart drew the run
again. A cell that keeps the loop busy for `CELL_SECONDS` without a break now has
`CellTimeLimit` raised inside it, an error the agent sees, so it can rewrite the cell. Time a
cell spends awaiting (a lead waiting for its sub-agents) does not count: the loop runs then.
The limit is the same for every arm; code outside a cell (the harness, validators) is never
interrupted.

How: a heartbeat on the loop marks each turn of it; a watchdog thread that sees no beat for
`CELL_SECONDS` signals the main thread, whose handler raises only when the code running there
is a cell's (a context variable, so concurrent sub-agents each keep their own).
"""

from __future__ import annotations

import asyncio
import signal
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

CELL_SECONDS = 600.0
_BEAT_S = 1.0
_RESIGNAL_S = 30.0      # a cell inside a long C call (a query) sees the signal when it returns

_in_cell: ContextVar[bool] = ContextVar("in_agent_cell", default=False)


class CellTimeLimit(BaseException):
    """Raised inside a cell that ran too long. A BaseException, as KeyboardInterrupt is, so
    that an agent's `except Exception: continue` in the loop it is stuck in does not swallow
    it; IPython reports it as the cell's error."""


@contextmanager
def cell() -> Iterator[None]:
    """Agent code runs inside this."""
    _start_watchdog()
    token = _in_cell.set(True)
    try:
        yield
    finally:
        _in_cell.reset(token)


@contextmanager
def outside_cell() -> Iterator[None]:
    """A stage started from inside a cell (a sub-agent the lead's code delegated to) runs its
    own harness code, which is never interrupted; its own cells enter `cell()` again."""
    token = _in_cell.set(False)
    try:
        yield
    finally:
        _in_cell.reset(token)


class _Watchdog:
    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self.beat = time.monotonic()
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None

    def attach(self, loop: asyncio.AbstractEventLoop) -> None:
        with self.lock:
            if self.loop is loop:
                return
            self.loop, self.beat = loop, time.monotonic()
        self._tick(loop)
        if self.thread is None:
            signal.signal(signal.SIGUSR1, _interrupt)
            self.thread = threading.Thread(target=self._watch, name="cell-watchdog", daemon=True)
            self.thread.start()

    def _tick(self, loop: asyncio.AbstractEventLoop) -> None:
        if self.loop is not loop or loop.is_closed():
            return
        self.beat = time.monotonic()
        loop.call_later(_BEAT_S, self._tick, loop)

    def _watch(self) -> None:
        signalled = 0.0
        while True:
            time.sleep(min(_BEAT_S, _RESIGNAL_S))
            loop = self.loop
            if loop is None or loop.is_closed() or not loop.is_running():
                continue
            now = time.monotonic()
            if now - self.beat > CELL_SECONDS and now - signalled > _RESIGNAL_S:
                signalled = now
                signal.pthread_kill(threading.main_thread().ident, signal.SIGUSR1)


_watchdog = _Watchdog()


def _start_watchdog() -> None:
    if threading.current_thread() is not threading.main_thread():
        return          # signals reach the main thread only; there is no loop to watch here
    _watchdog.attach(asyncio.get_running_loop())


def _interrupt(signum: int, frame: Any) -> None:
    if _in_cell.get():
        raise CellTimeLimit(
            f"this cell ran for over {CELL_SECONDS / 60:.0f} minutes without finishing and was"
            " stopped; rewrite it to do less per cell (aggregate or filter in SQL rather than"
            " one query per hour or row, and avoid loops over every row)")
