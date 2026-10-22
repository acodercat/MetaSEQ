"""How code reaches the runtime: the agent runs its code through one native ``python`` tool
call per step (`agents.harness.tool`).
"""

from __future__ import annotations

from typing import assert_never

from agents.harness.base import (
    EXEC_OUTPUT_CHARS,
    STREAM_IDLE_TIMEOUT,
    Agent,
    Harness,
    HarnessName,
)
from llm import ModelConfig

__all__ = ["EXEC_OUTPUT_CHARS", "STREAM_IDLE_TIMEOUT", "Agent", "Harness", "HarnessName",
           "build_harness", "harness_type"]


def harness_type(name: HarnessName) -> type[Harness]:
    """The harness class *name* names."""
    match name:
        case "tool":
            from agents.harness.tool import ToolHarness
            return ToolHarness
        case _:
            assert_never(name)


def build_harness(name: HarnessName, config: ModelConfig) -> Harness:
    """The harness *name* over the endpoint *config* describes."""
    return harness_type(name).for_model(config)
