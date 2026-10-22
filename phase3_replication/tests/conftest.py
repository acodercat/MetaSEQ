from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from domains import Domain, register_domain
from tasks import Suite
from tests.fakes import FakeEndpoint

FIXTURES = Path(__file__).parent / "fixtures"

register_domain(
    "toy",
    lambda: Domain(
        "toy",
        handles={"readings_df": lambda: pd.DataFrame({"value": [10.0, 12.0, 20.0]})},
        functions={},
    ),
)


@pytest.fixture
def toy_suite() -> Suite:
    return Suite.load("toy", suites_dir=FIXTURES / "suites")


@pytest.fixture
def endpoint(monkeypatch) -> FakeEndpoint:
    """The tool gateway's endpoint, offline: every `ToolGateway` made in the test talks to it."""
    fake = FakeEndpoint()
    monkeypatch.setattr("llm.tool_gateway.openai.AsyncOpenAI", fake.client)
    return fake

