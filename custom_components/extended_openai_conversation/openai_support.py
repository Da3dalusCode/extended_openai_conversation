"""Build Async OpenAI clients with OpenAI 1.x SDK."""

from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI
try:
    from openai import AsyncAzureOpenAI  # available in 1.x
except Exception:  # pragma: no cover
    AsyncAzureOpenAI = None  # type: ignore[assignment]


def _looks_like_azure(url: Optional[str]) -> bool:
    if not url:
        return False
    u = url.lower()
    return ("azure.com" in u) or ("cognitive.microsoft.com" in u)


def build_async_client(
    hass,
    *,
    api_key: str,
    base_url: Optional[str] = None,
    api_version: Optional[str] = None,
    organization: Optional[str] = None,
):
    """Return an AsyncOpenAI or AsyncAzureOpenAI client."""
    if (AsyncAzureOpenAI is not None) and (api_version or _looks_like_azure(base_url)):
        # Azure variant requires api_version and endpoint (azure_endpoint)
        return AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=base_url,
            api_version=api_version or "2024-10-21",
        )
    return AsyncOpenAI(api_key=api_key, base_url=base_url, organization=organization)
