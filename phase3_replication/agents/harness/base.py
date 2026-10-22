"""What every harness provides and every agent answers to.

A harness makes every agent of a run, answers the plain completions that are not agents (the
coordinator's plan) and gives the suite prompt in its protocol's words; topologies, prompts,
budgets, the runtime and scoring are shared. An agent runs a query, keeps its history,
says why a run ended without an answer (`agents.failure`), and writes its history as transcript
lines in one schema, whichever harness made it.

Transcript lines are AirBench's: ``type``, ``role`` (as the provider saw it) and ``content``
(text), plus whatever else a harness keeps (a call's ``call_id``, a Responses message's
``phase``). ``type`` names the kind of message in cave-agent's message class names --
``SystemMessage``, ``UserMessage``, ``AssistantMessage``, ``CodeExecutionMessage`` (a turn that
ran code, the code as a fenced block), ``ExecutionResultMessage``, ``SummaryMessage`` -- and
``ReasoningMessage`` for a reasoning summary the tool harness keeps. Readers such as
`analysis.study` rely on that vocabulary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal, Protocol, Self

from cave_agent import AgentResponse, ModelResponse

from agents.failure import Failure
from agents.workspace import Workspace
from llm import ModelConfig

HarnessName = Literal["tool"]

# Characters of an execution's output shown inline; a longer one is kept in the runtime.
EXEC_OUTPUT_CHARS = 10_000
# Seconds a model stream may stay silent. Above cave-agent's 120 s because concurrent agents
# share one event loop and one agent's long cell holds the others' streams; longer than a cell
# may run (`domains.cell_time`), as a cell blocks the loop for up to that long.
STREAM_IDLE_TIMEOUT = 1200.0


class Agent(Protocol):
    """What the lab asks of an agent (`agents.stage.run_stage`)."""

    max_steps: int                  # settable between runs (a resumed single agent)
    failure: Failure | None         # why the last run ended with MODEL_ERROR; None otherwise

    @property
    def messages(self) -> list[Any]:
        """The history, in the agent's own form; new messages are told apart by identity."""

    async def run(self, query: str) -> AgentResponse: ...

    def transcript(self, messages: list[Any]) -> list[dict[str, Any]]:
        """*messages* (from `messages`) as transcript lines (this module's schema)."""

    def compactions(self, messages: list[Any]) -> int:
        """How many times the history was summarised among *messages*."""


class Harness(ABC):
    name: HarnessName

    @classmethod
    @abstractmethod
    def for_model(cls, config: ModelConfig) -> Self:
        """This harness over the endpoint *config* describes."""

    @staticmethod
    @abstractmethod
    def system_prompt(prompt: str) -> str:
        """The suite system prompt as this harness's agents read it."""

    @abstractmethod
    def agent(self, workspace: Workspace, *, max_steps: int, instructions: str | None,
              system_prompt: str) -> Agent:
        """A new agent over *workspace*'s runtime. Without *instructions*, cave-agent's
        default, which is what the archived single agent saw for a task with no brief."""

    @abstractmethod
    async def complete(self, messages: list[dict[str, str]]) -> ModelResponse:
        """One plain reply, no code run. A failure raises cave-agent's typed `ModelError`."""
