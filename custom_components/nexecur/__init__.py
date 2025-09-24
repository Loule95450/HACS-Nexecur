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
            
            # Start with existing coordinator data to preserve switch states
            data = coordinator.data.copy() if coordinator.data else {}
            
            # Update with current panel status
            data.update({
                "panel_status": state.status, 
                "panel_sp1_available": state.panel_sp1_available,
                "panel_sp2_available": state.panel_sp2_available,
                **(state.raw or {})
            })
            
            # Extract devices and cameras from site data (but don't auto-fetch streams)
            raw_data = state.raw or {}
            devices = raw_data.get("devices", [])
            cameras = raw_data.get("cameras", [])
            
            # Debug logging to understand the API response structure
            _LOGGER.debug("Nexecur API response keys: %s", list(raw_data.keys()))
            _LOGGER.debug("Nexecur devices count: %d", len(devices))
            _LOGGER.debug("Nexecur cameras count: %d", len(cameras))
            
            # Initialize stream data if not present
            if "camera_streams" not in data:
                data["camera_streams"] = {}
            if "stream_switches" not in data:
                data["stream_switches"] = {}
                
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
