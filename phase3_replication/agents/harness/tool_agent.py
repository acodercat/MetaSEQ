"""An agent that executes Python through one native tool call: the tool harness.

The code harness's `CaveAgent` reads code out of the model's text (one fenced ```python block
per step); this agent offers a ``python`` tool and runs the ``code`` argument of each call.
Everything else is held the same, so the two harnesses differ in how code reaches the runtime
and in nothing the lab controls:

- the same runtime (`agents.workspace.Workspace.runtime`): the namespace, registered
  functions, security checker and the time per cell;
- the same system prompt template, filled from the runtime as `CaveAgent` fills it, with only
  the suite prompt's protocol paragraphs swapped (`agents.harness.tool_prompt`);
- the same output shaping and feedback texts, imported from cave-agent where it defines them;
- the same `AgentResponse` and `StopReason`, and `CaveAgent`'s rules for counting steps,
  filtered replies and output cuts (the guarantees below);
- the same transcript schema (`agents.harness.base`): a call is written as cave-agent writes a
  turn that ran code, its result as an execution result.

The loop: send the history, run the step's tool call, answer it, repeat. A response with no
tool call is the final answer. It guarantees:

1. Every step is counted before it is sent, one that fails included, as `CaveAgent` counts.
2. Every tool call is answered, in the order asked; a call that did not run says so and why.
   (A runtime that fails, or a filtered reply, ends the run as an infrastructure failure,
   whose history is not kept.)
3. At most one execution per step: the gateway asks for one call, and any further call an
   endpoint sends anyway is answered as not run.
4. A refusal with no other text is the answer, even under a content-filter finish; text the
   filter withdrew, or a filtered reply with none, is no answer.
5. A reply the output cap cut is resumed, and a call it cut before its arguments ended runs
   nothing and counts as a cut too; consecutive cuts use up cave-agent's recovery limit.
6. A run that ends ``MODEL_ERROR`` -- a reply with neither text nor a call, a cut past the
   last recovery, a filtered reply, a provider failure -- says why in
   :attr:`ToolAgent.failure` (`agents.failure`).
7. The budget is :attr:`ToolAgent.max_steps`, read at each step; running out ends the run
   ``MAX_STEPS``, with no answer forced on the last step, as under `CaveAgent`.

The layers: the gateway (`llm.tool_gateway`) is transport and wire format and knows no tool;
the tool, what a call carries and what the model is told an execution did, is
`agents.harness.python_tool`; the history as transcript lines is
`agents.harness.tool_transcript`. This module is the loop and nothing else.

Known differences from `CaveAgent`, beyond the protocol (AirBench's list): the model's own
reasoning goes back to it on later steps; tool results are the raw execution output, without
the ``<execution_output>`` wrapper and its per-step reminder; no context compaction, so a
prompt past the window ends the run as the model's failure where `CaveAgent` would compact and
go on; no resumption of a stream that breaks mid-reply (that step fails as a provider error
and the run is retried); a stalled stream ends at the client read timeout.

Ported from AirBench (``adapters/tool_agent.py`` at d5bcc29), itself from FinBench.

Texts and limits taken from cave-agent's internals (pinned at 0.8.0, so that both harnesses
answer the model in the same words): ``_placeholders.OUTPUT_RECOVERY_PROMPT`` and
``agent.MAX_OUTPUT_RECOVERIES``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from cave_agent import AgentResponse, StopReason
from cave_agent._placeholders import OUTPUT_RECOVERY_PROMPT
from cave_agent.agent import MAX_OUTPUT_RECOVERIES
from cave_agent.models.base import TokenUsage
from cave_agent.models.errors import ModelError
from cave_agent.prompts import DEFAULT_INSTRUCTIONS, DEFAULT_SYSTEM_PROMPT_TEMPLATE
from cave_agent.runtime import Runtime, RuntimeExecutionError
from cave_agent.skills import SkillRegistry
from cave_agent.utils import sanitize_surrogates

from agents.failure import EMPTY_ANSWER, FILTERED, TRUNCATED, WITHDRAWN, Failure, classify
from agents.harness.python_tool import BAD_ARGUMENTS, PYTHON, code_of, execution_output
from agents.harness.tool_transcript import transcript_lines
from llm.tool_gateway import Gateway, Step, ToolCall

logger = logging.getLogger(__name__)

# Replies to a call that was not run. Each says so, so that the model cannot read an
# unexecuted call as a silent success.
UNKNOWN_TOOL = f"There is no tool named {{name}}; the only tool is `{PYTHON.name}`. Nothing ran."
CUT_ARGUMENTS = "The call was cut off at the output limit before its arguments ended. Nothing ran."
EXTRA_CALL = "Only one tool call runs per step, and this was not the first. Nothing ran."


@dataclass
class _Run:
    """What one :meth:`ToolAgent.run` has done so far."""

    started: float = field(default_factory=time.monotonic)
    steps: int = 0
    usage: TokenUsage = field(default_factory=TokenUsage)
    code_snippets: list[str] = field(default_factory=list)
    text: str = ""
    pending: str = ""       # text of replies cut at the output cap, which the next continues
    output_recoveries: int = 0

    def stop(self, reason: StopReason) -> AgentResponse:
        return AgentResponse(content=self.text, stop_reason=reason, steps=self.steps,
                             elapsed=time.monotonic() - self.started, usage=self.usage,
                             code_snippets=self.code_snippets)


class ToolAgent:
    """The tool harness's agent: the lab's `agents.harness.base.Agent`."""

    def __init__(
        self,
        gateway: Gateway,
        *,
        runtime: Runtime,
        system_instructions: str,
        max_steps: int,
        max_exec_output: int,
        instructions: str | None = None,
        exec_output_preview_chars: int = 2_000,
    ):
        """Without *instructions*, cave-agent's default, as `CaveAgent`'s."""
        self.runtime = runtime
        self.instructions = instructions if instructions is not None else DEFAULT_INSTRUCTIONS
        # CaveAgent formats its system instructions once, which turns the prompts' doubled
        # braces back into single ones.
        self.system_instructions = system_instructions.format(python_block_identifier="python")
        self.max_steps = max_steps
        # Why the last run ended with MODEL_ERROR; None when it did not.
        self.failure: Failure | None = None
        self.max_exec_output = max_exec_output
        self.exec_output_preview_chars = exec_output_preview_chars
        self._conversation = gateway.conversation([PYTHON])

    @property
    def messages(self) -> list[dict[str, Any]]:
        return self._conversation.messages

    def build_system_prompt(self) -> str:
        """CaveAgent's prompt, filled from the runtime's current registrations."""
        return DEFAULT_SYSTEM_PROMPT_TEMPLATE.format(
            instructions=self.instructions,
            system_instructions=self.system_instructions,
            functions=self.runtime.describe_functions(),
            variables=self.runtime.describe_variables(),
            types=self.runtime.describe_types(),
            skills=SkillRegistry().describe_skills(),
        )

    async def run(self, query: str) -> AgentResponse:
        run = _Run()
        self.failure = None
        # Rebuilt per run: a later turn registers outputs the earlier prompt did not list.
        self._conversation.set_system(self.build_system_prompt())
        self._conversation.add_user(sanitize_surrogates(query))
        while run.steps < self.max_steps:
            run.steps += 1              # a step that fails is still spent, as in CaveAgent
            try:
                step = await self._conversation.step()
            except ModelError as error:
                logger.warning("Model error — ending run: %s", error)
                return self._fail(run, classify(error))
            run.usage = run.usage + step.usage
            run.text = run.pending + step.text
            if step.finish_reason == "content_filter" and not step.refused:
                return self._fail(run, WITHDRAWN if step.text else FILTERED)
            if step.tool_calls:
                run.pending = ""
                cut = _cut_call(step)
                try:
                    await self._answer_calls(step, run, cut=cut)
                except RuntimeExecutionError:
                    logger.exception("Runtime error — ending run")
                    return run.stop(StopReason.RUNTIME_ERROR)
                if cut:
                    # Nothing ran: a cut like any other.
                    if not self._spend_recovery(run):
                        return self._fail(run, TRUNCATED)
                else:
                    run.output_recoveries = 0       # only consecutive cuts use them up
            elif step.finish_reason == "length":
                # Cut at the output cap with no call: resume, as CaveAgent does.
                if not self._spend_recovery(run):
                    return self._fail(run, TRUNCATED)
                run.pending = run.text
                self._conversation.add_user(OUTPUT_RECOVERY_PROMPT)
            elif run.text.strip():
                return run.stop(StopReason.COMPLETED)
            else:
                return self._fail(run, EMPTY_ANSWER)
        return run.stop(StopReason.MAX_STEPS)

    def _fail(self, run: _Run, failure: Failure) -> AgentResponse:
        self.failure = failure
        return run.stop(StopReason.MODEL_ERROR)

    @staticmethod
    def _spend_recovery(run: _Run) -> bool:
        """Count one more consecutive cut; ``False`` once none are left."""
        if run.output_recoveries == MAX_OUTPUT_RECOVERIES:
            return False
        run.output_recoveries += 1
        return True

    async def _answer_calls(self, step: Step, run: _Run, *, cut: bool) -> None:
        """Answer every call the step made: the first is run, the rest are not."""
        first, *extra = step.tool_calls
        answers = [(first.id, await self._answer(first, cut=cut, run=run))]
        answers += [(call.id, EXTRA_CALL) for call in extra]
        for call_id, output in answers:
            self._conversation.add_tool_result(call_id, output)

    async def _answer(self, call: ToolCall, *, cut: bool, run: _Run) -> str:
        """The reply to *call*, after running it if it can run. *cut*: the output cap cut
        it before its arguments ended."""
        if call.name != PYTHON.name:
            return UNKNOWN_TOOL.format(name=call.name)
        code = code_of(call.arguments)
        if code is None:
            return CUT_ARGUMENTS if cut else BAD_ARGUMENTS
        run.code_snippets.append(code)
        return await execution_output(self.runtime, await self.runtime.execute(code),
                                      max_chars=self.max_exec_output,
                                      preview_chars=self.exec_output_preview_chars)

    def transcript(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [line for message in messages for line in transcript_lines(message)]

    def compactions(self, messages: list[dict[str, Any]]) -> int:
        return 0                        # the tool harness keeps the whole history


def _cut_call(step: Step) -> bool:
    """The output cap cut the step's (first) call before its arguments ended. A call whose
    arguments are whole but carry no code was not cut, whatever the finish."""
    return step.finish_reason == "length" and step.tool_calls[0].is_malformed

