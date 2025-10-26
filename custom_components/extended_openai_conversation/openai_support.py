"""Build OpenAI clients (SDK 1.x) with lazy imports so platform setup never fails at import time."""

from __future__ import annotations

from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.exceptions import HomeAssistantError

from .const import DEFAULT_BASE_URL


def is_azure(base_url: str | None) -> bool:
    if not base_url:
        return False
    u = base_url.lower()
    return "azure" in u or u.endswith(".openai.azure.com") or "openai.azure.com" in u


def build_async_client(
    hass: HomeAssistant,
    *,
    api_key: str,
    base_url: Optional[str] = None,
    api_version: Optional[str] = None,
    organization: Optional[str] = None,
):
    """
    Return an AsyncOpenAI or AsyncAzureOpenAI client.

    NOTE: This function performs the OpenAI imports lazily to avoid import-time failures
    during platform setup (which can cause repeated “Setting up …” loops).
    """
    http_client = get_async_client(hass)
    base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")

    try:
        if is_azure(base_url):
            # Azure requires azure_endpoint + api_version; model = *deployment name*
            from openai import AsyncAzureOpenAI  # type: ignore
            return AsyncAzureOpenAI(
                api_key=api_key,
                azure_endpoint=base_url,
                api_version=(api_version or "2024-12-01-preview"),
                http_client=http_client,
                organization=organization,
            )
        else:
            from openai import AsyncOpenAI  # type: ignore
            return AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client,
                organization=organization,
            )
    except Exception as exc:
        raise HomeAssistantError(
            "OpenAI Python SDK 1.x is required (manifest requires openai>=1,<2). "
            "Install/update the integration via HACS and restart Home Assistant."
        ) from exc
