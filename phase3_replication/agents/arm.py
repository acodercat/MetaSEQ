"""Arms: one configuration of the system under test.

    topology   single      one agent answers the turn
               fixed_roles the MetaSEQ topology: coordinator, domain workers, synthesis,
                           all within `max_steps`
    verification  (fixed_roles) the verifier ends the turn within the verifier's reserve

`max_steps` is the turn's budget: the single agent's limit, and for the MetaSEQ topology
the budget shared out among the producers, the synthesis worker (`synthesis_steps` held
back) and the verifier (`verify_steps` held back).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from errors import ConfigurationError
from settings import settings

# Fields that configured code paths no longer in this tree, with the one value a stored run
# may carry and still have run under the remaining code (`evaluation.experiment`).
REMOVED_FIELDS: dict[str, object] = {
    "rules": False, "delegation_steps": 12, "subagent_steps": 6, "delegation": "optional",
    "review_steps": 8, "reviewers": "separate", "revise_steps": 6, "verifier": "overwrite",
    "revision_reserve": 2, "prompts": "stripped", "conventions": "none",
}


class Arm(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str = ""
    topology: Literal["single", "fixed_roles"]

    max_steps: int = Field(20, gt=0)            # the answering agent, per turn
    # fixed_roles: an independent verifier audits the outputs within the same `max_steps`;
    # it holds `verify_steps` back and gets what the turn has not used
    verification: bool = False
    verify_steps: int = Field(6, gt=0)
    # fixed_roles: steps held back for the synthesis worker
    synthesis_steps: int = Field(3, gt=0)

    @model_validator(mode="after")
    def _verifier_fits(self) -> Arm:
        if self.verification and self.topology != "fixed_roles":
            raise ValueError("verification is defined for the fixed_roles topology")
        reserved = self.synthesis_steps + (self.verify_steps if self.verification else 0)
        if self.topology == "fixed_roles" and reserved >= self.max_steps:
            raise ValueError("synthesis_steps and verify_steps must leave the producers a step")
        return self

    @property
    def components(self) -> str:
        return self.topology


def load_arms(path: Path | None = None) -> dict[str, Arm]:
    path = path or settings.configs_dir / "arms.toml"
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    defaults = raw.pop("defaults", {})
    arms = {}
    for name, fields in raw.items():
        try:
            arms[name] = Arm(name=name, **{**defaults, **fields})
        except Exception as exc:
            raise ConfigurationError(f"arm {name!r} in {path}: {exc}") from exc
    return arms
