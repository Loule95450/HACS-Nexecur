"""Binary sensor platform for Nexecur sub-devices (zones, keypads, sirens)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_PHONE,
    CONF_ACCOUNT,
    ALARM_VERSION_HIKVISION,
    DEVICE_TYPE_ZONE,
    DEVICE_TYPE_KEYPAD,
    DEVICE_TYPE_SIREN,
    DETECTOR_TYPE_PIR,
    DETECTOR_TYPE_PIRCAM,
    DETECTOR_TYPE_MAGNET,
    DETECTOR_TYPE_MAGNET_SHOCK,
    DETECTOR_TYPE_SMOKE,
    DETECTOR_TYPE_CO,
    DETECTOR_TYPE_GLASS,
    DETECTOR_TYPE_WATER,
    DETECTOR_TYPE_GAS,
)

_LOGGER = logging.getLogger(__name__)

# Map detector types to binary sensor device classes
DETECTOR_DEVICE_CLASS_MAP = {
    DETECTOR_TYPE_PIR: BinarySensorDeviceClass.MOTION,
    DETECTOR_TYPE_PIRCAM: BinarySensorDeviceClass.MOTION,
    DETECTOR_TYPE_MAGNET: BinarySensorDeviceClass.DOOR,
    DETECTOR_TYPE_MAGNET_SHOCK: BinarySensorDeviceClass.DOOR,
    DETECTOR_TYPE_SMOKE: BinarySensorDeviceClass.SMOKE,
    DETECTOR_TYPE_CO: BinarySensorDeviceClass.CO,
    DETECTOR_TYPE_GLASS: BinarySensorDeviceClass.WINDOW,
    DETECTOR_TYPE_WATER: BinarySensorDeviceClass.MOISTURE,
    DETECTOR_TYPE_GAS: BinarySensorDeviceClass.GAS,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Nexecur binary sensor entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    alarm_version = data.get("alarm_version")

    # Sub-device sensors are only available for Hikvision
    if alarm_version != ALARM_VERSION_HIKVISION:
        return

    # Get the main device identifier for linking
    account = entry.data.get(CONF_ACCOUNT) or entry.data.get(CONF_PHONE, "unknown")
    main_device_id = f"hikvision_{account}"

    # Track created entities to avoid duplicates
    created_entities: set[str] = set()

    @callback
    def async_add_sub_device_binary_sensors() -> None:
        """Add binary sensors for discovered sub-devices."""
        if not coordinator.data:
            return

        entities: list[BinarySensorEntity] = []

        # Process zones
        for zone in coordinator.data.get("zones", []):
            zone_id = zone.get("id")
            if zone_id is None:
                continue

            zone_name = zone.get("name", f"Zone {zone_id}")
            detector_type = zone.get("detectorType", "")

            # Main status sensor (alarm/motion/door state)
            status_uid = f"{main_device_id}_zone_{zone_id}_status"
            if status_uid not in created_entities:
                created_entities.add(status_uid)
                entities.append(
                    NexecurZoneStatusSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        zone_id=zone_id,
                        zone_name=zone_name,
                        detector_type=detector_type,
                        zone_data=zone,
                    )
                )

            # Tamper sensor (if tamperEvident is available)
            if zone.get("tamperEvident") is not None:
                tamper_uid = f"{main_device_id}_zone_{zone_id}_tamper"
                if tamper_uid not in created_entities:
                    created_entities.add(tamper_uid)
                    entities.append(
                        NexecurTamperSensor(
                            coordinator=coordinator,
                            main_device_id=main_device_id,
                            device_type=DEVICE_TYPE_ZONE,
                            device_id=zone_id,
                            device_name=zone_name,
                            zone_data=zone,
                        )
                    )

            # Online status sensor
            online_uid = f"{main_device_id}_zone_{zone_id}_online"
            if online_uid not in created_entities:
                created_entities.add(online_uid)
                entities.append(
                    NexecurOnlineSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_ZONE,
                        device_id=zone_id,
                        device_name=zone_name,
                        zone_data=zone,
                    )
                )

            # Bypassed sensor (if available)
            if zone.get("bypassed") is not None:
                bypass_uid = f"{main_device_id}_zone_{zone_id}_bypassed"
                if bypass_uid not in created_entities:
                    created_entities.add(bypass_uid)
                    entities.append(
                        NexecurBypassSensor(
                            coordinator=coordinator,
                            main_device_id=main_device_id,
                            zone_id=zone_id,
                            zone_name=zone_name,
                            zone_data=zone,
                        )
                    )

        # Process keypads
        for keypad in coordinator.data.get("keypads", []):
            keypad_id = keypad.get("id")
            if keypad_id is None:
                continue

            keypad_name = keypad.get("name", f"Keypad {keypad_id}")

            # Online status sensor
            online_uid = f"{main_device_id}_keypad_{keypad_id}_online"
            if online_uid not in created_entities:
                created_entities.add(online_uid)
                entities.append(
                    NexecurOnlineSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_KEYPAD,
                        device_id=keypad_id,
                        device_name=keypad_name,
                        zone_data=keypad,
                    )
                )

            # Tamper sensor (if available)
            if keypad.get("tamperEvident") is not None:
                tamper_uid = f"{main_device_id}_keypad_{keypad_id}_tamper"
                if tamper_uid not in created_entities:
                    created_entities.add(tamper_uid)
                    entities.append(
                        NexecurTamperSensor(
                            coordinator=coordinator,
                            main_device_id=main_device_id,
                            device_type=DEVICE_TYPE_KEYPAD,
                            device_id=keypad_id,
                            device_name=keypad_name,
                            zone_data=keypad,
                        )
                    )

        # Process sirens
        for siren in coordinator.data.get("sirens", []):
            siren_id = siren.get("id")
            if siren_id is None:
                continue

            siren_name = siren.get("name", f"Siren {siren_id}")

            # Siren active status sensor
            status_uid = f"{main_device_id}_siren_{siren_id}_status"
            if status_uid not in created_entities:
                created_entities.add(status_uid)
                entities.append(
                    NexecurSirenStatusSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        siren_id=siren_id,
                        siren_name=siren_name,
                        siren_data=siren,
                    )
                )

            # Online status sensor
            online_uid = f"{main_device_id}_siren_{siren_id}_online"
            if online_uid not in created_entities:
                created_entities.add(online_uid)
                entities.append(
                    NexecurOnlineSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_SIREN,
                        device_id=siren_id,
                        device_name=siren_name,
                        zone_data=siren,
                    )
                )

            # Tamper sensor (if available)
            if siren.get("tamperEvident") is not None:
                tamper_uid = f"{main_device_id}_siren_{siren_id}_tamper"
                if tamper_uid not in created_entities:
                    created_entities.add(tamper_uid)
                    entities.append(
                        NexecurTamperSensor(
                            coordinator=coordinator,
                            main_device_id=main_device_id,
                            device_type=DEVICE_TYPE_SIREN,
                            device_id=siren_id,
                            device_name=siren_name,
                            zone_data=siren,
                        )
                    )

        if entities:
            _LOGGER.debug("Adding %d sub-device binary sensors", len(entities))
            async_add_entities(entities)

    # Add entities for data already available
    async_add_sub_device_binary_sensors()

    # Listen for coordinator updates to discover new devices
    coordinator.async_add_listener(async_add_sub_device_binary_sensors)


class NexecurSubDeviceBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for Nexecur sub-device binary sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        main_device_id: str,
        device_type: str,
        device_id: int,
        device_name: str,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._main_device_id = main_device_id
        self._device_type = device_type
        self._device_id = device_id
        self._device_name = device_name
        self._initial_data = zone_data

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information to link this entity to the sub-device."""
        device_info: dict[str, Any] = {
            "identifiers": {(DOMAIN, f"{self._main_device_id}_{self._device_type}_{self._device_id}")},
            "name": self._device_name,
            "via_device": (DOMAIN, self._main_device_id),
            "manufacturer": "Nexecur (Hikvision)",
        }

        # Add model info based on device type and detector type
        if self._device_type == DEVICE_TYPE_ZONE:
            detector_type = self._get_device_data().get("detectorType", "Unknown")
            model = self._get_device_data().get("model", "")
            device_info["model"] = f"{detector_type}" + (f" ({model})" if model else "")
        elif self._device_type == DEVICE_TYPE_KEYPAD:
            device_info["model"] = "Keypad"
        elif self._device_type == DEVICE_TYPE_SIREN:
            device_info["model"] = "Siren"

        # Add firmware version if available
        version = self._get_device_data().get("version")
        if version:
            device_info["sw_version"] = version

        return device_info

    def _get_device_data(self) -> dict[str, Any]:
        """Get current device data from coordinator."""
        if not self.coordinator.data:
            return self._initial_data

        if self._device_type == DEVICE_TYPE_ZONE:
            devices = self.coordinator.data.get("zones", [])
        elif self._device_type == DEVICE_TYPE_KEYPAD:
            devices = self.coordinator.data.get("keypads", [])
        elif self._device_type == DEVICE_TYPE_SIREN:
            devices = self.coordinator.data.get("sirens", [])
        else:
            return self._initial_data

        for device in devices:
            if device.get("id") == self._device_id:
                return device

        return self._initial_data


class NexecurZoneStatusSensor(NexecurSubDeviceBinarySensorBase):
    """Binary sensor for zone status (motion, door open, smoke detected, etc.)."""

    def __init__(
        self,
        coordinator,
        main_device_id: str,
        zone_id: int,
        zone_name: str,
        detector_type: str,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize the zone status sensor."""
        super().__init__(
            coordinator=coordinator,
            main_device_id=main_device_id,
            device_type=DEVICE_TYPE_ZONE,
            device_id=zone_id,
            device_name=zone_name,
            zone_data=zone_data,
        )
        self._detector_type = detector_type
        self._attr_unique_id = f"{main_device_id}_zone_{zone_id}_status"
        self._attr_name = "Status"

        # Set device class based on detector type
        self._attr_device_class = DETECTOR_DEVICE_CLASS_MAP.get(
            detector_type, BinarySensorDeviceClass.PROBLEM
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the zone is triggered/alarming."""
        device_data = self._get_device_data()

        # Check for magnet shock detector specific status
        if self._detector_type in [DETECTOR_TYPE_MAGNET, DETECTOR_TYPE_MAGNET_SHOCK]:
            magnet_status = device_data.get("MagnetShockCurrentStatus", {})
            # Door is "on" (open) if magnetOpenStatus is true
            return magnet_status.get("magnetOpenStatus", False)

        # For other detectors, check sensorStatus
        sensor_status = device_data.get("sensorStatus", "normal")
        return sensor_status != "normal"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        device_data = self._get_device_data()
        attrs: dict[str, Any] = {
            "detector_type": self._detector_type,
            "sensor_status": device_data.get("sensorStatus", "unknown"),
            "armed": device_data.get("armed", False),
        }

        # Add magnet shock detector specific attributes
        if self._detector_type in [DETECTOR_TYPE_MAGNET, DETECTOR_TYPE_MAGNET_SHOCK]:
            magnet_status = device_data.get("MagnetShockCurrentStatus", {})
            attrs["magnet_open"] = magnet_status.get("magnetOpenStatus", False)
            attrs["shock_detected"] = magnet_status.get("magnetShockStatus", False)
            attrs["tilt_detected"] = magnet_status.get("magnetTiltStatus", False)

        return attrs


class NexecurTamperSensor(NexecurSubDeviceBinarySensorBase):
    """Binary sensor for tamper detection."""

    def __init__(
        self,
        coordinator,
        main_device_id: str,
        device_type: str,
        device_id: int,
        device_name: str,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize the tamper sensor."""
        super().__init__(
            coordinator=coordinator,
            main_device_id=main_device_id,
            device_type=device_type,
            device_id=device_id,
            device_name=device_name,
            zone_data=zone_data,
        )
        self._attr_unique_id = f"{main_device_id}_{device_type}_{device_id}_tamper"
        self._attr_name = "Tamper"
        self._attr_device_class = BinarySensorDeviceClass.TAMPER

    @property
    def is_on(self) -> bool | None:
        """Return True if tamper is detected."""
        device_data = self._get_device_data()
        return device_data.get("tamperEvident", False)


class NexecurOnlineSensor(NexecurSubDeviceBinarySensorBase):
    """Binary sensor for online/connectivity status."""

    def __init__(
        self,
        coordinator,
        main_device_id: str,
        device_type: str,
        device_id: int,
        device_name: str,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize the online sensor."""
        super().__init__(
            coordinator=coordinator,
            main_device_id=main_device_id,
            device_type=device_type,
            device_id=device_id,
            device_name=device_name,
            zone_data=zone_data,
        )
        self._attr_unique_id = f"{main_device_id}_{device_type}_{device_id}_online"
        self._attr_name = "Online"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_entity_category = "diagnostic"

    @property
    def is_on(self) -> bool | None:
        """Return True if the device is online."""
        device_data = self._get_device_data()
        status = device_data.get("status", "offline")
        return status == "online"


class NexecurBypassSensor(NexecurSubDeviceBinarySensorBase):
    """Binary sensor for zone bypass status."""

    def __init__(
        self,
        coordinator,
        main_device_id: str,
        zone_id: int,
        zone_name: str,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize the bypass sensor."""
        super().__init__(
            coordinator=coordinator,
            main_device_id=main_device_id,
            device_type=DEVICE_TYPE_ZONE,
            device_id=zone_id,
            device_name=zone_name,
            zone_data=zone_data,
        )
        self._attr_unique_id = f"{main_device_id}_zone_{zone_id}_bypassed"
        self._attr_name = "Bypassed"
        self._attr_icon = "mdi:debug-step-over"
        self._attr_entity_category = "diagnostic"

    @property
    def is_on(self) -> bool | None:
        """Return True if the zone is bypassed."""
        device_data = self._get_device_data()
        return device_data.get("bypassed", False)


class NexecurSirenStatusSensor(NexecurSubDeviceBinarySensorBase):
    """Binary sensor for siren active status."""

    def __init__(
        self,
        coordinator,
        main_device_id: str,
        siren_id: int,
        siren_name: str,
        siren_data: dict[str, Any],
    ) -> None:
        """Initialize the siren status sensor."""
        super().__init__(
            coordinator=coordinator,
            main_device_id=main_device_id,
            device_type=DEVICE_TYPE_SIREN,
            device_id=siren_id,
            device_name=siren_name,
            zone_data=siren_data,
        )
        self._attr_unique_id = f"{main_device_id}_siren_{siren_id}_status"
        self._attr_name = "Sounding"
        self._attr_device_class = BinarySensorDeviceClass.SOUND
        self._attr_icon = "mdi:alarm-light"

    @property
    def is_on(self) -> bool | None:
        """Return True if the siren is sounding."""
        device_data = self._get_device_data()
        status = device_data.get("status", "off")
        # Status is "on" when siren is active, "off" when inactive
        return status == "on"
