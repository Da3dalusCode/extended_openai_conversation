"""Central tool orchestration for Responses API and Chat Completions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components import conversation
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENABLE_MCP,
    CONF_ENABLE_WEB_SEARCH,
    CONF_FUNCTIONS_YAML,
    CONF_INCLUDE_HOME_LOCATION,
    CONF_MAX_TOOL_CALLS,
    CONF_MCP_MAX_PAYLOAD,
    CONF_MCP_TIMEOUT,
    CONF_SEARCH_CONTEXT_SIZE,
    DEFAULT_ENABLE_MCP,
    DEFAULT_ENABLE_WEB_SEARCH,
    DEFAULT_INCLUDE_HOME_LOCATION,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_MCP_MAX_PAYLOAD,
    DEFAULT_MCP_TIMEOUT,
    DEFAULT_SEARCH_CONTEXT_SIZE,
)
from .memory_tools import (
    MEMORY_SEARCH_NAME,
    MEMORY_WRITE_NAME,
    MEMORY_TOOL_SPECS,
    MemoryServiceConfig,
    build_memory_tool_definitions,
    dispatch_memory_tool,
    get_memory_service_config,
    is_configured as memory_is_configured,
)
from .tools_builtin import FunctionTool, load_function_tools, build_default_functions_yaml
from .tools_web_search import WebSearchConfig, build_web_search_tool
from .tools_mcp_bridge import (
    McpBridgeConfig,
    load_mcp_tools,
    McpTool,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ToolExecutionContext:
    """Context passed to tool executors."""

    hass: HomeAssistant
    user_input: conversation.ConversationInput
    exposed_entities: list[dict[str, Any]]


class ToolError(Exception):
    """Raised when a tool execution fails."""


class ToolOrchestrator:
    """Registry and execution engine for Home Assistant tool calls."""

    def __init__(
        self,
        hass: HomeAssistant,
        options: dict[str, Any],
    ) -> None:
        self.hass = hass
        self.options = options

        self.max_tool_calls = int(
            options.get(CONF_MAX_TOOL_CALLS, DEFAULT_MAX_TOOL_CALLS)
        )
        self._function_tools = self._load_function_tools()
        self._memory_config = get_memory_service_config(options)
        self._memory_enabled = memory_is_configured(self._memory_config)
        self._web_search_config = self._build_web_search_config()
        self._mcp_tools = self._load_mcp_tools()

    def _load_function_tools(self) -> dict[str, FunctionTool]:
        text = self.options.get(CONF_FUNCTIONS_YAML)
        if text is None:
            text = build_default_functions_yaml()
        try:
            tools = load_function_tools(self.hass, text)
        except Exception as err:
            _LOGGER.error("Unable to load toolbox functions: %s", err)
            return {}
        return {tool.name: tool for tool in tools}

    def _build_web_search_config(self) -> WebSearchConfig | None:
        enabled = bool(
            self.options.get(CONF_ENABLE_WEB_SEARCH, DEFAULT_ENABLE_WEB_SEARCH)
        )
        if not enabled:
            return None

        context_size = int(
            self.options.get(CONF_SEARCH_CONTEXT_SIZE, DEFAULT_SEARCH_CONTEXT_SIZE)
        )
        include_home = bool(
            self.options.get(
                CONF_INCLUDE_HOME_LOCATION, DEFAULT_INCLUDE_HOME_LOCATION
            )
        )
        return WebSearchConfig(
            enabled=enabled,
            context_size=context_size,
            include_home_location=include_home,
        )

    def _load_mcp_tools(self) -> dict[str, McpTool]:
        if not bool(self.options.get(CONF_ENABLE_MCP, DEFAULT_ENABLE_MCP)):
            return {}
        config = McpBridgeConfig(
            timeout=int(self.options.get(CONF_MCP_TIMEOUT, DEFAULT_MCP_TIMEOUT)),
            max_payload=int(
                self.options.get(CONF_MCP_MAX_PAYLOAD, DEFAULT_MCP_MAX_PAYLOAD)
            ),
        )
        tools = load_mcp_tools(self.hass, config=config)
        return {tool.name: tool for tool in tools}

    @property
    def function_specs(self) -> list[dict[str, Any]]:
        """Function specs suitable for Chat Completions API."""
        specs: list[dict[str, Any]] = [tool.spec for tool in self._function_tools.values()]
        if self._memory_enabled:
            specs.extend(MEMORY_TOOL_SPECS)
        return specs

    @property
    def responses_tools(self) -> list[dict[str, Any]]:
        """Tool definitions for the Responses API."""
        tools: list[dict[str, Any]] = [
            {"type": "function", "function": tool.spec}
            for tool in self._function_tools.values()
        ]
        if self._memory_enabled:
            tools.extend(build_memory_tool_definitions())
        tools.extend(tool.definition for tool in self._mcp_tools.values())
        if self._web_search_config and self._web_search_config.enabled:
            tools.append(build_web_search_tool(self.hass, self._web_search_config))
        return tools

    def supports_web_search(self) -> bool:
        return bool(self._web_search_config and self._web_search_config.enabled)

    def max_calls(self) -> int:
        return max(1, self.max_tool_calls)

    async def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> str:
        """Execute a tool by name and return a stringified result."""

        if tool := self._function_tools.get(name):
            try:
                result = await tool.async_execute(
                    context.hass,
                    arguments=arguments,
                    user_input=context.user_input,
                    exposed_entities=context.exposed_entities,
                )
            except Exception as err:
                raise ToolError(str(err)) from err
            return _stringify_result(result)

        if self._memory_enabled and name in (MEMORY_SEARCH_NAME, MEMORY_WRITE_NAME):
            result = await dispatch_memory_tool(
                context.hass, self._memory_config, name, arguments
            )
            return _stringify_result(result)

        if mcp_tool := self._mcp_tools.get(name):
            try:
                result = await mcp_tool.async_execute(arguments)
            except Exception as err:
                raise ToolError(f"MCP tool '{name}' failed: {err}") from err
            return _stringify_result(result)

        raise ToolError(f"Unknown tool '{name}'")


def _stringify_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False)
    except Exception:
        return str(result)
