"""Hong Kong domain: database engine, file datasets, and agent tools.

Deliberately holds no prompts. What an agent is told is part of a suite
(`suites/<suite>/environments/<domain>.json`), frozen with the tasks it was written for.
"""

from domains.hk.data import DATA_DIR, HANDLES, load_population
from domains.hk.tools import FUNCTIONS

__all__ = ["DATA_DIR", "FUNCTIONS", "HANDLES", "load_population"]
