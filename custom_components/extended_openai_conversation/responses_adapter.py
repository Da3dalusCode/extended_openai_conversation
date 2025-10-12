"""Helpers to normalize OpenAI Responses API payloads."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List


def responses_to_chat_like(resp_obj: Any) -> Dict[str, Any]:
    """Convert a Responses API payload to a Chat Completions-like object."""

    response_dict = _to_dict(resp_obj)

    output_items: List[Dict[str, Any]] = response_dict.get("output") or []
    assistant_text_segments: List[str] = []
    tool_calls: List[Dict[str, Any]] = []

    finish_reason = response_dict.get("stop_reason") or "stop"

    for item in output_items:
        finish_reason = _extract_finish_reason(item, finish_reason)
        contents = item.get("content") or []
        if item.get("type") in {"output_text", "text"}:
            text = item.get("text")
            if isinstance(text, str):
                assistant_text_segments.append(text)
            continue
        if item.get("type") == "output_json":
            json_payload = item.get("json")
            if isinstance(json_payload, str):
                assistant_text_segments.append(json_payload)
            elif json_payload is not None:
                assistant_text_segments.append(json.dumps(json_payload))
            continue

        if isinstance(contents, list):
            for content in contents:
                content_type = content.get("type") if isinstance(content, dict) else None
                if content_type in {"output_text", "text"}:
                    text = content.get("text") if isinstance(content, dict) else None
                    if isinstance(text, str):
                        assistant_text_segments.append(text)
                elif content_type == "output_json":
                    if isinstance(content, dict):
                        json_payload = content.get("json")
                        if isinstance(json_payload, str):
                            assistant_text_segments.append(json_payload)
                        elif json_payload is not None:
                            assistant_text_segments.append(json.dumps(json_payload))
                elif content_type == "tool_call":
                    tool_call = (
                        content.get("tool_call") if isinstance(content, dict) else None
                    )
                    formatted = _format_tool_call(tool_call, item)
                    if formatted:
                        tool_calls.append(formatted)

        if item.get("type") == "tool_call":
            formatted = _format_tool_call(item.get("tool_call"), item)
            if formatted:
                tool_calls.append(formatted)

    top_level_tool_calls = response_dict.get("tool_calls") or []
    for tool in top_level_tool_calls:
        formatted = _format_tool_call(tool, None)
        if formatted:
            tool_calls.append(formatted)

    if not assistant_text_segments:
        output_text = response_dict.get("output_text")
        if isinstance(output_text, str):
            assistant_text_segments.append(output_text)

    assistant_text = "".join(assistant_text_segments)

    if tool_calls and finish_reason == "stop":
        finish_reason = "tool_calls"

    usage = _normalise_usage(response_dict.get("usage"))

    message: Dict[str, Any] = {"role": "assistant", "content": assistant_text or None}
    if tool_calls:
        message["tool_calls"] = tool_calls

    choice: Dict[str, Any] = {
        "index": 0,
        "message": message,
        "finish_reason": finish_reason or "stop",
    }

    chat_payload: Dict[str, Any] = {
        "id": response_dict.get("id"),
        "object": "chat.completion",
        "created": response_dict.get("created"),
        "model": response_dict.get("model"),
        "choices": [choice],
    }

    if usage:
        chat_payload["usage"] = usage

    return chat_payload


def _to_dict(resp_obj: Any) -> Dict[str, Any]:
    if isinstance(resp_obj, dict):
        return resp_obj
    if hasattr(resp_obj, "model_dump"):
        return resp_obj.model_dump()
    if hasattr(resp_obj, "dict"):
        return resp_obj.dict()  # type: ignore[no-any-return]
    raise TypeError("Unsupported Responses payload type")


def _format_tool_call(tool_call: Any, item: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not isinstance(tool_call, dict):
        return None

    call_id = tool_call.get("id") or (item.get("id") if isinstance(item, dict) else None)
    if not call_id:
        call_id = f"call_{uuid.uuid4().hex}"

    function_payload: Dict[str, Any]
    if "function" in tool_call and isinstance(tool_call["function"], dict):
        function_payload = tool_call["function"]
    else:
        function_payload = {
            "name": tool_call.get("name"),
            "arguments": tool_call.get("arguments"),
        }

    arguments = function_payload.get("arguments")
    if isinstance(arguments, (dict, list)):
        function_payload["arguments"] = json.dumps(arguments)
    elif arguments is None:
        function_payload["arguments"] = "{}"
    else:
        function_payload["arguments"] = str(arguments)

    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": function_payload.get("name"),
            "arguments": function_payload.get("arguments") or "{}",
        },
    }


def _normalise_usage(usage: Any) -> Dict[str, Any] | None:
    if not isinstance(usage, dict):
        return None
    prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
    completion_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
    total_tokens = usage.get("total_tokens")

    normalised = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }

    return {k: v for k, v in normalised.items() if v is not None}


def _extract_finish_reason(item: Dict[str, Any], default: str) -> str:
    if not isinstance(item, dict):
        return default
    for key in ("finish_reason", "stop_reason", "status"):
        reason = item.get(key)
        if isinstance(reason, str):
            return reason
    return default
