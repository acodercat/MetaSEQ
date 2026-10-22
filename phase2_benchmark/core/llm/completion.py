"""Value object returned by `LLMClient.complete`.

Kept as a frozen dataclass so it's hashable, thread-safe, and cheap to
pass through a pipeline. `reasoning_tokens=None` means "the provider did
not report a reasoning-token count" — distinct from `0` (no reasoning).
`reasoning` text is captured when the model config declares a
`thinking_echo_field` and the stream actually emits one, otherwise None.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Completion:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning: Optional[str] = None
    reasoning_tokens: Optional[int] = None
