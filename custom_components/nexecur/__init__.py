from __future__ import annotations

from datetime import timedelta
import logging
from typing import Union

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_ALARM_VERSION,
    CONF_ID_SITE,
    CONF_PASSWORD,
    CONF_DEVICE_NAME,
    CONF_PHONE,
    CONF_COUNTRY_CODE,
    ALARM_VERSION_VIDEOFIED,
    ALARM_VERSION_HIKVISION,
)
from .nexecur_api import NexecurClient, NexecurError
from .nexecur_api_hikvision import NexecurHikvisionClient, NexecurError as HikvisionError

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)

# Type alias for both client types
NexecurClientType = Union[NexecurClient, NexecurHikvisionClient]


def _get_alarm_version(entry: ConfigEntry) -> str:
    """Get the alarm version from entry data, with backward compatibility."""
    # For backward compatibility: if no alarm_version key, assume Videofied
    return entry.data.get(CONF_ALARM_VERSION, ALARM_VERSION_VIDEOFIED)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    alarm_version = _get_alarm_version(entry)

    client: NexecurClientType

    if alarm_version == ALARM_VERSION_HIKVISION:
        # Hikvision client
        client = NexecurHikvisionClient(
            phone=entry.data[CONF_PHONE],
            password=entry.data[CONF_PASSWORD],
            country_code=entry.data.get(CONF_COUNTRY_CODE, "33"),
            device_name=entry.data.get(CONF_DEVICE_NAME, "Home Assistant"),
            session=session,
        )
        await client.async_login()
        _LOGGER.info(
            "Nexecur Hikvision debug: session_id=%s phone=%s",
            client.token[:20] + "..." if client.token else "",
            entry.data.get(CONF_PHONE, "")[:6] + "***",
        )
    else:
        # Videofied client (default)
        client = NexecurClient(
            id_site=entry.data[CONF_ID_SITE],
            password=entry.data[CONF_PASSWORD],
            device_name=entry.data.get(CONF_DEVICE_NAME, "Home Assistant"),
            session=session,
        )
        await client.async_login()

        _LOGGER.info(
            "Nexecur Videofied debug: token=%s id_site=%s id_device=%s",
            getattr(client, "token", "")[:20] + "..." if getattr(client, "token", "") else "",
            entry.data.get(CONF_ID_SITE),
            getattr(client, "id_device", ""),
        )

        # Persist id_device to the entry for reuse (Videofied only)
        if not entry.data.get("id_device") and getattr(client, "id_device", None):
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, "id_device": client.id_device}
            )

    async def async_update():
        try:
            state = await client.async_get_status()

            # Start with existing coordinator data to preserve switch states
            data = coordinator.data.copy() if coordinator.data else {}

            # Update with current panel status
            data.update(
                {
                    "panel_status": state.status,
                    "panel_sp1_available": state.panel_sp1_available,
                    "panel_sp2_available": state.panel_sp2_available,
                    "alarm_version": alarm_version,
                    **(state.raw or {}),
                }
            )

            # Extract devices and cameras from site data
            raw_data = state.raw or {}
            devices = raw_data.get("devices", [])
            cameras = raw_data.get("cameras", [])

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
        except (NexecurError, HikvisionError) as err:
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
        "alarm_version": alarm_version,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry to new version."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        # Migration from version 1 to 2: add alarm_version field
        new_data = {**config_entry.data}
        if CONF_ALARM_VERSION not in new_data:
            # Existing entries are Videofied
            new_data[CONF_ALARM_VERSION] = ALARM_VERSION_VIDEOFIED

        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=2
        )
        _LOGGER.info("Migration to version 2 successful")

    return True
