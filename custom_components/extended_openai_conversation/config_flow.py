"""Config and Options flows for Extended OpenAI Conversation."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
import yaml
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
    CONF_FUNCTIONS_YAML,
    CONF_ENABLE_WEB_SEARCH,
    CONF_SEARCH_CONTEXT_SIZE,
    CONF_INCLUDE_HOME_LOCATION,
    CONF_MAX_TOOL_CALLS,
    CONF_ENABLE_MCP,
    CONF_MCP_TIMEOUT,
    CONF_MCP_MAX_PAYLOAD,
    DEFAULT_BASE_URL,
    DEFAULT_CHAT_MODEL,
    DEFAULT_MODEL_STRATEGY,
    DEFAULT_USE_RESPONSES_API,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPT,
    DEFAULT_ENABLE_WEB_SEARCH,
    DEFAULT_SEARCH_CONTEXT_SIZE,
    DEFAULT_INCLUDE_HOME_LOCATION,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_ENABLE_MCP,
    DEFAULT_MCP_TIMEOUT,
    DEFAULT_MCP_MAX_PAYLOAD,
)
from .tools_builtin import build_default_functions_yaml

DEFAULT_FUNCTIONS_YAML = build_default_functions_yaml()


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

    def _validate_functions_yaml(self, functions_text: str | None) -> str | None:
        """Ensure the provided YAML parses into a list/dict structure."""
        if not functions_text:
            return ""
        try:
            data = yaml.safe_load(functions_text) if functions_text.strip() else None
        except yaml.YAMLError as err:
            raise vol.Invalid(f"Invalid YAML: {err}") from err

        if data is None:
            return ""
        if not isinstance(data, (list, dict)):
            raise vol.Invalid("Functions YAML must be a list or mapping.")
        return functions_text

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            try:
                user_input[CONF_FUNCTIONS_YAML] = self._validate_functions_yaml(
                    user_input.get(CONF_FUNCTIONS_YAML)
                )
            except vol.Invalid as err:
                errors = {"base": "invalid_functions_yaml"}
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._build_schema(self.config_entry.options, user_input),
                    errors=errors,
                )

            return self.async_create_entry(data=user_input)

        # Build the form with suggested current values.
        opts = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=self._build_schema(opts),
        )

    def _build_schema(
        self, opts: dict[str, Any], user_input: dict[str, Any] | None = None
    ) -> vol.Schema:
        """Build the options schema with defaults."""
        data = user_input or opts
        return vol.Schema(
            {
                vol.Optional(CONF_CHAT_MODEL, default=data.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)): str,
                vol.Optional(CONF_MODEL_STRATEGY, default=data.get(CONF_MODEL_STRATEGY, DEFAULT_MODEL_STRATEGY)): vol.In(
                    ["auto", "force_chat_completions", "force_responses_api"]
                ),
                vol.Optional(CONF_USE_RESPONSES_API, default=data.get(CONF_USE_RESPONSES_API, DEFAULT_USE_RESPONSES_API)): bool,
                vol.Optional(CONF_REASONING_EFFORT, default=data.get(CONF_REASONING_EFFORT, "medium")): vol.In(
                    ["minimal", "low", "medium", "high"]
                ),
                vol.Optional(CONF_TEMPERATURE, default=data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): vol.Coerce(float),
                vol.Optional(CONF_TOP_P, default=data.get(CONF_TOP_P, DEFAULT_TOP_P)): vol.Coerce(float),
                vol.Optional(CONF_MAX_TOKENS, default=data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): vol.Coerce(int),
                vol.Optional(CONF_ENABLE_WEB_SEARCH, default=data.get(CONF_ENABLE_WEB_SEARCH, DEFAULT_ENABLE_WEB_SEARCH)): bool,
                vol.Optional(CONF_SEARCH_CONTEXT_SIZE, default=data.get(CONF_SEARCH_CONTEXT_SIZE, DEFAULT_SEARCH_CONTEXT_SIZE)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=32)
                ),
                vol.Optional(CONF_INCLUDE_HOME_LOCATION, default=data.get(CONF_INCLUDE_HOME_LOCATION, DEFAULT_INCLUDE_HOME_LOCATION)): bool,
                vol.Optional(CONF_MAX_TOOL_CALLS, default=data.get(CONF_MAX_TOOL_CALLS, DEFAULT_MAX_TOOL_CALLS)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=16)
                ),
                vol.Optional(CONF_ENABLE_MCP, default=data.get(CONF_ENABLE_MCP, DEFAULT_ENABLE_MCP)): bool,
                vol.Optional(CONF_MCP_TIMEOUT, default=data.get(CONF_MCP_TIMEOUT, DEFAULT_MCP_TIMEOUT)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=120)
                ),
                vol.Optional(CONF_MCP_MAX_PAYLOAD, default=data.get(CONF_MCP_MAX_PAYLOAD, DEFAULT_MCP_MAX_PAYLOAD)): vol.All(
                    vol.Coerce(int), vol.Range(min=1024, max=65536)
                ),
                vol.Optional(CONF_FUNCTIONS_YAML, default=data.get(CONF_FUNCTIONS_YAML, DEFAULT_FUNCTIONS_YAML)): str,
                vol.Optional("prompt", default=data.get("prompt", DEFAULT_PROMPT)): str,
            }
        )
