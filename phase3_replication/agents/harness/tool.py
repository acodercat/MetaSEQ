"""The tool harness: the agent runs its code through one native ``python`` tool call
(`agents.harness.tool_agent`), over the tool gateway (`llm.tool_gateway`). Models built to act
through tool calls (GPT-6 Luna) write fences rarely and unreliably, so this is the harness a
backbone comparison can hold them all under.
"""

from __future__ import annotations

from typing import Self

import httpx
from cave_agent import ModelResponse

from agents.harness.base import EXEC_OUTPUT_CHARS, STREAM_IDLE_TIMEOUT, Agent, Harness
from agents.harness.tool_agent import ToolAgent
from agents.harness.tool_prompt import for_tool_harness
from agents.workspace import Workspace
from llm import DEFAULT_TIMEOUT_S, TRANSPORT_RETRIES, ModelConfig
from llm.tool_gateway import Gateway, ToolGateway

# Seconds to open a connection: an unreachable endpoint fails fast and is retried, instead of
# holding a step for a whole read timeout per retry.
CONNECT_TIMEOUT_S = 30.0


def request_timeout(config: ModelConfig) -> httpx.Timeout:
    """The model's own timeout for each phase of a request, but a stream may stay silent as
    long as a cell may block the loop it is read on (`STREAM_IDLE_TIMEOUT`)."""
    limit = config.timeout or DEFAULT_TIMEOUT_S
    return httpx.Timeout(limit, connect=min(CONNECT_TIMEOUT_S, limit),
                         read=max(limit, STREAM_IDLE_TIMEOUT))


class ToolHarness(Harness):
    name = "tool"

    def __init__(self, gateway: Gateway):
        self._gateway = gateway

    @classmethod
    def for_model(cls, config: ModelConfig) -> Self:
        return cls(ToolGateway(config, timeout=request_timeout(config),
                               retries=TRANSPORT_RETRIES))

    @staticmethod
    def system_prompt(prompt: str) -> str:
        return for_tool_harness(prompt)

    async def complete(self, messages: list[dict[str, str]]) -> ModelResponse:
        return await self._gateway.complete(messages)

    def agent(self, workspace: Workspace, *, max_steps: int, instructions: str | None,
              system_prompt: str) -> Agent:
        return ToolAgent(self._gateway, runtime=workspace.runtime, max_steps=max_steps,
                         max_exec_output=EXEC_OUTPUT_CHARS, instructions=instructions,
                         system_instructions=system_prompt)
