"""The MetaSEQ topology: a coordinator plans over domain workers sharing one runtime, a
synthesis worker assigns the outputs and, with `verification`, a verifier audits them.

The mechanics follow the group's released multi-agent harness (`MultiAgentWrapper`), which
the tests compare them with. Per turn:

    coordinator   one model call for a JSON plan over the four producer roles
                  (data_acquisition, knowledge_retrieval, pollution_analysis,
                  multivariate_meteo); an unusable reply gives the fixed default plan
    producers     the planned roles in order, each a fresh agent over the
                  conversation's workspace, shown what is staged ({name: type})
    synthesis     always last (appended when the plan does not end with it):
                  assigns the turn's outputs
    verifier      `arm.verification`: rechecks every output and may reassign it
                  (`agents.verification`)

Budget: `max_steps` in all (20 as released). The coordinator's one planning call
is not counted as a step. The verifier holds `verify_steps` back and synthesis
`synthesis_steps` (6 and 3 as released); each producer may use all of what is left
of the rest, and a producer is skipped once that is spent; the verifier gets
whatever the turn has not used. Without the verifier the whole budget goes to the
producers and synthesis. Every stage's tokens count, the coordinator's included.

The prompts are the harness's with the analysis knowledge removed
(prompts/fixed_roles/stripped; see prompts/fixed_roles/README.md).
"""

from __future__ import annotations

import json
import time
from typing import Any

from cave_agent import Variable
from cave_agent.models.errors import ModelError

from agents import instructions
from agents.failure import classify
from agents.instructions import SYNTHESIS, VERIFICATION
from agents.stage import StageRecord, Usage
from agents.topologies.base import Team, Topology, TurnOutcome
from agents.verification import manifest, output_values, required_outputs, verified_answer, verify
from agents.workspace import own_copy
from errors import InfrastructureError

COORDINATOR = "coordinator"
PRODUCERS = ("data_acquisition", "knowledge_retrieval", "pollution_analysis", "multivariate_meteo")
ROLES = (*PRODUCERS, SYNTHESIS, VERIFICATION)
DEFAULT_PIPELINE = ("data_acquisition", "pollution_analysis", "multivariate_meteo", SYNTHESIS)
MAX_PLAN_STEPS = 6


class FixedRoles(Topology):
    def __init__(self, team: Team):
        super().__init__(team)
        self._queries: list[str] = []

    async def run_turn(
        self, query: str, contract: str, outputs: list[Variable]
    ) -> TurnOutcome:
        self._queries.append(query)
        context = instructions.fixed_roles_context(self._queries)
        required = required_outputs(outputs)
        plan, fallback, coordinator = await self._plan(context, required)
        stages = [coordinator]
        used = 0
        answer = synthesis = ""
        skipped: list[dict[str, str]] = []

        total = self.arm.max_steps
        plan_budget = total - (self.arm.verify_steps if self.arm.verification else 0)
        pool = plan_budget - self.arm.synthesis_steps
        last = len(plan) - 1
        for index, step in enumerate(plan):
            if index == last:                       # synthesis: its reserve and what is left
                steps = plan_budget - used
            else:
                steps = pool - used                 # all of the pool that is left
                if steps < 1:
                    skipped.append(step)            # the pool is spent: skip, keep the budget
                    continue
            record = await self._worker(step["role"], step["task"], context, required, steps)
            stages.append(record)
            used += record.steps
            if record.answer.strip():
                answer = record.answer
                if step["role"] == SYNTHESIS:
                    synthesis = record.answer

        answered = synthesis or answer
        before = None
        if self.arm.verification and required:
            # Copied: the verifier may change a list or frame in place.
            before = {name: own_copy(value)
                      for name, value in (await output_values(self)).items()}
            record = await verify(self, query=query, context=context, required=required,
                                  steps=total - used)
            stages.append(record)
            answered = verified_answer(record, answered)

        return TurnOutcome(
            answer=answered,
            stages=stages,
            coordination={"kind": "fixed_roles", "plan": plan, "skipped": skipped,
                          "fallback": fallback["reason"] if fallback else None,
                          "before_verification": before,
                          "answer_before_verification": (synthesis or answer)
                          if before is not None else None},
        )

    async def _plan(self, context: str, required: str
                    ) -> tuple[list[dict[str, str]], dict[str, str] | None, StageRecord]:
        """The coordinator's plan, why the default plan replaced it (None when it did not),
        and its record.

        The default plan replaces a reply that holds no usable plan, as in the harness,
        and a reply the model failed to give (`agents.failure.classify`); a provider failure
        is the infrastructure's and raises, as in every other stage."""
        started = time.monotonic()
        text, usage, fallback = "", Usage(), None
        try:
            response = await self.team.harness.complete(
                instructions.fixed_roles_coordinator(context, required))
            text, usage = response.content or "", Usage.of(response.usage)
        except ModelError as exc:
            failure = classify(exc)
            if not failure.model_fault:
                raise InfrastructureError(f"{COORDINATOR}: {failure.kind}: {exc}",
                                          kind=failure.kind) from exc
            fallback = {"reason": f"model_failure:{failure.kind}"}
        if fallback is None:
            try:
                plan = parse_plan(text, context)
            except (ValueError, TypeError, KeyError) as exc:    # JSONDecodeError included
                fallback = {"reason": f"unparsed plan: {type(exc).__name__}: {exc}"}
        if fallback is not None:
            plan = default_plan(context)
        record = StageRecord(role=COORDINATOR, task="plan", budget=0, steps=0,
                             stop_reason="fallback" if fallback else "completed", answer=text,
                             code=[], usage=usage, elapsed_s=time.monotonic() - started,
                             changed=[])
        return plan, fallback, record

    async def _worker(self, role: str, task: str, context: str, required: str,
                      steps: int) -> StageRecord:
        return await self.fresh_stage(
            role,
            instructions.fixed_roles_worker(role, self.team.brief, task=task,
                                         manifest=await manifest(self.team.workspace),
                                         context=context, required=required,
                                         verified=self.arm.verification),
            query=task, task=task, steps=steps,
        )


def parse_plan(text: str, context: str) -> list[dict[str, Any]]:
    """The coordinator's steps as the harness read them: known roles, at most six,
    synthesis appended when it is not last. Raises when there is no usable plan."""
    start, end = text.find("["), text.rfind("]") + 1
    if start < 0 or end <= start:
        raise ValueError("no JSON array in coordinator output")
    steps = [
        {"role": step["role"], "task": str(step.get("task", context))}
        for step in json.loads(text[start:end])
        if isinstance(step, dict) and step.get("role") in ROLES
    ][:MAX_PLAN_STEPS]
    if not steps:
        raise ValueError("empty plan")
    if steps[-1]["role"] != SYNTHESIS:
        steps.append({"role": SYNTHESIS, "task": context})
    return steps


def default_plan(context: str) -> list[dict[str, Any]]:
    """The harness's fixed plan, used when the coordinator's reply is unusable."""
    return [{"role": role, "task": context} for role in DEFAULT_PIPELINE]
