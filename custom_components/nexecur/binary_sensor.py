"""Binary sensor platform for Nexecur sub-devices (zones, keypads, sirens)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    DEVICE_TYPE_BASE,
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

# Map detector types to binary sensor device classes for the main status
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

# Binary sensor definitions for zones
ZONE_BINARY_SENSORS = [
    # Status sensors
    {"key": "status", "name": "Online", "device_class": BinarySensorDeviceClass.CONNECTIVITY, "on_value": "online", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "sensorStatus", "name": "Sensor Status", "device_class": BinarySensorDeviceClass.PROBLEM, "on_value": "!normal", "icon": "mdi:alert-circle"},
    {"key": "alarm", "name": "Alarm", "device_class": BinarySensorDeviceClass.SAFETY, "on_value": True, "icon": "mdi:alarm-light"},
    {"key": "tamperEvident", "name": "Tamper", "device_class": BinarySensorDeviceClass.TAMPER, "on_value": True},
    {"key": "armed", "name": "Armed", "device_class": None, "on_value": True, "icon": "mdi:shield-lock"},
    {"key": "isArming", "name": "Arming", "device_class": None, "on_value": True, "icon": "mdi:shield-sync", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "bypassed", "name": "Bypassed", "device_class": None, "on_value": True, "icon": "mdi:debug-step-over", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "shielded", "name": "Shielded", "device_class": None, "on_value": True, "icon": "mdi:shield-off", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "stayAway", "name": "24h Zone", "device_class": None, "on_value": True, "icon": "mdi:shield-home", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "abnormalOrNot", "name": "Abnormal", "device_class": BinarySensorDeviceClass.PROBLEM, "on_value": True, "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "isViaRepeater", "name": "Via Repeater", "device_class": None, "on_value": True, "icon": "mdi:access-point-network", "entity_category": EntityCategory.DIAGNOSTIC},
]

# Specific sensors for magnetShockDetector
MAGNET_SHOCK_BINARY_SENSORS = [
    {"key": "magnetOpenStatus", "name": "Door/Window", "device_class": BinarySensorDeviceClass.DOOR, "on_value": True, "nested": "MagnetShockCurrentStatus"},
    {"key": "magnetShockStatus", "name": "Shock", "device_class": BinarySensorDeviceClass.VIBRATION, "on_value": True, "nested": "MagnetShockCurrentStatus"},
    {"key": "magnetTiltStatus", "name": "Tilt", "device_class": BinarySensorDeviceClass.MOVING, "on_value": True, "nested": "MagnetShockCurrentStatus"},
]

# Binary sensor definitions for keypads
KEYPAD_BINARY_SENSORS = [
    {"key": "status", "name": "Online", "device_class": BinarySensorDeviceClass.CONNECTIVITY, "on_value": "online", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "tamperEvident", "name": "Tamper", "device_class": BinarySensorDeviceClass.TAMPER, "on_value": True},
    {"key": "abnormalOrNot", "name": "Abnormal", "device_class": BinarySensorDeviceClass.PROBLEM, "on_value": True, "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "isViaRepeater", "name": "Via Repeater", "device_class": None, "on_value": True, "icon": "mdi:access-point-network", "entity_category": EntityCategory.DIAGNOSTIC},
]

# Binary sensor definitions for sirens
SIREN_BINARY_SENSORS = [
    {"key": "status", "name": "Sounding", "device_class": BinarySensorDeviceClass.SOUND, "on_value": "on", "icon": "mdi:alarm-light"},
    {"key": "status_online", "name": "Online", "device_class": BinarySensorDeviceClass.CONNECTIVITY, "on_value": ["on", "off", "online"], "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "tamperEvident", "name": "Tamper", "device_class": BinarySensorDeviceClass.TAMPER, "on_value": True},
    {"key": "abnormalOrNot", "name": "Abnormal", "device_class": BinarySensorDeviceClass.PROBLEM, "on_value": True, "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "isViaRepeater", "name": "Via Repeater", "device_class": None, "on_value": True, "icon": "mdi:access-point-network", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "intercomServiceEnabled", "name": "Intercom Enabled", "device_class": None, "on_value": True, "icon": "mdi:phone-voip", "entity_category": EntityCategory.DIAGNOSTIC},
]

# Binary sensor definitions for base station (AX Pro)
BASE_STATION_BINARY_SENSORS = [
    # HostStatus sensors
    {"key": "ACConnect", "name": "External Power", "device_class": BinarySensorDeviceClass.PLUG, "on_value": True, "nested": "HostStatus"},
    {"key": "tamperEvident", "name": "Tamper", "device_class": BinarySensorDeviceClass.TAMPER, "on_value": True, "nested": "HostStatus"},
    # CommuniStatus sensors - Connection states
    {"key": "wifi", "name": "WiFi Connected", "device_class": BinarySensorDeviceClass.CONNECTIVITY, "on_value": "normal", "icon": "mdi:wifi", "nested": "CommuniStatus"},
    {"key": "wired", "name": "Ethernet Connected", "device_class": BinarySensorDeviceClass.CONNECTIVITY, "on_value": "normal", "icon": "mdi:ethernet", "nested": "CommuniStatus"},
    {"key": "mobile", "name": "Mobile Connected", "device_class": BinarySensorDeviceClass.CONNECTIVITY, "on_value": "normal", "icon": "mdi:signal-cellular-3", "nested": "CommuniStatus"},
    {"key": "cloud", "name": "Cloud Connected", "device_class": BinarySensorDeviceClass.CONNECTIVITY, "on_value": "normal", "icon": "mdi:cloud-check", "nested": "CommuniStatus"},
]


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

            zone_name = zone.get("name", f"Zone {zone_id}").strip()
            detector_type = zone.get("detectorType", "")

            # Add common zone binary sensors
            for sensor_def in ZONE_BINARY_SENSORS:
                sensor_key = sensor_def["key"]
                if zone.get(sensor_key) is None:
                    continue

                uid = f"{main_device_id}_zone_{zone_id}_{sensor_key}"
                if uid not in created_entities:
                    created_entities.add(uid)
                    entities.append(
                        NexecurBinarySensor(
                            coordinator=coordinator,
                            main_device_id=main_device_id,
                            device_type=DEVICE_TYPE_ZONE,
                            device_id=zone_id,
                            device_name=zone_name,
                            sensor_def=sensor_def,
                            initial_data=zone,
                        )
                    )

            # Add magnetShockDetector specific sensors
            if detector_type in [DETECTOR_TYPE_MAGNET, DETECTOR_TYPE_MAGNET_SHOCK]:
                magnet_status = zone.get("MagnetShockCurrentStatus", {})
                for sensor_def in MAGNET_SHOCK_BINARY_SENSORS:
                    sensor_key = sensor_def["key"]
                    if magnet_status.get(sensor_key) is None:
                        continue

                    uid = f"{main_device_id}_zone_{zone_id}_{sensor_key}"
                    if uid not in created_entities:
                        created_entities.add(uid)
                        entities.append(
                            NexecurBinarySensor(
                                coordinator=coordinator,
                                main_device_id=main_device_id,
                                device_type=DEVICE_TYPE_ZONE,
                                device_id=zone_id,
                                device_name=zone_name,
                                sensor_def=sensor_def,
                                initial_data=zone,
                            )
                        )

        # Process keypads
        for keypad in coordinator.data.get("keypads", []):
            keypad_id = keypad.get("id")
            if keypad_id is None:
                continue

            keypad_name = keypad.get("name", f"Keypad {keypad_id}").strip()

            for sensor_def in KEYPAD_BINARY_SENSORS:
                sensor_key = sensor_def["key"]
                if keypad.get(sensor_key) is None:
                    continue

                uid = f"{main_device_id}_keypad_{keypad_id}_{sensor_key}"
                if uid not in created_entities:
                    created_entities.add(uid)
                    entities.append(
                        NexecurBinarySensor(
                            coordinator=coordinator,
                            main_device_id=main_device_id,
                            device_type=DEVICE_TYPE_KEYPAD,
                            device_id=keypad_id,
                            device_name=keypad_name,
                            sensor_def=sensor_def,
                            initial_data=keypad,
                        )
                    )

        # Process sirens
        for siren in coordinator.data.get("sirens", []):
            siren_id = siren.get("id")
            if siren_id is None:
                continue

            siren_name = siren.get("name", f"Siren {siren_id}").strip()

            for sensor_def in SIREN_BINARY_SENSORS:
                sensor_key = sensor_def["key"]
                # Special handling for status_online which uses the same "status" field
                actual_key = "status" if sensor_key == "status_online" else sensor_key
                if siren.get(actual_key) is None:
                    continue

                uid = f"{main_device_id}_siren_{siren_id}_{sensor_key}"
                if uid not in created_entities:
                    created_entities.add(uid)
                    entities.append(
                        NexecurBinarySensor(
                            coordinator=coordinator,
                            main_device_id=main_device_id,
                            device_type=DEVICE_TYPE_SIREN,
                            device_id=siren_id,
                            device_name=siren_name,
                            sensor_def=sensor_def,
                            initial_data=siren,
                        )
                    )

        # Process base station binary sensors (attached to main device)
        for sensor_def in BASE_STATION_BINARY_SENSORS:
            sensor_key = sensor_def["key"]
            nested_key = sensor_def.get("nested")

            # Check if data exists
            has_data = False
            if nested_key == "HostStatus":
                host_status = coordinator.data.get("HostStatus", {})
                has_data = host_status.get(sensor_key) is not None
            elif nested_key == "CommuniStatus":
                communi_status = coordinator.data.get("CommuniStatus", {})
                has_data = communi_status.get(sensor_key) is not None

            if not has_data:
                continue

            uid = f"{main_device_id}_base_{sensor_key}"
            if uid not in created_entities:
                created_entities.add(uid)
                entities.append(
                    NexecurBaseStationBinarySensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        sensor_def=sensor_def,
                    )
                )

        if entities:
            _LOGGER.debug("Adding %d sub-device binary sensors", len(entities))
            async_add_entities(entities)

    # Add entities for data already available
    async_add_sub_device_binary_sensors()

    # Listen for coordinator updates to discover new devices
    coordinator.async_add_listener(async_add_sub_device_binary_sensors)


class NexecurBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor entity for Nexecur sub-devices."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        main_device_id: str,
        device_type: str,
        device_id: int,
        device_name: str,
        sensor_def: dict[str, Any],
        initial_data: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._main_device_id = main_device_id
        self._device_type = device_type
        self._device_id = device_id
        self._device_name = device_name
        self._sensor_def = sensor_def
        self._sensor_key = sensor_def["key"]
        self._on_value = sensor_def["on_value"]
        self._nested_key = sensor_def.get("nested")
        self._initial_data = initial_data

        # Set unique ID
        self._attr_unique_id = f"{main_device_id}_{device_type}_{device_id}_{self._sensor_key}"

        # Configure sensor from definition
        self._attr_name = sensor_def["name"]
        self._attr_device_class = sensor_def.get("device_class")

        if sensor_def.get("icon"):
            self._attr_icon = sensor_def["icon"]

        if sensor_def.get("entity_category"):
            self._attr_entity_category = sensor_def["entity_category"]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information to link this entity to the sub-device."""
        device_data = self._get_device_data()

        device_info: dict[str, Any] = {
            "identifiers": {(DOMAIN, f"{self._main_device_id}_{self._device_type}_{self._device_id}")},
            "name": self._device_name,
            "via_device": (DOMAIN, self._main_device_id),
            "manufacturer": "Nexecur (Hikvision)",
        }

        # Add model info
        model = device_data.get("model", "")
        if self._device_type == DEVICE_TYPE_ZONE:
            detector_type = device_data.get("detectorType", "Unknown")
            device_info["model"] = f"{detector_type}" + (f" ({model})" if model else "")
        elif self._device_type == DEVICE_TYPE_KEYPAD:
            device_info["model"] = f"Keypad" + (f" ({model})" if model else "")
        elif self._device_type == DEVICE_TYPE_SIREN:
            device_info["model"] = f"Siren" + (f" ({model})" if model else "")

        # Add firmware version
        version = device_data.get("version")
        if version:
            device_info["sw_version"] = version

        # Add serial number
        serial = device_data.get("seq") or device_data.get("sequenceID")
        if serial:
            device_info["serial_number"] = str(serial)

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

    def _get_value(self) -> Any:
        """Get the value for this sensor."""
        device_data = self._get_device_data()

        # Handle nested values (e.g., MagnetShockCurrentStatus.magnetOpenStatus)
        if self._nested_key:
            nested_data = device_data.get(self._nested_key, {})
            return nested_data.get(self._sensor_key)

        # Special handling for status_online on sirens
        if self._sensor_key == "status_online":
            return device_data.get("status")

        return device_data.get(self._sensor_key)

    @property
    def is_on(self) -> bool | None:
        """Return True if the binary sensor is on."""
        value = self._get_value()

        if value is None:
            return None

        # Handle special "not equal" comparison (e.g., "!normal")
        if isinstance(self._on_value, str) and self._on_value.startswith("!"):
            expected_off_value = self._on_value[1:]
            return value != expected_off_value

        # Handle list of on values
        if isinstance(self._on_value, list):
            return value in self._on_value

        # Direct comparison
        return value == self._on_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        device_data = self._get_device_data()
        attrs: dict[str, Any] = {}

        # Add raw value for debugging
        if self._nested_key:
            nested_data = device_data.get(self._nested_key, {})
            attrs["raw_value"] = nested_data.get(self._sensor_key)
        else:
            actual_key = "status" if self._sensor_key == "status_online" else self._sensor_key
            attrs["raw_value"] = device_data.get(actual_key)

        return attrs

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.data:
            return False

        device_data = self._get_device_data()
        status = device_data.get("status", "offline")

        # For sirens, status can be "on" or "off" which indicates it's working
        if self._device_type == DEVICE_TYPE_SIREN:
            return status in ["online", "on", "off"]

        return status == "online"


class NexecurBaseStationBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor entity for Nexecur base station (AX Pro)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        main_device_id: str,
        sensor_def: dict[str, Any],
    ) -> None:
        """Initialize the base station binary sensor."""
        super().__init__(coordinator)
        self._main_device_id = main_device_id
        self._sensor_key = sensor_def["key"]
        self._on_value = sensor_def["on_value"]
        self._nested_key = sensor_def.get("nested")

        # Set unique ID
        self._attr_unique_id = f"{main_device_id}_base_{self._sensor_key}"

        # Configure sensor from definition
        self._attr_name = sensor_def["name"]
        self._attr_device_class = sensor_def.get("device_class")

        if sensor_def.get("icon"):
            self._attr_icon = sensor_def["icon"]

        if sensor_def.get("entity_category"):
            self._attr_entity_category = sensor_def["entity_category"]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information to link this entity to the main device."""
        return {
            "identifiers": {(DOMAIN, self._main_device_id)},
        }

    def _get_value(self) -> Any:
        """Get the value for this sensor."""
        if not self.coordinator.data:
            return None

        if self._nested_key == "HostStatus":
            host_status = self.coordinator.data.get("HostStatus", {})
            return host_status.get(self._sensor_key)
        elif self._nested_key == "CommuniStatus":
            communi_status = self.coordinator.data.get("CommuniStatus", {})
            return communi_status.get(self._sensor_key)

        return None

    @property
    def is_on(self) -> bool | None:
        """Return True if the binary sensor is on."""
        value = self._get_value()

        if value is None:
            return None

        # Handle special "not equal" comparison (e.g., "!normal")
        if isinstance(self._on_value, str) and self._on_value.startswith("!"):
            expected_off_value = self._on_value[1:]
            return value != expected_off_value

        # Handle list of on values
        if isinstance(self._on_value, list):
            return value in self._on_value

        # Direct comparison
        return value == self._on_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {"raw_value": self._get_value()}

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Base station is always available if coordinator has data
        return self.coordinator.data is not None
