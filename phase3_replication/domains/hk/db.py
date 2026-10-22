"""The Hong Kong monitoring database, shared by agents and validators.

One engine per process. Agents receive it as the `engine` runtime variable and
validators read through `read_frame` on the same engine, so ground truth and the
answer are computed against the same connection settings.

`engine` is None when `METASEQ_HK_DATABASE_URL` is unset, which keeps task
modules importable offline (`metaseq check`, unit tests). Anything that
actually queries calls `settings.require("hk_database_url")` first.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import psycopg
from sqlalchemy import Engine, TextClause, create_engine, event

from domains import outages
from settings import settings

# Guards against a runaway query, not honest work. Phase 2 ran with 3 s when
# `hourly_station_air_quality` held ~250k rows; the record has since been
# extended back to 2020 (>1M rows) and a cold first read takes 4-7 s, so 3 s
# would now fail correct queries for agent and validator alike. 30 s still
# kills a cross join or an unbounded scan of the traffic table.
STATEMENT_TIMEOUT_MS = 30_000


def _create_engine(url: str | None) -> Engine | None:
    if not url:
        return None
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={
            "connect_timeout": 5,
            "options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS}",
            # The statement timeout is enforced by the server, so a connection that
            # dies silently (no reply, no reset) left a query waiting forever: one
            # experiment slice hung for 45 minutes. TCP keepalives notice within
            # about a minute and raise, which scoring retries as transient.
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 3,
            # psycopg prepares a query it has run 5 times and forgets the statement only
            # on a rollback, not on the `DISCARD ALL` a connection gets back in the pool:
            # its next run on a connection returned idle fails. Agent SQL is ad hoc.
            "prepare_threshold": None,
        },
    )


engine = _create_engine(settings.hk_database_url)

# Connection loss, by SQLSTATE: none (refused, or dropped before the server answered),
# class 08 (connection exception), 57P01-57P03 (the server shutting down or not yet
# accepting), 53300 (too many connections). Any other `OperationalError` -- out of memory,
# a program limit, a lock, the statement timeout -- is the outcome of the query itself.
_CONNECTION_LOST = ("08", "57P01", "57P02", "57P03", "53300")


def _reset_session(dbapi_connection: Any, record: Any) -> None:
    """Clear a connection's session state when it returns to the pool.

    Agents and validators share this engine's connections. A setting an agent makes
    (`SET TIME ZONE`, `SET search_path`, a prepared statement) would otherwise reach
    the next run or a validator through the pooled connection. A connection that
    cannot be reset is dropped from the pool rather than reused; one already dropped
    (invalidated) arrives as ``None`` and has nothing to reset.
    """
    if dbapi_connection is None:
        return
    try:
        autocommit = dbapi_connection.autocommit
        dbapi_connection.autocommit = True      # DISCARD cannot run in a transaction
        with dbapi_connection.cursor() as cursor:
            cursor.execute("DISCARD ALL")
        dbapi_connection.autocommit = autocommit
    except Exception:
        record.invalidate()


def _note_outage(context: Any) -> None:
    """A connection the database refused or dropped, recorded for the runner
    (`domains.outages`). A pooled connection that fails its pre-ping is not one: the
    pool replaces it before the query runs."""
    if context.is_pre_ping:
        return
    exc = context.original_exception
    if isinstance(exc, psycopg.OperationalError) and (
            exc.sqlstate is None or exc.sqlstate.startswith(_CONNECTION_LOST)):
        outages.record(f"{type(exc).__name__}: {str(exc).splitlines()[0][:200]}")


if engine is not None:
    event.listen(engine, "checkin", _reset_session)
    event.listen(engine, "handle_error", _note_outage)


# Validators recompute their ground truth from the database every time they judge
# an answer, and one scoring pass judges each task's answers dozens of times (every
# repeat, arm and model, before and after verification). The ground truth does not
# depend on the answer, so a validator reads through `read_frame`: each distinct
# query (its SQL and parameters) runs once per process, and every later call gets
# a copy of that first result. The cache lives only as long as the process, so
# every scoring pass still reads the database it is scored against. Agents use
# `engine` directly and are unaffected.
_FRAMES: dict[tuple[str, str], pd.DataFrame] = {}


def read_frame(query: TextClause, params: Mapping[str, Any] | None = None) -> pd.DataFrame:
    """`pd.read_sql(query, engine, params=params)`, read once per process."""
    key = (str(query), repr(sorted((params or {}).items())))
    if key not in _FRAMES:
        _FRAMES[key] = pd.read_sql(query, engine, params=params)
    return _FRAMES[key].copy()
