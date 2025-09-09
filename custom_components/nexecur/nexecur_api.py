from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://monnexecur-prd.nexecur.fr"
CONFIG_URI = "/webservices/configuration"
SALT_URI = "/webservices/salt"
SITE_URI = "/webservices/site"
REGISTER_URI = "/webservices/register"
PANEL_STATUS_URI = "/webservices/panel-status"
PANEL_CHECK_STATUS_URI = "/webservices/check-panel-status"
STREAM_URI = "/webservices/stream"

MAX_WAIT_SECONDS = 60

class NexecurError(Exception):
    pass

class NexecurAuthError(NexecurError):
    pass

@dataclass
class NexecurState:
    status: int  # 0 disabled, 1 enabled
    raw: Dict[str, Any]

class NexecurClient:
    def __init__(self, id_site: str, password: str, device_name: str = "Home Assistant", session: Optional[ClientSession] = None) -> None:
        self._id_site = id_site
        # User-provided PIN/password; we also reuse it for the 'pin' field like the TS client
        self._password_plain = password
        self._device_name = device_name
        self._token: str = ""
        self._id_device: str = ""
        self._session: Optional[ClientSession] = session

    async def _session_ensure(self) -> ClientSession:
        if self._session is None or self._session.closed:
            # Fallback session; in HA we prefer passing the shared session from hass
            from aiohttp import ClientSession as _CS  # local import to avoid HA type checker issues
            self._session = _CS()
        return self._session

    async def async_close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def async_login(self) -> None:
        await self._ensure_device()

    async def _ensure_device(self) -> None:
        # If we don't have a token, perform full device registration
        if not self._token:
            salt = await self._get_salt()
            pwd_hash, pin_hash = self._compute_hashes(self._password_plain, salt)
            res = await self._site(pwd_hash, pin_hash)
            # Expect token
            token = res.get("token", "")
            if not token:
                raise NexecurAuthError("No token returned by site API")
            self._token = token
            # Register device to obtain id_device if necessary
            reg = await self._register()
            # Some responses place id_device directly at root
            self._id_device = str(reg.get("id_device") or res.get("id_device") or "")
            if not self._id_device:
                _LOGGER.debug("Register response: %s", reg)
                raise NexecurAuthError("Unable to register device (no id_device)")

    async def async_get_status(self) -> NexecurState:
        await self._ensure_token_valid()
        # Site call returns panel_status
        salt = await self._get_salt()
        pwd_hash, pin_hash = self._compute_hashes(self._password_plain, salt)
        data = await self._site(pwd_hash, pin_hash)
        status = int(data.get("panel_status", 0))
        return NexecurState(status=status, raw=data)

    async def async_set_armed(self, armed: bool) -> None:
        await self._ensure_token_valid()
        await self._panel_status(1 if armed else 0)

    async def async_get_stream(self, serial: str) -> str:
        """Return an RTSP URL for the given camera serial. Token must be valid.
        The URL is short lived (~30s), caller should refresh periodically.
        """
        await self._ensure_token_valid()
        body = {"serial": serial}
        data = await self._post_json(STREAM_URI, json=body, token=self._token or None)
        if data.get("message") != "OK" or data.get("status") != 0:
            raise NexecurError(f"Failed to get stream for {serial}: {data}")
        uri = data.get("uri")
        if not uri:
            raise NexecurError("No URI in stream response")
        return uri

    # --- Low level HTTP helpers ---
    async def _post_json(self, path: str, json: Optional[Dict[str, Any]] = None, token: Optional[str] = None) -> Dict[str, Any]:
        session = await self._session_ensure()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if token:
            headers["X-Auth-Token"] = token
        url = BASE_URL + path
        async with session.post(url, json=json or {}, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
            if isinstance(data, dict) and data.get("status") not in (None, 0):
                # API uses status==0 on success
                _LOGGER.debug("API error on %s: %s", path, data)
            return data if isinstance(data, dict) else {}

    async def _get_salt(self) -> str:
        payload = {
            "id_site": self._id_site,
            "password": self._password_plain,
            "id_device": self._id_device,
            "partage": "1",
            # TS client passes userConfig.pin; we reuse password to match README (single PIN)
            "pin": self._password_plain,
        }
        data = await self._post_json(SALT_URI, json=payload)
        if data.get("message") != "OK" or data.get("status") != 0:
            raise NexecurAuthError("Error while generating salt")
        salt = data.get("salt")
        if not salt:
            raise NexecurAuthError("No salt in response")
        return salt

    def _compute_hashes(self, password: str, salt_b64: str) -> tuple[str, str]:
        # Replicates TS: s_new = password encoded as utf16le; abyte0 = base64(salt); s2 = abyte0 + s_new
        s_new = password.encode("utf-16le")
        abyte0 = base64.b64decode(salt_b64)
        s2 = abyte0 + s_new
        pin_hash = base64.b64encode(hashlib.sha1(s2).digest()).decode()
        pwd_hash = base64.b64encode(hashlib.sha256(s2).digest()).decode()
        return pwd_hash, pin_hash

    async def _site(self, password_hash: str, pin_hash: str) -> Dict[str, Any]:
        payload = {
            "id_site": self._id_site,
            "password": password_hash,
            "id_device": self._id_device,
            "partage": "1",
            "pin": pin_hash,
        }
        data = await self._post_json(SITE_URI, json=payload, token=self._token or None)
        # Update token if provided
        token = data.get("token")
        if token:
            self._token = token
        return data

    async def _register(self) -> Dict[str, Any]:
        body = {
            "alert": "enabled",
            "appname": "Mon+Nexecur",
            "nom": "",
            "badge": "enabled",
            "options": [1],
            "sound": "enabled",
            "id_device": self._id_device,
            "actif": 1,
            "plateforme": "gcm",
            "app_version": "1.15 (30)",
            "device_model": "HomeAssistant",
            "device_name": self._device_name,
            "device_version": "2025.0",
        }
        data = await self._post_json(REGISTER_URI, json=body, token=self._token or None)
        if data.get("status") != 0:
            _LOGGER.debug("Register response: %s", data)
        return data

    async def _panel_status(self, order_status: int) -> None:
        body = {"status": order_status}
        data = await self._post_json(PANEL_STATUS_URI, json=body, token=self._token or None)
        if data.get("message") != "OK" or data.get("status") != 0:
            raise NexecurError("Error while sending panel status")
        # If pending, poll until done or timeout
        if int(data.get("pending", 0)) != 0:
            await self._wait_panel_done()

    async def _wait_panel_done(self) -> None:
        for i in range(MAX_WAIT_SECONDS // 2):
            data = await self._post_json(PANEL_CHECK_STATUS_URI, token=self._token or None)
            if int(data.get("still_pending", 0)) == 0:
                return
            await asyncio.sleep(2)
        raise NexecurError("Operation still pending after timeout")

    async def _ensure_token_valid(self) -> None:
        if not self._token:
            await self._ensure_device()

    # --- Properties ---
    @property
    def id_device(self) -> str:
        return self._id_device

    @property
    def token(self) -> str:
        return self._token
