import atexit
import gc

import pytest
from cave_agent import Variable

from agents import instructions
from agents.arm import load_arms
from agents.security import LAB_MODULES
from agents.workspace import Workspace, changed

# --- arms --------------------------------------------------------------------


def test_catalogue_holds_the_two_arms_of_experiment_2():
    arms = load_arms()
    assert set(arms) == {"single_agent_bare", "multi_agent_fixed_roles_verified"}
    bare, metaseq = arms["single_agent_bare"], arms["multi_agent_fixed_roles_verified"]
    assert (bare.topology, bare.max_steps, bare.verification) == ("single", 50, False)
    # 50 steps a turn, the released reserves scaled in proportion: synthesis 8, verifier 15.
    assert (metaseq.topology, metaseq.max_steps, metaseq.verification,
            metaseq.synthesis_steps, metaseq.verify_steps) == ("fixed_roles", 50, True, 8, 15)


# --- instructions ------------------------------------------------------------


def test_bare_single_agent_gets_the_archived_baseline_instructions():
    assert instructions.solo(instructions.TaskBrief()) is None
    brief = instructions.TaskBrief(requirements="store x (int)")
    assert instructions.solo(brief) == "TASK REQUIREMENTS:\nstore x (int)"


# --- workspace ---------------------------------------------------------------


async def test_inventory_summarises_and_detects_changes():
    ws = Workspace(functions=[], variables=[Variable("engine", object(), "db")])
    before = ws.inventory()
    await ws.runtime.execute(
        "import pandas as pd\n"
        "df = pd.DataFrame({'a': [1, 2]})\n"
        "note = 'w' * 300\n"
        "n = 3"
    )
    after = ws.inventory()
    assert "engine" not in after                      # environment handle, not staged work
    assert after["df"].summary.startswith("DataFrame 2x1 [a]")
    assert after["note"].summary.endswith("...")      # long values are clipped
    assert changed(before, after) == ["df", "n", "note"]
    await ws.runtime.execute("n = 4")
    assert changed(after, ws.inventory()) == ["n"]


async def test_values_normalise_numpy_scalars():
    ws = Workspace(functions=[], variables=[Variable("x", None, "float")])
    await ws.runtime.execute("import numpy as np\nx = np.float64(1.5)")
    values = await ws.values(["x", "unregistered"])
    assert values == {"x": 1.5} and type(values["x"]) is float


async def test_an_output_the_agent_deleted_reads_as_not_set():
    ws = Workspace(functions=[], variables=[Variable("x", None, "float")])
    await ws.runtime.execute("x = 1.5\ndel x")
    assert await ws.values(["x"]) == {"x": None}
    ws.close()


async def test_close_frees_the_runtime():
    from IPython.core.interactiveshell import InteractiveShell

    gc.collect()
    shells = sum(isinstance(o, InteractiveShell) for o in gc.get_objects())
    ws = Workspace(functions=[], variables=[])
    await ws.runtime.execute("big = list(range(1000))")
    ws.close()
    del ws
    gc.collect()
    assert sum(isinstance(o, InteractiveShell) for o in gc.get_objects()) == shells


@pytest.mark.parametrize("code", [
    "import os", "import metaseq_suites", "pd.read_json('suites/x/tasks/a.py')",
    *(f"import {m}" for m in LAB_MODULES), "from tasks.model import Task",
    "from domains.hk.db import engine",
])
async def test_security_checker_blocks_reading_the_answer_key(code):
    ws = Workspace(functions=[], variables=[])
    result = await ws.runtime.execute(code)
    assert result.error is not None, code
    ws.close()


@pytest.mark.parametrize("code", [
    "df = pd.DataFrame({'a': [1]})\ndf.to_pickle('cache.pkl')",
    "x = pd.read_pickle('/tmp/merged.pkl')", "x = pd.read_parquet('x.parquet')",
    "df = pd.DataFrame({'a': [1]})\ndf.to_csv('out.csv')",
    "df = pd.DataFrame({'a': [1]})\ndf.to_csv(path, index=False)",
    "import numpy as np\nnp.save('a.npy', [1])", "import pickle", "path = '/tmp/NF.pkl'",
])
async def test_security_checker_blocks_files_other_runs_could_share(code):
    ws = Workspace(functions=[], variables=[])
    result = await ws.runtime.execute(code)
    assert result.error is not None, code
    ws.close()


@pytest.mark.parametrize("code", [
    "q = \"SET statement_timeout = '300s'\"", "q = 'set statement_timeout to 0'",
    "q = \"SELECT set_config('statement_timeout', '0', false)\"",
    "q = 'SET LOCAL lock_timeout = 0'", "q = 'SET work_mem = \\'4GB\\''",
])
async def test_security_checker_blocks_changing_the_databases_limits(code):
    ws = Workspace(functions=[], variables=[])
    result = await ws.runtime.execute(code)
    assert result.error is not None, code
    ws.close()


@pytest.mark.parametrize("code", [
    "try:\n    x = 1\nexcept:\n    pass",
    "try:\n    x = 1\nexcept BaseException:\n    pass",
    "try:\n    x = 1\nexcept (ValueError, BaseException) as e:\n    pass",
])
async def test_security_checker_blocks_catching_what_stops_a_cell(code):
    ws = Workspace(functions=[], variables=[])
    result = await ws.runtime.execute(code)
    assert result.error is not None, code
    ws.close()


@pytest.mark.parametrize("code", [
    "try:\n    x = 1\nexcept Exception:\n    pass",
    "df = pd.DataFrame({'a': [1]})\nprint(df.to_csv())",
    "df = pd.DataFrame({'a': [1]})\nprint(df.to_csv(index=False))",
    "df = pd.DataFrame({'a': [1]})\ns = df.to_json(orient='records')",
    "x = 'read_sql is fine'",
])
async def test_security_checker_allows_text_output_and_queries(code):
    ws = Workspace(functions=[], variables=[])
    result = await ws.runtime.execute("import pandas as pd\n" + code)
    assert result.error is None, (code, result.error)
    ws.close()


def test_atexit_is_not_left_holding_closed_workspaces():
    before = atexit._ncallbacks()
    for _ in range(3):
        Workspace(functions=[], variables=[]).close()
    # IPython registers two exit hooks per shell; close() removes the one that
    # holds the shell (and so its data). The other is a small, data-free entry.
    assert atexit._ncallbacks() - before <= 3


async def test_a_cell_that_runs_too_long_is_stopped_and_the_agent_sees_why(monkeypatch):
    from domains import cell_time

    monkeypatch.setattr(cell_time, "CELL_SECONDS", 1.5)
    monkeypatch.setattr(cell_time, "_RESIGNAL_S", 0.5)
    ws = Workspace(functions=[], variables=[])
    # Stuck in a loop that swallows ordinary errors, as agents write them.
    result = await ws.runtime.execute(
        "import time\nwhile True:\n    try:\n        time.sleep(0.2)\n"
        "    except Exception:\n        continue")
    assert isinstance(result.error, cell_time.CellTimeLimit)
    assert "was stopped" in str(result.error)
    # The next cell runs normally; a cell that awaits (yields) is not stopped.
    waited = await ws.runtime.execute("import asyncio\nawait asyncio.sleep(2.5)\nx = 1")
    assert waited.error is None
    # Harness code that blocks the loop outside any cell is never interrupted.
    import time
    time.sleep(2.5)
    ws.close()

