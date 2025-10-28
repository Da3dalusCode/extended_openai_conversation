"""Hosted web search helpers for Extended OpenAI Conversation."""

from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENABLE_WEB_SEARCH,
    CONF_WEB_SEARCH_CONTEXT_SIZE,
    CONF_INCLUDE_HOME_LOCATION,
    DEFAULT_ENABLE_WEB_SEARCH,
    DEFAULT_WEB_SEARCH_CONTEXT_SIZE,
)

LOGGER = logging.getLogger(__name__)

_CONTEXT_ALIASES = {
    "small": "low",
    "low": "low",
    "medium": "medium",
    "med": "medium",
    "mid": "medium",
    "large": "high",
    "high": "high",
}


def _normalize_context_size(value: Any) -> str:
    """Map user option to OpenAI context size token."""

    if isinstance(value, str):
        key = value.strip().lower()
        if key in _CONTEXT_ALIASES:
            return _CONTEXT_ALIASES[key]

    if isinstance(value, (int, float)):
        if value <= 384:
            return "low"
        if value <= 768:
            return "medium"
        return "high"

    return "medium"


def _build_user_location(hass: HomeAssistant) -> Dict[str, str] | None:
    """Return approximate location payload if HA config provides details."""

    location: Dict[str, str] = {"type": "approximate"}

    city = getattr(hass.config, "location_name", None)
    if city and city.lower() not in {"home", "house"}:
        location["city"] = city

    region = getattr(hass.config, "state", None)
    if region:
        location["region"] = region

    country = getattr(hass.config, "country", None)
    if country:
        location["country"] = country

    timezone = getattr(hass.config, "time_zone", None)
    if timezone:
        location["timezone"] = timezone

    if len(location) > 1:
        return location
    return None


def build_responses_web_search_tool(
    hass: HomeAssistant, options: dict[str, Any]
) -> dict[str, Any] | None:
    """Return Responses API tool payload for hosted web search if enabled."""

    if not options.get(CONF_ENABLE_WEB_SEARCH, DEFAULT_ENABLE_WEB_SEARCH):
        return None

    context_size = _normalize_context_size(
        options.get(CONF_WEB_SEARCH_CONTEXT_SIZE, DEFAULT_WEB_SEARCH_CONTEXT_SIZE)
    )
    tool: dict[str, Any] = {
        "type": "web_search",
        "search_context_size": context_size,
    }

    if options.get(CONF_INCLUDE_HOME_LOCATION):
        if location := _build_user_location(hass):
            tool["user_location"] = location

    return tool


def configure_chat_completion_web_search(
    *,
    options: dict[str, Any],
    model: str | None,
) -> None:
    """Chat Completions do not yet expose hosted web search; log and skip."""

    if not options.get(CONF_ENABLE_WEB_SEARCH, DEFAULT_ENABLE_WEB_SEARCH):
        return

    LOGGER.info(
        "Hosted web search is enabled but chat model '%s' does not expose the "
        "feature via Chat Completions; continuing without search.",
        model or "<unknown>",
    )
