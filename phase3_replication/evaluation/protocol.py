"""The protocol a run was made under, as a fingerprint.

Resume compares a stored run's fingerprint with the current one and reruns the
run when they differ, so runs made under different code are never mixed. A
change of form only (a moved module, removed dead code) is recorded instead in
`protocol_aliases.json` after a checked migration (see `evaluation.store`).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from functools import cache
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tasks.suite import Environment

if TYPE_CHECKING:       # the fingerprint module imports nothing of the agents it fingerprints
    from agents.harness import HarnessName

_ROOT = Path(__file__).resolve().parents[1]
# What decides how an agent behaves: every topology, prompt and instruction,
# the domains' tools, data loaders, database access and convention libraries,
# the limits every cell runs under, how a task is run, and how the model is called;
# and the agent framework's version. Scoring and reporting are not here:
# `metaseq score` already re-judges stored runs with today's code.
_FILES = ("agents/**/*.py", "agents/**/*.md", "domains/*.py", "domains/*/*.py",
          "evaluation/runner.py", "llm/*.py")


def protocol_fingerprint(environment: Environment, harness: HarnessName = "tool") -> str:
    """What a run was made under: the agent code and prompts, what the environment
    tells the agent, and the harness that carried its code to the runtime. A stored
    run with another fingerprint was made under a different protocol, and resuming
    reruns it rather than mixing the two."""
    digest = hashlib.sha256(_code_digest().encode())
    described = {
        "system_prompt": environment.system_prompt,
        "variables": [[v.name, v.description] for v in environment.variables],
        "functions": list(environment.functions),
    }
    described["harness"] = harness
    digest.update(json.dumps(described, ensure_ascii=False).encode())
    return digest.hexdigest()[:16]


@cache
def _code_digest() -> str:
    digest = hashlib.sha256()
    files = sorted({p for pattern in _FILES for p in _ROOT.glob(pattern)
                    if "__pycache__" not in p.parts})
    for path in files:
        digest.update(path.relative_to(_ROOT).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    digest.update(f"cave-agent {version('cave-agent')}".encode())
    return digest.hexdigest()


@cache
def code_state() -> dict[str, Any]:
    """The lab's commit and whether the tree differed from it, recorded with every run.
    Not part of the fingerprint: a commit that changes nothing an agent sees must not
    make stored runs stale."""
    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=_ROOT, capture_output=True, text=True,
                                  timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    commit = git("rev-parse", "HEAD")
    return {"commit": commit or None,
            "dirty": bool(git("status", "--porcelain", "--untracked-files=no")) if commit
            else None}
