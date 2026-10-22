"""The three ways a run can go wrong, kept apart because they mean different things.

- `ConfigurationError`: the lab is not set up (missing credential, unknown
  model or arm). Nothing ran.
- `TaskSpecificationError`: a task is malformed or its validator crashed.
  Deterministic — retrying cannot help, and the result must not be scored as
  a model failure.
- `InfrastructureError`: the provider or database failed. Retryable; the run
  is recorded as errored and picked up again on resume. `kind` names the failure
  (`agents.failure.classify`).
"""


class ConfigurationError(RuntimeError):
    pass


class TaskSpecificationError(RuntimeError):
    pass


class InfrastructureError(RuntimeError):
    def __init__(self, message: str, kind: str = "unknown"):
        super().__init__(message)
        self.kind = kind
