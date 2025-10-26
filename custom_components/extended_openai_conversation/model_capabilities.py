"""Detect model capabilities for routing/sampling."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Capabilities:
    is_reasoning: bool
    accepts_temperature: bool


def detect_model_capabilities(model: str | None) -> Capabilities:
    name = (model or "").lower().strip()
    # Treat gpt-5 / o# / o#-mini series as "reasoning-class"
    reasoning_markers = ("gpt-5", "o1", "o2", "o3", "o4")
    is_reasoning = name.startswith(reasoning_markers)
    # Most reasoning-class endpoints ignore or forbid temperature/top_p.
    accepts_temperature = not is_reasoning
    return Capabilities(is_reasoning=is_reasoning, accepts_temperature=accepts_temperature)
