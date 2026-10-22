"""Compose each stage's instructions from the prompt files and the task.

Every prompt the lab adds lives in `prompts/` as plain text; this module only
decides which pieces a stage receives:

    single      the task brief, or cave-agent's default instructions when there is none
    fixed_roles prompts/fixed_roles/stripped/* the MetaSEQ roles without analysis knowledge

The suite's system prompt is passed separately (cave-agent's
`system_instructions`) and is identical across arms.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from pathlib import Path

from cave_agent import Variable


@cache
def _prompt(name: str) -> str:
    return (files("agents") / "prompts" / name).read_text(encoding="utf-8").strip()


def load_prompts() -> int:
    """Read every prompt file now, as the protocol fingerprint does, so that a file
    edited while an experiment runs cannot reach runs stamped with the old fingerprint."""
    root = files("agents") / "prompts"
    names = [str(p.relative_to(root)) for p in Path(str(root)).rglob("*.md")]
    for name in names:
        _prompt(name)
    return len(names)


@dataclass(frozen=True)
class TaskBrief:
    """Task-level text every stage is given, as the source corpus gave it."""

    description: str | None = None
    requirements: str | None = None

    def blocks(self) -> list[str]:
        out = []
        if self.description:
            out.append(f"TASK DESCRIPTION:\n{self.description}")
        if self.requirements:
            out.append(f"TASK REQUIREMENTS:\n{self.requirements}")
        return out


# --- shared pieces -----------------------------------------------------------

def conversation_contract(queries: list[str]) -> str:
    """All turns so far, the current one marked; fresh stages have no history of their own."""
    if len(queries) == 1:
        return f"CURRENT TURN (1):\n{queries[0]}"
    prior = "\n\n".join(f"PRIOR TURN {i}:\n{q}" for i, q in enumerate(queries[:-1], 1))
    return (
        "FULL CONVERSATION (prior turns fix the dates, entities, thresholds and outputs"
        " that later turns refer to):\n"
        f"{prior}\n\nCURRENT TURN ({len(queries)}):\n{queries[-1]}"
    )


# --- single ------------------------------------------------------------------

def solo(brief: TaskBrief) -> str | None:
    """The single agent: the source corpus's instructions. None (cave-agent's default
    instructions) when there is nothing to add, so the bare single agent reproduces the
    archived baseline exactly."""
    return "\n\n".join(brief.blocks()) or None



# --- fixed roles -------------------------------------------------------------
# The MetaSEQ topology, assembled as the group's released multi-agent harness assembled it.
# prompts/fixed_roles/stripped/ holds the role texts without the analysis knowledge, so
# that a worker knows no more about the analysis than the single agent it is compared with;
# prompts/fixed_roles/published/ keeps the deployed texts for reference, and the README there
# gives the rule and the two adaptations to this suite.

SYNTHESIS = "synthesis_report"
VERIFICATION = "verification"
# The staged-values heading as the harness wrote it, and as the lab writes it: the harness
# ran one turn, so "verify EACH" meant every staged value; here a turn's earlier outputs
# are immutable, so the verifier is pointed at the REQUIRED list it was given.
HARNESS_STAGED_HEADING = ("CURRENT STAGED VALUES — verify EACH against your OWN fresh "
                          "recomputation; do NOT trust them:")
STAGED_HEADING = ("CURRENT STAGED VALUES (name: type) — verify EACH of the REQUIRED OUTPUTS "
                  "above against your OWN fresh recomputation; do NOT trust them. The other "
                  "values here are what earlier stages staged, and outputs completed in prior "
                  "turns are immutable:")
_FIXED_ROLES_TURN_RULES = (
    "TURN RULES:\n"
    "- Resolve relative phrases in the CURRENT TURN ('that hour', 'same day', 'the station') "
    "from the PRIOR TURNS above.\n"
    "- Outputs completed in prior turns are immutable; do not recompute or overwrite them.\n"
    "- Work only on outputs requested by the CURRENT TURN; do not precompute future-turn outputs."
)


def fixed_roles_context(queries: list[str]) -> str:
    """All turns so far, the current one marked, in the harness's wording."""
    if len(queries) == 1:
        return f"CURRENT TURN (1):\n{queries[0]}"
    prior = "\n\n".join(f"PRIOR TURN {i}:\n{q}" for i, q in enumerate(queries[:-1], 1))
    return (
        "FULL CONVERSATION SCOPE (prior turns define immutable dates, entities, "
        "thresholds, and staged outputs):\n"
        f"{prior}\n\n"
        f"CURRENT TURN ({len(queries)}):\n{queries[-1]}"
    )


def fixed_roles_required(variables: list[Variable]) -> str:
    """The required outputs as the harness listed them: name and description."""
    return "\n".join(
        f"- {v.name}: {(v.description or 'required runtime output').strip()}" for v in variables
    )


def fixed_roles_coordinator(context: str, required: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _prompt("fixed_roles/stripped/coordinator.md")},
        {"role": "user", "content": f"TASK: {context}\n\n"
                                    f"REQUIRED OUTPUT VARIABLES: {required or '(see task)'}\n\n"
                                    "Produce the JSON plan now."},
    ]


# The synthesis prompt's closing sentence; true only when a verifier follows it.
_VERIFIER_FOLLOWS = (" (A verification agent will independently double-check your values after"
                     " you, so assign your best current values.)")


def fixed_roles_worker(role: str, brief: TaskBrief, *, task: str, manifest: str, context: str,
                    required: str, verified: bool = True) -> str:
    """One worker's instructions, assembled as the harness's `_build_worker` did, plus
    the conversation contract (see the prompts README).

    Two additions to the harness: the role's rules are said to take precedence over the
    suite system prompt's single-analyst guidance (`fixed_roles/precedence.md`), and without
    a verifier (`verified=False`) synthesis is not told that one will check its values."""
    verify = role == VERIFICATION
    text = _prompt(f"fixed_roles/stripped/roles/{role}.md")
    if role == SYNTHESIS and not verified:
        if _VERIFIER_FOLLOWS not in text:
            raise ValueError("the synthesis prompt no longer ends with the verifier sentence")
        text = text.replace(_VERIFIER_FOLLOWS, "")
    parts = [text, _prompt("fixed_roles/precedence.md")]
    if not verify:
        parts.append(_prompt("fixed_roles/stripped/discipline.md"))
    parts.extend(brief.blocks())
    parts.append(f"EXACT CONVERSATION CONTRACT:\n{context}\n\n{_FIXED_ROLES_TURN_RULES}")
    staged = manifest and manifest != "{}"
    if verify:
        if required:
            parts.append(f"REQUIRED OUTPUTS TO VERIFY (and correct if wrong):\n{required}")
        if staged:
            parts.append(f"{STAGED_HEADING}\n{manifest}")
    else:
        if required:
            if role == SYNTHESIS:
                parts.append(
                    "OUTPUT OWNERSHIP: you are the ONLY producer that assigns the required output "
                    "variables. Assign each of them now — reusing the intermediate variables "
                    "upstream agents staged rather than recomputing from scratch — and print each "
                    f"to confirm it is set:\n{required}"
                )
            else:
                parts.append(
                    "OUTPUT OWNERSHIP: do NOT assign or create the task's required output "
                    f"variables ({required}); the synthesis agent alone assigns them. Stage your "
                    "findings in your OWN descriptively-named variables for it to reuse."
                )
        if staged:
            parts.append("VARIABLES ALREADY IN THE SHARED RUNTIME (already computed and correct) "
                         f"— reuse these directly; do NOT re-query or re-derive them:\n{manifest}")
    parts.append(f"YOUR SUBTASK:\n{task}")
    return "\n\n".join(parts)
