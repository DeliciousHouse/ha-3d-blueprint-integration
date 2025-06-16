"""Button platform for HA 3D Blueprint."""

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .api import BlueprintApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

BUTTON_DESCRIPTIONS = (
    ButtonEntityDescription(key="tag_corner", name="Tag Corner", icon="mdi:vector-square"),
    ButtonEntityDescription(key="tag_doorway", name="Tag Doorway", icon="mdi:door"),
    ButtonEntityDescription(
        key="update_obstruction_map",
        name="Update Obstruction Map",
        icon="mdi:wall",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    # Get the API client from the config entry's runtime_data.
    # This is the instance we created in __init__.py.
    api_client: BlueprintApiClient = entry.runtime_data

    buttons = [
        BlueprintButton(api_client, entry, description)
        for description in BUTTON_DESCRIPTIONS
    ]
    async_add_entities(buttons)


class BlueprintButton(ButtonEntity):
    """A button to trigger blueprinting actions."""

    def __init__(
        self,
        api_client: BlueprintApiClient,
        entry: ConfigEntry,
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        self.api_client = api_client
        self.entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="HA 3D Blueprint Control",
            manufacturer="DeliciousHouse",
            model="Blueprint Engine",
        )

    async def async_press(self) -> None:
        """Handle the button press by sending a timestamped event via the API client."""
        tag_type = self.entity_description.key
        _LOGGER.info("'%s' button pressed!", self.name)

        # The button's only job is to provide the "what" and "when".
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tag_type": tag_type,
            "mobile_beacon_id": self.entry.data.get("mobile_beacon_sensor"),
        }

        _LOGGER.debug("Sending payload to add-on: %s", payload)
        try:
            # Use the API client to send the data. This is much cleaner
            # and uses the dynamic host from the config entry.
            await self.api_client.tag_location(payload)
            _LOGGER.info("Successfully sent '%s' tag to Blueprint Engine.", tag_type)
        except Exception as e:
            _LOGGER.error("Error communicating with add-on: %s", e)

