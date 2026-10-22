"""Validator-side primitives used by every ported task module.

Copied unchanged in behaviour from AirBench `core/validation.py` (a superset
of the Phase 2 copy: identical `compare_numeric`, plus `reports_as`), so a
ported validator scores exactly as it did in its source corpus.

Every validator inspects the runtime variables the agent populated and
compares them against ground truth it recomputes from the source data.
This module exposes the four primitives that hand-off requires:

- `ValidatorResult`: the (success, message, variables_not_set) tuple that
  every `validate_*` returns.
- `is_finite_number`: NaN/None/bool/inf guard before any arithmetic.
- `compare_numeric`: signed numeric equality within an explicit tolerance,
  for bands that absorb a measured implementation spread. Never hand-roll
  `abs(a - b) > tol` — sign-erasing patterns slip in otherwise.
- `reports_as`: for a value the Variable asks for to N decimal places — the
  submission must report to the same N-place figure as the truth. The
  `decimals=` band of `compare_numeric` does not guarantee that (see below).
"""

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

try:
    import numpy as np
    _NUMPY_NUMERIC: tuple = (np.integer, np.floating)
except ImportError:
    _NUMPY_NUMERIC = ()


@dataclass
class ValidatorResult:
    """Return value of every `validate_*` in a task module.

    `variables_not_set` distinguishes "the agent didn't even populate the
    required runtime variables" (an infrastructure / refusal signal) from
    "the agent computed values but they're wrong" (a substantive failure).
    """

    success: bool
    message: str
    variables_not_set: bool = False


def is_finite_number(value) -> bool:
    """Return True iff `value` is a finite int/float (or numpy numeric).

    Rejects None, bool, NaN, +/-inf, strings, lists, and any non-numeric type.
    Use this as a NaN/None guard before any arithmetic comparison — without it,
    `abs(nan - x) > tol` is False, causing NaN to silently pass validation.
    """
    if value is None or isinstance(value, bool):
        return False
    if not isinstance(value, (int, float, *_NUMPY_NUMERIC)):
        return False
    return math.isfinite(float(value))


def _report(value: float, decimals: int) -> Decimal:
    """`value` rounded to `decimals` places, half away from zero, in decimal
    arithmetic on the number's shortest repr — NOT `round()`, which works on
    the binary float and turns 2.675 into 2.67."""
    return Decimal(repr(float(value))).quantize(
        Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def reports_as(actual, expected, *, decimals: int) -> bool:
    """Whether `actual` is `expected` reported to `decimals` places.

    True iff `actual` is finite, reports to the same `decimals`-place figure
    as `expected` under the corpus rounding convention — decimal, half away
    from zero, on the shortest repr of the float — and lies within half a
    unit of the last place of the UNROUNDED `expected`. So the correctly
    rounded figure passes, the unrounded figure passes, and a value from a
    different method passes only if it would have been reported identically.

    Use it where the Variable asks for N decimal places. Keep
    `compare_numeric(..., tolerance=)` where the band is meant to absorb
    measured implementation variance rather than a reporting format.

    Why not `compare_numeric(..., decimals=)`: its band is centred on the
    unrounded truth and admits anything within 0.006 — including a wrong
    method's rounded figure when the two happen to fall 0.0056 apart (Gate B
    round 14, -1.39 for -1.38). Centring the band on the rounded truth
    instead admits a wrong method's UNROUNDED figure (round 15, -1.38539
    passing for -1.38). Requiring the same rounding closes both: -1.39 and
    -1.38539 both round to -1.39, and -1.38 is the report.
    """
    if not is_finite_number(expected):
        raise ValueError(
            f"reports_as: `expected` must be a finite number, got {expected!r}"
        )
    if not is_finite_number(actual):
        return False
    actual, expected = float(actual), float(expected)
    # Decimal on both sides: 2.68 - 2.675 is 0.00500000000000034 in binary,
    # which would refuse the exact half-unit distance the rule allows.
    gap = abs(Decimal(repr(actual)) - Decimal(repr(expected)))
    if gap > Decimal(5).scaleb(-decimals - 1):
        return False
    return _report(actual, decimals) == _report(expected, decimals)


def compare_numeric(
    actual,
    expected,
    *,
    tolerance: float | None = None,
    decimals: int | None = None,
) -> bool:
    """Signed numeric equality within tolerance.

    Returns True iff `actual` is a finite number within tolerance of `expected`.
    Returns False (never raises) for None, NaN, +/-inf, bool, or non-numeric
    `actual` — so wrong-type and NaN agent outputs always fail validation.

    Use this in every validator instead of hand-rolling `abs(a - b) > tol`.
    Critically, this compares the **signed** difference: `+12` vs `-12` is
    a failure (≠), which is the correct behaviour for variables whose
    sign carries scientific meaning (jumps, declines, z-scores, year-over-
    year changes). Hand-rolled `abs(abs(a) - abs(b))` patterns erase signs
    and have caused real bugs in this repo — do not introduce new ones.

    Specify exactly one of `tolerance` or `decimals`:
      - tolerance=0.1     → absolute tolerance of ±0.1
      - decimals=2        → derives tolerance = 0.6 * 10^(-decimals) = 0.006.
                            This does NOT mean "rounds to the same 2-dp number":
                            a value 0.0056 away rounds differently and passes
                            (Gate B round 14). For that guarantee use
                            `reports_as`; keep `decimals=` only where a case
                            was reviewed on it and not yet migrated.
    """
    if (tolerance is None) == (decimals is None):
        raise ValueError(
            "compare_numeric: pass exactly one of `tolerance=` or `decimals=`"
        )
    if tolerance is None:
        tolerance = 0.6 * (10 ** (-decimals))

    if not is_finite_number(expected):
        raise ValueError(
            f"compare_numeric: `expected` must be a finite number, got {expected!r}"
        )
    if not is_finite_number(actual):
        return False
    return abs(float(actual) - float(expected)) <= tolerance
