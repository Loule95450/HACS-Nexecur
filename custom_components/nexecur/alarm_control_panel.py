from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_NAME, CONF_DISARM_CODE
from .nexecur_api import NexecurClient, NexecurError

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    client: NexecurClient = data["client"]
    coordinator = data["coordinator"]

    async_add_entities([NexecurAlarmEntity(client, coordinator, entry)])

class NexecurAlarmEntity(CoordinatorEntity, AlarmControlPanelEntity):
    _attr_has_entity_name = True
    _attr_name = DEFAULT_NAME
    _attr_supported_features = AlarmControlPanelEntityFeature.ARM_AWAY
    _attr_code_arm_required = False

    def __init__(self, client: NexecurClient, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._client = client
        self._attr_unique_id = f"nexecur_{entry.data['id_site']}"
        self._attr_should_poll = False
        self._id_site = entry.data["id_site"]
        self._disarm_code = entry.data.get(CONF_DISARM_CODE)

    @property
    def state(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        status = int(data.get("panel_status", 0))
        return "armed_away" if status == 1 else "disarmed"

    @property
    def code_format(self) -> str | None:
        # Return appropriate format if disarm code is configured and not empty
        if self._disarm_code:
            return "text"
        return None

    @property
    def code_arm_required(self) -> bool:
        return False

    @property
    def code_disarm_required(self) -> bool:
        return bool(self._disarm_code)

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, str(self._id_site))},
            "manufacturer": "Nexecur",
            "name": "Nexecur Alarm",
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # expose raw coordinator data for debugging
        return dict(self.coordinator.data or {})

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        # Validate disarm code if configured and not empty
        if self._disarm_code:
            if code != self._disarm_code:
                raise ServiceValidationError("Invalid disarm code")
        
        try:
            await self._client.async_set_armed(False)
            await self.coordinator.async_request_refresh()
        except NexecurError as err:
            _LOGGER.error("Failed to disarm: %s", err)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        try:
            await self._client.async_set_armed(True)
            await self.coordinator.async_request_refresh()
        except NexecurError as err:
            _LOGGER.error("Failed to arm: %s", err)
