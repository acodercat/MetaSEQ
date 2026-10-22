"""Synchronous LLM client with JSON-mode, retry, and reasoning-trace capture.

The sync workhorse for AirBench's auditing / classification / response
scoring scripts. The async agent loop in `runner.py` continues to use the
cave-agent runtime separately — that path is not touched here.

Provider routing (per `cfg.provider`):
  - `openai_responses` → Responses API (`client.responses.create`), needed
    for GPT-5.5-style reasoning summaries and the `input=...` message shape.
  - `google` → NotImplementedError (native Gemini not wired; use a
    base_url pointing at Google's OpenAI-compat endpoint instead).
  - anything else (`openai`, `anthropic`, `moonshot`, None) → chat
    completions via streaming. Many "provider=anthropic"-style entries
    point base_url at a translating proxy, hence the shared path.

Chat completions are streamed internally (even though the interface is
sync single-shot) for two reasons: reasoning models can take minutes and
non-streaming requests risk proxy idle-timeouts; and when the model
config declares a `thinking_echo_field`, only streaming exposes the
CoT delta from the provider.

Reasoning-mode requests skip `temperature` and switch to
`max_completion_tokens` (the OpenAI convention that Azure GPT-5.x
enforces). `reasoning_effort`, `reasoning_summary`, and `extra_body` are
pass-throughs.
"""

import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from core.llm.completion import Completion
from core.llm.registry import ModelConfig
from core.llm.retry import with_retry


logger = logging.getLogger("llm.client")


class LLMClient:
    """One client per ModelConfig. Thread-safe (openai.OpenAI is)."""

    def __init__(
        self,
        cfg: ModelConfig,
        *,
        timeout: Optional[float] = None,
        max_attempts: int = 3,
    ):
        self.cfg = cfg
        self._max_attempts = max_attempts
        self._client = OpenAI(
            api_key=cfg.api_key,
            base_url=cfg.base_url,  # OpenAI SDK handles None as default
            timeout=timeout if timeout is not None else (cfg.timeout or 120.0),
            max_retries=0,  # retry logic lives in core.llm.retry
        )

    def complete(
        self,
        prompt: str,
        *,
        json_mode: bool = False,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[Completion]:
        """Send one completion. Returns a `Completion` or None on terminal failure.

        Callers can access `.text` for the response body and `.reasoning`
        for the CoT trace (present only when the model config declares a
        `thinking_echo_field` and the provider actually emitted one).
        A None return means "this call dropped out"; caller decides whether
        to treat that as a partial-panel signal or hard failure.
        """
        messages = self._build_messages(prompt, system)
        if self.cfg.provider == "google":
            raise NotImplementedError(
                f"{self.cfg.name}: provider='google' (native Gemini) is not "
                "supported by this sync client — point base_url at Google's "
                "OpenAI-compatible endpoint (see the [gemini] entry in models.toml)."
            )
        do_call = (
            self._call_responses if self.cfg.provider == "openai_responses"
            else self._call_chat_completions
        )
        try:
            return with_retry(
                lambda: do_call(messages, json_mode, temperature, max_tokens),
                max_attempts=self._max_attempts,
                context=f"{self.cfg.name}: ",
            )
        except Exception as err:
            logger.warning(f"{self.cfg.name}: terminal failure: {err}")
            return None

    # ------------------------------------------------------------------
    # Message construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_messages(prompt: str, system: Optional[str]) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    # ------------------------------------------------------------------
    # Chat completions (streamed, with optional reasoning capture)
    # ------------------------------------------------------------------

    def _call_chat_completions(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool,
        temperature_override: Optional[float],
        max_tokens_override: Optional[int],
    ) -> Completion:
        kwargs = self._chat_kwargs(messages, json_mode, temperature_override, max_tokens_override)
        content_parts: List[str] = []
        reasoning_parts: List[str] = []
        prompt_tokens = 0
        completion_tokens = 0
        reasoning_tokens: Optional[int] = None
        echo_field = self.cfg.thinking_echo_field

        with self._client.chat.completions.create(
            **kwargs, stream=True, stream_options={"include_usage": True}
        ) as stream:
            for chunk in stream:
                # Final chunk carries usage totals; earlier chunks may have `choices=[]`.
                if getattr(chunk, "usage", None):
                    prompt_tokens = chunk.usage.prompt_tokens or 0
                    completion_tokens = chunk.usage.completion_tokens or 0
                    details = getattr(chunk.usage, "completion_tokens_details", None)
                    if details is not None:
                        reasoning_tokens = getattr(details, "reasoning_tokens", None)
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    content_parts.append(delta.content)
                if echo_field:
                    piece = _thinking_delta(delta, echo_field)
                    if piece:
                        reasoning_parts.append(piece)

        return Completion(
            text="".join(content_parts),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            reasoning="".join(reasoning_parts) if reasoning_parts else None,
            reasoning_tokens=reasoning_tokens,
        )

    def _chat_kwargs(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool,
        temperature_override: Optional[float],
        max_tokens_override: Optional[int],
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {"model": self.cfg.api_model, "messages": messages}
        max_tok = max_tokens_override if max_tokens_override is not None else (self.cfg.max_tokens or 4096)

        if self.cfg.reasoning:
            # OpenAI reasoning models (o1/o3/gpt-5) reject `temperature` and
            # require `max_completion_tokens`. `reasoning_effort` is a
            # top-level param in the SDK.
            kwargs["max_completion_tokens"] = max_tok
            if self.cfg.reasoning_effort:
                kwargs["reasoning_effort"] = self.cfg.reasoning_effort
            if temperature_override is not None:
                # A caller pinning temperature (the judge protocol pins 0.1)
                # cannot have it honored here — reasoning chat-completions
                # reject the param. Say so loudly rather than silently running
                # the judge at provider-default sampling.
                logger.warning(
                    f"{self.cfg.name}: temperature={temperature_override} requested but "
                    "dropped — reasoning-mode chat completions reject `temperature`. "
                    "If this model is used as a judge, document it as unpinned."
                )
        else:
            kwargs["max_tokens"] = max_tok
            kwargs["temperature"] = (
                temperature_override if temperature_override is not None else self.cfg.temperature
            )

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if self.cfg.extra_body:
            kwargs["extra_body"] = self.cfg.extra_body
        return kwargs

    # ------------------------------------------------------------------
    # Responses API (non-streaming; used for GPT-5.5-style reasoning summaries)
    # ------------------------------------------------------------------

    def _call_responses(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool,
        temperature_override: Optional[float],
        max_tokens_override: Optional[int],
    ) -> Completion:
        kwargs = self._responses_kwargs(messages, json_mode, temperature_override, max_tokens_override)
        resp = self._client.responses.create(**kwargs)
        usage = getattr(resp, "usage", None)
        return Completion(
            text=resp.output_text or "",
            prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
            completion_tokens=getattr(usage, "output_tokens", 0) or 0,
            reasoning=_responses_reasoning_text(resp),
            reasoning_tokens=getattr(getattr(usage, "output_tokens_details", None), "reasoning_tokens", None),
        )

    def _responses_kwargs(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool,
        temperature_override: Optional[float],
        max_tokens_override: Optional[int],
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "model": self.cfg.api_model,
            "input": messages,
            "max_output_tokens": max_tokens_override if max_tokens_override is not None else (self.cfg.max_tokens or 4096),
        }
        reasoning: Dict[str, Any] = {}
        if self.cfg.reasoning_effort:
            reasoning["effort"] = self.cfg.reasoning_effort
        if self.cfg.reasoning_summary:
            reasoning["summary"] = self.cfg.reasoning_summary
        if reasoning:
            kwargs["reasoning"] = reasoning
        if temperature_override is not None:
            kwargs["temperature"] = temperature_override
        if json_mode:
            # Responses API expresses JSON mode via `text.format`, not the
            # `response_format` kwarg used by chat.completions.
            kwargs["text"] = {"format": {"type": "json_object"}}
        if self.cfg.extra_body:
            kwargs["extra_body"] = self.cfg.extra_body
        return kwargs


def _responses_reasoning_text(resp) -> Optional[str]:
    """Concatenate the reasoning-summary text emitted by a Responses API call.

    The response's top-level `reasoning` attribute only echoes the request
    config (effort, summary mode). The actual generated summary lives in
    `resp.output` as items with `type == "reasoning"`, each carrying a
    `summary: list[SummaryText]` where each entry has `.text`. Returns None
    when the model did not emit any summary text (e.g., proxies that gate
    on `generate_summary`, or short answers that don't trip summarisation).
    """
    parts: List[str] = []
    for item in getattr(resp, "output", None) or []:
        if getattr(item, "type", None) != "reasoning":
            continue
        for s in getattr(item, "summary", None) or []:
            text = getattr(s, "text", None)
            if isinstance(text, str) and text:
                parts.append(text)
    return "\n".join(parts) if parts else None


def _thinking_delta(delta, name: str) -> Optional[str]:
    """Fetch a provider-extension delta field (e.g. `reasoning_content` from
    Moonshot / DeepSeek). OpenAI SDK v2 exposes such fields via `model_extra`
    on the underlying pydantic model — the canonical place, so we read there
    only and ignore anything else to avoid picking up MagicMock-style
    attribute autospawn.
    """
    extra = getattr(delta, "model_extra", None)
    if not isinstance(extra, dict):
        return None
    value = extra.get(name)
    return value if isinstance(value, str) else None
