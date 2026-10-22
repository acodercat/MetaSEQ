"""What every topology shares: its inputs, its per-turn result, and fresh stages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from cave_agent import Variable

from agents.arm import Arm
from agents.harness import Harness
from agents.instructions import TaskBrief
from agents.stage import StageRecord, Usage, run_stage
from agents.workspace import Workspace


@dataclass(frozen=True)
class Team:
    """Fixed for a conversation: who runs, with what, where results must land."""

    arm: Arm
    harness: Harness          # makes every agent and answers plain completions
    workspace: Workspace      # the conversation's workspace; scoring reads its outputs
    system_prompt: str
    brief: TaskBrief
    # Every variable the task declares, then the environment's (metaseq lists them all).
    variables: tuple[Variable, ...] = ()


@dataclass
class TurnOutcome:
    answer: str                                 # the user-facing answer of the turn
    stages: list[StageRecord]
    # How the topology coordinated this turn (fixed_roles: the plan, skipped steps and the
    # outputs before the verifier), with its "kind"; None for the single agent.
    coordination: dict[str, Any] | None = None

    @property
    def steps(self) -> int:
        return sum(s.steps for s in self.stages)

    @property
    def usage(self) -> Usage:
        total = Usage()
        for stage in self.stages:
            total = total + stage.usage
        return total

    @property
    def elapsed_s(self) -> float:
        return sum(s.elapsed_s for s in self.stages)


class Topology(ABC):
    def __init__(self, team: Team):
        self.team = team
        self.arm = team.arm

    @abstractmethod
    async def run_turn(self, query: str, contract: str, outputs: list[Variable]) -> TurnOutcome:
        """Answer the current turn, leaving its outputs in `team.workspace`."""

    async def fresh_stage(
        self,
        role: str,
        instructions: str,
        *,
        query: str,
        task: str,
        steps: int,
    ) -> StageRecord:
        """Run a new agent for one stage, allowed `steps` steps."""
        workspace = self.team.workspace
        agent = self.team.harness.agent(
            workspace,
            max_steps=steps,
            instructions=instructions,
            system_prompt=self.team.system_prompt,
        )
        return await run_stage(agent, workspace, role=role, query=query, task=task,
                               budget=steps)
