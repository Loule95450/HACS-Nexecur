from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Nexecur camera entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    # Track created entities to avoid duplicates
    created_entities = set()
    
    _LOGGER.info("Setting up Nexecur camera platform")
    
    @callback
    def add_new_cameras():
        """Add new camera entities when their streams are activated."""
        if not coordinator.data:
            _LOGGER.info("No coordinator data available yet")
            return
            
        camera_streams = coordinator.data.get("camera_streams", {})
        _LOGGER.debug("Camera platform: Found %d active camera streams: %s", len(camera_streams), list(camera_streams.keys()))
        
        new_entities = []
        
        for device_serial, stream_data in camera_streams.items():
            if device_serial not in created_entities:
                _LOGGER.info("Creating camera entity for device %s", device_serial)
                new_entities.append(NexecurCamera(coordinator, entry, device_serial, stream_data))
                created_entities.add(device_serial)
        
        if new_entities:
            _LOGGER.info("Adding %d new Nexecur camera(s)", len(new_entities))
            async_add_entities(new_entities)
        else:
            _LOGGER.debug("No new camera entities to add")
    
    # Add any cameras that are already discovered
    add_new_cameras()
    
    # Listen for coordinator updates to add new cameras
    coordinator.async_add_listener(add_new_cameras)

class NexecurCamera(CoordinatorEntity, Camera):
    """Representation of a Nexecur camera."""
    
    _attr_has_entity_name = True
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, coordinator, entry: ConfigEntry, device_serial: str, stream_data: dict) -> None:
        """Initialize the camera."""
        # Initialize Camera first to ensure all required attributes are set
        Camera.__init__(self)
        super().__init__(coordinator)
        
        self._device_serial = device_serial
        self._attr_unique_id = f"nexecur_camera_{entry.data['id_site']}_{device_serial}"
        self._id_site = entry.data["id_site"]
        
        # Set name from device info if available
        device_info = stream_data.get("device_info", {})
        device_name = device_info.get("name") or device_info.get("nom") or f"Camera {device_serial}"
        self._attr_name = device_name

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self._id_site}_{self._device_serial}")},
            "name": self.name,
            "manufacturer": "Nexecur",
            "model": "Camera",
            "via_device": (DOMAIN, str(self._id_site)),
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.last_update_success:
            return False
        
        camera_streams = self.coordinator.data.get("camera_streams", {}) if self.coordinator.data else {}
        return self._device_serial in camera_streams and camera_streams[self._device_serial].get("stream_url") is not None

    @property
    def is_streaming(self) -> bool:
        """Return True if the camera is streaming."""
        return self.available

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        if not self.coordinator.data:
            return None
            
        camera_streams = self.coordinator.data.get("camera_streams", {})
        stream_data = camera_streams.get(self._device_serial, {})
        stream_url = stream_data.get("stream_url")
        
        # Log stream URL for debugging (but don't expose full URL for security)
        if stream_url:
            _LOGGER.debug("Providing stream for camera %s", self._device_serial)
        
        return stream_url

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
            
        camera_streams = self.coordinator.data.get("camera_streams", {})
        stream_data = camera_streams.get(self._device_serial, {})
        device_info = stream_data.get("device_info", {})
        
        return {
            "device_serial": self._device_serial,
            "has_stream": bool(stream_data.get("stream_url")),
            "device_type": device_info.get("type"),
            "streaming_enabled": device_info.get("streaming_enabled"),
            "source": stream_data.get("source"),
        }

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        # RTSP streams don't typically provide still images directly
        # Home Assistant will handle extracting frames from the stream
        return None