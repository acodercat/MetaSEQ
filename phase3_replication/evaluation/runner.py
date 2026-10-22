"""Run one task under one arm with one model."""

from __future__ import annotations

import copy
import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from cave_agent import Variable

from agents import Arm, MetaSEQAgent, TaskBrief, Workspace
from agents.harness import Harness
from agents.workspace import private_copy
from domains import outages
from errors import InfrastructureError, TaskSpecificationError
from evaluation.protocol import code_state
from evaluation.records import ConversationRecord, Cost, RunRecord, TurnRecord
from evaluation.scoring import unserialisable
from tasks import Conversation, Task, TaskModule, Turn

logger = logging.getLogger(__name__)


@dataclass
class RunContext:
    """Everything one run needs besides its task: the arm, the model and the environment."""

    experiment: str
    domain: str
    protocol: str            # `evaluation.protocol` fingerprint of code and environment
    arm: Arm
    harness: Harness         # the model's agents; `system_prompt` is already in its words
    model_fingerprint: dict[str, Any]
    system_prompt: str
    environment_variables: list[Variable]
    environment_functions: list[Callable]


@dataclass
class TaskRun:
    record: RunRecord
    transcripts: dict[str, list[dict[str, Any]]]   # conversation id -> transcript lines


async def run_task(ctx: RunContext, task: Task, module: TaskModule, repeat: int) -> TaskRun:
    started = _now()
    conversations, transcripts, error, kind = [], {}, None, None
    for conversation in task.conversations:
        record, lines, failure = await _run_conversation(ctx, task, module, conversation)
        conversations.append(record)
        transcripts[conversation.id] = lines
        if failure:
            error, kind = failure
            break   # the run is retried whole on resume
    run = RunRecord(
        experiment=ctx.experiment,
        suite=task.suite,
        domain=ctx.domain,
        protocol=ctx.protocol,
        category=task.category,
        task=task.name,
        arm=ctx.arm.model_dump(),
        model=ctx.model_fingerprint,
        repeat=repeat,
        started_at=started,
        finished_at=_now(),
        conversations=conversations,
        error=error,
        error_kind=kind,
        code=code_state(),
        harness=ctx.harness.name,
    )
    return TaskRun(run, transcripts)


async def _run_conversation(
    ctx: RunContext, task: Task, module: TaskModule, conversation: Conversation
) -> tuple[ConversationRecord, list[dict[str, Any]], tuple[str, str] | None]:
    """The conversation's record, its transcript lines, and (error, kind) if it failed."""
    # Fresh variable objects per conversation: mutable defaults must not leak.
    declared = {v.name: v for v in copy.deepcopy(module.variables)}
    upfront = [] if conversation.scoped else list(declared.values())

    workspace = Workspace(
        functions=ctx.environment_functions + module.tools,
        variables=[private_copy(v) for v in ctx.environment_variables] + upfront,
        types=module.types,
    )
    try:
        agent = MetaSEQAgent(
            ctx.arm, ctx.harness, workspace,
            system_prompt=ctx.system_prompt,
            brief=TaskBrief(task.description, task.requirements),
            variables=(*declared.values(), *ctx.environment_variables),
        )

        transcript = f"transcripts/{conversation.id}.jsonl"
        turns, lines = [], []
        for index, turn in enumerate(conversation.turns, 1):
            if conversation.scoped:
                outputs = [declared[name] for name in (turn.stores or ())]
                workspace.register(outputs)
            else:
                outputs = list(declared.values())
            query = turn.query
            try:
                with outages.watch() as lost:
                    query = await _apply_hook(module, turn, workspace, turn.query)
                    outcome = await agent.run_turn(query, outputs)
                if lost:
                    # The agents met the data source going away: not something the
                    # model did, so the run is retried rather than scored.
                    raise InfrastructureError(
                        f"data source lost during the turn ({len(lost)} failures): {lost[0]}",
                        kind="data_source")
                registered = workspace.registered
                values = await workspace.values(n for n in declared if n in registered)
            except InfrastructureError as exc:
                logger.warning("%s/%s turn %d: %s", task.name, conversation.id, index, exc)
                turns.append(TurnRecord(turn=index, query=query, error=str(exc)))
                return (ConversationRecord(conversation.id, turns, transcript), lines,
                        (str(exc), exc.kind))
            except Exception as exc:
                # A fault of the lab's, not the provider's or the model's (an agent that
                # deleted an output, a hook that failed): recorded, and the shard goes on.
                logger.exception("%s/%s turn %d: harness error", task.name, conversation.id,
                                 index)
                error = f"{type(exc).__name__}: {exc}"
                turns.append(TurnRecord(turn=index, query=query, error=error))
                return (ConversationRecord(conversation.id, turns, transcript), lines,
                        (error, "harness"))

            usage = outcome.usage
            turns.append(TurnRecord(
                turn=index,
                query=query,
                response=outcome.answer,
                runtime_variables=values,
                snapshot_unserialisable=unserialisable(values),
                cost=Cost(outcome.steps, usage.prompt_tokens, usage.completion_tokens,
                          usage.total_tokens, outcome.elapsed_s),
                coordination=outcome.coordination,
                stages=[s.to_dict() for s in outcome.stages],
            ))
            for position, stage in enumerate(outcome.stages):
                # The agent's lines (`agents.harness.base`), and where in the run they
                # happened: the turn, the stage's position in it, the agent that ran it.
                lines.extend({**line, "turn": index, "stage": position, "agent": stage.role}
                             for line in stage.transcript)

        return ConversationRecord(conversation.id, turns, transcript), lines, None
    finally:
        workspace.close()     # frees the runtime and everything its agents loaded


async def _apply_hook(module: TaskModule, turn: Turn, workspace: Workspace, query: str) -> str:
    if not turn.pre_turn_hook:
        return query
    try:
        result = module.hooks[turn.pre_turn_hook](workspace.runtime, turn)
        if inspect.isawaitable(result):
            result = await result
    except Exception as exc:
        raise TaskSpecificationError(f"hook {turn.pre_turn_hook} crashed: {exc}") from exc
    return result if result is not None else query


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
