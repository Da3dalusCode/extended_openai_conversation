# custom_components/extended_openai_conversation/config_flow.py
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONFIG_ENTRY_VERSION,
    CONFIG_ENTRY_MINOR_VERSION,
    # data
    CONF_API_KEY, CONF_BASE_URL, CONF_API_VERSION, CONF_ORGANIZATION, CONF_CHAT_MODEL,
    DEFAULT_BASE_URL, DEFAULT_CHAT_MODEL, DEFAULT_API_VERSION,
    # options
    DEFAULTS,
    CONF_MODEL_STRATEGY, MODEL_STRATEGY_AUTO, MODEL_STRATEGY_FORCE_CHAT, MODEL_STRATEGY_FORCE_RESPONSES,
    CONF_USE_RESPONSES_API,
    CONF_REASONING_EFFORT, REASONING_EFFORT_ALLOWED,
    CONF_ENABLE_STREAMING, CONF_TEMPERATURE, CONF_TOP_P,
    CONF_MAX_TOKENS, CONF_MAX_COMPLETION_TOKENS,
    CONF_CONTEXT_THRESHOLD, CONF_CONTEXT_TRUNCATE_STRATEGY, TRUNCATE_KEEP_LATEST, TRUNCATE_CLEAR_ALL,
    CONF_ATTACH_USERNAME, CONF_SPEAK_CONFIRMATION_FIRST, CONF_STREAM_MIN_CHARS, CONF_PROMPT,
    CONF_ROUTER_FORCE_TOOLS, CONF_ROUTER_SEARCH_REGEX, CONF_ROUTER_WRITE_REGEX,
    CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION,
    CONF_BUDGET_PROFILE, CONF_BUDGET_RETRIEVED, CONF_BUDGET_SCRATCHPAD,
    CONF_MEMORY_BASE_URL, CONF_MEMORY_WRITE_PATH, CONF_MEMORY_SEARCH_PATH, CONF_MEMORY_ASK_PATH,
)

UNIQUE_ID = f"{DOMAIN}_singleton"


def _schema_with_defaults(entry_options: dict[str, Any]) -> vol.Schema:
    """Build Options schema w/ defaults merged from const.DEFAULTS and existing options."""
    o = {**DEFAULTS, **(entry_options or {})}

    return vol.Schema(
        {
            vol.Required(CONF_MODEL_STRATEGY, default=o[CONF_MODEL_STRATEGY]): vol.In(
                [MODEL_STRATEGY_AUTO, MODEL_STRATEGY_FORCE_CHAT, MODEL_STRATEGY_FORCE_RESPONSES]
            ),
            vol.Required(CONF_USE_RESPONSES_API, default=o[CONF_USE_RESPONSES_API]): bool,
            vol.Required(CONF_REASONING_EFFORT, default=o[CONF_REASONING_EFFORT]): vol.In(sorted(REASONING_EFFORT_ALLOWED)),
            vol.Required(CONF_ENABLE_STREAMING, default=o[CONF_ENABLE_STREAMING]): bool,
            vol.Required(CONF_TEMPERATURE, default=o[CONF_TEMPERATURE]): vol.Coerce(float),
            vol.Required(CONF_TOP_P, default=o[CONF_TOP_P]): vol.Coerce(float),
            vol.Required(CONF_MAX_TOKENS, default=o[CONF_MAX_TOKENS]): vol.Coerce(int),
            vol.Required(CONF_MAX_COMPLETION_TOKENS, default=o[CONF_MAX_COMPLETION_TOKENS]): vol.Coerce(int),
            vol.Required(CONF_CONTEXT_THRESHOLD, default=o[CONF_CONTEXT_THRESHOLD]): vol.Coerce(int),
            vol.Required(CONF_CONTEXT_TRUNCATE_STRATEGY, default=o[CONF_CONTEXT_TRUNCATE_STRATEGY]): vol.In(
                [TRUNCATE_KEEP_LATEST, TRUNCATE_CLEAR_ALL]
            ),
            vol.Required(CONF_ATTACH_USERNAME, default=o[CONF_ATTACH_USERNAME]): bool,
            vol.Required(CONF_SPEAK_CONFIRMATION_FIRST, default=o[CONF_SPEAK_CONFIRMATION_FIRST]): bool,
            vol.Required(CONF_STREAM_MIN_CHARS, default=o[CONF_STREAM_MIN_CHARS]): vol.Coerce(int),
            vol.Optional(CONF_PROMPT, default=o[CONF_PROMPT]): str,
            vol.Required(CONF_ROUTER_FORCE_TOOLS, default=o[CONF_ROUTER_FORCE_TOOLS]): bool,
            vol.Required(CONF_ROUTER_SEARCH_REGEX, default=o[CONF_ROUTER_SEARCH_REGEX]): str,
            vol.Required(CONF_ROUTER_WRITE_REGEX, default=o[CONF_ROUTER_WRITE_REGEX]): str,
            vol.Required(CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION, default=o[CONF_MAX_FUNCTION_CALLS_PER_CONVERSATION]): vol.Coerce(int),
            vol.Optional(CONF_BUDGET_PROFILE, default=o[CONF_BUDGET_PROFILE]): vol.Coerce(int),
            vol.Optional(CONF_BUDGET_RETRIEVED, default=o[CONF_BUDGET_RETRIEVED]): vol.Coerce(int),
            vol.Optional(CONF_BUDGET_SCRATCHPAD, default=o[CONF_BUDGET_SCRATCHPAD]): vol.Coerce(int),
            vol.Optional(CONF_MEMORY_BASE_URL, default=o[CONF_MEMORY_BASE_URL]): str,
            vol.Optional(CONF_MEMORY_WRITE_PATH, default=o[CONF_MEMORY_WRITE_PATH]): str,
            vol.Optional(CONF_MEMORY_SEARCH_PATH, default=o[CONF_MEMORY_SEARCH_PATH]): str,
            vol.Optional(CONF_MEMORY_ASK_PATH, default=o[CONF_MEMORY_ASK_PATH]): str,
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Extended OpenAI Conversation."""
    VERSION = CONFIG_ENTRY_VERSION
    MINOR_VERSION = CONFIG_ENTRY_MINOR_VERSION

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is None:
            # Single instance to avoid multiple agents fighting
            await self.async_set_unique_id(UNIQUE_ID, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_API_KEY): str,
                        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                        vol.Optional(CONF_CHAT_MODEL, default=DEFAULT_CHAT_MODEL): str,
                        vol.Optional(CONF_API_VERSION, default=DEFAULT_API_VERSION): str,
                        vol.Optional(CONF_ORGANIZATION, default=""): str,
                    }
                ),
                errors=errors,
            )

        # Create the entry, API key lives in config entry DATA (not options)
        await self.async_set_unique_id(UNIQUE_ID, raise_on_progress=False)
        self._abort_if_unique_id_configured()

        title = "Extended OpenAI Conversation"
        data = {
            CONF_API_KEY: user_input[CONF_API_KEY].strip(),
            CONF_BASE_URL: user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL).strip(),
            CONF_CHAT_MODEL: user_input.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL).strip(),
            CONF_API_VERSION: user_input.get(CONF_API_VERSION, DEFAULT_API_VERSION).strip(),
            CONF_ORGANIZATION: user_input.get(CONF_ORGANIZATION, "").strip(),
        }
        return self.async_create_entry(title=title, data=data, options={})

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Allow changing the API details later (without creating a new entry)."""
        entry = self._get_reconfigure_entry()

        if user_input is None:
            current = entry.data
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_API_KEY, default=current.get(CONF_API_KEY, "")): str,
                        vol.Optional(CONF_BASE_URL, default=current.get(CONF_BASE_URL, DEFAULT_BASE_URL)): str,
                        vol.Optional(CONF_CHAT_MODEL, default=current.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)): str,
                        vol.Optional(CONF_API_VERSION, default=current.get(CONF_API_VERSION, DEFAULT_API_VERSION)): str,
                        vol.Optional(CONF_ORGANIZATION, default=current.get(CONF_ORGANIZATION, "")): str,
                    }
                ),
            )

        new_data = {**entry.data, **user_input}
        return self.async_update_reload_and_abort(entry, data_updates=new_data)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options for Extended OpenAI Conversation."""

    def __init__(self, entry: config_entries.ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=_schema_with_defaults(self.entry.options))


# Backwards-compat alias (in case anything imports the old name)
ExtendedOpenAIConfigFlow = ConfigFlow
