"""Beijing domain: file datasets only (no database, no agent tools).

Deliberately holds no prompts. What an agent is told is part of a suite
(`suites/<suite>/environments/<domain>.json`), frozen with the tasks it was written for.
"""

from domains.beijing.data import DATA_DIR, HANDLES

FUNCTIONS: dict = {}

__all__ = ["DATA_DIR", "FUNCTIONS", "HANDLES"]
