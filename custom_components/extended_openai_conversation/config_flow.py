"""Config flow for Extended OpenAI Conversation."""

from __future__ import annotations

from typing import Any, Dict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.config_entries import OptionsFlowWithReload

from .const import (
    DOMAIN,
    CONFIG_ENTRY_VERSION,
    # base
    CONF_BASE_URL,
    CONF_API_VERSION,
    CONF_ORGANIZATION,
    CONF_CHAT_MODEL,
    # toggles
    CONF_USE_RESPONSES_API,
    CONF_MODEL_STRATEGY,
    MODEL_STRATEGY_AUTO,
    MODEL_STRATEGY_FORCE_CHAT,
    MODEL_STRATEGY_FORCE_RESPONSES,
    # sampling/limits
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_MAX_TOKENS,
    CONF_REASONING_EFFORT,
    # defaults
    DEFAULT_CHAT_MODEL,
    DEFAULT_USE_RESPONSES_API,
    DEFAULT_MODEL_STRATEGY,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_MAX_TOKENS,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_PROMPT,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Extended OpenAI Conversation."""

    VERSION = CONFIG_ENTRY_VERSION

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Collect the API key and initial model."""
        if user_input is not None:
            # Create the entry. Options are configured in OptionsFlow.
            title = user_input.get(CONF_NAME) or "Extended OpenAI Conversation"
            return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Optional(CONF_CHAT_MODEL, default=DEFAULT_CHAT_MODEL): str,
                vol.Optional(CONF_NAME, default="Extended OpenAI Conversation"): str,
                vol.Optional(CONF_BASE_URL, default=""): str,
                vol.Optional(CONF_ORGANIZATION, default=""): str,
                vol.Optional(CONF_API_VERSION, default=""): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_reconfigure(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Reconfigure the entry (e.g., rotate API key)."""
        entry = self._get_reconfigure_entry()

        if user_input is None:
            data = entry.data
            schema = vol.Schema(
                {
                    vol.Required(CONF_API_KEY, default=data.get(CONF_API_KEY, "")): str,
                    vol.Optional(CONF_CHAT_MODEL, default=data.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)): str,
                    vol.Optional(CONF_NAME, default=entry.title or "Extended OpenAI Conversation"): str,
                    vol.Optional(CONF_BASE_URL, default=data.get(CONF_BASE_URL, "")): str,
                    vol.Optional(CONF_ORGANIZATION, default=data.get(CONF_ORGANIZATION, "")): str,
                    vol.Optional(CONF_API_VERSION, default=data.get(CONF_API_VERSION, "")): str,
                }
            )
            return self.async_show_form(step_id="reconfigure", data_schema=schema)

        # Update and let the helper safely reload & finish the flow.
        new_data = {
            **entry.data,
            CONF_API_KEY: user_input.get(CONF_API_KEY, entry.data.get(CONF_API_KEY, "")),
            CONF_CHAT_MODEL: user_input.get(CONF_CHAT_MODEL, entry.data.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)),
            CONF_BASE_URL: user_input.get(CONF_BASE_URL, entry.data.get(CONF_BASE_URL, "")),
            CONF_ORGANIZATION: user_input.get(CONF_ORGANIZATION, entry.data.get(CONF_ORGANIZATION, "")),
            CONF_API_VERSION: user_input.get(CONF_API_VERSION, entry.data.get(CONF_API_VERSION, "")),
        }
        # One atomic operation: update → reload → abort the flow. (Prevents loop/deadlock.)
        return self.async_update_reload_and_abort(entry, data_updates=new_data)
        # Reconfigure guidance: https://developers.home-assistant.io/docs/config_entries_config_flow_handler  # noqa: E501


@staticmethod
@callback
def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> "OptionsFlowHandler":  # type: ignore[name-defined]
    """Return the options flow."""
    return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlowWithReload, config_entries.OptionsFlow):  # type: ignore[misc]
    """Handle options for Extended OpenAI Conversation.

    Uses OptionsFlowWithReload to automatically reload on save.
    """

    def __init__(self) -> None:
        super().__init__()

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        entry = self.config_entry  # Provided by HA (no manual assignment)
        opts = entry.options or {}

        if user_input is not None:
            # Just store the options; base class will handle the reload.
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(CONF_CHAT_MODEL, default=opts.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)): str,
                vol.Optional(CONF_MODEL_STRATEGY, default=opts.get(CONF_MODEL_STRATEGY, DEFAULT_MODEL_STRATEGY)): vol.In(
                    [MODEL_STRATEGY_AUTO, MODEL_STRATEGY_FORCE_CHAT, MODEL_STRATEGY_FORCE_RESPONSES]
                ),
                vol.Optional(CONF_USE_RESPONSES_API, default=opts.get(CONF_USE_RESPONSES_API, DEFAULT_USE_RESPONSES_API)): bool,
                vol.Optional(CONF_REASONING_EFFORT, default=opts.get(CONF_REASONING_EFFORT, DEFAULT_REASONING_EFFORT)): vol.In(
                    ["minimal", "low", "medium", "high"]
                ),
                vol.Optional(CONF_TEMPERATURE, default=opts.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): vol.Coerce(float),
                vol.Optional(CONF_TOP_P, default=opts.get(CONF_TOP_P, DEFAULT_TOP_P)): vol.Coerce(float),
                vol.Optional(CONF_MAX_TOKENS, default=opts.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): vol.Coerce(int),
                vol.Optional("prompt", default=opts.get("prompt", DEFAULT_PROMPT)): str,
            }
        )
        # Provide suggested values via helper (keeps input values on validation errors, etc.).
        schema = self.add_suggested_values_to_schema(schema, opts)
        return self.async_show_form(step_id="init", data_schema=schema)
