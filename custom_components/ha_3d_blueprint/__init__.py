"""The HA 3D Blueprint integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from typing import TypeAlias

from .api import ApiConnectionError, BlueprintApiClient
from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.CAMERA, Platform.BUTTON]
_LOGGER = logging.getLogger(__name__)
BlueprintConfigEntry: TypeAlias = ConfigEntry[BlueprintApiClient]

async def async_setup_entry(hass: HomeAssistant, entry: BlueprintConfigEntry) -> bool:
    """Set up HA 3D Blueprint from a config entry."""
    host = entry.data[CONF_HOST]

    # Create the API instance without the port
    api_client = BlueprintApiClient(
        host=host,
        session=async_get_clientsession(hass),
    )

    try:
        await api_client.configure_engine(config_data=entry.data)
    except ApiConnectionError as exc:
        _LOGGER.error("Failed to configure add-on, connection error: %s", exc)
        return False

    entry.runtime_data = api_client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: BlueprintConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)