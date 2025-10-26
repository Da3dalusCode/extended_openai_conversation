"""Helpers for loading function-call tools defined via YAML."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Iterable, List

import yaml

from homeassistant.components import conversation
from homeassistant.core import HomeAssistant

from .exceptions import FunctionLoadFailed, FunctionNotFound, InvalidFunction
from .helpers import get_function_executor, convert_to_template

_LOGGER = logging.getLogger(__name__)


@dataclass
class FunctionTool:
    """Runtime representation of a function-call tool."""

    spec: dict[str, Any]
    name: str
    executor_type: str
    function_config: dict[str, Any]

    async def async_execute(
        self,
        hass: HomeAssistant,
        *,
        arguments: dict[str, Any],
        user_input: conversation.ConversationInput,
        exposed_entities: list[dict[str, Any]],
    ) -> Any:
        executor = get_function_executor(self.executor_type)
        return await executor.execute(
            hass,
            self.function_config,
            arguments,
            user_input,
            exposed_entities,
        )


def _ensure_sequence(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    raise FunctionLoadFailed("Functions YAML must be a list or dictionary")


def load_function_tools(
    hass: HomeAssistant,
    yaml_text: str | None,
) -> list[FunctionTool]:
    """Parse the functions YAML into executable FunctionTool objects."""

    if yaml_text is None:
        return []

    try:
        parsed = yaml.safe_load(yaml_text) if yaml_text.strip() else None
    except yaml.YAMLError as err:
        raise FunctionLoadFailed(f"Invalid YAML: {err}") from err

    if parsed is None:
        return []

    tools: list[FunctionTool] = []
    for index, item in enumerate(_ensure_sequence(parsed)):
        if not isinstance(item, dict):
            _LOGGER.warning("Skipping function entry %s: expected mapping, got %s", index, type(item))
            continue

        spec = item.get("spec")
        function_cfg = item.get("function")

        if not isinstance(spec, dict) or not isinstance(function_cfg, dict):
            _LOGGER.warning("Skipping function entry %s: missing spec/function keys", index)
            continue

        name = spec.get("name")
        if not name or not isinstance(name, str):
            _LOGGER.warning("Skipping function entry %s: spec.name missing or invalid", index)
            continue

        fn_type = function_cfg.get("type")
        if not fn_type or not isinstance(fn_type, str):
            _LOGGER.warning("Skipping function entry %s (%s): function.type missing", index, name)
            continue

        try:
            executor = get_function_executor(fn_type)
            parsed_config = executor.to_arguments(function_cfg)
        except (InvalidFunction, FunctionNotFound) as err:
            raise FunctionLoadFailed(f"Invalid function configuration for '{name}': {err}") from err

        # Ensure any template-like structures are bound to hass for execution.
        convert_to_template(
            parsed_config,
            template_keys=[
                "data",
                "event_data",
                "target",
                "service",
                "payload_template",
                "resource_template",
                "value_template",
            ],
            hass=hass,
        )

        tools.append(
            FunctionTool(
                spec=spec,
                name=name,
                executor_type=fn_type,
                function_config=parsed_config,
            )
        )

    return tools


DEFAULT_FUNCTIONS: list[dict[str, Any]] = [
    {
        "spec": {
            "name": "execute_service",
            "description": "Call Home Assistant services on exposed devices. Use only after explicit user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "list": {
                        "type": "array",
                        "description": "List of services to call sequentially.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "domain": {
                                    "type": "string",
                                    "description": "Domain of the service (e.g. light, switch).",
                                },
                                "service": {
                                    "type": "string",
                                    "description": "Service name within the domain (e.g. turn_on).",
                                },
                                "service_data": {
                                    "type": "object",
                                    "description": "Service data dictionary matching Home Assistant service schema.",
                                },
                            },
                            "required": ["domain", "service"],
                        },
                    }
                },
                "required": ["list"],
            },
        },
        "function": {"type": "native", "name": "execute_service"},
    },
    {
        "spec": {
            "name": "add_automation",
            "description": "Write a Home Assistant automation given YAML configuration text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "automation_config": {
                        "type": "string",
                        "description": "Full automation YAML body to append to automations.yaml.",
                    }
                },
                "required": ["automation_config"],
            },
        },
        "function": {"type": "native", "name": "add_automation"},
    },
    {
        "spec": {
            "name": "get_history",
            "description": "Fetch state history for exposed entities within a time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Entity IDs to query. Must be exposed to the assistant.",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "ISO8601 timestamp for the beginning of the window. Defaults to 24h ago if omitted.",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "ISO8601 timestamp for the end of the window. Defaults to start_time + 24h.",
                    },
                    "include_start_time_state": {
                        "type": "boolean",
                        "description": "Whether to include state at the exact start time.",
                        "default": True,
                    },
                    "significant_changes_only": {
                        "type": "boolean",
                        "description": "If true, return only significant state changes.",
                        "default": True,
                    },
                    "minimal_response": {
                        "type": "boolean",
                        "description": "If true, omit intermediate event data to reduce payload size.",
                        "default": True,
                    },
                    "no_attributes": {
                        "type": "boolean",
                        "description": "If true, exclude attribute payloads.",
                        "default": True,
                    },
                },
                "required": ["entity_ids"],
            },
        },
        "function": {"type": "native", "name": "get_history"},
    },
]


def build_default_functions_yaml() -> str:
    """Return the canonical YAML string for the default toolbox."""
    return yaml.safe_dump(DEFAULT_FUNCTIONS, sort_keys=False)
