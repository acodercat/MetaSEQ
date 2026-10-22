"""`models.toml` -> validated `ModelConfig`s.

The schema is the AirBench one minus the judge-panel fields, so an existing
AirBench `models.toml` section can be copied over unchanged (`model_id` is
accepted as an alias for `api_model`; unknown keys are ignored rather than
rejected, for the same reason).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from errors import ConfigurationError

# Seconds an endpoint may take when a model section sets no `timeout`, for the clients the
# lab makes over the OpenAI SDK (the SDK's own default). LiteLLM keeps its own (6000 s).
DEFAULT_TIMEOUT_S = 600.0


class ModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    api_model: str
    api_key: str = Field(repr=False)
    base_url: str | None = None
    max_tokens: int | None = Field(None, gt=0)
    timeout: float | None = Field(None, gt=0)
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    # How the endpoint is spoken to: Chat Completions (through LiteLLM under the code
    # harness, the OpenAI SDK under the tool harness), OpenAI's Responses API, which
    # GPT-6 Luna needs, or Anthropic's Messages API through the anthropic SDK (tool harness
    # only), which Claude needs.
    provider: Literal["openai_compatible", "openai_responses", "anthropic"] = "openai_compatible"
    # Responses API: `reasoning.effort` ("none" turns reasoning off); Messages API:
    # `output_config.effort`.
    reasoning_effort: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _alias_model_id(cls, data: Any) -> Any:
        if isinstance(data, dict) and "api_model" not in data and "model_id" in data:
            data = dict(data)
            data["api_model"] = data.pop("model_id")
        return data

    def chat_options(self) -> dict[str, Any]:
        """Chat Completions sampling options: the cap, the provider switches in the raw
        body, and the temperature unless the body already carries it (some self-hosted
        endpoints take it there, and it is never sent twice)."""
        options: dict[str, Any] = {}
        if self.max_tokens:
            options["max_tokens"] = self.max_tokens
        if self.extra_body:
            options["extra_body"] = dict(self.extra_body)
        if "temperature" not in self.extra_body:
            options["temperature"] = self.temperature
        return options

    def responses_options(self) -> dict[str, Any]:
        """Responses API sampling options: temperature, the cap, the reasoning effort."""
        options: dict[str, Any] = {"temperature": self.temperature}
        if self.max_tokens:
            options["max_output_tokens"] = self.max_tokens
        if self.reasoning_effort:
            options["reasoning"] = {"effort": self.reasoning_effort}
        return options

    def anthropic_options(self) -> dict[str, Any]:
        """Messages API options, as FinBench sends them: the cap, and in the raw body the
        temperature, the provider switches (`thinking`, for one) and the effort. The cap is
        required by the API (default 8192 when a section sets none)."""
        body = {**self.extra_body, "temperature": self.temperature}
        if self.reasoning_effort:
            body["output_config"] = {"effort": self.reasoning_effort}
        return {"max_tokens": self.max_tokens or 8192, "extra_body": body}

    def fingerprint(self) -> dict[str, Any]:
        """What served a run, as recorded in `run.json`. Never the key."""
        record = {
            "config": self.name,
            "api_model": self.api_model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "extra_body": dict(self.extra_body) or None,
            # Recorded only where they differ from the default, so the records of
            # models served before these fields existed are unchanged.
            "provider": None if self.provider == "openai_compatible" else self.provider,
            "reasoning_effort": self.reasoning_effort,
        }
        return {k: v for k, v in record.items() if v is not None}


class ModelRegistry:
    def __init__(self, configs: dict[str, ModelConfig]):
        self._configs = configs

    @classmethod
    def load(cls, path: Path) -> ModelRegistry:
        if not path.exists():
            raise ConfigurationError(
                f"{path} not found; copy models.toml.example and fill in credentials"
            )
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        configs = {}
        for name, fields in raw.items():
            try:
                configs[name] = ModelConfig(name=name, **fields)
            except Exception as exc:
                raise ConfigurationError(f"model {name!r} in {path}: {exc}") from exc
        return cls(configs)

    def get(self, name: str) -> ModelConfig:
        if name not in self._configs:
            raise ConfigurationError(
                f"model {name!r} is not in models.toml; available: {sorted(self._configs)}"
            )
        return self._configs[name]

    @property
    def names(self) -> list[str]:
        return list(self._configs)
