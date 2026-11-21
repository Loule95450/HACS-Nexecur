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
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_ALARM_VERSION,
    CONF_ID_SITE,
    CONF_PHONE,
    CONF_ACCOUNT,
    CONF_DISARM_CODE,
    CONF_ARM_CODE,
    CONF_INVERT_STATUS,
    ALARM_VERSION_VIDEOFIED,
    ALARM_VERSION_HIKVISION,
)
from .alarm_mapping import (
    PANEL_CAMERA_DETECTION,
    PANEL_CONNECTED,
    PANEL_DISCONNECTED,
    PANEL_TRIGGERED_RESTORED,
    hikvision_panel_state,
    resolve_videofied_arm_status,
    videofied_panel_state,
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

        # Disarm code (optional, cannot be changed once set)
        self._disarm_code = entry.data.get(CONF_DISARM_CODE)
        # Arm code (optional, can be changed anytime)
        self._arm_code = entry.data.get(CONF_ARM_CODE)
        self._invert_status = entry.data.get(CONF_INVERT_STATUS, False)

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return the list of supported features based on panel SP availability."""
        data = self.coordinator.data

        # Hikvision panels typically support both modes
        if self._alarm_version == ALARM_VERSION_HIKVISION:
            return AlarmControlPanelEntityFeature.ARM_HOME | AlarmControlPanelEntityFeature.ARM_AWAY

        # Videofied: full arming is always available, the two partial modes
        # only when the site exposes them.
        features = AlarmControlPanelEntityFeature.ARM_AWAY
        if not data:
            return features
        if data.get("panel_sp1_available", True):
            features |= AlarmControlPanelEntityFeature.ARM_HOME
        if data.get("panel_sp2_available", False):
            features |= AlarmControlPanelEntityFeature.ARM_NIGHT
        return features

    def _panel_status(self) -> int | None:
        """Current panel status as an int, or None when it is not known."""
        data = self.coordinator.data
        if not data:
            return None
        raw = data.get("panel_status")
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current state, or None when the panel does not say.

        An unknown status is never reported as disarmed: statuses such as a
        disconnected panel or a camera detection carry no arming information,
        and showing "disarmed" for them would hide a live intrusion.
        """
        status = self._panel_status()
        if status is None:
            return None

        if self._alarm_version == ALARM_VERSION_HIKVISION:
            state = hikvision_panel_state(status)
        else:
            state = videofied_panel_state(status, self._invert_status)
        return AlarmControlPanelState(state) if state else None

    @property
    def available(self) -> bool:
        """A panel the cloud reports as disconnected is not controllable."""
        if not super().available or not self.coordinator.data:
            return False
        if self._alarm_version == ALARM_VERSION_VIDEOFIED:
            return self._panel_status() != PANEL_DISCONNECTED
        return True

    @property
    def code_format(self) -> str | None:
        # Return appropriate format if disarm code OR arm code is configured
        if self._disarm_code or self._arm_code:
            return "text"
        return None

    @property
    def code_arm_required(self) -> bool:
        # Arm code required if configured
        return bool(self._arm_code)

    @property
    def code_disarm_required(self) -> bool:
        return bool(self._disarm_code)

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
        # Whitelist only: coordinator.data holds raw API responses which may
        # contain credentials or other sensitive payloads
        data = self.coordinator.data or {}
        attributes: dict[str, Any] = {
            "alarm_version": self._alarm_version,
            "panel_status": data.get("panel_status"),
            "panel_sp1_available": data.get("panel_sp1_available"),
            "panel_sp2_available": data.get("panel_sp2_available"),
        }
        if self._alarm_version == ALARM_VERSION_VIDEOFIED:
            # Names the user gave the partial modes in the Mon Nexecur app.
            attributes["partial_1_name"] = data.get("panel_sp1_nom") or "Partiel 1"
            attributes["partial_2_name"] = data.get("panel_sp2_nom") or "Partiel 2"
            # Statuses that report an event rather than an arming state.
            events = {
                PANEL_CONNECTED: "panel_connected",
                PANEL_CAMERA_DETECTION: "camera_detection",
                PANEL_TRIGGERED_RESTORED: "intrusion_restored",
                PANEL_DISCONNECTED: "panel_disconnected",
            }
            event = events.get(self._panel_status())
            if event:
                attributes["nexecur_event"] = event
        return attributes

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        # Validate disarm code if configured and not empty
        if self._disarm_code:
            if code != self._disarm_code:
                raise ServiceValidationError("Invalid disarm code")
        
        try:
            await self._client.async_set_armed(False)
            await self.coordinator.async_request_refresh()
        except (NexecurError, HikvisionError) as err:
            _LOGGER.error("Failed to disarm: %s", err)
            raise HomeAssistantError(f"Failed to disarm: {err}") from err

    async def _async_arm(self, mode: str, code: str | None) -> None:
        """Arm in one of the three modes: away (full), home (SP1), night (SP2)."""
        if self._arm_code and code != self._arm_code:
            raise ServiceValidationError("Invalid arm code")

        try:
            if self._alarm_version == ALARM_VERSION_HIKVISION:
                # The cloud panel only exposes two modes.
                if mode == "away":
                    await self._client.async_set_armed_away()
                else:
                    await self._client.async_set_armed_home()
            else:
                data = self.coordinator.data or {}
                status = resolve_videofied_arm_status(
                    mode,
                    data.get("panel_sp1_available", True),
                    data.get("panel_sp2_available", False),
                    self._invert_status,
                )
                await self._client.async_set_panel_status(status)

            await self.coordinator.async_request_refresh()
        except (NexecurError, HikvisionError) as err:
            _LOGGER.error("Failed to arm %s: %s", mode, err)
            raise HomeAssistantError(f"Failed to arm {mode}: {err}") from err

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self._async_arm("away", code)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self._async_arm("home", code)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        await self._async_arm("night", code)
