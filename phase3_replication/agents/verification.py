"""The verifier stage the MetaSEQ topology ends every turn with."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from cave_agent import Variable

from agents import instructions
from agents.instructions import VERIFICATION
from agents.stage import StageRecord
from agents.workspace import Workspace

if TYPE_CHECKING:
    from agents.topologies.base import Topology

_IPYTHON_NAMES = ("In", "Out", "exit", "quit", "get_ipython")


async def manifest(workspace: Workspace) -> str:
    """What the agents have staged in the shared runtime, as the harness printed it:
    {name: type}.

    The harness ran a `locals()` probe in the runtime; the lab's security
    checker forbids that in agent code, so the same filter is applied to the
    namespace, read without executing anything. The environment's own data (the
    frames and handles every agent is given, described in the system prompt) are
    left out: they are not something an agent staged or a verifier should recheck.
    cave-agent queues a registration until the runtime's next read, so the outputs
    a turn has just registered (reset to None) are landed first; read before that,
    the namespace still showed what an earlier turn left under those names.
    """
    await workspace._land(workspace.registered)
    environment = workspace.environment_names
    return str({
        name: type(value).__name__
        for name, value in list(workspace.namespace().items())
        if not name.startswith("_") and name not in _IPYTHON_NAMES
        and name not in environment
        and value is not None and not callable(value) and type(value).__name__ != "module"
    })


def required_outputs(outputs: Iterable[Variable]) -> str:
    """The current turn's outputs, listed as the harness listed them.

    `outputs` are the turn's own: in a task that reveals its outputs turn by turn,
    the ones this turn stores, so outputs completed in earlier turns (immutable
    under the turn rules) and later turns' are not asked for; otherwise every
    declared output. The environment's variables are never among them.
    """
    return instructions.fixed_roles_required(list(outputs))


async def output_values(topology: Topology) -> dict[str, Any]:
    """The declared outputs' current values (the environment's variables excluded)."""
    workspace = topology.team.workspace
    return await workspace.values(sorted(workspace.registered - workspace.environment_names))


async def verify(topology: Topology, *, query: str, context: str, required: str,
                 steps: int) -> StageRecord:
    """The verifier, over the conversation's workspace, for at most `steps` steps.

    As in the harness: its subtask is the turn's query, it is run on the
    conversation so far, and it sees what is staged at that moment.
    """
    return await topology.fresh_stage(
        VERIFICATION,
        instructions.fixed_roles_worker(
            VERIFICATION, topology.team.brief, task=query,
            manifest=await manifest(topology.team.workspace), context=context,
            required=required, verified=True),
        query=context, task=query, steps=steps,
    )


def verified_answer(verifier: StageRecord, before: str) -> str:
    """The turn's answer after a verifier: its reply when it finished, else the answer it
    was given (a verifier stopped at its cap leaves code, not an answer)."""
    return verifier.answer if verifier.stop_reason == "completed" and verifier.answer.strip() \
        else before
