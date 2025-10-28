"""Helpers to extract text from OpenAI Responses API results."""

from __future__ import annotations

from typing import Any


def response_text_from_responses_result(result: Any) -> str:
    """
    Return best-effort text from a Responses API result (OpenAI 1.x).

    Priority:
      1) result.output_text if provided by the SDK
      2) Traverse result.output[*].content[*].text where type == "output_text"
      3) Fallback to first string in a model_dump()/to_dict() structure
    """
    # 1) Direct convenience property (many SDK builds expose this)
    text = getattr(result, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text

    # 2) Walk the object attributes if available
    output = getattr(result, "output", None)
    if output:
        try:
            for item in output:  # items with role, content
                content = getattr(item, "content", None) or item.get("content")  # type: ignore[union-attr]
                if not content:
                    continue
                for part in content:
                    ptype = getattr(part, "type", None) or part.get("type")  # type: ignore[union-attr]
                    if ptype == "output_text":
                        txt = getattr(part, "text", None) or part.get("text")  # type: ignore[union-attr]
                        if isinstance(txt, str) and txt.strip():
                            return txt
        except Exception:
            pass

    # 3) Fallback: try dict conversion
    to_dict = getattr(result, "to_dict", None) or getattr(result, "model_dump", None)
    if callable(to_dict):
        try:
            data = to_dict()
            # naive scan
            if isinstance(data, dict):
                out = data.get("output")
                if isinstance(out, list):
                    for item in out:
                        for part in (item.get("content") or []):
                            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                                return part["text"]
        except Exception:
            pass

    return ""


def extract_function_calls_from_response(result: Any) -> list[dict[str, Any]]:
    """Return function-call payloads from a Responses API result."""

    try:
        data = result.model_dump()
    except AttributeError:
        data = result

    if not isinstance(data, dict):
        return []

    calls: list[dict[str, Any]] = []

    def _maybe_add(item: Any) -> None:
        if not item:
            return
        if hasattr(item, "model_dump"):
            item = item.model_dump()
        if not isinstance(item, dict):
            return
        if item.get("type") == "function_call":
            calls.append(item)

    for entry in data.get("output", []):
        _maybe_add(entry)
        if not isinstance(entry, dict) and not hasattr(entry, "model_dump"):
            continue
        if hasattr(entry, "model_dump"):
            entry = entry.model_dump()
        if not isinstance(entry, dict):
            continue
        for part in entry.get("content", []):
            _maybe_add(part)

    return calls
