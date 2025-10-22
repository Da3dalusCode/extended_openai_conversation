"""Config flow for Extended OpenAI Conversation."""

from __future__ import annotations

from typing import Any, Dict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
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
    # reasoning
    CONF_REASONING_EFFORT,
    # misc
    CONF_SKIP_AUTH,
    DEFAULT_BASE_URL,
    DEFAULT_API_VERSION,
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
    """Handle a config flow."""
    VERSION = 3

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            title = user_input.get(CONF_NAME) or "Extended OpenAI Conversation"
            data = {
                CONF_NAME: title,
                CONF_API_KEY: user_input[CONF_API_KEY],
                CONF_BASE_URL: user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                CONF_API_VERSION: user_input.get(CONF_API_VERSION, DEFAULT_API_VERSION),
                CONF_ORGANIZATION: user_input.get(CONF_ORGANIZATION) or None,
                CONF_CHAT_MODEL: user_input.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL),
                CONF_SKIP_AUTH: bool(user_input.get(CONF_SKIP_AUTH, False)),
            }
            return self.async_create_entry(title=title, data=data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="Extended OpenAI Conversation"): str,
                vol.Required(CONF_API_KEY): str,
                vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                vol.Optional(CONF_API_VERSION, default=DEFAULT_API_VERSION): str,
                vol.Optional(CONF_ORGANIZATION): str,
                vol.Optional(CONF_CHAT_MODEL, default=DEFAULT_CHAT_MODEL): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Reconfigure base creds later (HA 2024.10+)."""
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            new_data = {
                **entry.data,
                CONF_NAME: user_input.get(CONF_NAME, entry.data.get(CONF_NAME)),
                CONF_API_KEY: user_input.get(CONF_API_KEY, entry.data.get(CONF_API_KEY)),
                CONF_BASE_URL: user_input.get(CONF_BASE_URL, entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)),
                CONF_API_VERSION: user_input.get(CONF_API_VERSION, entry.data.get(CONF_API_VERSION, DEFAULT_API_VERSION)),
                CONF_ORGANIZATION: user_input.get(CONF_ORGANIZATION, entry.data.get(CONF_ORGANIZATION)),
                CONF_CHAT_MODEL: user_input.get(CONF_CHAT_MODEL, entry.data.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)),
            }
            self.hass.config_entries.async_update_entry(entry, data=new_data)
            await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_create_entry(title=new_data.get(CONF_NAME) or entry.title, data={})

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=entry.data.get(CONF_NAME, entry.title)): str,
                vol.Required(CONF_API_KEY, default=entry.data.get(CONF_API_KEY)): str,
                vol.Optional(CONF_BASE_URL, default=entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)): str,
                vol.Optional(CONF_API_VERSION, default=entry.data.get(CONF_API_VERSION, DEFAULT_API_VERSION)): str,
                vol.Optional(CONF_ORGANIZATION, default=entry.data.get(CONF_ORGANIZATION, "")): str,
                vol.Optional(CONF_CHAT_MODEL, default=entry.data.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)): str,
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        data = self.config_entry.data

        schema = vol.Schema(
            {
                vol.Optional("chat_model", default=opts.get("chat_model", data.get("chat_model", DEFAULT_CHAT_MODEL))): str,
                vol.Optional("model_strategy", default=opts.get("model_strategy", DEFAULT_MODEL_STRATEGY)): vol.In(
                    [MODEL_STRATEGY_AUTO, MODEL_STRATEGY_FORCE_CHAT, MODEL_STRATEGY_FORCE_RESPONSES]
                ),
                vol.Optional("use_responses_api", default=opts.get("use_responses_api", DEFAULT_USE_RESPONSES_API)): bool,
                vol.Optional("reasoning_effort", default=opts.get("reasoning_effort", DEFAULT_REASONING_EFFORT)): vol.In(
                    ["minimal", "low", "medium", "high"]
                ),
                vol.Optional("temperature", default=opts.get("temperature", DEFAULT_TEMPERATURE)): vol.Coerce(float),
                vol.Optional("top_p", default=opts.get("top_p", DEFAULT_TOP_P)): vol.Coerce(float),
                vol.Optional("max_tokens", default=opts.get("max_tokens", DEFAULT_MAX_TOKENS)): vol.Coerce(int),
                vol.Optional("prompt", default=opts.get("prompt", DEFAULT_PROMPT)): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
