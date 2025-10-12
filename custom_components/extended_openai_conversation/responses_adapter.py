"""Helpers to normalize Responses API payloads to chat-completions shape."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List


def _ensure_dict(payload: Any) -> Dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if hasattr(payload, "to_dict"):
        return payload.to_dict()  # type: ignore[no-any-return]
    if hasattr(payload, "__dict__"):
        return dict(payload.__dict__)
    raise TypeError("Unsupported response payload type for normalization")


def _collect_text(content_block: Dict[str, Any]) -> str:
    text = content_block.get("text")
    if text is None and "output_text" in content_block:
        text = content_block.get("output_text")
    if text is None and "content" in content_block:
        nested = content_block.get("content")
        if isinstance(nested, str):
            text = nested
    return text or ""


def _collect_tool_call(content_block: Dict[str, Any], index: int) -> Dict[str, Any] | None:
    tool_call = content_block.get("tool_call") or {}
    if not tool_call:
        return None
    if tool_call.get("type") != "function":
        return None
    function = tool_call.get("function") or {}
    if not function:
        return None
    arguments = function.get("arguments")
    if isinstance(arguments, (dict, list)):
        arguments = json.dumps(arguments)
    call_id = content_block.get("id") or tool_call.get("id") or f"call_{index}"
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": function.get("name"),
            "arguments": arguments or "{}",
        },
    }


def responses_to_chat_like(resp_obj: Any) -> Dict[str, Any]:
    """Convert a Responses API result to the chat completions format."""

    raw = _ensure_dict(resp_obj)
    envelope = raw.get("response") if isinstance(raw.get("response"), dict) else None
    if envelope is None:
        envelope = raw

    output_items: List[Dict[str, Any]] = envelope.get("output") or []

    text_parts: List[str] = []
    tool_calls: List[Dict[str, Any]] = []

    for item in output_items:
        if item.get("type") == "message":
            for content in item.get("content", []) or []:
                content_type = content.get("type")
                if content_type in {"output_text", "text"}:
                    text = _collect_text(content)
                    if text:
                        text_parts.append(text)
                elif content_type == "tool_call":
                    tool_call = _collect_tool_call(content, len(tool_calls))
                    if tool_call:
                        tool_calls.append(tool_call)
        elif item.get("type") == "tool_call":
            tool_call = _collect_tool_call(item, len(tool_calls))
            if tool_call:
                tool_calls.append(tool_call)

    if not text_parts:
        output_text = envelope.get("output_text") or raw.get("output_text")
        if output_text:
            text_parts.append(output_text)
        elif hasattr(resp_obj, "output_text"):
            text_value = getattr(resp_obj, "output_text")
            if text_value:
                text_parts.append(text_value)

    message_content = "".join(text_parts)
    message: Dict[str, Any] = {"role": "assistant", "content": message_content}
    if tool_calls:
        message["tool_calls"] = tool_calls

    finish_reason = "tool_calls" if tool_calls else "stop"

    usage_raw = envelope.get("usage") or raw.get("usage") or {}
    prompt_tokens = usage_raw.get("prompt_tokens", usage_raw.get("input_tokens"))
    completion_tokens = usage_raw.get(
        "completion_tokens", usage_raw.get("output_tokens")
    )
    total_tokens = usage_raw.get("total_tokens")
    if (
        total_tokens is None
        and prompt_tokens is not None
        and completion_tokens is not None
    ):
        total_tokens = prompt_tokens + completion_tokens

    usage: Dict[str, int] = {
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "total_tokens": int(total_tokens or 0),
    }

    created = envelope.get("created") or raw.get("created") or int(time.time())

    return {
        "id": raw.get("id"),
        "object": "chat.completion",
        "created": created,
        "model": raw.get("model"),
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": usage,
    }

