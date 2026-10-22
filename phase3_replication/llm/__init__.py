"""Model configuration: the `models.toml` registry and the transport settings. The tool
harness's connection is `llm.tool_gateway`. Every stage of every arm talks to the same client,
so topology never changes transport.
"""

from __future__ import annotations

from llm.registry import DEFAULT_TIMEOUT_S, ModelConfig, ModelRegistry

__all__ = ["DEFAULT_TIMEOUT_S", "TRANSPORT_RETRIES", "ModelConfig", "ModelRegistry"]

# Transport retries for transient provider failures (429s in particular), in the OpenAI or
# anthropic SDK client. A transport concern: it never changes a
# successful response's content, so it is identical across arms and not fingerprinted.
TRANSPORT_RETRIES = 10
