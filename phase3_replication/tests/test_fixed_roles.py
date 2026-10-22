"""The MetaSEQ topology (`multi_agent_fixed_roles_verified`) against the group's released
multi-agent harness.

Where the released harness's repository is checked out next to the lab, its adapter is
loaded and the topology is compared with it directly: the published prompt texts,
plan parsing and the default plan, the coordinator's messages, how every worker's
instructions are assembled, the manifest. The step budget follows the harness's
formula and is checked on toy plans, and the verifier is checked to reassign what it
recomputes.
"""

from __future__ import annotations

import ast
import contextlib
import difflib
import io
import itertools
import sys
import types
from types import SimpleNamespace

import pytest
from cave_agent import Variable

from agents import instructions
from agents.instructions import SYNTHESIS, TaskBrief, _prompt
from agents.topologies.fixed_roles import DEFAULT_PIPELINE, ROLES, default_plan, parse_plan
from agents.verification import manifest
from agents.workspace import Workspace
from settings import PROJECT_ROOT
from tests.fakes import CODE, DONE_MARKER, USAGE, fenced
from tests.test_end_to_end import ARMS, _run

# The released harness, checked out next to the lab or next to the repository that holds it.
_CANDIDATES = [root / "Neuro-Air" / "benchmark"
               for root in (PROJECT_ROOT.parent, PROJECT_ROOT.parent.parent)]
HARNESS = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])
PROMPTS = PROJECT_ROOT / "agents" / "prompts" / "fixed_roles"
CONTEXT = "PRIOR TURN 1:\nq1\n\nCURRENT TURN (2):\nq2"
PRECEDENCE = "\n\n" + _prompt("fixed_roles/precedence.md")
CONTRACT_BLOCK = (f"\n\nEXACT CONVERSATION CONTRACT:\n{CONTEXT}\n\n"
                  f"{instructions._FIXED_ROLES_TURN_RULES}")
# Analysis knowledge the published prompts carried; none may reach a stripped worker.
KNOWLEDGE = ("ST_", "PostGIS", "METRES", "SUM", "Pearson", "fuzzy", "x1000", "numpy", "np.",
             "NOW()", "SILENT ZERO", "PLAUSIBILITY", "row count", "company_id")


@pytest.fixture(scope="module")
def harness():
    path = HARNESS / "adapters" / "multiagent_adapter.py"
    if not path.exists():
        pytest.skip("the released harness is not checked out next to the lab")
    # The released file names the runtime `IIPythonRuntime` (a rename applied twice);
    # the class it means is cave-agent's IPythonRuntime.
    source = path.read_text().replace("IIPythonRuntime", "IPythonRuntime")
    module = types.ModuleType("released_harness")
    sys.path.insert(0, str(HARNESS))
    try:
        exec(compile(source, str(path), "exec"), module.__dict__)
    finally:
        sys.path.remove(str(HARNESS))
    return module


def _wrapper(harness, **attrs):
    wrapper = harness.MultiAgentWrapper.__new__(harness.MultiAgentWrapper)
    defaults = dict(_model=None, _runtime=None, _system_instructions=None, _description=None,
                    _requirements=None, _required_outputs="", _coordinator_mode="llm",
                    _max_total_steps=20, _synth_reserve=3, _verify_reserve=6)
    for name, value in {**defaults, **attrs}.items():
        setattr(wrapper, name, value)
    return wrapper


def _texts(prompts: str) -> dict[str, str]:
    return {"roles": {r: _prompt(f"fixed_roles/{prompts}/roles/{r}.md") for r in ROLES},
            "discipline": _prompt(f"fixed_roles/{prompts}/discipline.md"),
            "coordinator": _prompt(f"fixed_roles/{prompts}/coordinator.md")}


# --- the prompt sets ---------------------------------------------------------------


def test_published_texts_are_the_harness_texts(harness):
    texts = _texts("published")
    assert texts["roles"] == {r: harness.WORKER_ROLES[r].strip() for r in ROLES}
    assert texts["discipline"] == harness._SHARED_DISCIPLINE.strip()
    assert texts["coordinator"] == harness._COORDINATOR_SYS.strip()
    assert tuple(harness.DEFAULT_PIPELINE) == DEFAULT_PIPELINE


def test_stripped_texts_carry_no_analysis_knowledge():
    for path in sorted((PROMPTS / "stripped").rglob("*.md")):
        found = [k for k in KNOWLEDGE if k in path.read_text()]
        assert not found, (path.name, found)
    assert "NOW()" not in instructions._FIXED_ROLES_TURN_RULES
    assert [k for k in KNOWLEDGE if k in _texts("published")["roles"]["multivariate_meteo"]]


def test_diff_record_is_current():
    chunks = ["# Published -> stripped\n\nGenerated from the two prompt sets; the tests fail"
              " when it is out of date.\n"]
    for file in sorted(p.relative_to(PROMPTS / "published")
                       for p in (PROMPTS / "published").rglob("*.md")):
        a = (PROMPTS / "published" / file).read_text().splitlines(keepends=True)
        b = (PROMPTS / "stripped" / file).read_text().splitlines(keepends=True)
        diff = list(difflib.unified_diff(a, b, f"published/{file}", f"stripped/{file}", n=0))
        chunks.append(f"\n## {file}\n\n"
                      + ("unchanged\n" if not diff else "```diff\n" + "".join(diff) + "```\n"))
    assert (PROMPTS / "diff.md").read_text() == "".join(chunks)


# --- mechanics equal the harness ----------------------------------------------------


@pytest.mark.parametrize("text", [
    '[{"role": "data_acquisition", "task": "fetch"}, {"role": "pollution_analysis", "task": "x"}]',
    'Plan:\n[{"role": "pollution_analysis"}, {"role": "synthesis_report", "task": "s"}]\nDone.',
    '[{"role": "synthesis_report"}, {"role": "pollution_analysis"}]',       # synthesis not last
    '[{"role": "verification", "task": "v"}]',                    # listed by the coordinator
    '[{"role": "data_acquisition"}, {"role": "data_acquisition"}, {"role": "knowledge_retrieval"},'
    ' {"role": "pollution_analysis"}, {"role": "multivariate_meteo"}, {"role": "data_acquisition"},'
    ' {"role": "pollution_analysis"}]',                                     # seven: capped at six
    '[{"role": "made_up", "task": "x"}]',
    "no plan at all",
    "[]",
    '[{"role": "knowledge_retrieval", "task": 5}, "not a dict"]',
])
async def test_plan_parsing_matches_the_harness(harness, text):
    seen = {}

    async def call(messages):
        seen["messages"] = messages
        return SimpleNamespace(content=text, token_usage=None)

    wrapper = _wrapper(harness, _model=SimpleNamespace(call=call), _required_outputs="- x: float")
    expected, _ = await wrapper._plan(CONTEXT)
    try:
        ours = parse_plan(text, CONTEXT)
    except Exception:
        ours = default_plan(CONTEXT)
    assert ours == expected
    # The same messages, the coordinator's role text stripped of the analysis knowledge.
    published, stripped = _texts("published")["coordinator"], _texts("stripped")["coordinator"]
    assert seen["messages"][0]["content"] == published
    assert [{**seen["messages"][0], "content": stripped}, *seen["messages"][1:]] \
        == instructions.fixed_roles_coordinator(CONTEXT, "- x: float")


@pytest.mark.parametrize("role,manifest_text,brief,required", list(itertools.product(
    ROLES, ["", "{}", "{'station_id': 'int', 'df': 'DataFrame'}"],
    [(None, None), ("desc", "store x (float)")], ["", "- x: float: x\n- engine: db"],
)))
def test_worker_instructions_are_assembled_as_the_harness(harness, monkeypatch, role,
                                                          manifest_text, brief, required):
    # The harness assembling the stripped texts, as the lab's workers receive them.
    texts = _texts("stripped")
    monkeypatch.setattr(harness, "WORKER_ROLES", texts["roles"])
    monkeypatch.setattr(harness, "_SHARED_DISCIPLINE", texts["discipline"])
    monkeypatch.setattr(harness, "CaveAgent", lambda **kwargs: kwargs)
    description, requirements = brief
    wrapper = _wrapper(harness, _description=description, _requirements=requirements,
                       _required_outputs=required)
    expected = wrapper._build_worker(role, "the subtask", manifest_text, 5)["instructions"]
    ours = instructions.fixed_roles_worker(role, TaskBrief(description, requirements),
                                        task="the subtask", manifest=manifest_text,
                                        context=CONTEXT, required=required)
    # The harness's text, plus the contract block and the lab's precedence note after
    # the role text, and the staged-values heading pointed at the REQUIRED list
    # (prompts/fixed_roles/README.md); nothing else differs.
    assert CONTRACT_BLOCK in ours and PRECEDENCE in ours
    assert (ours.replace(CONTRACT_BLOCK, "").replace(PRECEDENCE, "", 1)
            .replace(instructions.STAGED_HEADING, instructions.HARNESS_STAGED_HEADING)
            == expected)


def test_synthesis_is_told_of_a_verifier_only_when_one_follows():
    kw = dict(task="t", manifest="", context=CONTEXT, required="- x: float")
    with_verifier = instructions.fixed_roles_worker(SYNTHESIS, TaskBrief(), **kw)
    without = instructions.fixed_roles_worker(SYNTHESIS, TaskBrief(), verified=False, **kw)
    sentence = instructions._VERIFIER_FOLLOWS.strip()
    assert sentence in with_verifier and sentence not in without
    assert without == with_verifier.replace(instructions._VERIFIER_FOLLOWS, "", 1)


async def test_manifest_matches_the_harness_probe(harness):
    ws = Workspace(functions=[], variables=[Variable("engine", object(), "db")])
    await ws.runtime.execute(
        "import pandas as pd\n"
        "df = pd.DataFrame({'a': [1]})\nstation_id = 17\nnothing = None\n_hidden = 1\n"
        "def helper():\n    return 1\n"
    )
    probe = dict(ws.namespace())
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(harness._MANIFEST_SNIPPET, probe)
    text = out.getvalue()
    probed = ast.literal_eval(text[text.find("VARS::") + len("VARS::"):].strip())
    # The harness's probe, less the environment's own data (`engine` here).
    ours = await manifest(ws)
    assert ast.literal_eval(ours) == {name: kind for name, kind in probed.items()
                                      if name not in ws.environment_names}
    assert "engine" in probed and "engine" not in ours
    # A turn's newly registered output is reset to None and left out, landed or not.
    ws.register([Variable("station_id", None, "the turn's output")])
    assert "station_id" not in await manifest(ws)
    ws.close()


# --- behaviour in the lab ------------------------------------------------------------


def _planning(plan: str):
    """A coordinator that returns `plan`; workers that answer at once (one step each)."""
    def policy(messages):
        if "CENTRAL COORDINATOR" in messages[0]["content"]:
            return plan
        if DONE_MARKER in str(messages[-1]["content"]):
            return "done"
        return "An answer without code."
    return policy


FOUR = ('[{"role": "data_acquisition"}, {"role": "knowledge_retrieval"},'
        ' {"role": "pollution_analysis"}, {"role": "multivariate_meteo"}]')


UNVERIFIED = ARMS["multi_agent_fixed_roles_verified"].model_copy(
    update={"name": "fixed_roles_unverified", "verification": False})


async def test_budgets_follow_the_harness_with_the_verifier(toy_suite):
    result, _, model = await _run(toy_suite, "multi_agent_fixed_roles_verified", _planning(FOUR))
    turn = result.record.conversations[0].turns[0]
    budgets = [(s["role"], s["budget"]) for s in turn.stages]
    # The verifier holds verify_steps back and synthesis synthesis_steps; each producer may
    # use all of the pool that is left (one step each here); synthesis what the plan's
    # budget leaves after them; the verifier what the turn has not used.
    arm = ARMS["multi_agent_fixed_roles_verified"]
    plan_budget = arm.max_steps - arm.verify_steps
    pool = plan_budget - arm.synthesis_steps
    assert budgets == [("coordinator", 0), ("data_acquisition", pool),
                       ("knowledge_retrieval", pool - 1), ("pollution_analysis", pool - 2),
                       ("multivariate_meteo", pool - 3), ("synthesis_report", plan_budget - 4),
                       ("verification", arm.max_steps - 5)]
    assert not turn.coordination["fallback"]
    assert turn.stages[0]["usage"]["total_tokens"] == USAGE.total_tokens   # counted
    coordinator = next(m for m in model.requests if "CENTRAL COORDINATOR" in m[0]["content"])
    assert "- total:" in coordinator[1]["content"] and "- doubled:" not in coordinator[1]["content"]


async def test_budgets_without_the_verifier(toy_suite):
    result, _, _ = await _run(toy_suite, UNVERIFIED, _planning(FOUR))
    turn = result.record.conversations[0].turns[0]
    arm = UNVERIFIED
    pool = arm.max_steps - arm.synthesis_steps
    assert [(s["role"], s["budget"]) for s in turn.stages] == [
        ("coordinator", 0), ("data_acquisition", pool), ("knowledge_retrieval", pool - 1),
        ("pollution_analysis", pool - 2), ("multivariate_meteo", pool - 3),
        ("synthesis_report", arm.max_steps - 4)]
    assert turn.coordination["before_verification"] is None


async def test_producers_are_skipped_once_the_pool_is_spent(toy_suite):
    def policy(messages):
        if "CENTRAL COORDINATOR" in messages[0]["content"]:
            return FOUR
        if DONE_MARKER in str(messages[-1]["content"]):
            return fenced("pass")          # never answers: every worker runs to its cap
        return fenced("pass")

    result, _, _ = await _run(toy_suite, "multi_agent_fixed_roles_verified", policy)
    turn = result.record.conversations[0].turns[0]
    roles = [s["role"] for s in turn.stages]
    # The first producer spends the whole pool; the others are skipped, and recorded.
    arm = ARMS["multi_agent_fixed_roles_verified"]
    pool = arm.max_steps - arm.verify_steps - arm.synthesis_steps
    assert roles == ["coordinator", "data_acquisition", "synthesis_report", "verification"]
    assert [s["steps"] for s in turn.stages[1:]] == [pool, arm.synthesis_steps,
                                                     arm.verify_steps]
    assert turn.cost.steps == arm.max_steps
    assert [s["role"] for s in turn.coordination["skipped"]] == [
        "knowledge_retrieval", "pollution_analysis", "multivariate_meteo"]


def _wrong_then_verified(role_marker: str):
    """The answering agent stores wrong values; the verifier recomputes and reassigns."""
    def policy(messages):
        role = messages[0]["content"]
        last = str(messages[-1]["content"])
        if "CENTRAL COORDINATOR" in role:
            return '[{"role": "pollution_analysis"}]'
        if DONE_MARKER in last:
            return "VERIFY total: stored=40.0 | independent=42.0 | final=42.0" \
                if "VERIFICATION & CORRECTION" in role else "stored"
        if "VERIFICATION & CORRECTION" in role:
            return CODE
        return fenced("total = 40.0", "doubled = 80.0")
    return policy


async def test_the_verifier_reassigns_what_it_recomputes(toy_suite):
    arm = "multi_agent_fixed_roles_verified"
    result, card, model = await _run(toy_suite, arm, _wrong_then_verified(arm))
    assert card.passed, card.verdicts
    first = result.record.conversations[0].turns[0]
    assert first.coordination["before_verification"] == {"total": 40.0}
    assert first.runtime_variables["total"] == 42.0
    assert first.response.startswith("VERIFY total")
    assert first.stages[-1]["role"] == "verification"
    verifier = next(m[0]["content"] for m in model.requests
                    if "VERIFICATION & CORRECTION" in m[0]["content"])
    assert "REQUIRED OUTPUTS TO VERIFY" in verifier and "CURRENT STAGED VALUES" in verifier


async def test_the_bare_single_agent_is_untouched(toy_suite):
    result, card, model = await _run(toy_suite, "single_agent_bare")
    assert card.passed
    for turn in result.record.conversations[0].turns:
        assert [(s["role"], s["budget"]) for s in turn.stages] == [
            ("solo", ARMS["single_agent_bare"].max_steps)]
        assert turn.coordination is None
    assert all("VERIFICATION" not in m[0]["content"] for m in model.requests)


def _section(text: str, heading: str) -> str:
    """The block of an instruction text that starts with `heading`."""
    start = text.find(heading)
    return "" if start < 0 else text[start:].split("\n\n")[0]


async def test_required_lists_hold_the_turns_own_outputs_and_no_environment_data(toy_suite):
    _, card, model = await _run(toy_suite, "multi_agent_fixed_roles_verified", _planning(FOUR))
    verifiers = [m[0]["content"] for m in model.requests
                 if "VERIFICATION & CORRECTION" in m[0]["content"]]
    turn1, turn2 = (_section(v, "REQUIRED OUTPUTS TO VERIFY") for v in verifiers[:2])
    assert "- total:" in turn1 and "doubled" not in turn1
    assert "- doubled:" in turn2 and "- total:" not in turn2      # turn 1's is immutable
    for text in verifiers + [m[0]["content"] for m in model.requests
                             if "SHARED-RUNTIME DISCIPLINE" in m[0]["content"]]:
        for heading in ("REQUIRED OUTPUTS TO VERIFY", "OUTPUT OWNERSHIP",
                        "CURRENT STAGED VALUES", "VARIABLES ALREADY IN THE SHARED RUNTIME"):
            section = _section(text, heading)
            assert "- readings_df:" not in section and "'readings_df'" not in section, heading


async def test_without_a_verifier_synthesis_is_not_told_of_one(toy_suite):
    _, _, model = await _run(toy_suite, UNVERIFIED, _planning(FOUR))
    synthesis = [m[0]["content"] for m in model.requests
                 if "You are the SYNTHESIS & REPORTING agent" in m[0]["content"]]
    assert synthesis and not any("verification agent" in text for text in synthesis)
    assert all(PRECEDENCE.strip() in text for text in synthesis)


async def test_an_unusable_plan_records_why_the_default_plan_ran(toy_suite):
    result, _, _ = await _run(toy_suite, UNVERIFIED, _planning("no plan here"))
    turn = result.record.conversations[0].turns[0]
    assert turn.coordination["fallback"].startswith("unparsed plan: ValueError")
    assert [s["role"] for s in turn.coordination["plan"]] == list(DEFAULT_PIPELINE)
