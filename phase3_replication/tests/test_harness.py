"""The harness: the tool harness builds its ToolAgent over the workspace's runtime, answers plain
completions, writes the transcript schema readers rely on, and changes the suite prompt only
where it speaks of the protocol."""

from __future__ import annotations

import json
from types import SimpleNamespace as NS

import pytest

from agents.harness import STREAM_IDLE_TIMEOUT, build_harness, harness_type
from agents.harness.tool import CONNECT_TIMEOUT_S, ToolHarness, request_timeout
from agents.harness.tool_agent import ToolAgent
from agents.harness.tool_prompt import TOOL_EXAMPLES_NOTE, TOOL_PROTOCOL, for_tool_harness
from agents.harness.tool_transcript import transcript_lines
from agents.workspace import Workspace
from errors import ConfigurationError
from evaluation.experiment import ExperimentSpec
from evaluation.protocol import protocol_fingerprint
from llm import DEFAULT_TIMEOUT_S, ModelConfig
from settings import PROJECT_ROOT, settings
from tests.fakes import ScriptedModel

SUITE = settings.suites_dir / "air_quality" / "environments"


def test_the_tool_harness_writes_the_transcript_schema():
    tool_lines = [line for message in [
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "plan", "reasoning_content": "think", "tool_calls": [
            {"id": "c1", "type": "function",
             "function": {"name": "python", "arguments": '{"code": "x = 1"}'}},
            {"id": "c2", "type": "function", "function": {"name": "python", "arguments": "{"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "ok"},
        {"type": "reasoning", "encrypted_content": "opaque", "summary": []},
        {"type": "function_call", "call_id": "c3", "name": "python",
         "arguments": '{"code": "y = 2"}'},
        {"type": "function_call_output", "call_id": "c3", "output": "done"},
        {"type": "message", "role": "assistant", "phase": "final_answer",
         "content": [{"type": "output_text", "text": "y is 2"}]},
    ] for line in transcript_lines(message)]
    assert [(line["type"], line["role"]) for line in tool_lines] == [
        ("UserMessage", "user"), ("ReasoningMessage", "assistant"),
        ("CodeExecutionMessage", "assistant"), ("CodeExecutionMessage", "assistant"),
        ("ExecutionResultMessage", "user"),
        ("ReasoningMessage", "assistant"), ("CodeExecutionMessage", "assistant"),
        ("ExecutionResultMessage", "user"), ("AssistantMessage", "assistant")]
    # A call reads as a turn that ran code: its text, then the code fenced.
    assert tool_lines[1]["content"] == "think"                  # the reasoning it was sent back
    assert tool_lines[2]["content"] == "plan\n```python\nx = 1\n```"
    assert tool_lines[3]["content"] == "{"                      # unreadable: as written
    assert "opaque" not in json.dumps(tool_lines)              # state, not text


def test_the_tool_harness_bounds_each_phase_of_a_request():
    plain = request_timeout(ModelConfig(name="m", api_model="m", api_key="k"))
    assert (plain.connect, plain.read, plain.write) == (CONNECT_TIMEOUT_S, STREAM_IDLE_TIMEOUT,
                                                        DEFAULT_TIMEOUT_S)
    slow = request_timeout(ModelConfig(name="m", api_model="m", api_key="k", timeout=1800.0))
    assert (slow.connect, slow.read, slow.write) == (CONNECT_TIMEOUT_S, 1800.0, 1800.0)


def test_the_harness_is_built_for_a_model_and_makes_its_agent():
    config = ModelConfig(name="m", api_model="m", api_key="k")
    harness = build_harness("tool", config)
    assert isinstance(harness, ToolHarness) and harness_type("tool") is ToolHarness
    ws = Workspace(functions=[], variables=[])
    agent = harness.agent(ws, max_steps=5, instructions=None, system_prompt="S {{x}}")
    assert isinstance(agent, ToolAgent) and agent.runtime is ws.runtime
    assert (agent.max_steps, agent.system_instructions) == (5, "S {x}")   # formatted as CaveAgent
    ws.close()


async def test_the_harness_answers_a_plain_completion():
    model = ScriptedModel(lambda messages: "plan")
    chosen = ToolHarness(NS(complete=model.call))
    assert (await chosen.complete([{"role": "user", "content": "q"}])).content == "plan"


@pytest.mark.parametrize("domain", ["hk", "beijing"])
def test_the_suite_prompt_changes_only_in_its_protocol_paragraphs(domain):
    prompt = json.loads((SUITE / f"{domain}.json").read_text())["system_prompt"]
    tool = for_tool_harness(prompt)
    assert "Only a Markdown ```python fence is executed" not in tool
    assert "Only code passed to the `python` tool is executed" in tool
    assert TOOL_EXAMPLES_NOTE in tool
    # Undo the swaps: what is left is the prompt as it was, character for character.
    back = tool.replace(TOOL_EXAMPLES_NOTE, "")
    for code, swapped in TOOL_PROTOCOL:
        back = back.replace(swapped, code)
    assert back == prompt


def test_a_prompt_without_the_protocol_paragraphs_is_refused_not_half_translated():
    with pytest.raises(ConfigurationError, match="fence-protocol paragraph"):
        for_tool_harness("Analyse the data.")


def test_the_harness_enters_the_fingerprint(toy_suite):
    environment = next(iter(toy_suite.environments.values()))
    assert protocol_fingerprint(environment) == protocol_fingerprint(environment, "tool")


def test_an_experiment_holds_the_tool_harness():
    base = dict(name="x", suite="air_quality", arms=["single_agent_bare"], models=["m"])
    assert ExperimentSpec(**base).harness == "tool"
    with pytest.raises(ValueError):
        ExperimentSpec(**base, harness="code")
    config = PROJECT_ROOT / "configs" / "experiments" / "study.toml"
    assert ExperimentSpec.load(str(config)).harness == "tool"
