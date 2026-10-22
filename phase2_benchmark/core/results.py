"""Result-file conventions shared by the runner and all analysis scripts.

A benchmark directory (`experiments/{exp}/{domain}/{category}/{benchmark}/`)
holds three kinds of JSON files:

- main PV result files: `{model_id}_{YYYYmmdd}_{HHMMSS}.json`
- RQ sibling: `{main_stem}_scores.json` (written by scripts.score_responses)
- CC sibling: `{main_stem}_claims.json` (written by scripts.verify_claims)

Every consumer that globs `*.json` MUST distinguish main files from siblings.
Sorting `*.json` lexicographically and taking the last entry silently selects
a sibling once RQ/CC have run (`_` sorts after `.`), which is how the
"every scored benchmark reports PASS" bug shipped. Use these helpers instead
of ad-hoc globs.
"""

from pathlib import Path
from typing import List, Optional

SIBLING_SUFFIXES = ("_scores", "_claims")


def sanitize_model_id(api_model: str) -> str:
    """Make an api_model id safe for use in result filenames.

    OpenRouter-style ids contain `/` (e.g. `deepseek/deepseek-chat`), which
    would silently create an extra directory level and break every glob over
    `{model_id}_*.json`. Applied at write time by scripts.run and at lookup
    time by core.judging.infer_agent_lab, so the two stay consistent.
    """
    return api_model.replace("/", "-").replace(":", "-")


def is_main_result_file(path: Path) -> bool:
    """True for a main PV result file, False for RQ/CC siblings."""
    return path.suffix == ".json" and not path.stem.endswith(SIBLING_SUFFIXES)


def main_result_files(bench_dir: Path, pattern: str = "*.json") -> List[Path]:
    """Main result files in one benchmark directory, sorted by filename.

    Filenames embed `{YYYYmmdd}_{HHMMSS}`, so lexicographic order equals
    chronological order for a fixed model_id.
    """
    return sorted(p for p in bench_dir.glob(pattern) if is_main_result_file(p))


def latest_result_file(bench_dir: Path, pattern: str = "*.json") -> Optional[Path]:
    """The most recent main result file in one benchmark directory, or None."""
    files = main_result_files(bench_dir, pattern)
    return files[-1] if files else None


def result_has_infra_error(data: dict) -> bool:
    """True if any turn in a loaded main-result dict carries an infra `error`.

    Turns written by `runner._make_error_result` (API/DB crash) and turns
    aborted mid-conversation both set `error`; genuine model failures do not.
    Resume logic treats such results as retryable, not as completed runs.
    """
    for scenario in data.values():
        if not isinstance(scenario, dict):
            continue
        for conv in scenario.get("conversations", []):
            for turn in conv.get("turns", []):
                if turn.get("error"):
                    return True
    return False


def result_is_complete(data: dict) -> bool:
    """True if every turn in a loaded main-result dict was evaluated.

    "Evaluated" means the turn has a `success` verdict — pass or fail — and
    no infrastructure `error`. A result where the model legitimately failed
    counts as complete; a result frozen by an API/DB outage does not.
    """
    for scenario in data.values():
        if not isinstance(scenario, dict):
            continue
        for conv in scenario.get("conversations", []):
            for turn in conv.get("turns", []):
                if "success" not in turn or turn.get("error"):
                    return False
    return True
