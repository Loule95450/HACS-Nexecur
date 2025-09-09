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
            
            # Extract devices and cameras from site data 
            # Note: We no longer fetch stream URLs here because they expire every 5 seconds
            # Stream URLs will be fetched on-demand by camera entities
            raw_data = state.raw or {}
            devices = raw_data.get("devices", [])
            cameras = raw_data.get("cameras", [])
            camera_devices = {}
            
            # Debug logging to understand the API response structure
            _LOGGER.debug("Nexecur API response keys: %s", list(raw_data.keys()))
            _LOGGER.debug("Nexecur devices count: %d", len(devices))
            _LOGGER.debug("Nexecur cameras count: %d", len(cameras))
            
            # Collect all potential camera devices without testing streams
            # (streams expire every 5 seconds, so we'll fetch them on-demand)
            all_camera_devices = []
            
            # Add devices from cameras array
            for camera in cameras:
                if camera.get("serial"):
                    all_camera_devices.append({
                        "serial": camera["serial"],
                        "info": camera,
                        "source": "cameras"
                    })
            
            # Add devices from devices array
            for device in devices:
                if device.get("serial"):
                    # Check if not already added from cameras
                    if not any(d["serial"] == device["serial"] for d in all_camera_devices):
                        all_camera_devices.append({
                            "serial": device["serial"],
                            "info": device,
                            "source": "devices"
                        })
            
            # Store device info for camera entities (but not stream URLs)
            for device_data in all_camera_devices:
                device_serial = device_data["serial"]
                device_info = device_data["info"]
                source = device_data["source"]
                
                camera_devices[device_serial] = {
                    "device_info": device_info,
                    "source": source
                }
            
            _LOGGER.info("Found %d potential camera devices", len(camera_devices))
            
            data["camera_devices"] = camera_devices
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
