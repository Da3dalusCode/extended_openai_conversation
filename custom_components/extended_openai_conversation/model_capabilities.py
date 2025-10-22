"""Detect model capabilities (reasoning vs non-reasoning) and token knobs."""

from __future__ import annotations

from dataclasses import dataclass


REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")
REASONING_MODELS_EXPLICIT = {
    # keep list for models without clear prefix patterns
    "gpt-4.1-reasoning",
}

@dataclass(frozen=True)
class ModelCapabilities:
    is_reasoning: bool
    accepts_temperature: bool
    chat_max_tokens_param: str  # "max_tokens" or "max_completion_tokens"
    responses_max_tokens_param: str  # almost always "max_output_tokens"


def detect_model_capabilities(model: str | None) -> ModelCapabilities:
    name = (model or "").lower()
    is_reasoning = any(name.startswith(p) for p in REASONING_PREFIXES) or name in REASONING_MODELS_EXPLICIT

    # Reasoning models generally reject temperature/top_p.
    accepts_temperature = not is_reasoning

    chat_max_param = "max_completion_tokens" if is_reasoning else "max_tokens"
    responses_max_param = "max_output_tokens"

    return ModelCapabilities(
        is_reasoning=is_reasoning,
        accepts_temperature=accepts_temperature,
        chat_max_tokens_param=chat_max_param,
        responses_max_tokens_param=responses_max_param,
    )
