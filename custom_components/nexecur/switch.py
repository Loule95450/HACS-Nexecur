from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN
from .nexecur_api import NexecurClient

_LOGGER = logging.getLogger(__name__)

# Stream is valid for 5 seconds, but can only be requested every 30 seconds
STREAM_AUTO_OFF_DELAY = 30  # seconds

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Nexecur camera stream switch entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: NexecurClient = data["client"]
    coordinator = data["coordinator"]
    
    # Track created entities to avoid duplicates
    created_entities = set()
    
    _LOGGER.info("Setting up Nexecur camera stream switch platform")
    
    @callback
    def add_new_switches():
        """Add new camera stream switch entities when discovered."""
        if not coordinator.data:
            _LOGGER.info("No coordinator data available yet for switches")
            return
            
        # Look for potential camera devices
        all_devices = []
        devices = coordinator.data.get("devices", [])
        cameras = coordinator.data.get("cameras", [])
        
        # Add devices from cameras array
        for camera in cameras:
            if camera.get("serial"):
                all_devices.append({
                    "serial": camera["serial"],
                    "info": camera,
                    "source": "cameras"
                })
        
        # Add devices from devices array
        for device in devices:
            if device.get("serial"):
                # Check if not already added from cameras
                if not any(d["serial"] == device["serial"] for d in all_devices):
                    all_devices.append({
                        "serial": device["serial"],
                        "info": device,
                        "source": "devices"
                    })
        
        _LOGGER.info("Switch platform: Found %d potential camera devices: %s", 
                    len(all_devices), [d["serial"] for d in all_devices])
        
        new_entities = []
        
        for device_data in all_devices:
            device_serial = device_data["serial"]
            if device_serial not in created_entities:
                _LOGGER.info("Creating camera stream switch for device %s", device_serial)
                new_entities.append(NexecurCameraStreamSwitch(client, coordinator, entry, device_serial, device_data))
                created_entities.add(device_serial)
        
        if new_entities:
            _LOGGER.info("Adding %d new Nexecur camera stream switch(es)", len(new_entities))
            async_add_entities(new_entities)
        else:
            _LOGGER.info("No new camera stream switch entities to add")
    
    # Add any switches that are already discovered
    add_new_switches()
    
    # Listen for coordinator updates to add new switches
    coordinator.async_add_listener(add_new_switches)

class NexecurCameraStreamSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to control camera stream activation for a Nexecur camera."""
    
    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, client: NexecurClient, coordinator, entry: ConfigEntry, device_serial: str, device_data: dict) -> None:
        """Initialize the camera stream switch."""
        super().__init__(coordinator)
        
        self._client = client
        self._device_serial = device_serial
        self._device_data = device_data
        self._attr_unique_id = f"nexecur_stream_switch_{entry.data['id_site']}_{device_serial}"
        self._id_site = entry.data["id_site"]
        self._auto_off_timer = None
        
        # Set name from device info
        device_info = device_data.get("info", {})
        device_name = device_info.get("name") or device_info.get("nom") or f"Camera {device_serial}"
        self._attr_name = f"Allumer {device_name}"
        self._device_name = device_name

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self._id_site}_{self._device_serial}")},
            "name": self._device_name,
            "manufacturer": "Nexecur",
            "model": "Camera",
            "via_device": (DOMAIN, str(self._id_site)),
        }

    @property
    def is_on(self) -> bool:
        """Return True if the stream is active."""
        if not self.coordinator.data:
            return False
        
        stream_switches = self.coordinator.data.get("stream_switches", {})
        return stream_switches.get(self._device_serial, {}).get("is_on", False)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        stream_switches = self.coordinator.data.get("stream_switches", {})
        switch_data = stream_switches.get(self._device_serial, {})
        
        return {
            "device_serial": self._device_serial,
            "stream_url": switch_data.get("stream_url"),
            "stream_expires_at": switch_data.get("expires_at"),
            "last_activated": switch_data.get("last_activated"),
            "device_source": self._device_data.get("source"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the camera stream."""
        _LOGGER.info("Activating camera stream for device %s", self._device_serial)
        
        try:
            # Request stream from API
            stream_url = await self._client.async_get_stream(self._device_serial)
            
            if stream_url:
                # Update coordinator data with the new stream
                if not self.coordinator.data:
                    self.coordinator.data = {}
                
                if "stream_switches" not in self.coordinator.data:
                    self.coordinator.data["stream_switches"] = {}
                
                if "camera_streams" not in self.coordinator.data:
                    self.coordinator.data["camera_streams"] = {}
                
                import time
                current_time = time.time()
                
                # Update switch state
                self.coordinator.data["stream_switches"][self._device_serial] = {
                    "is_on": True,
                    "stream_url": stream_url,
                    "last_activated": current_time,
                    "expires_at": current_time + STREAM_AUTO_OFF_DELAY,
                }
                
                # Update camera stream data
                self.coordinator.data["camera_streams"][self._device_serial] = {
                    "stream_url": stream_url,
                    "device_info": self._device_data.get("info", {}),
                    "source": self._device_data.get("source"),
                }
                
                _LOGGER.info("✓ Camera stream activated for device %s", self._device_serial)
                
                # Schedule auto-off after 30 seconds
                if self._auto_off_timer:
                    self._auto_off_timer()  # Cancel existing timer
                
                self._auto_off_timer = async_call_later(
                    self.hass, STREAM_AUTO_OFF_DELAY, self._async_auto_turn_off
                )
                
            else:
                _LOGGER.warning("Failed to get stream URL for device %s", self._device_serial)
                
        except Exception as err:
            _LOGGER.error("Error activating stream for device %s: %s", self._device_serial, err)
            
        # Update all entities
        self.coordinator.async_update_listeners()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the camera stream."""
        _LOGGER.info("Deactivating camera stream for device %s", self._device_serial)
        
        # Cancel auto-off timer if running
        if self._auto_off_timer:
            self._auto_off_timer()
            self._auto_off_timer = None
        
        # Update coordinator data
        if self.coordinator.data:
            stream_switches = self.coordinator.data.get("stream_switches", {})
            if self._device_serial in stream_switches:
                stream_switches[self._device_serial]["is_on"] = False
                stream_switches[self._device_serial]["stream_url"] = None
            
            # Remove from camera streams
            camera_streams = self.coordinator.data.get("camera_streams", {})
            if self._device_serial in camera_streams:
                del camera_streams[self._device_serial]
        
        # Update all entities
        self.coordinator.async_update_listeners()

    async def _async_auto_turn_off(self, *args) -> None:
        """Automatically turn off the switch after timeout."""
        _LOGGER.info("Auto-turning off camera stream for device %s after %d seconds", 
                    self._device_serial, STREAM_AUTO_OFF_DELAY)
        await self.async_turn_off()