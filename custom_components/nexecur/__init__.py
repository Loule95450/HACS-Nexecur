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

    # Persist id_device to the entry for reuse
    if not entry.data.get("id_device") and getattr(client, "id_device", None):
        hass.config_entries.async_update_entry(entry, data={**entry.data, "id_device": client.id_device})

    async def async_update():
        try:
            state = await client.async_get_status()
            # Coordinator data is a dict for easy consumption by entities
            return {"panel_status": state.status, **(state.raw or {})}
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
