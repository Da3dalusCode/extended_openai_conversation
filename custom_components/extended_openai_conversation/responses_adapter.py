"""Helpers to normalise Responses API payloads."""

from __future__ import annotations

import json
from typing import Any

CHAT_COMPLETION_OBJECT = "chat.completion"


def _coerce_dict(value: Any) -> dict:
    """Convert OpenAI response models or plain objects into dictionaries."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "to_dict"):
        return value.to_dict()  # type: ignore[no-any-return]
    if hasattr(value, "dict"):
        return value.dict()  # type: ignore[no-any-return]
    # Fallback: try to build from __dict__
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {}


def _tool_arguments_to_json(arguments: Any) -> str:
    if isinstance(arguments, str):
        return arguments
    if arguments in (None, ""):
        return "{}"
    try:
        return json.dumps(arguments)
    except TypeError:
        return json.dumps({"value": str(arguments)})


def _normalise_tool_call(raw_call: dict, index: int) -> dict | None:
    name = (
        raw_call.get("name")
        or raw_call.get("function", {}).get("name")
        or raw_call.get("tool_call", {}).get("name")
    )
    if not name:
        return None
    arguments = (
        raw_call.get("input")
        or raw_call.get("arguments")
        or raw_call.get("function", {}).get("arguments")
        or raw_call.get("tool_call", {}).get("arguments")
    )
    call_id = (
        raw_call.get("id")
        or raw_call.get("tool_call_id")
        or raw_call.get("call_id")
        or f"call_{index}"
    )
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": _tool_arguments_to_json(arguments),
        },
    }


def responses_to_chat_like(response: Any) -> dict:
    """Normalise a Responses API payload to a chat.completions-like dict."""

    response_dict = _coerce_dict(response)

    # Gather text parts and tool calls
    text_parts: list[str] = []
    tool_calls: list[dict] = []
    role = "assistant"

    output_items = response_dict.get("output") or []

    for idx, item in enumerate(output_items):
        item_dict = _coerce_dict(item)
        item_type = item_dict.get("type")
        if item_type == "message":
            role = item_dict.get("role", role)
            for content in item_dict.get("content") or []:
                content_dict = _coerce_dict(content)
                content_type = content_dict.get("type")
                if content_type in {"text", "output_text"}:
                    text_value = (
                        content_dict.get("text")
                        or content_dict.get("value")
                        or content_dict.get("content")
                        or ""
                    )
                    if text_value:
                        text_parts.append(str(text_value))
                elif content_type in {"tool_use", "tool_call"}:
                    normalised = _normalise_tool_call(content_dict, len(tool_calls))
                    if normalised:
                        tool_calls.append(normalised)
        elif item_type in {"tool_use", "tool_call"}:
            normalised = _normalise_tool_call(item_dict, len(tool_calls))
            if normalised:
                tool_calls.append(normalised)

    if not text_parts:
        output_text = response_dict.get("output_text")
        if isinstance(output_text, str) and output_text:
            text_parts.append(output_text)
        elif hasattr(response, "output_text"):
            output_text_attr = getattr(response, "output_text")
            if isinstance(output_text_attr, str) and output_text_attr:
                text_parts.append(output_text_attr)

    message_content = "\n".join(text_parts) if text_parts else None

    usage_raw = _coerce_dict(response_dict.get("usage"))
    prompt_tokens = (
        usage_raw.get("prompt_tokens")
        if usage_raw
        else None
    )
    if prompt_tokens is None:
        prompt_tokens = usage_raw.get("input_tokens") if usage_raw else None
    completion_tokens = (
        usage_raw.get("completion_tokens")
        if usage_raw
        else None
    )
    if completion_tokens is None:
        completion_tokens = usage_raw.get("output_tokens") if usage_raw else None
    total_tokens = usage_raw.get("total_tokens") if usage_raw else None
    if total_tokens is None:
        candidate_sum = 0
        have_value = False
        if isinstance(prompt_tokens, int):
            candidate_sum += prompt_tokens
            have_value = True
        if isinstance(completion_tokens, int):
            candidate_sum += completion_tokens
            have_value = True
        if have_value:
            total_tokens = candidate_sum
    usage: dict[str, int] | None = None
    if any(
        token is not None
        for token in (prompt_tokens, completion_tokens, total_tokens)
    ):
        usage = {
            "prompt_tokens": int(prompt_tokens or 0),
            "completion_tokens": int(completion_tokens or 0),
            "total_tokens": int(total_tokens or 0),
        }

    finish_reason = "tool_calls" if tool_calls else "stop"

    message: dict[str, Any] = {"role": role}
    if message_content is not None:
        message["content"] = message_content
    else:
        message["content"] = None
    if tool_calls:
        message["tool_calls"] = tool_calls

    chat_like = {
        "id": response_dict.get("id"),
        "object": CHAT_COMPLETION_OBJECT,
        "created": response_dict.get("created"),
        "model": response_dict.get("model"),
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": message,
            }
        ],
    }

    system_fingerprint = response_dict.get("system_fingerprint")
    if system_fingerprint:
        chat_like["system_fingerprint"] = system_fingerprint

    if usage is not None:
        chat_like["usage"] = usage

    return chat_like
