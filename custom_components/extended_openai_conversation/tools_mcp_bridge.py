"""Minimal Model Context Protocol (MCP) bridge."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Awaitable, Callable, List

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class McpBridgeConfig:
    timeout: int
    max_payload: int


@dataclass
class McpTool:
    name: str
    spec: dict[str, Any]
    definition: dict[str, Any]
    _executor: Callable[[dict[str, Any]], Awaitable[Any]]

    async def async_execute(self, arguments: dict[str, Any]) -> Any:
        return await self._executor(arguments)


def load_mcp_tools(hass: HomeAssistant, config: McpBridgeConfig) -> List[McpTool]:
    """Discover MCP tools exposed by the Home Assistant MCP integration.

    The current Home Assistant builds do not yet expose a formal API for listing MCP
    servers. This helper keeps the plumbing ready while gracefully degrading when MCP
    is unavailable.
    """

    servers = hass.data.get("mcp_servers")
    if isinstance(servers, dict):
        server_iter = servers.items()
    elif isinstance(servers, list):
        server_iter = ((str(index), item) for index, item in enumerate(servers))
    else:
        server_iter = []

    discovered: list[McpTool] = []
    saw_server = False

    for server_id, server in server_iter:
        saw_server = True
        if not server:
            continue
        tools = getattr(server, "tools", None)
        if tools is None and isinstance(server, dict):
            tools = server.get("tools")
        if not tools:
            continue
        _LOGGER.debug("MCP bridge: no servers discovered")
        for tool in tools:
            name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", None)
            spec = tool.get("spec") if isinstance(tool, dict) else getattr(tool, "spec", None)
            if not name or not spec:
                continue

            definition = {
                "type": "mcp",
                "mcp": {
                    "server_label": server_id,
                    "type": "mcp",
                    "allowed_tools": [name],
                },
            }

            async def _call_tool(arguments: dict[str, Any], *, server_ref=server, tool_name=name) -> Any:
                call = getattr(server_ref, "async_call_tool", None)
                if call is None and isinstance(server_ref, dict):
                    call = server_ref.get("async_call_tool")
                if call is None:
                    raise RuntimeError("Server does not support async_call_tool")
                if callable(call):
                    return await call(tool_name, arguments)
                raise RuntimeError("async_call_tool is not callable")

            discovered.append(
                McpTool(
                    name=name,
                    spec=spec,
                    definition=definition,
                    _executor=_call_tool,
                )
            )

    if not saw_server:
        _LOGGER.debug("MCP bridge: no servers discovered")
    elif not discovered:
        _LOGGER.debug("MCP bridge: servers found but no compatible tools exposed")

    return discovered
