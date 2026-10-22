"""Model registry: load and validate `models.toml`, expose typed configs.

The `lab` field is the foundation lab each model belongs to (anthropic,
openai, google, moonshot, alibaba, deepseek, zhipu, minimax, ...). It is
used by `rater_pool(exclude_same_lab=True)` to skip same-lab judges as a
robustness check.

Lab resolution is explicit-first with a prefix-heuristic fallback: an
explicit `lab = "..."` in the entry wins, otherwise the key prefix is
matched against `_LAB_PREFIXES`, otherwise `lab` is `None` (and
`rater_pool(exclude_same_lab=True)` will raise on that).

The `provider` field routes to the correct API surface at request time
(see `core/llm/client.py`): `openai_responses` uses the Responses API,
`google` uses native Gemini, everything else (`openai`, `anthropic`,
`moonshot`, `None`) goes through the OpenAI-compatible chat completions
endpoint (many "provider=anthropic" style entries point base_url at a
translating proxy, hence the shared path).

Reasoning parameters (`reasoning`, `reasoning_effort`, `reasoning_summary`,
`thinking_level`, `extra_body`) are passed straight through to the API
request; `thinking_echo_field` is agent-side metadata (which response
field holds the CoT) and is unused by the sync judge client.
"""

import tomllib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Convenience prefix → lab heuristic. Set `lab = "..."` explicitly in
# models.toml for any entry that should not rely on this table.
_LAB_PREFIXES: List[tuple[tuple[str, ...], str]] = [
    (("claude-", "opus", "sonnet", "haiku"), "anthropic"),
    (("gpt-", "gpt", "o1-", "o3-", "o4-"), "openai"),
    (("gemini",), "google"),
    (("kimi",), "moonshot"),
    (("qwen",), "alibaba"),
    (("deepseek",), "deepseek"),
    (("glm",), "zhipu"),
    (("minimax/",), "minimax"),
]


def _infer_lab_from_name(name: str) -> Optional[str]:
    n = name.lower()
    for prefixes, lab_name in _LAB_PREFIXES:
        if n.startswith(prefixes):
            return lab_name
    return None


class ModelConfig(BaseModel):
    """One model's configuration; immutable, validated at registry load time."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str                                          # registry key (section header)
    api_model: str                                     # identifier sent to the provider's API
    api_key: str
    base_url: Optional[str] = None
    max_tokens: Optional[int] = Field(None, gt=0)
    timeout: Optional[float] = Field(None, gt=0)
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    lab: Optional[str] = None

    # Provider dispatch and reasoning knobs. `provider=None` means the
    # OpenAI-compatible chat completions endpoint at base_url.
    provider: Optional[str] = None                     # "openai" | "openai_responses" | "anthropic" | "google" | "moonshot" | None
    reasoning: bool = False                            # if True, request reasoning (chat completions: max_completion_tokens + no temperature)
    reasoning_effort: Optional[str] = None             # "none" | "low" | "medium" | "high" | "max"
    reasoning_summary: Optional[str] = None            # "concise" | "detailed" — Responses API only
    thinking_level: Optional[str] = None               # Google native Gemini reasoning depth
    thinking_echo_field: Optional[str] = None          # response field carrying the CoT (agent-side metadata; unused by judge client)
    extra_body: Dict[str, Any] = Field(default_factory=dict)  # provider-specific passthrough (e.g. {reasoning: {enabled: false}}, provider routing)

    @model_validator(mode="before")
    @classmethod
    def _alias_model_id(cls, data: Any) -> Any:
        """Accept `model_id` as an alias for `api_model` in toml entries."""
        if isinstance(data, dict) and "api_model" not in data and "model_id" in data:
            data = dict(data)
            data["api_model"] = data.pop("model_id")
        return data


class ModelRegistry:
    """Loaded view of `models.toml`. Construct via `ModelRegistry.load(path)`."""

    def __init__(self, configs: Dict[str, ModelConfig]):
        self._configs = configs

    @classmethod
    def load(cls, path: Path | str) -> "ModelRegistry":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Create it with the schema from models.toml.example."
            )
        raw = tomllib.loads(path.read_text())
        configs: Dict[str, ModelConfig] = {}
        for name, fields in raw.items():
            try:
                fields = dict(fields)
                if "lab" not in fields:
                    inferred = _infer_lab_from_name(name)
                    if inferred is not None:
                        fields["lab"] = inferred
                configs[name] = ModelConfig(name=name, **fields)
            except Exception as e:
                raise ValueError(f"model {name!r} in {path}: {e}") from e
        return cls(configs)

    def get(self, name: str) -> ModelConfig:
        if name not in self._configs:
            raise ValueError(
                f"model {name!r} not registered; available: {sorted(self._configs)}"
            )
        return self._configs[name]

    def find_by_api_model(self, api_model: str) -> Optional[ModelConfig]:
        """Reverse-lookup by api_model. Returns the first match or None."""
        for cfg in self._configs.values():
            if cfg.api_model == api_model:
                return cfg
        return None

    def all(self) -> List[ModelConfig]:
        """All registered model configs, in models.toml order."""
        return list(self._configs.values())

    def select(self, names: Iterable[str]) -> List[ModelConfig]:
        return [self.get(n) for n in names]

    def __contains__(self, name: str) -> bool:
        return name in self._configs

    @property
    def names(self) -> List[str]:
        return sorted(self._configs)
