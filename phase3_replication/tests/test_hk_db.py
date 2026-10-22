"""The Hong Kong database's engine: validators read each query once per process, a pooled
connection gives its slot back whatever happened to it, and only a lost connection is an
outage."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pandas as pd
import psycopg
import pytest
from sqlalchemy import QueuePool, create_engine, event, text

from domains import outages
from domains.hk import db


def test_read_frame_reads_each_query_once_and_hands_out_copies(monkeypatch):
    reads = []

    def read_sql(query, engine, params=None):
        reads.append((str(query), params))
        return pd.DataFrame({"v": [1.0, 2.0]})

    monkeypatch.setattr(db.pd, "read_sql", read_sql)
    monkeypatch.setattr(db, "_FRAMES", {})
    query = text("select v from t where s = :s")

    first = db.read_frame(query, {"s": "Central"})
    first.loc[0, "v"] = 99.0                                # a validator edits its copy
    again = db.read_frame(text("select v from t where s = :s"), {"s": "Central"})
    other = db.read_frame(query, {"s": "Southern"})         # other parameters, another read
    bare = db.read_frame(text("select 1"))

    assert again["v"].tolist() == [1.0, 2.0]
    assert other["v"].tolist() == [1.0, 2.0] and bare is not again
    assert reads == [("select v from t where s = :s", {"s": "Central"}),
                     ("select v from t where s = :s", {"s": "Southern"}),
                     ("select 1", None)]


def test_a_connection_dropped_before_it_returns_to_the_pool_frees_its_slot():
    """A dropped connection -- the database gone, or a cell stopped mid-query -- reaches the
    reset as ``None``; it must give its slot back, or the pool runs dry."""
    engine = create_engine("sqlite://", poolclass=QueuePool, pool_size=1, max_overflow=0,
                           pool_timeout=1)
    event.listen(engine, "checkin", db._reset_session)
    with engine.connect() as connection:
        connection.invalidate()
    with engine.connect() as connection:            # the only slot, free again
        assert connection.execute(text("select 1")).scalar() == 1


@pytest.mark.parametrize(("error", "lost"), [
    (psycopg.OperationalError("connection refused"), True),     # no reply: no SQLSTATE
    (psycopg.errors.ConnectionFailure("dropped"), True),
    (psycopg.errors.AdminShutdown("shutting down"), True),
    (psycopg.errors.CannotConnectNow("in recovery mode"), True),
    (psycopg.errors.TooManyConnections("too many clients"), True),
    (psycopg.errors.QueryCanceled("statement timeout"), False),  # the query's own outcome
    (psycopg.errors.OutOfMemory("out of memory"), False),
    (psycopg.errors.LockNotAvailable("lock"), False),
])
def test_only_a_lost_connection_is_recorded_as_an_outage(error, lost):
    with outages.watch() as recorded:
        db._note_outage(NS(original_exception=error, is_pre_ping=False))
    assert bool(recorded) is lost


def test_a_stale_pooled_connection_failing_its_pre_ping_is_not_an_outage():
    with outages.watch() as recorded:
        db._note_outage(NS(original_exception=psycopg.OperationalError("closed"),
                           is_pre_ping=True))
    assert not recorded
