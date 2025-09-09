from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_NAME
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
    _attr_code_arm_required = False
    _attr_code_disarm_required = False

    def __init__(self, client: NexecurClient, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._client = client
        self._attr_unique_id = f"nexecur_{entry.data['id_site']}"
        self._attr_should_poll = False
        self._id_site = entry.data["id_site"]

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return the list of supported features based on panel_sp2 availability."""
        data = self.coordinator.data
        if not data:
            return AlarmControlPanelEntityFeature.ARM_AWAY
        
        panel_sp2_available = data.get("panel_sp2_available", False)
        if panel_sp2_available:
            # When panel_sp2 is available, we support both HOME (sp1) and AWAY (sp2)
            return AlarmControlPanelEntityFeature.ARM_HOME | AlarmControlPanelEntityFeature.ARM_AWAY
        else:
            # When panel_sp2 is not available, only ARM_AWAY (which will use sp1)
            return AlarmControlPanelEntityFeature.ARM_AWAY

    @property
    def state(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        status = int(data.get("panel_status", 0))
        panel_sp2_available = data.get("panel_sp2_available", False)
        
        if status == 0:
            return AlarmControlPanelState.DISARMED
        elif status == 1:
            # Status 1 = sp1 (home/partial arming)
            return AlarmControlPanelState.ARMED_HOME if panel_sp2_available else AlarmControlPanelState.ARMED_AWAY
        elif status == 2:
            # Status 2 = sp2 (away/full arming) - only when panel_sp2 available
            return AlarmControlPanelState.ARMED_AWAY
        else:
            # Unknown status, assume armed away
            return AlarmControlPanelState.ARMED_AWAY

    @property
    def code_format(self) -> str | None:
        # No code required in UI; the client handles auth/pin internally
        return None

    @property
    def code_arm_required(self) -> bool:
        return False

    @property
    def code_disarm_required(self) -> bool:
        return False

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
        try:
            await self._client.async_set_armed(False)
            await self.coordinator.async_request_refresh()
        except NexecurError as err:
            _LOGGER.error("Failed to disarm: %s", err)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        try:
            data = self.coordinator.data
            panel_sp2_available = data.get("panel_sp2_available", False) if data else False
            
            if panel_sp2_available:
                # When panel_sp2 is available, away mode uses sp2 (status 2)
                await self._client.async_set_armed_away()
            else:
                # When panel_sp2 is not available, use sp1 (status 1) for away
                await self._client.async_set_armed_home()
            
            await self.coordinator.async_request_refresh()
        except NexecurError as err:
            _LOGGER.error("Failed to arm away: %s", err)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        try:
            # Home mode always uses sp1 (status 1)
            await self._client.async_set_armed_home()
            await self.coordinator.async_request_refresh()
        except NexecurError as err:
            _LOGGER.error("Failed to arm home: %s", err)
