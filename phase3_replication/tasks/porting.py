"""Port a task set from an AirBench-layout repository into a frozen suite.

This is how `suites/*` were produced, and re-running it against a newer source
commit is how a suite is refreshed (`metaseq port ... --force`). It does four
things and nothing more:

1. For every task the source registry lists under each source domain key,
   copy its JSON (unwrapped from the one-element list, `module` dropped: the
   module is the sibling `.py`; the lab domain recorded as `domain`) and its
   module to `tasks/<category>/<name>.{json,py}`. Each turn's `claims`
   (statements an LLM judge checks in the answer text) are dropped: the lab
   scores the stored outputs with the validators only.
2. Rewrite the module's imports from the source framework to the lab's modules
   (`_REWRITES`, per source domain). Validator logic is not touched; any
   remaining reference to the source framework aborts the port.
3. Extract each domain's environment -- system prompt, runtime variable
   descriptions, function names -- by importing the source's domain module with
   the source's own interpreter, and write it verbatim to
   `environments/<domain>.json`.
4. Write `suite.toml` recording the source commit and whether its tree was
   dirty at port time.

The suite is assembled in a temporary directory and moved into place only when
complete, so a failed port never leaves a half-written suite behind.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from errors import ConfigurationError, TaskSpecificationError

# (pattern, replacement), applied in order to the module source.
# Imports may sit inside a function (indented); the indent is kept.
_COMMON: list[tuple[str, str]] = [
    (r"^(\s*)from core\.types import Turn$", r"\1from tasks import Turn"),
    (r"^(\s*)from core\.validation import ", r"\1from validation import "),
    (r"^(\s*)from evals\._shared\.scientific_outputs import ",
     r"\1from domains.scientific_outputs import "),
]
_HK: list[tuple[str, str]] = [
    (r"^(\s*)from domains\.HK\.db import (engine|read_frame)$",
     r"\1from domains.hk.db import \2"),
    (r"^(\s*)from config import PROJECT_ROOT$", r"\1from domains.hk.data import DATA_DIR"),
    (r'PROJECT_ROOT\s*/\s*"datasets"\s*/\s*"HK"\s*/\s*', "DATA_DIR / "),
    (r"PROJECT_ROOT\s*/\s*([\"'])datasets/HK/", r"DATA_DIR / \1"),     # one-string path
    (r'PROJECT_ROOT\s*/\s*"datasets"\s*/\s*"HK_population_1km\.csv"',
     'DATA_DIR / "population_1km.csv"'),
    (r"^from domains\.HK import BASE_VARIABLES$",
     "from domains.hk.data import load_population"),
    (r'\[v for v in BASE_VARIABLES if v\.name == "pop_df"\]\[0\]\.value', "load_population()"),
]
_BEIJING: list[tuple[str, str]] = [
    (r"^(\s*)from config import PROJECT_ROOT$", r"\1from domains.beijing.data import DATA_DIR"),
    (r'PROJECT_ROOT\s*/\s*"datasets"\s*/\s*"Beijing"', "DATA_DIR"),
    (r"PROJECT_ROOT\s*/\s*([\"'])datasets/Beijing/", r"DATA_DIR / \1"),  # one-string path
    (r"^(\s*)from evals\._shared\.mda8 import ", r"\1from domains.beijing.mda8 import "),
]
_REWRITES: dict[str, list[tuple[str, str]]] = {
    "HK": _COMMON + _HK,
    "Beijing": _COMMON + _BEIJING,
}
# Anything still naming the source framework after rewriting.
# The lab's own `domains` package (lower-case `hk`, `beijing`) shares its name
# with the source's (`domains.HK`, `domains.Beijing`, `domains.HB`), so only the
# source's forms count as residue.
_RESIDUE = re.compile(
    r"^\s*(from|import)\s+(core|config|evals|adapters)\b"
    r"|^\s*(from|import)\s+domains(\.(HK|HB|Beijing)\b|\s|$)"
    r"|PROJECT_ROOT|BASE_VARIABLES",
    re.MULTILINE,
)

_EXTRACT_ENV = """
import json, importlib
mod = importlib.import_module("domains.{domain_key}")
print(json.dumps({{
    "system_prompt": mod.SYSTEM_PROMPT,
    "variables": [{{"name": v.name, "description": v.description}} for v in mod.BASE_VARIABLES],
    "functions": [f.__name__ for f in getattr(mod, "EXTRA_FUNCTIONS", [])],
}}))
"""


@dataclass(frozen=True)
class PortResult:
    suite_dir: Path
    tasks: int
    commit: str
    dirty: bool


def rewrite_module(source: str, domain_key: str = "HK") -> str:
    """A source task module with its framework imports pointed at the lab's modules."""
    if domain_key not in _REWRITES:
        raise ConfigurationError(f"no import rewrites for source domain {domain_key!r}")
    for pattern, replacement in _REWRITES[domain_key]:
        source = re.sub(pattern, replacement, source, flags=re.MULTILINE)
    if residue := sorted({m.group(0).strip() for m in _RESIDUE.finditer(source)}):
        raise TaskSpecificationError(f"unported references remain: {residue}")
    return source


def port_suite(
    source: Path,
    registry: str,
    suite: str,
    *,
    suites_dir: Path,
    domains: dict[str, str],
    description: str = "",
    force: bool = False,
) -> PortResult:
    """`domains` maps each lab domain to its key in the source registry,
    e.g. {"hk": "HK", "beijing": "Beijing"}."""
    source = source.resolve()
    target = suites_dir / suite
    if target.exists() and not force:
        raise ConfigurationError(f"{target} exists; pass --force to replace it")

    listing = _read_json(source / registry)
    paths = {
        domain: [path for category in listing[key].values() for path in category.values()]
        for domain, key in domains.items()
    }
    with tempfile.TemporaryDirectory(dir=suites_dir) as scratch:
        staging = Path(scratch) / suite
        for domain, key in domains.items():
            for rel in paths[domain]:
                _port_task(source, rel, staging / "tasks", key, domain)
            _write_json(staging / "environments" / f"{domain}.json",
                        _extract_environment(source, key))

        repo_root = Path(_git(source, "rev-parse", "--show-toplevel"))
        commit = _git(source, "rev-parse", "HEAD")
        dirty = bool(_git(source, "status", "--porcelain", "--", "."))
        manifest = {
            "name": suite,
            "domains": list(domains),
            "description": description,
        }
        provenance = {
            "repository": repo_root.name,
            "path": str(source.relative_to(repo_root)) if source != repo_root else ".",
            "registry": registry,
            "commit": commit,
            "dirty": dirty,
            "ported_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tasks": sum(len(p) for p in paths.values()),
        }
        (staging / "suite.toml").write_text(
            _toml(manifest) + "\n[source]\n" + _toml(provenance), encoding="utf-8"
        )

        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
    return PortResult(target, sum(len(p) for p in paths.values()), commit, dirty)


def _port_task(source: Path, rel: str, tasks_dir: Path, domain_key: str, domain: str) -> None:
    cases = _read_json(source / rel)
    if not (isinstance(cases, list) and len(cases) == 1):
        raise TaskSpecificationError(f"{rel}: expected exactly one case")
    case = cases[0]
    for conversation in case.get("conversations", []):
        for turn in conversation.get("turns", []):
            turn.pop("claims", None)
    module_file = source / (case.pop("module").replace(".", "/") + ".py")
    case["domain"] = domain
    stem = tasks_dir / case["category"] / case["name"]
    stem.parent.mkdir(parents=True, exist_ok=True)
    if stem.with_suffix(".json").exists():
        raise TaskSpecificationError(f"{rel}: a task named {case['name']!r} was already ported")
    _write_json(stem.with_suffix(".json"), case)
    try:
        ported = rewrite_module(module_file.read_text(encoding="utf-8"), domain_key)
    except TaskSpecificationError as exc:
        raise TaskSpecificationError(f"{module_file}: {exc}") from exc
    stem.with_suffix(".py").write_text(ported, encoding="utf-8")


def _extract_environment(source: Path, domain_key: str) -> dict:
    python = source / ".venv" / "bin" / "python"
    if not python.exists():
        raise ConfigurationError(f"{python} not found; run `uv sync` in the source first")
    result = subprocess.run(
        [str(python), "-c", _EXTRACT_ENV.format(domain_key=domain_key)],
        cwd=source, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise ConfigurationError(f"extracting the environment failed:\n{result.stderr[-2000:]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


def _git(source: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(source), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _toml(table: dict) -> str:
    """Flat TOML key/values. JSON string escaping is valid TOML basic-string escaping."""
    def value(v: object) -> str:
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, int):
            return str(v)
        if isinstance(v, list):
            return json.dumps([str(x) for x in v], ensure_ascii=False)
        return json.dumps(str(v), ensure_ascii=False)
    return "".join(f"{k} = {value(v)}\n" for k, v in table.items())


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, document) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
