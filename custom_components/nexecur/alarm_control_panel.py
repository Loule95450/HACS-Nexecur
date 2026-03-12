from __future__ import annotations

import logging
from typing import Any, Union

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_ALARM_VERSION,
    CONF_ID_SITE,
    CONF_PHONE,
    CONF_ACCOUNT,
    ALARM_VERSION_VIDEOFIED,
    ALARM_VERSION_HIKVISION,
)
from .nexecur_api import NexecurClient, NexecurError
from .nexecur_api_hikvision import NexecurHikvisionClient, NexecurError as HikvisionError

_LOGGER = logging.getLogger(__name__)

# Type alias for both client types
NexecurClientType = Union[NexecurClient, NexecurHikvisionClient]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    client: NexecurClientType = data["client"]
    coordinator = data["coordinator"]
    alarm_version = data.get("alarm_version", ALARM_VERSION_VIDEOFIED)

    async_add_entities([NexecurAlarmEntity(client, coordinator, entry, alarm_version)])


class NexecurAlarmEntity(CoordinatorEntity, AlarmControlPanelEntity):
    _attr_has_entity_name = True
    _attr_name = DEFAULT_NAME
    _attr_code_arm_required = False
    _attr_code_disarm_required = False

    def __init__(
        self,
        client: NexecurClientType,
        coordinator,
        entry: ConfigEntry,
        alarm_version: str,
    ) -> None:
        super().__init__(coordinator)
        self._client = client
        self._alarm_version = alarm_version
        self._attr_should_poll = False

        # Set unique ID based on alarm version
        if alarm_version == ALARM_VERSION_HIKVISION:
            identifier = entry.data.get(CONF_ACCOUNT) or entry.data.get(CONF_PHONE, "unknown")
            self._attr_unique_id = f"nexecur_hikvision_{identifier}"
            self._identifier = identifier
        else:
            identifier = entry.data.get(CONF_ID_SITE, "unknown")
            self._attr_unique_id = f"nexecur_{identifier}"
            self._identifier = identifier

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return the list of supported features based on panel SP availability."""
        data = self.coordinator.data
        if not data:
            return AlarmControlPanelEntityFeature.ARM_AWAY

        panel_sp1_available = data.get("panel_sp1_available", True)
        panel_sp2_available = data.get("panel_sp2_available", False)

        # Hikvision panels typically support both modes
        if self._alarm_version == ALARM_VERSION_HIKVISION:
            return AlarmControlPanelEntityFeature.ARM_HOME | AlarmControlPanelEntityFeature.ARM_AWAY

        # Videofied logic
        if not panel_sp1_available:
            return AlarmControlPanelEntityFeature(0)

        if panel_sp2_available:
            return AlarmControlPanelEntityFeature.ARM_HOME | AlarmControlPanelEntityFeature.ARM_AWAY
        else:
            return AlarmControlPanelEntityFeature.ARM_AWAY

    @property
    def state(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        status = int(data.get("panel_status", 0))
        panel_sp1_available = data.get("panel_sp1_available", True)
        panel_sp2_available = data.get("panel_sp2_available", False)

        if status == 0:
            return AlarmControlPanelState.DISARMED
        elif status == 1:
            # Status 1 = sp1 active / stay mode
            if self._alarm_version == ALARM_VERSION_HIKVISION:
                return AlarmControlPanelState.ARMED_HOME
            if not panel_sp1_available:
                return AlarmControlPanelState.DISARMED
            return AlarmControlPanelState.ARMED_HOME if panel_sp2_available else AlarmControlPanelState.ARMED_AWAY
        elif status == 2:
            # Status 2 = sp2 active / away mode
            return AlarmControlPanelState.ARMED_AWAY
        else:
            return AlarmControlPanelState.DISARMED

    @property
    def code_format(self) -> str | None:
        return None

    @property
    def code_arm_required(self) -> bool:
        return False

    @property
    def code_disarm_required(self) -> bool:
        return False

    @property
    def device_info(self) -> dict[str, Any]:
        if self._alarm_version == ALARM_VERSION_HIKVISION:
            return {
                "identifiers": {(DOMAIN, f"hikvision_{self._identifier}")},
                "manufacturer": "Nexecur (Hikvision)",
                "name": "Nexecur Alarm",
                "model": "Hikvision AX PRO",
            }
        return {
            "identifiers": {(DOMAIN, str(self._identifier))},
            "manufacturer": "Nexecur",
            "name": "Nexecur Alarm",
            "model": "Videofied",
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = dict(self.coordinator.data or {})
        attrs["alarm_version"] = self._alarm_version
        return attrs

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        try:
            await self._client.async_set_armed(False)
            await self.coordinator.async_request_refresh()
        except (NexecurError, HikvisionError) as err:
            _LOGGER.error("Failed to disarm: %s", err)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        try:
            if self._alarm_version == ALARM_VERSION_HIKVISION:
                await self._client.async_set_armed_away()
            else:
                data = self.coordinator.data
                panel_sp1_available = data.get("panel_sp1_available", True) if data else True
                panel_sp2_available = data.get("panel_sp2_available", False) if data else False

                if not panel_sp1_available:
                    _LOGGER.error("Cannot arm: SP1 not available")
                    return

                if panel_sp2_available:
                    await self._client.async_set_armed_away()
                else:
                    await self._client.async_set_armed_home()

            await self.coordinator.async_request_refresh()
        except (NexecurError, HikvisionError) as err:
            _LOGGER.error("Failed to arm away: %s", err)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        try:
            if self._alarm_version == ALARM_VERSION_HIKVISION:
                await self._client.async_set_armed_home()
            else:
                data = self.coordinator.data
                panel_sp1_available = data.get("panel_sp1_available", True) if data else True

                if not panel_sp1_available:
                    _LOGGER.error("Cannot arm home: SP1 not available")
                    return

                await self._client.async_set_armed_home()

            await self.coordinator.async_request_refresh()
        except (NexecurError, HikvisionError) as err:
            _LOGGER.error("Failed to arm home: %s", err)
