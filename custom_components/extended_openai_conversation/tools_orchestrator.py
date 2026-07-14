"""Orchestrates tool execution for both Chat Completions and Responses API."""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import time
from typing import Any

from homeassistant.components.conversation.chat_log import ChatLog, ToolResultContent
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_FUNCTIONS,
    CONF_MAX_TOOL_CALLS,
    CONF_MAX_TOOL_CHAIN,
    CONF_TOOL_TIMEOUT,
    CONF_TOOL_MAX_OUTPUT_CHARS,
    CONF_MEMORY_ENABLED,
    DEFAULT_FUNCTIONS,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_MAX_TOOL_CHAIN,
    DEFAULT_TOOL_TIMEOUT,
    DEFAULT_TOOL_MAX_OUTPUT_CHARS,
    DEFAULT_MEMORY_ENABLED,
)
from .exceptions import InvalidFunction, FunctionNotFound, NativeNotFound
from .memory_tools import (
    MEMORY_TOOL_SPECS,
    dispatch_memory_tool,
    get_memory_service_config,
)
from .tools_builtin import FUNCTION_EXECUTORS, get_function_executor
from .tools_mcp_bridge import MCPBridge, create_bridge
from .tools_web_search import (
    build_responses_web_search_tool,
    configure_chat_completion_web_search,
)

LOGGER = logging.getLogger(__name__)

class ToolExecutionError(Exception):
    """Raised when a tool fails to execute cleanly."""


class ToolsOrchestrator:
    """Coordinate execution of built-in, memory, and optional MCP tools."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        options: dict[str, Any],
        chat_log: ChatLog | None,
        agent_id: str,
    ) -> None:
        self.hass = hass
        self.options = options
        self.chat_log = chat_log
        self.agent_id = agent_id

        self._max_calls: int = options.get(CONF_MAX_TOOL_CALLS, DEFAULT_MAX_TOOL_CALLS)
        self._max_chain_depth: int = options.get(
            CONF_MAX_TOOL_CHAIN, DEFAULT_MAX_TOOL_CHAIN
        )
        self._call_timeout: float = float(
            options.get(CONF_TOOL_TIMEOUT, DEFAULT_TOOL_TIMEOUT)
        )
        self._result_cap: int = int(
            options.get(CONF_TOOL_MAX_OUTPUT_CHARS, DEFAULT_TOOL_MAX_OUTPUT_CHARS)
        )

        self._call_count = 0
        self._chain_depth = 0
        self._started = time.monotonic()
        self._exposed_entities: list[dict[str, Any]] | None = None
        self._exposed_entities_expires: float | None = None

        self._tool_specs: list[dict[str, Any]] = []
        self._runtime_map: dict[str, dict[str, Any]] = {}

        self._web_search_tool_type: str | None = None
        self._web_search_fallback_type: str | None = None

        self._load_builtin_functions(options.get(CONF_FUNCTIONS, DEFAULT_FUNCTIONS))
        self._memory_enabled = options.get(CONF_MEMORY_ENABLED, DEFAULT_MEMORY_ENABLED)
        self._memory_config = (
            get_memory_service_config(options) if self._memory_enabled else None
        )
        if self._memory_enabled:
            self._register_memory_tools()

        self._mcp_bridge: MCPBridge = create_bridge(options)
        if self._mcp_bridge.available:
            self._register_mcp_tools()

    # ---------------------------------------------------------------------
    # Tool specification helpers
    # ---------------------------------------------------------------------
    def _load_builtin_functions(self, functions: list[dict[str, Any]] | None) -> None:
        entries: list[dict[str, Any]] = copy.deepcopy(DEFAULT_FUNCTIONS)
        if functions:
            entries.extend(functions)

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            spec = entry.get("spec")
            runtime = entry.get("function")
            if not isinstance(spec, dict) or not isinstance(runtime, dict):
                continue
            name = spec.get("name")
            if not name:
                continue
            self._tool_specs = [
                existing for existing in self._tool_specs if existing.get("name") != name
            ]
            self._tool_specs.append(dict(spec))
            self._runtime_map[name] = dict(runtime)

    def _register_memory_tools(self) -> None:
        for spec in MEMORY_TOOL_SPECS:
            name = spec.get("name")
            if not name:
                continue
            self._tool_specs.append(dict(spec))
            self._runtime_map[name] = {"type": "memory", "name": name}

    def _register_mcp_tools(self) -> None:
        for spec in self._mcp_bridge.describe_tools():
            name = spec.get("name")
            if not name:
                continue
            self._tool_specs.append(spec)
            self._runtime_map[name] = {"type": "mcp", "name": name}

    # ------------------------------------------------------------------
    # Tool definitions exposed to OpenAI APIs
    # ------------------------------------------------------------------
    def conversation_tools_for_chat(self) -> list[dict[str, Any]]:
        return [
            {"type": "function", "function": dict(spec)} for spec in self._tool_specs
        ]

    def conversation_tools_for_responses(
        self,
        hass: HomeAssistant,
        *,
        model: str | None,
        tool_type_override: str | None = None,
    ) -> list[dict[str, Any]]:
        tools = [
            {"type": "function", "function": dict(spec)}
            for spec in self._tool_specs
        ]
        self._web_search_tool_type = None
        self._web_search_fallback_type = None
        if tool_spec := build_responses_web_search_tool(
            hass,
            self.options,
            model=model,
            tool_type_override=tool_type_override,
        ):
            payload, fallback_type = tool_spec
            self._web_search_tool_type = payload.get("type")
            self._web_search_fallback_type = fallback_type
            tools.append(payload)
        return tools

    def configure_chat_web_search(self, model: str | None) -> None:
        configure_chat_completion_web_search(options=self.options, model=model)

    # ------------------------------------------------------------------
    # Execution helpers
    # ------------------------------------------------------------------
    def reset(self) -> None:
        self._call_count = 0
        self._chain_depth = 0
        self._started = time.monotonic()
        self._exposed_entities = None
        self._exposed_entities_expires = None
        self._web_search_tool_type = None
        self._web_search_fallback_type = None
        # Note: Options save/reconfigure triggers a reload of the entity which
        # constructs a new orchestrator. This reset (and the reload) ensure the
        # exposure cache reflects current UI settings immediately.

    @property
    def max_chain_depth(self) -> int:
        return self._max_chain_depth

    def _ensure_call_budget(self) -> None:
        if self._max_calls and self._call_count >= self._max_calls:
            raise ToolExecutionError("Maximum tool calls exceeded")

    def _ensure_time_budget(self) -> None:
        if self._call_timeout <= 0:
            return
        max_runtime = self._call_timeout * max(1, self._max_chain_depth)
        elapsed = time.monotonic() - self._started
        if elapsed > max_runtime:
            LOGGER.debug(
                "Tool chain time budget exceeded after %.2fs (limit %.2fs)",
                elapsed,
                max_runtime,
            )
            raise ToolExecutionError("Tool chain time budget exceeded")

    def _get_exposed_entities(self) -> list[dict[str, Any]]:
        now = time.monotonic()
        if (
            self._exposed_entities is not None
            and self._exposed_entities_expires is not None
            and now < self._exposed_entities_expires
        ):
            return self._exposed_entities

        exposed: list[dict[str, Any]] = []
        for state in self.hass.states.async_all():
            # Assist exposure uses the 'conversation' assistant id; see
            # homeassistant.components.homeassistant.exposed_entities.async_should_expose.
            if async_should_expose(self.hass, "conversation", state.entity_id):
                exposed.append(
                    {
                        "entity_id": state.entity_id,
                        "name": state.name,
                        "state": state.state,
                    }
                )
        self._exposed_entities = exposed
        # Expose settings may change from the UI at runtime; refresh every 5 minutes.
        self._exposed_entities_expires = now + 300
        return exposed

    def _stringify_result(self, result: Any) -> str:
        if isinstance(result, str):
            text = result
        else:
            try:
                text = json.dumps(result, default=str, ensure_ascii=False)
            except TypeError:
                text = str(result)

        text = text.strip()
        if self._result_cap and len(text) > self._result_cap:
            truncated = text[: self._result_cap - 16].rstrip()
            text = f"{truncated}... (truncated)"
        return text

    async def execute_tool_call(
        self,
        *,
        name: str,
        arguments: str | dict[str, Any] | None,
        user_input,
        call_id: str | None,
    ) -> str:
        self._ensure_call_budget()
        self._ensure_time_budget()
        self._call_count += 1
        runtime = self._runtime_map.get(name)
        if runtime is None:
            raise ToolExecutionError(f"Unknown tool '{name}'")

        try:
            payload = self._prepare_arguments(runtime, arguments)
        except (json.JSONDecodeError, InvalidFunction) as err:
            raise ToolExecutionError(f"Invalid arguments for {name}: {err}") from err

        LOGGER.debug(
            "Tool %s starting (call_id=%s, invocation=%s/%s)",
            name,
            call_id or "<none>",
            self._call_count,
            self._max_calls if self._max_calls else "unbounded",
        )
        started = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                self._invoke(runtime, payload, user_input),
                timeout=self._call_timeout,
            )
        except asyncio.TimeoutError as err:
            elapsed_ms = (time.perf_counter() - started) * 1000
            message = f"Tool {name} timed out"
            self._record_tool_result(
                call_id=call_id or name or "tool",
                tool_name=name,
                text=message,
                elapsed_ms=elapsed_ms,
            )
            raise ToolExecutionError(message) from err
        except (HomeAssistantError, ToolExecutionError) as err:
            elapsed_ms = (time.perf_counter() - started) * 1000
            message = str(err) or f"Tool {name} failed"
            self._record_tool_result(
                call_id=call_id or name or "tool",
                tool_name=name,
                text=message,
                elapsed_ms=elapsed_ms,
            )
            raise ToolExecutionError(message) from err
        except Exception as err:  # pragma: no cover - defensive guard
            elapsed_ms = (time.perf_counter() - started) * 1000
            message = f"Tool {name} failed: {err}"
            self._record_tool_result(
                call_id=call_id or name or "tool",
                tool_name=name,
                text=message,
                elapsed_ms=elapsed_ms,
            )
            raise ToolExecutionError(message) from err

        elapsed_ms = (time.perf_counter() - started) * 1000
        text = self._stringify_result(result)
        LOGGER.debug("Tool %s completed in %.1f ms -> %s", name, elapsed_ms, text)
        self._record_tool_result(
            call_id=call_id or name or "tool",
            tool_name=name,
            text=text,
            elapsed_ms=elapsed_ms,
        )
        return text

    def _prepare_arguments(
        self, runtime: dict[str, Any], arguments: str | dict[str, Any] | None
    ) -> dict[str, Any]:
        if isinstance(arguments, str) and arguments.strip():
            data = json.loads(arguments)
        elif isinstance(arguments, dict):
            data = dict(arguments)
        else:
            data = {}

        runtime_type = runtime.get("type")
        if runtime_type in {"memory", "mcp"}:
            return data

        executor = get_function_executor(runtime_type)
        validated = executor.to_arguments({"type": runtime_type, **data})
        validated.pop("type", None)
        return validated

    async def _invoke(
        self, runtime: dict[str, Any], arguments: dict[str, Any], user_input
    ) -> Any:
        runtime_type = runtime.get("type")
        if runtime_type == "memory":
            if not self._memory_config:
                raise ToolExecutionError("Memory service not configured")
            name = runtime.get("name")
            return await dispatch_memory_tool(
                self.hass, self._memory_config, name, arguments
            )

        if runtime_type == "mcp":
            return await self._mcp_bridge.async_call_tool(
                runtime.get("name"), arguments
            )

        executor = FUNCTION_EXECUTORS.get(runtime_type)
        if executor is None:
            raise ToolExecutionError(f"Unsupported tool type {runtime_type}")

        try:
            return await executor.execute(
                self.hass,
                runtime,
                arguments,
                user_input,
                self._get_exposed_entities(),
            )
        except NativeNotFound as err:
            raise ToolExecutionError(str(err)) from err
        except FunctionNotFound as err:
            raise ToolExecutionError(str(err)) from err

    def _record_tool_result(
        self,
        *,
        call_id: str,
        tool_name: str,
        text: str,
        elapsed_ms: float,
    ) -> None:
        if not self.chat_log:
            return

        payload: dict[str, Any] = {
            "content": text,
            "elapsed_ms": round(elapsed_ms, 2),
        }
        try:
            self.chat_log.async_add_assistant_content_without_tools(
                ToolResultContent(
                    agent_id=self.agent_id,
                    tool_call_id=call_id,
                    tool_name=tool_name,
                    tool_result=payload,
                )
            )
        except Exception as err:  # pragma: no cover - defensive guard
            LOGGER.debug("Unable to append tool result to chat log: %s", err)

    @property
    def web_search_tool_type(self) -> str | None:
        return self._web_search_tool_type

    @property
    def web_search_fallback_type(self) -> str | None:
        return self._web_search_fallback_type

    def update_web_search_tool_type(self, new_type: str | None) -> None:
        if new_type:
            self._web_search_tool_type = new_type
            # Only allow a single fallback step to avoid loops.
            self._web_search_fallback_type = None
