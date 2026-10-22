"""How a validator's database errors are classified."""

import pytest

import evaluation.scoring as scoring
from errors import InfrastructureError, TaskSpecificationError
from tasks.model import Turn


class QueryCanceled(Exception):
    """Stands in for psycopg's statement-timeout error (matched by class name)."""


class PandasDatabaseError(Exception):
    """pandas' wrapper when a query runs on a raw driver connection."""


def _timing_out(*_):
    try:
        raise QueryCanceled("canceling statement due to statement timeout")
    except QueryCanceled as exc:
        raise PandasDatabaseError("Execution failed on sql '\nSELECT ...") from exc


def _broken(*_):
    raise KeyError("no_such_column")


TURN = Turn.from_dict({"query": "q", "validator": "v"})


async def test_a_statement_timeout_is_retried_then_reported_as_infrastructure(monkeypatch):
    monkeypatch.setattr(scoring, "_DB_RETRY_SLEEP_S", 0)
    with pytest.raises(InfrastructureError, match="statement timeout"):
        await scoring.judge(_timing_out, "", {}, TURN, conversation="c", turn_number=1)


async def test_a_validator_bug_is_a_task_defect_with_its_root_message():
    with pytest.raises(TaskSpecificationError, match="KeyError: 'no_such_column'"):
        await scoring.judge(_broken, "", {}, TURN, conversation="c", turn_number=1)
