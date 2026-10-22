"""Centralized LLM configuration + sync client.

Use:
    from core.llm import ModelRegistry, LLMClient
    registry = ModelRegistry.load("models.toml")
    client = LLMClient(registry.get("opus48"))
    result = client.complete("hello", json_mode=True)
    print(result.text, result.reasoning)
"""

from core.llm.client import LLMClient
from core.llm.completion import Completion
from core.llm.registry import ModelConfig, ModelRegistry

__all__ = ["Completion", "LLMClient", "ModelConfig", "ModelRegistry"]
