"""Config and Options flows for Extended OpenAI Conversation."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.const import CONF_API_KEY, CONF_NAME

from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_API_VERSION,
    CONF_ORGANIZATION,
    CONF_CHAT_MODEL,
    CONF_MODEL_STRATEGY,
    CONF_USE_RESPONSES_API,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_MAX_TOKENS,
    CONF_REASONING_EFFORT,
    DEFAULT_BASE_URL,
    DEFAULT_CHAT_MODEL,
    DEFAULT_MODEL_STRATEGY,
    DEFAULT_USE_RESPONSES_API,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPT,
)


class ExtendedOpenAIConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create the config entry."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            title = user_input.get(CONF_NAME) or "Extended OpenAI Conversation"
            data = {
                CONF_API_KEY: user_input[CONF_API_KEY],
                CONF_CHAT_MODEL: user_input.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL),
                CONF_BASE_URL: (user_input.get(CONF_BASE_URL) or "").strip() or None,
                CONF_ORGANIZATION: (user_input.get(CONF_ORGANIZATION) or "").strip()
                or None,
                CONF_API_VERSION: (user_input.get(CONF_API_VERSION) or "").strip()
                or None,
            }
            return self.async_create_entry(title=title, data=data)

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

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update credentials without touching options."""
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            new_data = dict(entry.data)
            for key in (CONF_API_KEY, CONF_CHAT_MODEL, CONF_BASE_URL, CONF_ORGANIZATION, CONF_API_VERSION):
                val = (user_input.get(key) or "").strip() if isinstance(user_input.get(key), str) else user_input.get(key)
                new_data[key] = val or (None if key in (CONF_BASE_URL, CONF_ORGANIZATION, CONF_API_VERSION) else new_data.get(key))
            return self.async_update_reload_and_abort(entry=entry, data=new_data)

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY, default=entry.data.get(CONF_API_KEY, "")): str,
                vol.Optional(CONF_CHAT_MODEL, default=entry.data.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)): str,
                vol.Optional(CONF_NAME, default=entry.title or "Extended OpenAI Conversation"): str,
                vol.Optional(CONF_BASE_URL, default=entry.data.get(CONF_BASE_URL) or ""): str,
                vol.Optional(CONF_ORGANIZATION, default=entry.data.get(CONF_ORGANIZATION) or ""): str,
                vol.Optional(CONF_API_VERSION, default=entry.data.get(CONF_API_VERSION) or ""): str,
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Register Options UI (this must live on the ConfigFlow class)."""
        return EOCOptionsFlow()


class EOCOptionsFlow(OptionsFlowWithReload):
    """Options flow that auto-reloads on save."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        # Build the form with suggested current values.
        opts = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Optional(CONF_CHAT_MODEL, default=opts.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)): str,
                vol.Optional(CONF_MODEL_STRATEGY, default=opts.get(CONF_MODEL_STRATEGY, DEFAULT_MODEL_STRATEGY)): vol.In(
                    ["auto", "force_chat_completions", "force_responses_api"]
                ),
                vol.Optional(CONF_USE_RESPONSES_API, default=opts.get(CONF_USE_RESPONSES_API, True)): bool,
                vol.Optional(CONF_REASONING_EFFORT, default=opts.get(CONF_REASONING_EFFORT, "medium")): vol.In(
                    ["minimal", "low", "medium", "high"]
                ),
                vol.Optional(CONF_TEMPERATURE, default=opts.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): vol.Coerce(float),
                vol.Optional(CONF_TOP_P, default=opts.get(CONF_TOP_P, DEFAULT_TOP_P)): vol.Coerce(float),
                vol.Optional(CONF_MAX_TOKENS, default=opts.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): vol.Coerce(int),
                vol.Optional("prompt", default=opts.get("prompt", DEFAULT_PROMPT)): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
