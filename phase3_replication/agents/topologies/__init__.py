"""Topologies: how a turn is divided among agents.

    single      one agent (the baseline)
    fixed_roles the MetaSEQ topology: coordinator -> domain workers -> synthesis -> verifier
"""

from agents.topologies.base import Team, Topology, TurnOutcome
from agents.topologies.fixed_roles import FixedRoles
from agents.topologies.single import Single

TOPOLOGIES: dict[str, type[Topology]] = {
    "single": Single,
    "fixed_roles": FixedRoles,
}


def build_topology(team: Team) -> Topology:
    return TOPOLOGIES[team.arm.topology](team)


__all__ = ["TOPOLOGIES", "Team", "Topology", "TurnOutcome", "build_topology"]
