"""Helpers to configure OpenAI hosted web search tool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant


@dataclass
class WebSearchConfig:
    enabled: bool
    context_size: int
    include_home_location: bool


def _context_size_label(value: int) -> str:
    if value <= 4:
        return "low"
    if value <= 12:
        return "medium"
    return "high"


def _home_location_payload(hass: HomeAssistant) -> dict[str, Any] | None:
    name = (hass.config.location_name or "").strip()
    country = getattr(hass.config, "country", None)
    region = None
    timezone = hass.config.time_zone

    if not any([name, country, timezone]):
        return None

    payload: dict[str, Any] = {"type": "approximate"}
    if name:
        payload["city"] = name
    if region:
        payload["region"] = region
    if country:
        payload["country"] = country
    if timezone:
        payload["timezone"] = timezone
    return payload


def build_web_search_tool(
    hass: HomeAssistant, config: WebSearchConfig
) -> dict[str, Any]:
    """Return the tool definition for hosted web search."""

    tool: dict[str, Any] = {"type": "web_search"}
    payload: dict[str, Any] = {
        "search_context_size": _context_size_label(config.context_size)
    }

    if config.include_home_location:
        location = _home_location_payload(hass)
        if location:
            payload["user_location"] = location

    if payload:
        tool["web_search"] = payload

    return tool
