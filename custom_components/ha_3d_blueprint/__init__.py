"""The HA 3D Blueprint integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ApiConnectionError, BlueprintApiClient
from .const import DOMAIN

# List of platforms that this integration will support.
PLATFORMS: list[Platform] = [Platform.CAMERA, Platform.BUTTON]

_LOGGER = logging.getLogger(__name__)

# Create a type alias for the ConfigEntry that holds our API object.
type BlueprintConfigEntry = ConfigEntry[BlueprintApiClient]


async def async_setup_entry(hass: HomeAssistant, entry: BlueprintConfigEntry) -> bool:
    """Set up HA 3D Blueprint from a config entry."""
    _LOGGER.info("Setting up HA 3D Blueprint entry: %s", entry.title)

    host = entry.data[CONF_HOST]

    # 1. Create an API instance to communicate with the add-on.
    api_client = BlueprintApiClient(
        host=host,
        session=async_get_clientsession(hass),
    )

    # 2. Configure the add-on engine with the data from the config entry.
    # This is the new step we are adding.
    try:
        _LOGGER.info("Sending configuration to Blueprint Engine Add-on...")
        await api_client.configure_engine(config_data=entry.data)
        _LOGGER.info("Successfully configured Blueprint Engine Add-on.")
    except ApiConnectionError as exc:
        _LOGGER.error("Failed to configure add-on, connection error: %s", exc)
        # We return False here because the integration cannot function
        # if the initial configuration fails.
        return False
    except Exception as exc:
        _LOGGER.error("An unexpected error occurred during add-on configuration: %s", exc)
        return False


    # 3. Store the API object in the entry's runtime_data.
    # This makes it accessible to our platforms (camera.py and button.py).
    entry.runtime_data = api_client

    # 4. Forward the setup to the camera and button platforms.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BlueprintConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading HA 3D Blueprint entry: %s", entry.title)

    # Unload the platforms that were set up.
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
