from cave_agent import Variable

from tasks import Turn
from validation import ValidatorResult, compare_numeric

TOTAL = 42.0


def validate_total(response: str, runtime, turn: Turn) -> ValidatorResult:
    value = runtime.retrieve("total")
    if value is None:
        return ValidatorResult(False, "total not set", variables_not_set=True)
    return ValidatorResult(compare_numeric(value, TOTAL, tolerance=1e-9), f"total={value!r}")


def validate_doubled(response: str, runtime, turn: Turn) -> ValidatorResult:
    value = runtime.retrieve("doubled")
    if value is None:
        return ValidatorResult(False, "doubled not set", variables_not_set=True)
    return ValidatorResult(compare_numeric(value, 2 * TOTAL, tolerance=1e-9), f"doubled={value!r}")


variables = [
    Variable("total", None, "float: sum of readings_df.value"),
    Variable("doubled", None, "float: twice the total from the previous turn"),
]
validators = {"validate_total": validate_total, "validate_doubled": validate_doubled}
