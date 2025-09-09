from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Optional, Set

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .nexecur_api import NexecurClient, NexecurError

_LOGGER = logging.getLogger(__name__)

# Stream URLs are valid ~30s. Refresh a bit earlier.
REFRESH_INTERVAL = timedelta(seconds=25)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    client: NexecurClient = data["client"]
    coordinator = data["coordinator"]

    known_serials: Set[str] = data.setdefault("camera_known_serials", set())

    async def discover_and_add() -> None:
        site = coordinator.data or {}
        cameras = site.get("cameras") or []
        new_entities: list[NexecurCamera] = []
        for cam in cameras:
            serial = cam.get("serial") or cam.get("device_serial") or cam.get("id")
            if not serial or serial in known_serials:
                continue
            name = cam.get("name") or f"Nexecur Camera {serial}"
            known_serials.add(serial)
            new_entities.append(NexecurCamera(client, entry, serial, name))

        if new_entities:
            async_add_entities(new_entities)

    # Initial discovery
    await discover_and_add()

    # Keep discovering on coordinator updates (new cameras appearing later)
    remove_listener = coordinator.async_add_listener(lambda: entry.hass.async_create_task(discover_and_add()))
    entry.async_on_unload(remove_listener)


class NexecurCamera(CoordinatorEntity, Camera):
    _attr_should_poll = False
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, client: NexecurClient, entry: ConfigEntry, serial: str, name: str) -> None:
        # Bind to the main coordinator so attributes like camera list get refreshed via site call
        coordinator = entry.hass.data[DOMAIN][entry.entry_id]["coordinator"]
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._client = client
        self._serial = serial
        self._attr_name = name
        self._attr_unique_id = f"nexecur_camera_{entry.data['id_site']}_{serial}"
        self._last_url: Optional[str] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._available = True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Start background refresh loop
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def async_will_remove_from_hass(self) -> None:
        if self._refresh_task:
            self._refresh_task.cancel()
            self._refresh_task = None

    async def _refresh_loop(self) -> None:
        try:
            while True:
                try:
                    url = await self._client.async_get_stream(self._serial)
                    if url != self._last_url:
                        self._last_url = url
                        self.async_write_ha_state()
                    self._available = True
                except NexecurError as err:
                    _LOGGER.warning("Stream refresh failed for %s: %s", self._serial, err)
                    self._available = False
                await asyncio.sleep(REFRESH_INTERVAL.total_seconds())
        except asyncio.CancelledError:  # graceful shutdown
            return

    @property
    def available(self) -> bool:
        return self._available

    @property
    def supported_features(self) -> int:
        # No special features
        return 0

    async def stream_source(self) -> str | None:
        # Home Assistant uses this to feed stream component. Return cached RTSP.
        # If not fetched yet, trigger one fetch.
        if not self._last_url:
            try:
                self._last_url = await self._client.async_get_stream(self._serial)
            except NexecurError as err:
                _LOGGER.error("Unable to obtain initial stream for %s: %s", self._serial, err)
                return None
        return self._last_url

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, f"camera_{self._serial}")},
            "manufacturer": "Nexecur",
            "name": self.name,
        }
