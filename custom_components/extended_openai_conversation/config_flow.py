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
    CONF_FUNCTIONS,
    CONF_FUNCTIONS_RAW,
    CONF_MAX_TOOL_CALLS,
    CONF_MAX_TOOL_CHAIN,
    CONF_TOOL_TIMEOUT,
    CONF_TOOL_MAX_OUTPUT_CHARS,
    CONF_ENABLE_WEB_SEARCH,
    CONF_WEB_SEARCH_CONTEXT_SIZE,
    CONF_INCLUDE_HOME_LOCATION,
    CONF_ENABLE_MCP,
    CONF_MCP_TIMEOUT,
    CONF_MCP_MAX_PAYLOAD,
    DEFAULT_FUNCTIONS,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_MAX_TOOL_CHAIN,
    DEFAULT_TOOL_TIMEOUT,
    DEFAULT_TOOL_MAX_OUTPUT_CHARS,
    DEFAULT_ENABLE_WEB_SEARCH,
    DEFAULT_WEB_SEARCH_CONTEXT_SIZE,
    DEFAULT_INCLUDE_HOME_LOCATION,
    DEFAULT_ENABLE_MCP,
    DEFAULT_MCP_TIMEOUT,
    DEFAULT_MCP_MAX_PAYLOAD,
    WEB_SEARCH_CONTEXT_SIZE_PRESETS,
    DEFAULT_BASE_URL,
    DEFAULT_CHAT_MODEL,
    DEFAULT_MODEL_STRATEGY,
    DEFAULT_USE_RESPONSES_API,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPT,
)

def _dump_functions_yaml(functions: list[dict[str, Any]] | None) -> str:
    if not functions:
        return ""
    return yaml.safe_dump(functions, sort_keys=False)


def _parse_functions_yaml(raw: str) -> list[dict[str, Any]]:
    if not raw.strip():
        return []

    try:
        loaded = yaml.safe_load(raw) or []
    except yaml.YAMLError as err:
        raise vol.Invalid("invalid_yaml") from err

    if not isinstance(loaded, list):
        raise vol.Invalid("invalid_yaml")

    normalized: list[dict[str, Any]] = []
    for item in loaded:
        if not isinstance(item, dict):
            raise vol.Invalid("invalid_yaml")

        spec = item.get("spec")
        runtime = item.get("function")
        if not isinstance(spec, dict) or not isinstance(runtime, dict):
            raise vol.Invalid("invalid_yaml")
        if not spec.get("name") or not runtime.get("type"):
            raise vol.Invalid("invalid_yaml")
        normalized.append({"spec": spec, "function": runtime})

    return normalized


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
        errors: dict[str, str] = {}
        if user_input is not None:
            raw_functions = user_input.get(CONF_FUNCTIONS_RAW, "")
            try:
                parsed_functions = _parse_functions_yaml(raw_functions)
            except vol.Invalid:
                errors[CONF_FUNCTIONS_RAW] = "invalid_functions_yaml"
            else:
                user_input[CONF_FUNCTIONS] = parsed_functions
                user_input[CONF_FUNCTIONS_RAW] = raw_functions.strip()

            if not errors:
                return self.async_create_entry(data=user_input)

        # Build the form with suggested current values.
        opts = self.config_entry.options
        functions_default = opts.get(CONF_FUNCTIONS)
        functions_default_raw = opts.get(CONF_FUNCTIONS_RAW)
        if functions_default_raw is None:
            functions_default_raw = _dump_functions_yaml(functions_default or DEFAULT_FUNCTIONS)
        if user_input and CONF_FUNCTIONS_RAW in user_input:
            functions_default_raw = user_input.get(CONF_FUNCTIONS_RAW, functions_default_raw)

        max_tool_calls_default = opts.get(CONF_MAX_TOOL_CALLS, DEFAULT_MAX_TOOL_CALLS)
        max_tool_chain_default = opts.get(CONF_MAX_TOOL_CHAIN, DEFAULT_MAX_TOOL_CHAIN)
        tool_timeout_default = opts.get(CONF_TOOL_TIMEOUT, DEFAULT_TOOL_TIMEOUT)
        tool_max_output_default = opts.get(
            CONF_TOOL_MAX_OUTPUT_CHARS, DEFAULT_TOOL_MAX_OUTPUT_CHARS
        )
        enable_search_default = opts.get(
            CONF_ENABLE_WEB_SEARCH, DEFAULT_ENABLE_WEB_SEARCH
        )
        search_context_default = opts.get(
            CONF_WEB_SEARCH_CONTEXT_SIZE, DEFAULT_WEB_SEARCH_CONTEXT_SIZE
        )
        include_location_default = opts.get(
            CONF_INCLUDE_HOME_LOCATION, DEFAULT_INCLUDE_HOME_LOCATION
        )
        enable_mcp_default = opts.get(CONF_ENABLE_MCP, DEFAULT_ENABLE_MCP)
        mcp_timeout_default = opts.get(CONF_MCP_TIMEOUT, DEFAULT_MCP_TIMEOUT)
        mcp_payload_default = opts.get(CONF_MCP_MAX_PAYLOAD, DEFAULT_MCP_MAX_PAYLOAD)

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
                vol.Optional(CONF_FUNCTIONS_RAW, default=functions_default_raw): str,
                vol.Optional(
                    CONF_MAX_TOOL_CALLS, default=max_tool_calls_default
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=10)),
                vol.Optional(
                    CONF_MAX_TOOL_CHAIN, default=max_tool_chain_default
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=8)),
                vol.Optional(CONF_TOOL_TIMEOUT, default=tool_timeout_default): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=60)
                ),
                vol.Optional(
                    CONF_TOOL_MAX_OUTPUT_CHARS, default=tool_max_output_default
                ): vol.All(vol.Coerce(int), vol.Range(min=256, max=16384)),
                vol.Optional(CONF_ENABLE_WEB_SEARCH, default=enable_search_default): bool,
                vol.Optional(
                    CONF_WEB_SEARCH_CONTEXT_SIZE,
                    default=search_context_default,
                ): vol.Any(
                    vol.In(list(WEB_SEARCH_CONTEXT_SIZE_PRESETS.keys())),
                    vol.All(vol.Coerce(int), vol.Range(min=128, max=4096)),
                ),
                vol.Optional(CONF_INCLUDE_HOME_LOCATION, default=include_location_default): bool,
                vol.Optional(CONF_ENABLE_MCP, default=enable_mcp_default): bool,
                vol.Optional(CONF_MCP_TIMEOUT, default=mcp_timeout_default): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=60)
                ),
                vol.Optional(
                    CONF_MCP_MAX_PAYLOAD, default=mcp_payload_default
                ): vol.All(vol.Coerce(int), vol.Range(min=512, max=65536)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
