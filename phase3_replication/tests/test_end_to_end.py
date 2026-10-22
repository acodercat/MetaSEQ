"""Both arms, driven by a scripted model over the offline toy suite, through the tool harness."""

from __future__ import annotations

import pytest

from agents import Arm, load_arms
from agents.harness.tool import ToolHarness
from domains import get_domain
from evaluation.protocol import protocol_fingerprint
from evaluation.runner import RunContext, run_task
from evaluation.scoring import score_run
from tests.fakes import ScriptedGateway, toy_policy

ARMS = load_arms()


async def _run(toy_suite, arm_name: str | Arm, policy=toy_policy):
    """One run of the toy task; the policy's fences become tool calls
    (`tests.fakes.ScriptedGateway`), and the scripted gateway is returned as the model."""
    task = toy_suite.tasks["toy_sum_then_double"]
    module = task.load()
    environment = toy_suite.environment_of(task)
    variables, functions = environment.materialise(get_domain(toy_suite.domain_of(task)))
    gateway = ScriptedGateway(policy)
    harness = ToolHarness(gateway)
    ctx = RunContext(
        experiment="test",
        domain=toy_suite.domain_of(task),
        protocol=protocol_fingerprint(environment),
        arm=arm_name if isinstance(arm_name, Arm) else ARMS[arm_name],
        harness=harness,
        model_fingerprint={"config": "scripted"},
        system_prompt=harness.system_prompt(environment.system_prompt),
        environment_variables=variables,
        environment_functions=functions,
    )
    result = await run_task(ctx, task, module, repeat=1)
    return result, await score_run(result.record, task, module), gateway


def _roles(turn) -> list[str]:
    return [s["role"] for s in turn.stages]


@pytest.mark.parametrize("arm_name", sorted(ARMS))
async def test_every_arm_solves_the_toy_task(toy_suite, arm_name):
    result, scorecard, _ = await _run(toy_suite, arm_name)
    run = result.record
    assert run.ok, run.error
    assert scorecard.status == "ok"
    assert [v.passed for v in scorecard.verdicts] == [True, True], scorecard.verdicts

    arm = ARMS[arm_name]
    for turn in run.conversations[0].turns:
        roles = _roles(turn)
        if arm.topology == "single":
            assert roles == ["solo"]
        else:
            # The toy policy answers the coordinator with code, not JSON: the default plan.
            assert roles == ["coordinator", "data_acquisition", "pollution_analysis",
                             "multivariate_meteo", "synthesis_report",
                             *(["verification"] if arm.verification else [])]
            assert turn.coordination["fallback"]
        assert turn.cost.steps <= arm.max_steps


async def test_turn_scoped_outputs_are_registered_per_turn(toy_suite):
    result, _, _ = await _run(toy_suite, "single_agent_bare")
    first, second = result.record.conversations[0].turns
    # Turn 1 only knows `total`; the speculative `doubled` it computed is not
    # an output until turn 2 registers (and resets) it.
    assert set(first.runtime_variables) == {"total"}
    assert second.runtime_variables == {"total": 42.0, "doubled": 84.0}


async def test_scoring_refuses_a_changed_query(toy_suite):
    result, _, _ = await _run(toy_suite, "single_agent_bare")
    task = toy_suite.tasks["toy_sum_then_double"]
    result.record.conversations[0].turns[0].query = "a different question"
    card = await score_run(result.record, task, task.load())
    # Turn 1 is not judged (and not failed); turn 2 still is.
    assert [v.status for v in card.verdicts] == ["query_changed", "scored"]
    assert card.outcome == "refused" and not card.passed


async def test_an_output_json_cannot_hold_fails_its_turn_not_the_run(toy_suite):
    result, _, _ = await _run(toy_suite, "single_agent_bare")
    task = toy_suite.tasks["toy_sum_then_double"]
    first = result.record.conversations[0].turns[0]
    first.runtime_variables["total"] = "Timestamp('2025-03-01 00:00:00')"   # the stored repr
    first.snapshot_unserialisable = ["total"]
    card = await score_run(result.record, task, task.load())
    assert card.status == "ok" and card.outcome == "failed"
    assert [v.passed for v in card.verdicts] == [False, True]
    assert "JSON cannot hold" in card.verdicts[0].message


async def test_a_turn_missing_a_now_declared_output_is_stale(toy_suite):
    result, _, _ = await _run(toy_suite, "single_agent_bare")
    task = toy_suite.tasks["toy_sum_then_double"]
    result.record.conversations[0].turns[1].runtime_variables.pop("doubled")
    card = await score_run(result.record, task, task.load())
    assert [v.status for v in card.verdicts] == ["scored", "stale"]
    assert card.outcome == "refused"


async def test_a_turn_that_lost_its_data_source_is_retried_not_scored(toy_suite, monkeypatch):
    from agents import MetaSEQAgent
    from domains import outages

    original = MetaSEQAgent.run_turn

    async def losing(self, query, outputs):
        outages.record("OperationalError: server closed the connection unexpectedly")
        return await original(self, query, outputs)

    monkeypatch.setattr(MetaSEQAgent, "run_turn", losing)
    result, card, _ = await _run(toy_suite, "single_agent_bare")
    assert not result.record.ok and result.record.error_kind == "data_source"
    assert "server closed the connection" in result.record.error


async def test_the_run_records_its_calls_and_its_harness(toy_suite):
    result, card, gateway = await _run(toy_suite, "multi_agent_fixed_roles_verified")
    assert card.passed and result.record.harness == "tool"
    assert result.record.to_dict()["run"]["harness"] == "tool"
    lines = [line for lines in result.transcripts.values() for line in lines]
    # A call is recorded as a turn that ran code, its code fenced.
    calls = [line for line in lines if line["type"] == "CodeExecutionMessage"]
    results = [line for line in lines if line["type"] == "ExecutionResultMessage"]
    assert calls and len(results) == len(calls)
    assert all(line["content"].startswith("```python\n") for line in calls)
    assert all({"type", "role", "content", "turn", "stage", "agent"} <= set(line)
               for line in lines)
    # The agents read the suite prompt in the tool harness's words, never the fence's.
    # (The coordinator's planning call carries its own system prompt, not the suite's.)
    systems = {m[0]["content"] for m in gateway.requests if m[0]["role"] == "system"}
    assert any("Only code passed to the `python` tool is executed" in s for s in systems)
    assert not any("Only a Markdown ```python fence" in s for s in systems)
