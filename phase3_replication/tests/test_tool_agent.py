"""The tool harness's agent runs what the model asks, answers every call, and ends its runs
as CaveAgent does, so the lab classifies both alike. Ported from AirBench."""

from __future__ import annotations

import json
from types import SimpleNamespace as NS

import httpx
import pytest
from cave_agent import StopReason, Variable
from cave_agent._placeholders import OUTPUT_RECOVERY_PROMPT
from cave_agent.agent import MAX_OUTPUT_RECOVERIES
from cave_agent.models.base import TokenUsage
from cave_agent.models.errors import PromptTooLongError, ProviderError
from cave_agent.prompts import SECURITY_ERROR_PROMPT
from cave_agent.runtime import RuntimeExecutionError
from cave_agent.security import SecurityError

from agents.harness import EXEC_OUTPUT_CHARS
from agents.harness.python_tool import BAD_ARGUMENTS, PYTHON
from agents.harness.tool_agent import CUT_ARGUMENTS, EXTRA_CALL, UNKNOWN_TOOL, ToolAgent
from agents.workspace import Workspace
from llm import ModelConfig
from llm.tool_gateway import Step, ToolCall, ToolGateway
from tests.fakes import SDKStream, final_event, function_call, output_message, responses_reply


def _call(code, call_id="c1", name="python"):
    """A call running *code*; ``None`` gives arguments that stop short, as a cut call's do."""
    arguments = json.dumps({"code": code}) if code is not None else '{"code": "'
    return ToolCall(call_id, name, arguments)


def _step(text="", calls=(), finish=None):
    return Step(text, tuple(calls), finish or ("tool_calls" if calls else "stop"),
                TokenUsage(10, 5, 15))


class _Scripted:
    """A gateway that plays scripted steps and records what the agent sent. It is its own
    conversation: the agent opens one, and these tests read what it was told there."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.system, self.users, self.results, self.history = [], [], [], []
        self.tools = None

    def conversation(self, tools):
        self.tools = list(tools)
        return self

    @property
    def messages(self):
        return self.history

    def set_system(self, prompt):
        self.system.append(prompt)

    def add_user(self, text):
        self.users.append(text)

    def add_tool_result(self, call_id, output):
        self.results.append((call_id, output))

    async def step(self):
        return self.steps.pop(0)


class _Failing(_Scripted):
    """Raises *error* on its first step, then plays *steps*."""

    def __init__(self, error, steps=()):
        super().__init__(steps)
        self.error = error

    async def step(self):
        if self.error is not None:
            error, self.error = self.error, None
            raise error
        return await super().step()


class _Runtime:
    def __init__(self, outputs=None):
        self.ran, self.outputs, self.bound = [], dict(outputs or {}), {}

    def describe_variables(self):
        return "- name: answer\n  type: NoneType\n  description: The answer."

    def describe_functions(self):
        return "No functions available"

    def describe_types(self):
        return "No types available"

    async def execute(self, code):
        self.ran.append(code)
        return NS(success=True, error=None, stdout=self.outputs.get(code, "ok"), state_lost=False)

    async def bind_unique(self, prefix, value, start=1):
        name = f"{prefix}_{len(self.bound) + 1}"
        self.bound[name] = value
        return name


def _agent(steps, runtime=None, max_steps=14, gateway=None):
    gateway = gateway or _Scripted(steps)
    return ToolAgent(gateway, runtime=runtime or _Runtime(), system_instructions="Analyse.",
                     max_steps=max_steps, max_exec_output=EXEC_OUTPUT_CHARS), gateway


async def _outcome(agent):
    """Run *agent*; its response, and (kind, the model's) of the failure it recorded, if any."""
    result = await agent.run("q")
    failure = agent.failure
    return result, (failure.kind, failure.model_fault) if failure else None


async def test_runs_each_call_then_returns_the_text_answer():
    agent, gateway = _agent([_step(calls=[_call("print(1)")]),
                             _step(calls=[_call("answer = 2", "c2")]), _step("The answer is 2.")])
    result = await agent.run("question")
    assert result.stop_reason is StopReason.COMPLETED and result.content == "The answer is 2."
    assert (result.steps, result.code_snippets, result.usage.total_tokens) == (
        3, ["print(1)", "answer = 2"], 45)
    assert agent.runtime.ran == ["print(1)", "answer = 2"]
    assert gateway.results == [("c1", "ok"), ("c2", "ok")] and gateway.users == ["question"]
    assert "<variables>" in gateway.system[0] and "answer" in gateway.system[0]
    assert gateway.tools == [PYTHON]                    # the agent's one tool, offered


async def test_a_step_runs_one_call_and_answers_the_rest_as_not_run():
    agent, gateway = _agent([_step(calls=[_call("a = 1", "c1"), _call("b = 2", "c2")]),
                             _step("done")])
    result = await agent.run("q")
    assert agent.runtime.ran == ["a = 1"] and result.code_snippets == ["a = 1"]
    assert gateway.results == [("c1", "ok"), ("c2", EXTRA_CALL)]


async def test_a_call_that_cannot_run_is_answered_without_running():
    agent, gateway = _agent([_step(calls=[_call("x", "c1", name="shell")]),
                             _step(calls=[_call(None, "c2")]),
                             _step(calls=[_call(None, "c3")], finish="length"), _step("done")])
    await agent.run("q")
    assert agent.runtime.ran == []
    assert gateway.results == [("c1", UNKNOWN_TOOL.format(name="shell")), ("c2", BAD_ARGUMENTS),
                               ("c3", CUT_ARGUMENTS)]


async def test_an_empty_answer_is_the_models_failure_as_under_cave_agent():
    result, kind = await _outcome(_agent([_step("  ")])[0])
    assert result.stop_reason is StopReason.MODEL_ERROR and kind == ("empty_answer", True)


async def test_a_filtered_step_or_a_provider_failure_is_the_infrastructures():
    filtered = _agent([_step(finish="content_filter")])[0]
    unreachable = _agent([], gateway=_Failing(ProviderError("APIConnectionError: reset")))[0]
    assert (await _outcome(filtered))[1] == ("content_filter", False)
    assert (await _outcome(unreachable))[1] == ("provider", False)


async def test_a_prompt_past_the_window_is_the_models_and_a_new_run_starts_clean():
    agent, _ = _agent([], gateway=_Failing(PromptTooLongError("context_length_exceeded"),
                                           [_step("fine")]))
    assert (await _outcome(agent))[1] == ("prompt_too_long", True)
    assert (await agent.run("again")).stop_reason is StopReason.COMPLETED
    assert agent.failure is None


async def test_any_other_failure_is_a_defect_and_propagates():
    agent = _agent([], gateway=_Failing(TypeError("bad parse")))[0]
    with pytest.raises(TypeError):
        await agent.run("q")


async def test_the_step_budget_ends_the_run_and_can_be_changed_between_runs():
    agent, gateway = _agent([_step(calls=[_call("print(1)")])] * 3, max_steps=2)
    result = await agent.run("q")
    assert result.stop_reason is StopReason.MAX_STEPS and result.steps == 2
    agent.max_steps = 1
    gateway.steps = [_step("final")]
    assert (await agent.run("nudge")).steps == 1 and len(gateway.system) == 2


async def test_oversize_output_is_kept_in_the_runtime_and_previewed():
    runtime = _Runtime({"print(big)": "x" * 12000})
    agent, gateway = _agent([_step(calls=[_call("print(big)")]), _step("done")], runtime=runtime)
    await agent.run("q")
    (_, output), = gateway.results
    assert runtime.bound == {"_output_1": "x" * 12000}
    assert "_output_1" in output and len(output) < 3000


async def test_on_the_labs_runtime_the_assigned_output_is_there_and_blocked_code_is_refused():
    ws = Workspace(functions=[], variables=[Variable("answer", None, "The answer.")])
    agent, gateway = _agent([_step(calls=[_call("answer = 6 * 7\nprint(answer)")]),
                             _step(calls=[_call("import os", "c2")]), _step("42")],
                            runtime=ws.runtime)
    result = await agent.run("q")
    assert result.stop_reason is StopReason.COMPLETED
    assert await ws.runtime.retrieve("answer") == 42
    assert gateway.results[0][1].strip() == "42"
    assert gateway.results[1][1].startswith(SECURITY_ERROR_PROMPT.split("{")[0])
    ws.close()


async def test_a_reply_cut_at_the_output_cap_is_resumed_then_is_the_models_failure():
    agent, gateway = _agent([_step("The ratio is 1.2 because", finish="length"),
                             _step(" margins rose.")])
    result = await agent.run("q")
    assert result.stop_reason is StopReason.COMPLETED
    assert result.content == "The ratio is 1.2 because margins rose."
    assert gateway.users == ["q", OUTPUT_RECOVERY_PROMPT]

    agent, gateway = _agent([_step("still going", finish="length")] * (MAX_OUTPUT_RECOVERIES + 1))
    result, kind = await _outcome(agent)
    assert result.stop_reason is StopReason.MODEL_ERROR and kind == ("truncated", True)
    assert gateway.users.count(OUTPUT_RECOVERY_PROMPT) == MAX_OUTPUT_RECOVERIES


async def test_a_call_cut_before_its_arguments_ended_counts_as_a_cut():
    """Nothing ran, so it must not reset the count: repeated, it ends the run as truncated."""
    cut_call = _step(calls=[_call(None)], finish="length")
    agent, gateway = _agent([cut_call] * (MAX_OUTPUT_RECOVERIES + 1), max_steps=30)
    result, kind = await _outcome(agent)
    assert result.stop_reason is StopReason.MODEL_ERROR and kind == ("truncated", True)
    assert {output for _, output in gateway.results} == {CUT_ARGUMENTS}
    assert OUTPUT_RECOVERY_PROMPT not in gateway.users


async def test_a_call_with_whole_arguments_but_no_code_is_not_a_cut_whatever_the_finish():
    no_code = _step(calls=[ToolCall("c1", "python", '{"script": "x = 1"}')], finish="length")
    agent, gateway = _agent([no_code] * (MAX_OUTPUT_RECOVERIES + 1) + [_step("done")],
                            max_steps=30)
    result, kind = await _outcome(agent)
    assert result.stop_reason is StopReason.COMPLETED and kind is None
    assert {output for _, output in gateway.results} == {BAD_ARGUMENTS}


async def test_only_consecutive_cuts_use_up_the_recoveries():
    cut, cut_call = _step("thinking", finish="length"), _step(calls=[_call(None)], finish="length")
    steps = ([cut, cut_call] * MAX_OUTPUT_RECOVERIES)[:MAX_OUTPUT_RECOVERIES]
    steps += [_step(calls=[_call("x = 1")])] + [cut] * MAX_OUTPUT_RECOVERIES + [_step("done")]
    result, kind = await _outcome(_agent(steps, max_steps=30)[0])
    assert result.stop_reason is StopReason.COMPLETED and kind is None


class _BrokenKernel(_Runtime):
    async def execute(self, code):
        raise RuntimeExecutionError("kernel would not start")


async def test_a_runtime_failure_ends_the_run_as_a_runtime_error():
    agent, _ = _agent([_step(calls=[_call("x = 1")])], runtime=_BrokenKernel())
    assert (await agent.run("q")).stop_reason is StopReason.RUNTIME_ERROR


class _GuardedKernel(_Runtime):
    async def execute(self, code):
        return NS(success=False, error=SecurityError("import os is blocked"), stdout=None,
                  state_lost=False)


async def test_blocked_code_gets_the_security_text():
    agent, gateway = _agent([_step(calls=[_call("import os")]), _step("ok")],
                            runtime=_GuardedKernel())
    await agent.run("q")
    assert gateway.results == [("c1", SECURITY_ERROR_PROMPT.format(error="import os is blocked"))]


async def test_a_refusal_is_the_answer_even_under_a_content_filter_finish_as_in_cave_agent():
    refused = Step("I can't help with that.", (), "content_filter", TokenUsage(10, 5, 15),
                   refused=True)
    result, kind = await _outcome(_agent([refused])[0])
    assert result.stop_reason is StopReason.COMPLETED and kind is None
    assert result.content == "I can't help with that."
    # Filtered with text of its own, or with nothing: withdrawn, the infrastructure's.
    for filtered in (_step("partial answer", finish="content_filter"),
                     _step(finish="content_filter")):
        assert (await _outcome(_agent([filtered])[0]))[1] == ("content_filter", False)


async def test_a_step_that_fails_is_still_counted_as_cave_agent_counts_it():
    agent, _ = _agent([], gateway=_Failing(PromptTooLongError("context_length_exceeded")))
    assert (await agent.run("q")).steps == 1


async def test_a_luna_turn_runs_through_the_responses_wire_and_its_history_replays(endpoint):
    endpoint.replies += [
        SDKStream([final_event(responses_reply([output_message("I'll compute it.", "commentary"),
                                                function_call("answer = 6 * 7\nprint(answer)")]))]),
        SDKStream([final_event(responses_reply([output_message("The answer is 42.")]))]),
    ]
    config = ModelConfig(name="luna", api_model="luna", api_key="k",
                         provider="openai_responses", reasoning_effort="none")
    ws = Workspace(functions=[], variables=[])
    agent = ToolAgent(ToolGateway(config, timeout=httpx.Timeout(60.0), retries=0),
                      runtime=ws.runtime, system_instructions="S", max_steps=5,
                      max_exec_output=EXEC_OUTPUT_CHARS)
    result = await agent.run("q")
    assert (result.content, result.steps, result.code_snippets) == (
        "The answer is 42.", 2, ["answer = 6 * 7\nprint(answer)"])
    # The second request replays the first reply's items, then the call's output.
    replayed = endpoint.sent[1]["input"]
    assert [item.get("type") for item in replayed[-3:]] == [
        "message", "function_call", "function_call_output"]
    assert replayed[-1] == {"type": "function_call_output", "call_id": "c1", "output": "42\n"}
    assert [line["type"] for line in agent.transcript(agent.messages)[-3:]] == [
        "CodeExecutionMessage", "ExecutionResultMessage", "AssistantMessage"]
    ws.close()

