"""Small helpers to work with the OpenAI Responses API results."""

from __future__ import annotations

from typing import Any


def response_text_from_responses_result(result: Any) -> str:
    """Extract the plain text from a responses.create() result."""
    # openai>=1.0 exposes a convenience property
    text = getattr(result, "output_text", None)
    if isinstance(text, str) and text:
        return text

    # fallback: scan output choices
    try:
        output = getattr(result, "output", []) or []
        for item in output:
            if isinstance(item, dict):
                content = item.get("content") or []
                for c in content:
                    if c.get("type") == "output_text" and "text" in c:
                        return c["text"] or ""
    except Exception:
        pass
    return ""

