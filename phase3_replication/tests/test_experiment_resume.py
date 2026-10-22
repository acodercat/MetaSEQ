"""Resuming an experiment: completed runs are skipped unless made under another protocol."""

import json

import pytest

import evaluation.experiment as ex
from evaluation.experiment import ExperimentSpec, Selection, run_experiment
from evaluation.protocol import protocol_fingerprint
from evaluation.store import ResultStore
from settings import settings
from tasks import Suite
from tests.conftest import FIXTURES
from tests.fakes import ScriptedGateway, toy_policy

SPEC = ExperimentSpec(name="resume", suite="toy", arms=["single_agent_bare"], models=["m"])


@pytest.fixture
def lab(tmp_path, monkeypatch):
    class Config:
        def fingerprint(self):
            return {"config": "m"}

    class Registry:
        def get(self, name):
            return Config()

    monkeypatch.setattr(ex.ModelRegistry, "load", staticmethod(lambda path: Registry()))
    from agents.harness.tool import ToolHarness

    monkeypatch.setattr(ex, "build_harness",
                        lambda name, config: ToolHarness(ScriptedGateway(toy_policy)))
    monkeypatch.setattr(settings, "results_dir", tmp_path)
    monkeypatch.setattr(settings, "suites_dir", FIXTURES / "suites")
    return ResultStore(tmp_path, SPEC.name)


async def _run(spec=SPEC, dry_run=False) -> list[str]:
    log = []
    await run_experiment(spec, Selection(), dry_run=dry_run, progress=log.append)
    return log


async def test_a_completed_run_is_skipped(lab):
    assert (await _run())[0] == "resume: 1 runs selected, 1 to run"
    (key,) = lab.runs()
    run = json.loads((lab.path(key) / "run.json").read_text())
    environment = Suite.load("toy").environments["toy"]
    assert run["run"]["protocol"] == protocol_fingerprint(environment)
    assert (await _run())[0] == "resume: 1 runs selected, 0 to run"


async def test_a_run_made_under_other_code_is_rerun(lab, monkeypatch):
    await _run()
    monkeypatch.setattr(ex, "protocol_fingerprint", lambda environment, harness="tool": "changed")
    assert (await _run())[0] == "resume: 1 runs selected, 1 to run (1 stale)"
    assert (await _run())[0] == "resume: 1 runs selected, 0 to run"


async def test_a_run_made_with_another_model_configuration_is_rerun(lab):
    await _run()
    (key,) = lab.runs()
    path = lab.path(key) / "run.json"
    run = json.loads(path.read_text())
    run["run"]["model"]["temperature"] = 0.9
    path.write_text(json.dumps(run))
    assert (await _run())[0] == "resume: 1 runs selected, 1 to run (1 stale)"


async def test_a_run_made_with_other_arm_settings_or_no_protocol_is_rerun(lab):
    await _run()
    (key,) = lab.runs()
    path = lab.path(key) / "run.json"
    run = json.loads(path.read_text())
    run["run"]["arm"]["max_steps"] = 99
    path.write_text(json.dumps(run))
    assert (await _run())[0] == "resume: 1 runs selected, 1 to run (1 stale)"
    run = json.loads(path.read_text())
    del run["run"]["protocol"]                  # made before runs recorded it
    path.write_text(json.dumps(run))
    assert (await _run())[0] == "resume: 1 runs selected, 1 to run (1 stale)"


def test_the_fingerprint_follows_what_the_agent_is_told():
    environment = Suite.load("toy", suites_dir=FIXTURES / "suites").environments["toy"]
    same = protocol_fingerprint(environment)
    assert protocol_fingerprint(environment) == same
    told_otherwise = type(environment)(environment.system_prompt + " ", environment.variables,
                                       environment.functions)
    assert protocol_fingerprint(told_otherwise) != same


async def test_no_shell_outlives_its_run(lab):
    import gc

    from IPython.core.interactiveshell import InteractiveShell

    def shells() -> int:
        gc.collect()
        return sum(isinstance(o, InteractiveShell) for o in gc.get_objects())

    before = shells()     # other tests' workspaces may still be alive
    arms = ["single_agent_bare", "multi_agent_fixed_roles_verified"]
    await _run(SPEC.model_copy(update={"arms": arms}))
    assert shells() == before


async def test_an_aliased_protocol_counts_as_current(lab, monkeypatch):
    await _run()
    (key,) = lab.runs()
    stored = json.loads((lab.path(key) / "run.json").read_text())["run"]["protocol"]
    monkeypatch.setattr(ex, "protocol_fingerprint", lambda environment, harness="tool": "moved")
    (lab.root / "protocol_aliases.json").write_text(json.dumps({"aliases": {stored: "moved"}}))
    assert (await _run())[0] == "resume: 1 runs selected, 0 to run"
    # the run.json itself still records what it was made under
    assert json.loads((lab.path(key) / "run.json").read_text())["run"]["protocol"] == stored


async def test_a_run_served_by_an_aliased_endpoint_counts_as_current(lab, monkeypatch):
    await _run()
    (key,) = lab.runs()
    run_file = lab.path(key) / "run.json"
    record = json.loads(run_file.read_text())
    record["run"]["model"] = {"config": "m", "base_url": "https://direct.example/v1"}
    run_file.write_text(json.dumps(record))
    assert (await _run(dry_run=True))[0] == "resume: 1 runs selected, 1 to run (1 stale)"
    (lab.root / "model_aliases.json").write_text(json.dumps({"aliases": [
        {"made": record["run"]["model"], "counts_as": {"config": "m"}, "why": "same model"}]}))
    assert (await _run(dry_run=True))[0] == "resume: 1 runs selected, 0 to run"
    # the run.json itself still records the endpoint that served it
    assert json.loads(run_file.read_text())["run"]["model"]["base_url"] == "https://direct.example/v1"



def test_a_field_added_to_arm_later_keeps_runs_at_its_default_current():
    from agents import load_arms
    from evaluation.experiment import _made_under_current

    arm = load_arms()["multi_agent_fixed_roles_verified"]
    before = {k: v for k, v in arm.model_dump().items() if k != "synthesis_steps"}
    changed = arm.model_copy(update={"synthesis_steps": 3})       # the field's default
    assert _made_under_current(("p", before, {}), "p", changed, {})
    assert not _made_under_current(("p", before, {}), "p", arm, {})
    before = arm.model_dump()
    assert not _made_under_current(("p", {**before, "gone": 1}, {}), "p", arm, {})
    assert not _made_under_current(("old", before, {}), "p", arm, {})
    reworded = arm.model_copy(update={"description": "same arm, new words"})
    assert _made_under_current(("p", before, {}), "p", reworded, {})


async def test_a_dry_run_reports_and_runs_nothing(lab):
    log = []
    await run_experiment(SPEC, Selection(), dry_run=True, progress=log.append)
    assert log == ["resume: 1 runs selected, 1 to run"]
    assert list(lab.runs()) == []


async def test_failed_attempts_are_logged_and_a_run_is_given_up_after_three(lab, monkeypatch):
    from dataclasses import replace

    real_run_task = ex.run_task

    async def failing(*args, **kwargs):
        result = await real_run_task(*args, **kwargs)
        result.record = replace(result.record, error="solo: provider: reset",
                                error_kind="provider")
        return result

    monkeypatch.setattr(ex, "run_task", failing)
    for attempt in range(1, ex.MAX_ATTEMPTS + 1):
        assert (await _run())[0] == "resume: 1 runs selected, 1 to run"
        (key,) = lab.runs()
        assert lab.attempts(key) == attempt
    run = json.loads((lab.path(key) / "run.json").read_text())["run"]
    assert (run["status"], run["error_kind"]) == ("error", "provider")
    assert (await _run())[0] == ("resume: 1 runs selected, 0 to run, 1 given up after "
                                 f"{ex.MAX_ATTEMPTS} failed attempts")


async def test_runs_failing_in_a_row_stop_the_process_before_the_rest_spend_attempts(
        lab, monkeypatch):
    from dataclasses import replace

    from errors import InfrastructureError

    real_run_task = ex.run_task

    async def failing(*args, **kwargs):
        result = await real_run_task(*args, **kwargs)
        result.record = replace(result.record, error="solo: provider: down",
                                error_kind="provider")
        return result

    monkeypatch.setattr(ex, "run_task", failing)
    monkeypatch.setattr(ex, "FAILURES_IN_A_ROW", 2)
    with pytest.raises(InfrastructureError, match="2 runs in a row failed"):
        await _run(SPEC.model_copy(update={"repeats": 3}))
    assert len(list(lab.runs())) == 2               # the third run never started


def test_a_field_removed_with_its_code_counts_only_at_the_behaviour_that_remains():
    from agents import load_arms
    from agents.arm import REMOVED_FIELDS
    from evaluation.experiment import _made_under_current

    arm = load_arms()["single_agent_bare"]
    made = {**arm.model_dump(), **REMOVED_FIELDS}      # a run recorded before the removal
    assert _made_under_current(("p", made, {}), "p", arm, {})
    assert not _made_under_current(("p", {**made, "rules": True}, {}), "p", arm, {})
    assert not _made_under_current(("p", {**made, "verifier": "evidence"}, {}), "p", arm, {})


async def test_a_run_is_made_under_the_tool_harness_fingerprint(lab):
    await _run()
    (key,) = lab.runs()
    run = json.loads((lab.path(key) / "run.json").read_text())["run"]
    environment = Suite.load("toy").environments["toy"]
    assert run["harness"] == "tool"
    assert run["protocol"] == protocol_fingerprint(environment, "tool")
