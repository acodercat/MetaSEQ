"""Where results live, in AirBench's layout plus the lab's `arm` level.

    results/                 the study; any other experiment under
                             results/<experiment>/
        <domain>/<category>/<task>/<arm>/<model>/r<repeat>/
            run.json
            programmatic_verification.json
            transcripts/<conversation>.jsonl
        report/              written by `metaseq report`
        protocol_aliases.json    (if any) old -> current protocol fingerprints, with
                                 the equivalence checks that justified each
        model_aliases.json       (if any) a model configuration runs were made under ->
                                 the one it counts as (the same model served elsewhere)

A run IS a directory containing run.json; enumerate with `ResultStore.runs`,
never a bare glob over *.json (which would pick up the verdict file as a run).
Repeats are numbered rather than timestamped, as in AirBench, because a
resumed experiment must find the run it is looking for by name.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from evaluation.records import (
    RunRecord,
    Scorecard,
    read_json,
    write_json,
)

ATTEMPTS_FILE = "attempts.jsonl"     # failed attempts, appended; kept across reruns
RUN_FILE = "run.json"
PV_FILE = "programmatic_verification.json"
TRANSCRIPTS_DIR = "transcripts"
REPORT_DIR = "report"
ALIASES_FILE = "protocol_aliases.json"
MODEL_ALIASES_FILE = "model_aliases.json"
STUDY = "study"                      # the experiment whose store is results/ itself


@dataclass(frozen=True)
class RunKey:
    """One cell of an experiment. Identity is (arm, model, task, repeat); domain
    and category only place the run in the tree."""

    arm: str
    model: str
    task: str
    repeat: int
    domain: str = field(default="", compare=False)
    category: str = field(default="", compare=False)

    def relative(self) -> Path:
        return (Path(self.domain) / self.category / self.task / self.arm / self.model
                / f"r{self.repeat}")


logger = logging.getLogger(__name__)

_SAVE_ATTEMPTS, _SAVE_PAUSE_S = 4, 5.0


def _retrying(write: Callable[[], None]) -> None:
    """`write`, tried again after a pause when the file system fails (the results may be on
    NFS, where a stale handle or a dropped mount comes and goes); the last failure raises."""
    for attempt in range(1, _SAVE_ATTEMPTS + 1):
        try:
            write()
            return
        except OSError as exc:
            if attempt == _SAVE_ATTEMPTS:
                raise
            logger.warning("save failed (%s); retrying in %.0f s", exc, _SAVE_PAUSE_S)
            time.sleep(_SAVE_PAUSE_S)


class ResultStore:
    def __init__(self, results_dir: Path, experiment: str):
        self.root = results_dir if experiment == STUDY else results_dir / experiment

    @property
    def report_dir(self) -> Path:
        return self.root / REPORT_DIR

    def path(self, key: RunKey) -> Path:
        if not (key.domain and key.category):
            raise ValueError(f"{key} has no domain/category to place it by")
        return self.root / key.relative()

    def status(self, key: RunKey) -> Literal["missing", "error", "ok"]:
        run_file = self.path(key) / RUN_FILE
        if not run_file.exists():
            return "missing"
        return "ok" if read_json(run_file)["run"].get("status") == "ok" else "error"

    def made_under(self, key: RunKey) -> tuple[str | None, dict, dict]:
        """The protocol fingerprint, arm and model configuration a stored run was made under.

        The fingerprint is read through `protocol_aliases.json` when the experiment
        has one: a record, written after checking equivalence, that code which
        changed only in form (a moved module, removed dead code) still counts as
        the protocol the run was made under. The model configuration is read through
        `model_aliases.json` alike: the same model and parameters served by another
        endpoint count as the configuration the experiment names. `run.json` itself is
        never rewritten, so it keeps what actually served the run.
        """
        run = read_json(self.path(key) / RUN_FILE)["run"]
        protocol = run.get("protocol")
        model = next((alias["counts_as"] for alias in self._model_aliases()
                      if alias["made"] == run["model"]), run["model"])
        return self._aliases().get(protocol, protocol), run["arm"], model

    def _aliases(self) -> dict[str, str]:
        path = self.root / ALIASES_FILE
        return read_json(path)["aliases"] if path.exists() else {}

    def _model_aliases(self) -> list[dict]:
        path = self.root / MODEL_ALIASES_FILE
        return read_json(path)["aliases"] if path.exists() else []

    def is_scored(self, key: RunKey) -> bool:
        """Whether the run has verdicts that need no retry. A turn left at
        `infra_error` (the validator's database was down) is transient, so
        its run counts as unscored and the next `run` scores it again."""
        card = self.load_scorecard(key)
        return card is not None and not any(v.status == "infra_error" for v in card.verdicts)

    def record_attempt(self, key: RunKey, run: RunRecord) -> None:
        """Append a failed attempt to the run's attempt log, which a rerun keeps: what
        failed, how, and when, so that retries are counted and reported."""
        target = self.path(key) / ATTEMPTS_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as log:
            log.write(json.dumps({"started_at": run.started_at, "finished_at": run.finished_at,
                                  "error_kind": run.error_kind, "error": run.error},
                                 ensure_ascii=False) + "\n")

    def attempts(self, key: RunKey) -> int:
        """Failed attempts recorded for the run."""
        target = self.path(key) / ATTEMPTS_FILE
        return sum(1 for _ in target.open(encoding="utf-8")) if target.exists() else 0

    def save_run(self, key: RunKey, run: RunRecord, transcripts: dict[str, list]) -> None:
        _retrying(lambda: self._save_run(key, run, transcripts))

    def _save_run(self, key: RunKey, run: RunRecord, transcripts: dict[str, list]) -> None:
        directory = self.path(key)
        # A rerun replaces the previous attempt whole: verdict and transcripts.
        (directory / PV_FILE).unlink(missing_ok=True)
        shutil.rmtree(directory / TRANSCRIPTS_DIR, ignore_errors=True)
        # Transcripts first, so a crash can leave an unreferenced transcript but
        # never a run.json citing one that does not exist.
        for conversation_id, lines in transcripts.items():
            if lines:
                target = directory / TRANSCRIPTS_DIR / f"{conversation_id}.jsonl"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    "".join(json.dumps({"index": i, **line}, ensure_ascii=False, default=repr)
                            + "\n" for i, line in enumerate(lines)),
                    encoding="utf-8",
                )
        write_json(directory / RUN_FILE, run.to_dict())

    def save_scorecard(self, key: RunKey, scorecard: Scorecard) -> None:
        _retrying(lambda: write_json(self.path(key) / PV_FILE, scorecard.to_dict()))

    def load_run(self, key: RunKey) -> RunRecord:
        return RunRecord.from_dict(read_json(self.path(key) / RUN_FILE))

    def load_scorecard(self, key: RunKey) -> Scorecard | None:
        """The verdicts on the run's final outputs."""
        path = self.path(key) / PV_FILE
        return Scorecard.from_dict(read_json(path)) if path.exists() else None

    def runs(self) -> Iterator[RunKey]:
        """Every stored run, in path order."""
        for run_file in sorted(self.root.glob(f"*/*/*/*/*/r*/{RUN_FILE}")):
            directory = run_file.parent
            model, arm, task, category, domain = (p.name for p in list(directory.parents)[:5])
            yield RunKey(arm=arm, model=model, task=task, repeat=int(directory.name[1:]),
                         domain=domain, category=category)
