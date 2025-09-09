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
            
            # Debug logging to understand the API response structure
            _LOGGER.info("Nexecur API response keys: %s", list(raw_data.keys()))
            _LOGGER.info("Nexecur devices count: %d", len(devices))
            _LOGGER.info("Nexecur cameras count: %d", len(cameras))
            
            # Log first few devices for structure understanding
            if devices:
                _LOGGER.info("First device example: %s", devices[0])
            if cameras:
                _LOGGER.info("First camera example: %s", cameras[0])
            
            # Check panel streaming capability
            panel_streaming = raw_data.get("panel_streaming", 0)
            streaming_available = raw_data.get("streaming_available", 0)
            _LOGGER.info("Panel streaming: %s, Streaming available: %s", panel_streaming, streaming_available)
            
            # Try to get streams for all devices, regardless of streaming flags
            # This matches the JavaScript example approach
            all_devices_to_test = []
            
            # Add devices from cameras array
            for camera in cameras:
                if camera.get("serial"):
                    all_devices_to_test.append({
                        "serial": camera["serial"],
                        "info": camera,
                        "source": "cameras"
                    })
            
            # Add devices from devices array
            for device in devices:
                if device.get("serial"):
                    # Check if not already added from cameras
                    if not any(d["serial"] == device["serial"] for d in all_devices_to_test):
                        all_devices_to_test.append({
                            "serial": device["serial"],
                            "info": device,
                            "source": "devices"
                        })
            
            _LOGGER.info("Testing %d devices for streaming capability", len(all_devices_to_test))
            
            # Test each device for streaming capability
            for device_test in all_devices_to_test:
                device_serial = device_test["serial"]
                device_info = device_test["info"]
                source = device_test["source"]
                
                _LOGGER.info("Testing stream for device %s (%s) from %s", 
                           device_serial, device_info.get("name", "Unknown"), source)
                
                stream_url = await client.async_get_stream(device_serial)
                if stream_url:
                    camera_streams[device_serial] = {
                        "stream_url": stream_url,
                        "device_info": device_info,
                        "source": source
                    }
                    _LOGGER.info("✓ Found working stream for device %s: %s", device_serial, stream_url[:50] + "..." if len(stream_url) > 50 else stream_url)
                else:
                    _LOGGER.info("✗ No stream available for device %s", device_serial)
            
            _LOGGER.info("Total working camera streams: %d", len(camera_streams))
            
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
