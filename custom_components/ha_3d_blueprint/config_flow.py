"""Config flow for the HA 3D Blueprint integration."""

from __future__ import annotations

import logging
from typing import Any
from itertools import combinations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    DeviceSelector,
    DeviceSelectorConfig,
)

from .api import ApiConnectionError, BlueprintApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def validate_host_connection(hass: HomeAssistant, host: str) -> None:
    """Validate that the host is reachable and the API responds."""
    api_client = BlueprintApiClient(host=host, session=async_get_clientsession(hass))
    await api_client.configure_engine(config_data={})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
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
                # Store the host and move to the next step
                self.flow_data.update(user_input)
                return await self.async_step_select_devices()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default="local-blueprint-engine"): str}),
            errors=errors,
        )

    async def async_step_select_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the second step: selecting devices."""
        if user_input is None:
            return self.async_show_form(
                step_id="select_devices",
                data_schema=vol.Schema(
                    {
                        vol.Required("stationary_devices"): DeviceSelector(
                            DeviceSelectorConfig(multiple=True, mode="list")
                        ),
                        # --- FIXED LINE HERE ---
                        vol.Required("mobile_device"): DeviceSelector(
                            DeviceSelectorConfig(multiple=False)
                        ),
                    }
                ),
            )

        # Combine host data from step 1 with new device data from this step
        self.flow_data.update(user_input)

        stationary_device_ids = self.flow_data["stationary_devices"]
        mobile_device_id = self.flow_data["mobile_device"]

        if len(stationary_device_ids) < 3:
            return self.async_show_form(
                step_id="select_devices",
                errors={"base": "not_enough_devices"},
            )

        entity_reg = er.async_get(self.hass)
        device_reg = dr.async_get(self.hass)

        # --- Find Stationary Sensors ---
        stationary_sensors = set()
        device_map = {dev_id: device_reg.async_get(dev_id) for dev_id in stationary_device_ids}
        all_sensor_entities = {
            entry.entity_id: entry
            for entry in entity_reg.entities.values()
            if entry.domain == "sensor" and entry.device_id in stationary_device_ids
        }

        for device1_id, device2_id in combinations(stationary_device_ids, 2):
            device1_name = device_map[device1_id].name.lower()
            device2_name = device_map[device2_id].name.lower()
            for entity_id, entity in all_sensor_entities.items():
                entity_name_lower = (entity.name or "").lower()
                if (
                    entity.device_id == device1_id and device2_name in entity_name_lower
                ) or (
                    entity.device_id == device2_id and device1_name in entity_name_lower
                ):
                    stationary_sensors.add(entity_id)

        # --- Find Mobile Beacon Sensor ---
        mobile_beacon_sensor = None
        mobile_entities = er.async_entries_for_device(entity_reg, mobile_device_id)
        for entity in mobile_entities:
            name_to_check = (entity.original_name or entity.name or "").lower()
            if entity.domain == "sensor" and ("ble" in name_to_check or "transmitter" in name_to_check):
                mobile_beacon_sensor = entity.entity_id
                break

        if not stationary_sensors or not mobile_beacon_sensor:
            return self.async_abort(reason="no_sensors_found")

        self.flow_data["stationary_sensors"] = list(stationary_sensors)
        self.flow_data["mobile_beacon_sensor"] = mobile_beacon_sensor

        # --- Add Area and Location Info ---
        area_reg_instance = ar.async_get(self.hass)
        self.flow_data["areas"] = {
            area.id: {"name": area.name, "floor": area.floor_id}
            for area in area_reg_instance.async_list_areas()
        }
        self.flow_data["latitude"] = self.hass.config.latitude
        self.flow_data["longitude"] = self.hass.config.longitude

        return self.async_create_entry(title="HA 3D Blueprint", data=self.flow_data)