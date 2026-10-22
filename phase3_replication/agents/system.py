"""MetaSEQAgent: the system under test, assembled from an `Arm`.

One instance per conversation. `run_turn` executes one user turn with the arm's
topology.
"""

from __future__ import annotations

from cave_agent import Variable

from agents import instructions
from agents.arm import Arm
from agents.harness import Harness
from agents.instructions import TaskBrief
from agents.topologies import Team, TurnOutcome, build_topology
from agents.workspace import Workspace


class MetaSEQAgent:
    def __init__(
        self,
        arm: Arm,
        harness: Harness,
        workspace: Workspace,
        *,
        system_prompt: str,
        brief: TaskBrief,
        variables: tuple[Variable, ...] = (),
    ):
        self.arm = arm
        self._team = Team(arm, harness, workspace, system_prompt, brief, variables)
        self._topology = build_topology(self._team)
        self._queries: list[str] = []

    async def run_turn(self, query: str, outputs: list[Variable]) -> TurnOutcome:
        """Answer one turn. `outputs` are the variables this turn must assign."""
        self._queries.append(query)
        contract = instructions.conversation_contract(self._queries)
        return await self._topology.run_turn(query, contract, outputs)
