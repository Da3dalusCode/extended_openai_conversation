"""Helpers to construct OpenAI clients in async mode (OpenAI SDK 1.x)."""

from __future__ import annotations

from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

from .const import DEFAULT_BASE_URL

# OpenAI SDK imports
from openai import AsyncOpenAI, AsyncAzureOpenAI


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
    """Return an AsyncOpenAI or AsyncAzureOpenAI client using HA's shared httpx client."""
    http_client = get_async_client(hass)
    base_url = base_url or DEFAULT_BASE_URL

    if is_azure(base_url):
        # Azure requires the "azure_endpoint" and an explicit api_version.
        # Note: In Azure, the "model" parameter is the *deployment name*.
        client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=base_url.rstrip("/"),
            api_version=(api_version or "2024-12-01-preview"),
            http_client=http_client,
            organization=organization,
        )
    else:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url.rstrip("/") if base_url else None,
            http_client=http_client,
            organization=organization,
        )
    return client

