"""Sensor platform for Nexecur sub-devices (zones, keypads, sirens)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    UnitOfTemperature,
    EntityCategory,
)
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
)

_LOGGER = logging.getLogger(__name__)

# Sensor type definitions with their configuration
ZONE_SENSORS = [
    # Measurement sensors
    {"key": "chargeValue", "name": "Battery", "device_class": SensorDeviceClass.BATTERY, "unit": PERCENTAGE, "icon": "mdi:battery", "state_class": SensorStateClass.MEASUREMENT},
    {"key": "realSignal", "name": "Signal Strength", "device_class": SensorDeviceClass.SIGNAL_STRENGTH, "unit": SIGNAL_STRENGTH_DECIBELS, "icon": "mdi:signal", "state_class": SensorStateClass.MEASUREMENT},
    {"key": "signal", "name": "Signal Raw", "device_class": None, "unit": None, "icon": "mdi:signal-variant", "state_class": SensorStateClass.MEASUREMENT, "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "temperature", "name": "Temperature", "device_class": SensorDeviceClass.TEMPERATURE, "unit": UnitOfTemperature.CELSIUS, "icon": "mdi:thermometer", "state_class": SensorStateClass.MEASUREMENT},
    # Diagnostic/info sensors
    {"key": "charge", "name": "Battery Status", "device_class": None, "unit": None, "icon": "mdi:battery-heart-variant", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "signalType", "name": "Signal Type", "device_class": None, "unit": None, "icon": "mdi:antenna", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "version", "name": "Firmware Version", "device_class": None, "unit": None, "icon": "mdi:information-outline", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "model", "name": "Model", "device_class": None, "unit": None, "icon": "mdi:chip", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "detectorType", "name": "Detector Type", "device_class": None, "unit": None, "icon": "mdi:smoke-detector-variant", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "zoneType", "name": "Zone Type", "device_class": None, "unit": None, "icon": "mdi:shield-home", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "deviceNo", "name": "Device Number", "device_class": None, "unit": None, "icon": "mdi:numeric", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "sequenceID", "name": "Sequence ID", "device_class": None, "unit": None, "icon": "mdi:identifier", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "subSystemNo", "name": "Subsystem", "device_class": None, "unit": None, "icon": "mdi:sitemap", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "zoneAttrib", "name": "Zone Attribute", "device_class": None, "unit": None, "icon": "mdi:tag", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "healthStatus", "name": "Health Status", "device_class": None, "unit": None, "icon": "mdi:heart-pulse", "entity_category": EntityCategory.DIAGNOSTIC},  # Smoke detector only
]

KEYPAD_SENSORS = [
    {"key": "chargeValue", "name": "Battery", "device_class": SensorDeviceClass.BATTERY, "unit": PERCENTAGE, "icon": "mdi:battery", "state_class": SensorStateClass.MEASUREMENT},
    {"key": "realSignal", "name": "Signal Strength", "device_class": SensorDeviceClass.SIGNAL_STRENGTH, "unit": SIGNAL_STRENGTH_DECIBELS, "icon": "mdi:signal", "state_class": SensorStateClass.MEASUREMENT},
    {"key": "signal", "name": "Signal Raw", "device_class": None, "unit": None, "icon": "mdi:signal-variant", "state_class": SensorStateClass.MEASUREMENT, "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "temperature", "name": "Temperature", "device_class": SensorDeviceClass.TEMPERATURE, "unit": UnitOfTemperature.CELSIUS, "icon": "mdi:thermometer", "state_class": SensorStateClass.MEASUREMENT},
    {"key": "charge", "name": "Battery Status", "device_class": None, "unit": None, "icon": "mdi:battery-heart-variant", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "signalType", "name": "Signal Type", "device_class": None, "unit": None, "icon": "mdi:antenna", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "version", "name": "Firmware Version", "device_class": None, "unit": None, "icon": "mdi:information-outline", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "model", "name": "Model", "device_class": None, "unit": None, "icon": "mdi:chip", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "deviceNo", "name": "Device Number", "device_class": None, "unit": None, "icon": "mdi:numeric", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "seq", "name": "Serial Number", "device_class": None, "unit": None, "icon": "mdi:barcode", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "sequenceID", "name": "Sequence ID", "device_class": None, "unit": None, "icon": "mdi:identifier", "entity_category": EntityCategory.DIAGNOSTIC},
]

SIREN_SENSORS = [
    {"key": "chargeValue", "name": "Battery", "device_class": SensorDeviceClass.BATTERY, "unit": PERCENTAGE, "icon": "mdi:battery", "state_class": SensorStateClass.MEASUREMENT},
    {"key": "realSignal", "name": "Signal Strength", "device_class": SensorDeviceClass.SIGNAL_STRENGTH, "unit": SIGNAL_STRENGTH_DECIBELS, "icon": "mdi:signal", "state_class": SensorStateClass.MEASUREMENT},
    {"key": "signal", "name": "Signal Raw", "device_class": None, "unit": None, "icon": "mdi:signal-variant", "state_class": SensorStateClass.MEASUREMENT, "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "temperature", "name": "Temperature", "device_class": SensorDeviceClass.TEMPERATURE, "unit": UnitOfTemperature.CELSIUS, "icon": "mdi:thermometer", "state_class": SensorStateClass.MEASUREMENT},
    {"key": "charge", "name": "Battery Status", "device_class": None, "unit": None, "icon": "mdi:battery-heart-variant", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "signalType", "name": "Signal Type", "device_class": None, "unit": None, "icon": "mdi:antenna", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "version", "name": "Firmware Version", "device_class": None, "unit": None, "icon": "mdi:information-outline", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "model", "name": "Model", "device_class": None, "unit": None, "icon": "mdi:chip", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "deviceNo", "name": "Device Number", "device_class": None, "unit": None, "icon": "mdi:numeric", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "seq", "name": "Serial Number", "device_class": None, "unit": None, "icon": "mdi:barcode", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "sequenceID", "name": "Sequence ID", "device_class": None, "unit": None, "icon": "mdi:identifier", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "sirenColor", "name": "Siren Color", "device_class": None, "unit": None, "icon": "mdi:palette", "entity_category": EntityCategory.DIAGNOSTIC},
    {"key": "mainPowerSupply", "name": "Power Supply", "device_class": None, "unit": None, "icon": "mdi:power-plug", "entity_category": EntityCategory.DIAGNOSTIC},
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Nexecur sensor entities from a config entry."""
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
    def async_add_sub_device_sensors() -> None:
        """Add sensors for discovered sub-devices."""
        if not coordinator.data:
            return

        entities: list[SensorEntity] = []

        # Process zones
        for zone in coordinator.data.get("zones", []):
            zone_id = zone.get("id")
            if zone_id is None:
                continue

            zone_name = zone.get("name", f"Zone {zone_id}").strip()

            for sensor_def in ZONE_SENSORS:
                sensor_key = sensor_def["key"]
                # Check if this data exists for this zone
                if zone.get(sensor_key) is None:
                    continue

                uid = f"{main_device_id}_zone_{zone_id}_{sensor_key}"
                if uid not in created_entities:
                    created_entities.add(uid)
                    entities.append(
                        NexecurSubDeviceSensor(
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

            for sensor_def in KEYPAD_SENSORS:
                sensor_key = sensor_def["key"]
                if keypad.get(sensor_key) is None:
                    continue

                uid = f"{main_device_id}_keypad_{keypad_id}_{sensor_key}"
                if uid not in created_entities:
                    created_entities.add(uid)
                    entities.append(
                        NexecurSubDeviceSensor(
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

            for sensor_def in SIREN_SENSORS:
                sensor_key = sensor_def["key"]
                if siren.get(sensor_key) is None:
                    continue

                uid = f"{main_device_id}_siren_{siren_id}_{sensor_key}"
                if uid not in created_entities:
                    created_entities.add(uid)
                    entities.append(
                        NexecurSubDeviceSensor(
                            coordinator=coordinator,
                            main_device_id=main_device_id,
                            device_type=DEVICE_TYPE_SIREN,
                            device_id=siren_id,
                            device_name=siren_name,
                            sensor_def=sensor_def,
                            initial_data=siren,
                        )
                    )

        if entities:
            _LOGGER.debug("Adding %d sub-device sensors", len(entities))
            async_add_entities(entities)

    # Add entities for data already available
    async_add_sub_device_sensors()

    # Listen for coordinator updates to discover new devices
    coordinator.async_add_listener(async_add_sub_device_sensors)


class NexecurSubDeviceSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for Nexecur sub-device measurements."""

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
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._main_device_id = main_device_id
        self._device_type = device_type
        self._device_id = device_id
        self._device_name = device_name
        self._sensor_key = sensor_def["key"]
        self._initial_data = initial_data

        # Set unique ID
        self._attr_unique_id = f"{main_device_id}_{device_type}_{device_id}_{self._sensor_key}"

        # Configure sensor from definition
        self._attr_name = sensor_def["name"]
        self._attr_device_class = sensor_def.get("device_class")
        self._attr_native_unit_of_measurement = sensor_def.get("unit")
        self._attr_icon = sensor_def.get("icon")
        self._attr_state_class = sensor_def.get("state_class")

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

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        device_data = self._get_device_data()
        return device_data.get(self._sensor_key)

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
