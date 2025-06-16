"""Config flow for the HA 3D Blueprint integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .api import ApiConnectionError, BlueprintApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# --- Step 1: Schema to get the add-on's hostname ---
STEP_HOST_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="local-blueprint-engine"): str,
    }
)

# --- Step 2: Schema to get the required sensor entities ---
STEP_SENSORS_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("stationary_sensors"): EntitySelector(
            EntitySelectorConfig(domain="sensor", multiple=True)
        ),
        vol.Required("mobile_beacon_sensor"): EntitySelector(
            EntitySelectorConfig(domain="sensor")
        ),
    }
)


async def validate_host_connection(
    hass: HomeAssistant, host: str
) -> None:
    """Validate that the host is reachable and the API responds."""
    api_client = BlueprintApiClient(host=host, session=async_get_clientsession(hass))
    # We don't need a real config here, just checking the connection.
    # An empty config will cause a validation error on the add-on side,
    # but as long as we don't get a connection error, we're good.
    await api_client.configure_engine(config_data={})


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA 3D Blueprint."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.flow_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the first step: getting the add-on host."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_host_connection(self.hass, user_input[CONF_HOST])
            except ApiConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during host validation")
                errors["base"] = "unknown"
            else:
                # Host is valid, store it and move to the next step
                self.flow_data.update(user_input)
                return await self.async_step_sensors()

        return self.async_show_form(
            step_id="user", data_schema=STEP_HOST_DATA_SCHEMA, errors=errors
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the second step: selecting sensors."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Combine data from the previous step with this step's data
            self.flow_data.update(user_input)

            # Add area and location info to the config entry data
            area_registry = ar.async_get(self.hass)
            self.flow_data["areas"] = {
                area.id: {"name": area.name, "floor": area.floor_id}
                for area in area_registry.async_list_areas()
            }
            self.flow_data["latitude"] = self.hass.config.latitude
            self.flow_data["longitude"] = self.hass.config.longitude

            return self.async_create_entry(
                title="HA 3D Blueprint", data=self.flow_data
            )

        return self.async_show_form(
            step_id="sensors", data_schema=STEP_SENSORS_DATA_SCHEMA, errors=errors
        )
