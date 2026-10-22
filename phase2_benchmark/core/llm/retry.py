"""Retry policy for LLM API calls.

The retry loop is provider-agnostic; each caller injects its own
`is_retryable` predicate (which errors should retry) and optional
`get_delay` (backoff schedule + Retry-After hint parsing). This
mirrors the pattern in metaseq-computer/axon and keeps the transient-
error classification separate from the loop mechanics.
"""

import logging
import time
from typing import Callable, TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)


logger = logging.getLogger("llm.retry")

T = TypeVar("T")

# Default: three attempts (1 initial + 2 retries). Judges are called in
# parallel from a bounded pool, so a slow-dying judge shouldn't block a
# sample for too long — we'd rather fail fast and mark partial-panel.
DEFAULT_MAX_ATTEMPTS = 3


def is_retryable_openai(err: Exception) -> bool:
    """True iff the error is a transient network/rate/5xx from the OpenAI SDK."""
    if isinstance(err, (APITimeoutError, APIConnectionError, RateLimitError)):
        return True
    if isinstance(err, APIStatusError) and 500 <= err.status_code < 600:
        return True
    return False


def exponential_backoff(attempt: int) -> float:
    """1.5s, 2.5s, 4.5s, ... (2^n + 0.5)."""
    return 2 ** attempt + 0.5


def with_retry(
    operation: Callable[[], T],
    *,
    is_retryable: Callable[[Exception], bool] = is_retryable_openai,
    get_delay: Callable[[int], float] = exponential_backoff,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    context: str = "",
) -> T:
    """Call `operation()` with retry on classified-retryable errors.

    Raises the last error after `max_attempts`; non-retryable errors propagate
    on the first hit. `context` is prepended to log messages (e.g. model name).
    """
    for attempt in range(max_attempts):
        try:
            return operation()
        except Exception as err:
            if not is_retryable(err) or attempt == max_attempts - 1:
                raise
            delay = get_delay(attempt)
            logger.info(f"{context}{err}; retrying in {delay:.1f}s")
            time.sleep(delay)
    # Unreachable — the loop either returns or raises.
    raise RuntimeError("with_retry: exhausted attempts without result or error")
