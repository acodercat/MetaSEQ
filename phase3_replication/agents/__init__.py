"""The system under test.

    arm           which configuration runs (topology, budget, verifier)
    system        MetaSEQAgent: runs the arm's topology turn by turn
    topologies/   single (one agent), fixed_roles (the MetaSEQ topology: coordinator, producers,
                  synthesis, verifier)
    harness/      how code reaches the runtime (one native tool call per step): makes the agents
    verification  the verifier stage
    workspace     a Python runtime plus lab-side access to it
    stage         one agent run by one role
    failure       why a run ended without an answer, and whether it was the model's
    instructions  which prompt pieces each stage receives
"""

from agents.arm import Arm, load_arms
from agents.instructions import TaskBrief
from agents.system import MetaSEQAgent
from agents.topologies import TurnOutcome
from agents.workspace import Workspace

__all__ = ["Arm", "MetaSEQAgent", "TaskBrief", "TurnOutcome", "Workspace", "load_arms"]
