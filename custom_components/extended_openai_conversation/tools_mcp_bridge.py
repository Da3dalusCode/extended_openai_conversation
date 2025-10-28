"""Optional MCP bridge for exposing external tools."""

from __future__ import annotations

import importlib
import logging
from typing import Any, Iterable

from .const import (
    CONF_ENABLE_MCP,
    CONF_MCP_MAX_PAYLOAD,
    CONF_MCP_TIMEOUT,
    DEFAULT_ENABLE_MCP,
    DEFAULT_MCP_MAX_PAYLOAD,
    DEFAULT_MCP_TIMEOUT,
)

LOGGER = logging.getLogger(__name__)


class MCPBridge:
    """Lazy MCP client facade."""

    def __init__(self, options: dict[str, Any]) -> None:
        self._enabled = options.get(CONF_ENABLE_MCP, DEFAULT_ENABLE_MCP)
        self._timeout = options.get(CONF_MCP_TIMEOUT, DEFAULT_MCP_TIMEOUT)
        self._payload_cap = options.get(CONF_MCP_MAX_PAYLOAD, DEFAULT_MCP_MAX_PAYLOAD)
        self._client_module = None
        self._load_error: str | None = None

        if not self._enabled:
            return

        try:
            self._client_module = importlib.import_module("mcp")
        except Exception as err:  # pragma: no cover - optional dependency
            self._load_error = str(err)
            LOGGER.debug("MCP bridge disabled: %s", err)
            self._enabled = False

    @property
    def available(self) -> bool:
        return self._enabled and self._client_module is not None

    @property
    def payload_cap(self) -> int:
        return self._payload_cap

    @property
    def timeout(self) -> float:
        return self._timeout

    def describe_tools(self) -> list[dict[str, Any]]:
        """Return MCP tool specs ready for registration."""

        if not self.available:
            return []

        # Full MCP discovery is not yet implemented. This placeholder keeps
        # the integration safe until the optional dependency is configured.
        LOGGER.info(
            "MCP support is enabled but automatic MCP tool discovery is not "
            "implemented in this build. No MCP tools will be exposed."
        )
        return []

    async def async_call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an MCP tool call. Currently returns informative error."""

        if not self.available:
            return {
                "error": "mcp_unavailable",
                "message": self._load_error
                or "MCP client library not installed. Install the 'mcp' package to enable MCP tools.",
            }

        return {
            "error": "mcp_not_implemented",
            "message": (
                "MCP support is enabled but runtime execution is not yet implemented."
            ),
        }


def create_bridge(options: dict[str, Any]) -> MCPBridge:
    """Factory used by the orchestrator."""

    return MCPBridge(options)
