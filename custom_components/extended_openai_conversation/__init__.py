from __future__ import annotations

from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

PLATFORMS: Final = ["conversation"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Extended OpenAI Conversation integration (namespace only)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    hass.data.setdefault(DOMAIN, {})
    # Store the config entry for runtime access (entity reads entry live; no reload needed)
    hass.data[DOMAIN][entry.entry_id] = {"entry": entry}

    # Forward to the conversation platform (adds the ConversationEntity).
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)
    return unload_ok
