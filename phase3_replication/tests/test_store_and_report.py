"""Store layout, resume status, and the paired report, on synthetic records."""

import json

import pytest

from analysis.outcomes import collect
from analysis.report import contrast, write_report
from evaluation.experiment import ExperimentSpec, Selection, grid
from evaluation.records import (
    ConversationRecord,
    Cost,
    RunRecord,
    Scorecard,
    TurnRecord,
    Verdict,
    read_json,
    write_json,
)
from evaluation.store import ResultStore, RunKey

SPEC = ExperimentSpec(
    name="t", suite="toy", arms=["a", "b"], models=["m1", "m2"],
    contrasts=[{"name": "b vs a", "treatment": "b", "control": "a"}],
)


def K(arm: str, model: str, task: str) -> RunKey:
    return RunKey(arm, model, task, 1, domain="hk", category="c")


def _run(tokens: int, error: str | None = None) -> RunRecord:
    turn = TurnRecord(turn=1, query="q", cost=Cost(steps=2, total_tokens=tokens))
    return RunRecord("t", "toy", "hk", "c", "task", {}, {}, 1, "s", "f",
                     [ConversationRecord("c", [turn])], error=error)


def _card(passed: bool) -> Scorecard:
    return Scorecard("task", "now", [Verdict("c", 1, "v", "scored", passed)])


@pytest.fixture
def store(tmp_path):
    store = ResultStore(tmp_path, "t")
    # b recovers 3 of a's failures and regresses 1, across two models.
    outcomes = {
        ("m1", "t1"): (False, True), ("m1", "t2"): (False, True), ("m1", "t3"): (True, True),
        ("m2", "t1"): (False, True), ("m2", "t2"): (True, False), ("m2", "t3"): (True, True),
    }
    for (model, task), (a, b) in outcomes.items():
        for arm, passed, tokens in (("a", a, 100), ("b", b, 400)):
            key = K(arm, model, task)
            store.save_run(key, _run(tokens), {"c": [{"turn": 1}]})
            store.save_scorecard(key, _card(passed))
    errored = K("b", "m1", "t4")
    store.save_run(errored, _run(0, error="provider down"), {})
    return store


def test_a_turns_outputs_are_written_whatever_keys_an_agent_made(tmp_path):
    flags = {True: 1, None: 2, 3: 4, 1.5: 5}
    outputs = {"by_station": ({("Central", 2020): 1.5},), "flags": flags}
    write_json(tmp_path / "turn.json",
               TurnRecord(turn=1, query="q", runtime_variables=outputs).to_dict())
    written = read_json(tmp_path / "turn.json")["runtime_variables"]
    assert written["by_station"] == [{"('Central', 2020)": 1.5}]     # a key JSON cannot hold
    assert written["flags"] == json.loads(json.dumps(flags))          # keys JSON writes itself


def test_status_and_enumeration(store):
    assert store.status(K("a", "m1", "t1")) == "ok"
    assert store.status(K("b", "m1", "t4")) == "error"
    assert store.status(K("a", "m9", "t1")) == "missing"
    assert len(list(store.runs())) == 13
    assert (store.path(K("a", "m1", "t1")) / "transcripts" / "c.jsonl").exists()


def test_rerun_discards_the_old_verdict_and_transcripts(store):
    key = K("a", "m1", "t1")
    store.save_run(key, _run(1), {})
    assert store.load_scorecard(key) is None
    assert not (store.path(key) / "transcripts").exists()


def test_an_empty_scorecard_is_not_a_pass():
    assert not Scorecard("task", "now", []).passed


def test_contrast_pairs_only_scored_runs(store):
    outcomes = collect(store)
    assert (outcomes.status == "error").sum() == 1
    result = contrast(outcomes, SPEC.contrasts[0])
    assert result["pairs"] == 6
    assert (result["recovered"], result["regressed"]) == (3, 1)
    assert result["delta_pp"] == pytest.approx(100 * (5 / 6 - 3 / 6))
    assert result["treatment_tokens_per_task"] / result["control_tokens_per_task"] \
        == pytest.approx(4.0)


def test_report_ignores_runs_outside_the_spec(store, tmp_path):
    store.save_run(K("old_arm", "m1", "t1"), _run(1), {})
    narrowed = SPEC.model_copy(update={"models": ["m1"]})
    write_report(narrowed, collect(store), tmp_path / "report")
    arms = (tmp_path / "report" / "arms.csv").read_text()
    assert "old_arm" not in arms and "m2" not in arms


def test_report_files(store, tmp_path):
    markdown = write_report(SPEC, collect(store), tmp_path / "report")
    # Per task (averaged over models): t1 +1, t2 0, t3 0 -> +33.3, CI by resampling tasks.
    assert "| b vs a | pooled |" in markdown and "| +33.3 [+0.0, +100.0] |" in markdown
    assert {p.name for p in (tmp_path / "report").iterdir()} == {
        "summary.md", "outcomes.csv", "arms.csv", "contrasts.csv", "categories.csv"
    }


def test_selection_and_shards_partition_the_grid():
    class T:
        def __init__(self, name):
            self.name, self.category = name, "c"

    class OneDomain:
        def domain_of(self, task):
            return "hk"
    keys = grid(SPEC, OneDomain(), [T(f"t{i}") for i in range(20)])
    assert len(keys) == 2 * 2 * 20
    shards = [[k for k in keys if Selection(shard=(i, 3)).keep(k)] for i in range(3)]
    assert sum(map(len, shards)) == len(keys)
    assert not set(shards[0]) & set(shards[1])
    assert all(k.arm == "a" for k in keys if Selection(arms=["a"]).keep(k))


def test_contrasts_must_name_listed_arms():
    with pytest.raises(ValueError, match="not in `arms`"):
        ExperimentSpec(name="x", suite="s", arms=["a"], models=["m"],
                       contrasts=[{"name": "c", "treatment": "b", "control": "a"}])


# --- failure causes ------------------------------------------------------------

from analysis.failures import cause, cause_table, collect_failures  # noqa: E402


@pytest.mark.parametrize(("turn", "not_set", "expected"), [
    (TurnRecord(turn=1, query="q", stages=[{"role": "solo", "stop_reason": "completed"}]),
     True, "outputs not set"),
    (TurnRecord(turn=1, query="q", snapshot_unserialisable=["x"]), False, "wrong type"),
    (TurnRecord(turn=1, query="q", stages=[{"stop_reason": "max_steps"}]), False, "out of steps"),
    (TurnRecord(turn=1, query="q", stages=[{"role": "solo", "stop_reason": "completed"}]),
     False, "wrong value"),
])
def test_failure_cause(turn, not_set, expected):
    assert cause(turn, not_set) == expected


def test_failures_list_only_failed_turns_of_scored_runs(store):
    failures = collect_failures(store)
    assert len(failures) == 4          # a fails t1, t2 (m1) and t1 (m2); b fails t2 (m2)
    assert set(failures.cause) == {"wrong value"}
    assert cause_table(failures).loc["a", "wrong value"] == 3


def test_report_carries_the_cause_table(store, tmp_path):
    markdown = write_report(SPEC, collect(store), tmp_path / "report", collect_failures(store))
    assert "## Failed turns by cause" in markdown
    assert (tmp_path / "report" / "failures.csv").exists()


# --- AirBench layout -------------------------------------------------------------


def test_layout_and_files_follow_airbench(store):
    import json

    key = K("a", "m1", "t1")
    directory = store.path(key)
    assert directory == store.root / "hk" / "c" / "t1" / "a" / "m1" / "r1"
    assert {p.name for p in directory.iterdir()} == {
        "run.json", "programmatic_verification.json", "transcripts"
    }
    run = json.loads((directory / "run.json").read_text())
    assert list(run) == ["schema", "benchmark", "run", "cost", "conversations"]
    assert run["run"]["domain"] == "hk" and run["cost"]["turns"] == 1
    pv = json.loads((directory / "programmatic_verification.json").read_text())
    assert list(pv) == ["schema", "benchmark", "scoring", "conversations"]
    assert set(pv["scoring"]) >= {"status", "scored_at", "turns", "scored", "passed", "failed"}
    turn = pv["conversations"][0]["turns"][0]
    assert set(turn) >= {"turn", "validator", "runtime_variables", "status", "success"}
    line = json.loads((directory / "transcripts" / "c.jsonl").read_text().splitlines()[0])
    assert next(iter(line)) == "index"


@pytest.mark.parametrize(("statuses", "outcome"), [
    ([("scored", True), ("scored", True)], "passed"),
    ([("scored", False), ("raised", False)], "failed"),     # a known failure stands
    ([("scored", True), ("infra_error", False)], "refused"),
    ([], "refused"),
])
def test_task_outcome(statuses, outcome):
    verdicts = [Verdict("c", i, "v", status, passed)
                for i, (status, passed) in enumerate(statuses, 1)]
    assert Scorecard("task", "now", verdicts).outcome == outcome


def test_a_database_outage_is_rescored_by_the_next_run(store):
    key = K("a", "m1", "t1")
    assert store.is_scored(key)
    store.save_scorecard(key, Scorecard("t1", "now", [Verdict("c", 1, "v", "infra_error")]))
    assert not store.is_scored(key)
    store.save_scorecard(key, Scorecard("t1", "now", [Verdict("c", 1, "v", "raised")]))
    assert store.is_scored(key)              # a validator defect is not retried
