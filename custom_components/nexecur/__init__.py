from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, PLATFORMS
from .nexecur_api import NexecurClient, NexecurError

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    client = NexecurClient(
        id_site=entry.data["id_site"],
        password=entry.data["password"],
        device_name=entry.data.get("device_name", "Home Assistant"),
        session=session,
    )
    await client.async_login()

    # Log requested values on reload/setup for debugging
    try:
        _LOGGER.info(
            "Nexecur debug: token=%s id_site=%s password=%s id_device=%s pin=%s deviceName=%s",
            getattr(client, "token", ""),
            entry.data.get("id_site"),
            entry.data.get("password"),
            getattr(client, "id_device", ""),
            entry.data.get("password"),  # pin is same as password in our client
            entry.data.get("device_name", "Home Assistant"),
        )
    except Exception:  # pragma: no cover - logging shouldn't break setup
        pass

    # Persist id_device to the entry for reuse
    if not entry.data.get("id_device") and getattr(client, "id_device", None):
        hass.config_entries.async_update_entry(entry, data={**entry.data, "id_device": client.id_device})

    async def async_update():
        try:
            state = await client.async_get_status()
            # Coordinator data is a dict for easy consumption by entities
            data = {"panel_status": state.status, **(state.raw or {})}
            
            # Extract devices and cameras from site data and fetch stream URLs
            raw_data = state.raw or {}
            devices = raw_data.get("devices", [])
            cameras = raw_data.get("cameras", [])
            camera_streams = {}
            
            # Check panel streaming capability
            panel_streaming = raw_data.get("panel_streaming", 0)
            streaming_available = raw_data.get("streaming_available", 0)
            
            if panel_streaming and streaming_available:
                # Process explicit cameras array first
                for camera in cameras:
                    camera_serial = camera.get("serial")
                    if camera_serial:
                        stream_url = await client.async_get_stream(camera_serial)
                        if stream_url:
                            camera_streams[camera_serial] = {
                                "stream_url": stream_url,
                                "device_info": camera,
                                "source": "cameras"
                            }
                            _LOGGER.debug("Found camera stream for device %s: %s", camera_serial, stream_url)
                
                # Also check devices for any that might have streaming capability
                for device in devices:
                    device_serial = device.get("serial")
                    device_name = device.get("name", "").lower()
                    
                    # Skip if already found in cameras array
                    if device_serial and device_serial not in camera_streams:
                        # Check if this looks like a camera device
                        if ("camera" in device_name or "cam" in device_name or 
                            device.get("streaming_enabled") or device.get("type", "").lower() in ["camera", "cam"]):
                            stream_url = await client.async_get_stream(device_serial)
                            if stream_url:
                                camera_streams[device_serial] = {
                                    "stream_url": stream_url,
                                    "device_info": device,
                                    "source": "devices"
                                }
                                _LOGGER.debug("Found device stream for device %s: %s", device_serial, stream_url)
            
            data["camera_streams"] = camera_streams
            data["devices"] = devices
            data["cameras"] = cameras
            
            return data
        except NexecurError as err:
            _LOGGER.warning("Nexecur update failed: %s", err)
            raise

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update,
        update_interval=SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
