"""The ported suites are complete and loadable offline."""

import pytest

from domains import get_domain
from errors import TaskSpecificationError
from tasks import Suite, available_suites
from tasks.porting import _port_task, _toml, rewrite_module

EXPECTED = {"air_quality": 111}


def test_every_suite_is_present():
    assert set(EXPECTED) <= set(available_suites())


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_suite_loads_and_every_module_checks(name):
    suite = Suite.load(name)
    assert len(suite.tasks) == EXPECTED[name]
    assert suite.source.get("commit")
    for task in suite.tasks.values():
        task.load()   # imports, validators exist, stores cover the variables


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_environment_is_bound_by_the_domain(name):
    suite = Suite.load(name)
    for name, environment in suite.environments.items():
        domain = get_domain(name)
        assert {v.name for v in environment.variables} <= set(domain.handles)
        assert set(environment.functions) <= set(domain.functions)


def test_air_quality_tasks_each_run_in_their_own_domain():
    suite = Suite.load("air_quality")
    assert suite.domains == ["hk", "beijing"]
    counts = {d: sum(suite.domain_of(t) == d for t in suite.tasks.values()) for d in suite.domains}
    assert counts == {"hk": 58, "beijing": 53}
    hk = next(t for t in suite.tasks.values() if t.domain == "hk")
    bj = next(t for t in suite.tasks.values() if t.domain == "beijing")
    assert "engine" in {v.name for v in suite.environment_of(hk).variables}
    assert "cities_df" in {v.name for v in suite.environment_of(bj).variables}


def test_port_rewrites_imports_and_rejects_residue():
    source = (
        "from core.types import Turn\n"
        "from domains.HK.db import read_frame\n"
        "from config import PROJECT_ROOT\n"
        'pop = pd.read_csv(PROJECT_ROOT/"datasets"/"HK_population_1km.csv")\n'
    )
    ported = rewrite_module(source)
    assert "from tasks import Turn" in ported
    assert "from domains.hk.db import read_frame" in ported
    nested = rewrite_module("def f():\n    from domains.HK.db import read_frame\n")
    assert "    from domains.hk.db import read_frame" in nested
    one_string = rewrite_module(
        "def f():\n    from config import PROJECT_ROOT\n"
        "    return pd.read_csv(PROJECT_ROOT/'datasets/HK/profile_sounding.csv')\n")
    assert "    from domains.hk.data import DATA_DIR" in one_string
    assert "pd.read_csv(DATA_DIR / 'profile_sounding.csv')" in one_string
    shared = rewrite_module("from evals._shared.scientific_outputs import check_evidence\n")
    assert shared == "from domains.scientific_outputs import check_evidence\n"
    assert 'DATA_DIR / "population_1km.csv"' in ported
    with pytest.raises(TaskSpecificationError, match="unported"):
        rewrite_module("from evals._shared import mda8\n")


def test_manifest_toml_survives_quotes():
    import tomllib

    table = {"description": 'the "Phase 2" set\nline two', "dirty": True, "tasks": 3}
    assert tomllib.loads(_toml(table)) == table


def test_port_rewrites_beijing_modules_to_the_beijing_domain():
    source = (
        "from config import PROJECT_ROOT\n"
        "from evals._shared.mda8 import frame_to_mda8\n"
        'bj = PROJECT_ROOT / "datasets" / "Beijing"\n'
        'df = pd.read_csv(PROJECT_ROOT / "datasets" / "Beijing" / "air_quality.csv")\n'
    )
    ported = rewrite_module(source, "Beijing")
    assert "from domains.beijing.data import DATA_DIR" in ported
    assert "from domains.beijing.mda8 import frame_to_mda8" in ported
    assert "bj = DATA_DIR\n" in ported and 'DATA_DIR / "air_quality.csv"' in ported
    with pytest.raises(TaskSpecificationError, match="unported"):
        rewrite_module(source, "HK")          # HK rewrites leave the mda8 import behind


def test_port_drops_claims(tmp_path):
    import json

    (tmp_path / "evals").mkdir()
    (tmp_path / "evals" / "t.py").write_text("from core.types import Turn\n")
    case = {"name": "t", "module": "evals.t", "category": "c", "conversations": [
        {"id": "x", "turns": [{"query": "q", "validator": "v", "claims": [{"id": "a"}]}]}]}
    (tmp_path / "t.json").write_text(json.dumps([case]))
    _port_task(tmp_path, "t.json", tmp_path / "out", "HK", "hk")
    ported = json.loads((tmp_path / "out" / "c" / "t.json").read_text())
    assert "claims" not in ported["conversations"][0]["turns"][0]
    assert ported["domain"] == "hk"
    assert "module" not in ported

