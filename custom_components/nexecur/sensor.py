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
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS, UnitOfTemperature
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

            # Battery sensor
            battery_uid = f"{main_device_id}_zone_{zone_id}_battery"
            if battery_uid not in created_entities and zone.get("chargeValue") is not None:
                created_entities.add(battery_uid)
                entities.append(
                    NexecurSubDeviceSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_ZONE,
                        device_id=zone_id,
                        device_name=zone.get("name", f"Zone {zone_id}"),
                        sensor_type="battery",
                        zone_data=zone,
                    )
                )

            # Signal sensor
            signal_uid = f"{main_device_id}_zone_{zone_id}_signal"
            if signal_uid not in created_entities and zone.get("realSignal") is not None:
                created_entities.add(signal_uid)
                entities.append(
                    NexecurSubDeviceSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_ZONE,
                        device_id=zone_id,
                        device_name=zone.get("name", f"Zone {zone_id}"),
                        sensor_type="signal",
                        zone_data=zone,
                    )
                )

            # Temperature sensor
            temp_uid = f"{main_device_id}_zone_{zone_id}_temperature"
            if temp_uid not in created_entities and zone.get("temperature") is not None:
                created_entities.add(temp_uid)
                entities.append(
                    NexecurSubDeviceSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_ZONE,
                        device_id=zone_id,
                        device_name=zone.get("name", f"Zone {zone_id}"),
                        sensor_type="temperature",
                        zone_data=zone,
                    )
                )

        # Process keypads
        for keypad in coordinator.data.get("keypads", []):
            keypad_id = keypad.get("id")
            if keypad_id is None:
                continue

            # Battery sensor
            battery_uid = f"{main_device_id}_keypad_{keypad_id}_battery"
            if battery_uid not in created_entities and keypad.get("chargeValue") is not None:
                created_entities.add(battery_uid)
                entities.append(
                    NexecurSubDeviceSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_KEYPAD,
                        device_id=keypad_id,
                        device_name=keypad.get("name", f"Keypad {keypad_id}"),
                        sensor_type="battery",
                        zone_data=keypad,
                    )
                )

            # Signal sensor
            signal_uid = f"{main_device_id}_keypad_{keypad_id}_signal"
            if signal_uid not in created_entities and keypad.get("realSignal") is not None:
                created_entities.add(signal_uid)
                entities.append(
                    NexecurSubDeviceSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_KEYPAD,
                        device_id=keypad_id,
                        device_name=keypad.get("name", f"Keypad {keypad_id}"),
                        sensor_type="signal",
                        zone_data=keypad,
                    )
                )

            # Temperature sensor (if available)
            temp_uid = f"{main_device_id}_keypad_{keypad_id}_temperature"
            if temp_uid not in created_entities and keypad.get("temperature") is not None:
                created_entities.add(temp_uid)
                entities.append(
                    NexecurSubDeviceSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_KEYPAD,
                        device_id=keypad_id,
                        device_name=keypad.get("name", f"Keypad {keypad_id}"),
                        sensor_type="temperature",
                        zone_data=keypad,
                    )
                )

        # Process sirens
        for siren in coordinator.data.get("sirens", []):
            siren_id = siren.get("id")
            if siren_id is None:
                continue

            # Battery sensor
            battery_uid = f"{main_device_id}_siren_{siren_id}_battery"
            if battery_uid not in created_entities and siren.get("chargeValue") is not None:
                created_entities.add(battery_uid)
                entities.append(
                    NexecurSubDeviceSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_SIREN,
                        device_id=siren_id,
                        device_name=siren.get("name", f"Siren {siren_id}"),
                        sensor_type="battery",
                        zone_data=siren,
                    )
                )

            # Signal sensor
            signal_uid = f"{main_device_id}_siren_{siren_id}_signal"
            if signal_uid not in created_entities and siren.get("realSignal") is not None:
                created_entities.add(signal_uid)
                entities.append(
                    NexecurSubDeviceSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_SIREN,
                        device_id=siren_id,
                        device_name=siren.get("name", f"Siren {siren_id}"),
                        sensor_type="signal",
                        zone_data=siren,
                    )
                )

            # Temperature sensor (if available)
            temp_uid = f"{main_device_id}_siren_{siren_id}_temperature"
            if temp_uid not in created_entities and siren.get("temperature") is not None:
                created_entities.add(temp_uid)
                entities.append(
                    NexecurSubDeviceSensor(
                        coordinator=coordinator,
                        main_device_id=main_device_id,
                        device_type=DEVICE_TYPE_SIREN,
                        device_id=siren_id,
                        device_name=siren.get("name", f"Siren {siren_id}"),
                        sensor_type="temperature",
                        zone_data=siren,
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
        sensor_type: str,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._main_device_id = main_device_id
        self._device_type = device_type
        self._device_id = device_id
        self._device_name = device_name
        self._sensor_type = sensor_type
        self._initial_data = zone_data

        # Set unique ID
        self._attr_unique_id = f"{main_device_id}_{device_type}_{device_id}_{sensor_type}"

        # Configure sensor based on type
        if sensor_type == "battery":
            self._attr_name = "Battery"
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_icon = "mdi:battery"
        elif sensor_type == "signal":
            self._attr_name = "Signal Strength"
            self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS
            self._attr_icon = "mdi:signal"
        elif sensor_type == "temperature":
            self._attr_name = "Temperature"
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_icon = "mdi:thermometer"

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

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor value."""
        device_data = self._get_device_data()

        if self._sensor_type == "battery":
            return device_data.get("chargeValue")
        elif self._sensor_type == "signal":
            return device_data.get("realSignal")
        elif self._sensor_type == "temperature":
            return device_data.get("temperature")

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        device_data = self._get_device_data()
        attrs: dict[str, Any] = {
            "device_type": self._device_type,
            "device_id": self._device_id,
        }

        # Add battery charge status
        if self._sensor_type == "battery":
            attrs["charge_status"] = device_data.get("charge", "unknown")

        # Add signal type
        if self._sensor_type == "signal":
            attrs["signal_type"] = device_data.get("signalType", "unknown")

        # Add detector-specific attributes for zones
        if self._device_type == DEVICE_TYPE_ZONE:
            attrs["detector_type"] = device_data.get("detectorType", "unknown")
            attrs["model"] = device_data.get("model")
            attrs["version"] = device_data.get("version")

        return attrs

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.data:
            return False

        device_data = self._get_device_data()
        status = device_data.get("status", "offline")
        return status == "online"
