"""One agent answers every turn, keeping its own history across turns."""

from __future__ import annotations

from cave_agent import Variable

from agents import instructions
from agents.stage import run_stage
from agents.topologies.base import Team, Topology, TurnOutcome

ROLE = "solo"


class Single(Topology):
    def __init__(self, team: Team):
        super().__init__(team)
        self._steps = team.arm.max_steps
        self._agent = team.harness.agent(
            team.workspace,
            max_steps=self._steps,
            instructions=instructions.solo(team.brief),
            system_prompt=team.system_prompt,
        )

    async def run_turn(
        self, query: str, contract: str, outputs: list[Variable]
    ) -> TurnOutcome:
        record = await run_stage(self._agent, self.team.workspace, role=ROLE, query=query,
                                 task=query, budget=self._steps)
        return TurnOutcome(answer=record.answer, stages=[record])
