"""Static checks on agent-generated code.

Defence in depth, not a sandbox: the authoritative controls are a read-only
database role and running the lab in an OS/container boundary. Rules are the
AirBench set, plus the lab's own packages: task modules document their
ground truth, so importing one from the runtime would let an agent read the
answer key instead of doing the analysis.
"""

from __future__ import annotations

from cave_agent import AttributeRule, FunctionRule, ImportRule, RegexRule, SecurityChecker

from tasks.model import TASK_MODULE_PACKAGE

# Every top-level module of the lab (the layout is flat, so there is no single
# package name to forbid). Validators and task modules hold the answer key.
LAB_MODULES = (
    "agents", "evaluation", "analysis", "domains", "tasks", "llm",
    "cli", "settings", "validation", "errors",
)
FORBIDDEN_IMPORTS = {
    "os", "subprocess", "sys", "shutil", "pathlib", "socket", "urllib", "http",
    "ctypes", "gc", "csv", "multiprocessing", "threading", "inspect", "importlib",
    "pickle", "shelve", "tempfile", "joblib",
    *LAB_MODULES, TASK_MODULE_PACKAGE,
}
FORBIDDEN_FUNCTIONS = {
    "exec", "compile", "open", "input", "raw_input", "exit", "quit",
    "__import__", "globals", "locals", "breakpoint", "eval",
}
FORBIDDEN_ATTRIBUTES = {
    "__globals__", "__locals__", "__code__", "__closure__", "__defaults__",
    "__dict__", "__class__", "__bases__", "__mro__", "__subclasses__",
    "__import__", "__builtins__",
}
# SQL write statements, matched as statement shapes rather than bare keywords
# so ordinary Python (`dict.update()`, `create_engine`) is not penalised.
_SQL_WRITES = [
    (r"(?i)\bdelete\s+from\b", "SQL DELETE FROM"),
    (r"(?i)\bdrop\s+(table|database|index|view|schema|extension|function|trigger|role|user)\b",
     "SQL DROP"),
    (r"(?i)\balter\s+(table|database|index|view|schema|role|user|system)\b", "SQL ALTER"),
    (r"(?i)\bcreate\s+(table|database|index|view|schema|extension|function|trigger|role|user"
     r"|materialized)\b", "SQL CREATE"),
    (r"(?i)\binsert\s+into\b", "SQL INSERT INTO"),
    (r"(?i)\bupdate\s+[\w.\"]+\s+set\b", "SQL UPDATE ... SET"),
    (r"(?i)\btruncate\s+(table\s+)?[\w.\"]+", "SQL TRUNCATE"),
    (r"(?i)\bgrant\s+(select|insert|update|delete|all|usage|create|connect|references)\b",
     "SQL GRANT"),
    (r"(?i)\brevoke\s+(select|insert|update|delete|all|usage|create|connect|references)\b",
     "SQL REVOKE"),
]


# Paths that hold answers. `open` and path modules are already forbidden, but
# `pd.read_csv`/`pd.read_json` need no forbidden import: task modules document
# their ground truth, and `results/` holds other runs' answers. Matched as path
# shapes, never bare words.
_ANSWER_PATHS = [
    (r"(?:^|[^\w.])(?:suites|results)[/\\]", "access to a path that stores ground truth"),
]


# Files at all. The suite's system prompt tells the agent the data are the runtime's variables
# and the database, and that reading or writing files is blocked; `open` and the path modules
# are, but pandas and NumPy read and write files on their own. Runs share a machine, so a file
# one run writes (`/tmp/x.pkl`, `x.pkl` in the working directory) another can read. Saving or
# loading a file, a `/tmp` path, and `to_csv`/`to_json` given a destination are refused;
# `pd.read_sql` and `to_csv()`/`to_json()` returning text are not.
_FILE_IO = [
    (r"\.(?:to_(?:pickle|parquet|feather|hdf|excel|stata|orc|sql)"
     r"|read_(?:csv|pickle|parquet|feather|hdf|excel|table|fwf|stata|orc|json|html|xml|sas"
     r"|spss|clipboard))\s*\(", "reading or writing a file"),
    (r"\.to_(?:csv|json)\s*\(\s*(?![)\s]|(?:index|header|sep|orient|float_format|columns"
     r"|na_rep|date_format|lines|indent|double_precision|date_unit)\s*=)",
     "writing a file"),
    (r"\b(?:np|numpy)\.(?:save|savez|savez_compressed|load|loadtxt|savetxt|genfromtxt"
     r"|fromfile|memmap)\s*\(|\.tofile\s*\(", "reading or writing a file"),
    (r"[\'\"]/tmp\b", "a path in /tmp"),
]


# The database's limits. Every session starts with a 30 s statement timeout (domains/hk/db.py),
# the same for every run; an agent that raised it (`SET statement_timeout = '300s'`, seen on
# 2026-10-09) could run queries others cannot, and one left a scan running for hours that slowed
# every other run on the shared database. Session settings are not the agent's to change.
_SESSION = [
    (r"(?i)\b(?:statement_timeout|lock_timeout|idle_in_transaction_session_timeout"
     r"|work_mem|max_parallel_workers(?:_per_gather)?)\b", "changing the database's limits"),
    (r"(?i)\bset_config\s*\(", "changing the database's limits"),
]


# Catching everything. The cell time limit (`domains.cell_time`) stops a cell by raising a
# `BaseException`, which `except Exception` lets through; a bare `except:` or `except
# BaseException` in a loop swallows it at every retry, and the cell runs on unbounded (a loop
# of `try: read_sql(...) except: continue` held a run for hours). `except Exception` loses
# nothing an analysis needs.
_CATCH_ALL = [
    (r"\bexcept\s*:|\bexcept\b[^:\n]*\bBaseException\b",
     "catching every exception; catch `Exception` instead"),
]


def create_security_checker() -> SecurityChecker:
    return SecurityChecker([
        ImportRule(FORBIDDEN_IMPORTS),
        FunctionRule(FORBIDDEN_FUNCTIONS),
        AttributeRule(FORBIDDEN_ATTRIBUTES),
        *(RegexRule(pattern, label) for pattern, label in
          _SQL_WRITES + _ANSWER_PATHS + _FILE_IO + _SESSION + _CATCH_ALL),
    ])
