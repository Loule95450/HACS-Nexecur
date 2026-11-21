from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from aiohttp import ClientError, ClientSession

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
REQUEST_TIMEOUT = 30

# Service statuses meaning the session is gone, and the one meaning the account
# is locked out. Anything else unknown is treated as a temporary unavailability:
# the API is private and an unlisted code is no proof that the PIN is wrong.
SESSION_ERROR_STATUSES = {2, 3, 4}
ACCOUNT_LOCKED_STATUS = 7

# Error codes returned when the panel refuses a command.
ACTION_ERRORS = {
    101: "another action is already running",
    102: "unknown alarm panel",
    103: "the alarm panel is disconnected",
    104: "invalid code",
    105: "the alarm panel rejected the request",
    106: "internal alarm panel error",
}

class NexecurError(Exception):
    pass

class NexecurAuthError(NexecurError):
    pass

class NexecurUnavailableError(NexecurError):
    """The service or the panel is temporarily unavailable."""

class NexecurAccountLockedError(NexecurUnavailableError):
    """Authentication is temporarily blocked; the PIN is not necessarily wrong."""

class NexecurCommandError(NexecurError):
    """An alarm command was rejected or could not be confirmed."""

class NexecurConnectionError(NexecurUnavailableError):
    """The service could not be reached or returned something unusable."""

class NexecurHTTPError(NexecurConnectionError):
    """A request returned a non-success HTTP status."""

    def __init__(self, path: str, status: int) -> None:
        self.status = status
        super().__init__(f"HTTP {status} from {path}")

@dataclass
class NexecurState:
    status: int  # 0 disabled, 1 sp1 enabled, 2 sp2 enabled
    panel_sp1_available: bool  # True if sp1 is available
    panel_sp2_available: bool  # True if sp2 is available
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
        # One alarm order at a time: two concurrent services must never race
        # on the same panel.
        self._command_lock = asyncio.Lock()

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
        panel_sp1_available = bool(int(data.get("panel_sp1", 0)))
        panel_sp2_available = bool(int(data.get("panel_sp2", 0)))
        return NexecurState(
            status=status, 
            panel_sp1_available=panel_sp1_available,
            panel_sp2_available=panel_sp2_available, 
            raw=data
        )

    async def async_set_armed(self, armed: bool) -> None:
        """Disarm, or arm the whole site."""
        await self.async_set_panel_status(1 if armed else 0)

    async def async_set_panel_status(self, status: int) -> None:
        """Send one alarm order: 0 disarmed, 1 full, 2 partial 1, 3 partial 2."""
        if status not in (0, 1, 2, 3):
            raise ValueError(f"Unsupported panel status: {status}")
        async with self._command_lock:
            await self._ensure_token_valid()
            await self._panel_status(status)

    # --- Low level HTTP helpers ---
    async def _post_json(self, path: str, json: Optional[Dict[str, Any]] = None, token: Optional[str] = None) -> Dict[str, Any]:
        session = await self._session_ensure()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if token:
            headers["X-Auth-Token"] = token
        url = BASE_URL + path
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with session.post(url, json=json or {}, headers=headers) as resp:
                    if resp.status < 200 or resp.status >= 300:
                        # Error pages can echo the PIN or the token: never keep the body.
                        resp.release()
                        raise NexecurHTTPError(path, resp.status)
                    data = await resp.json(content_type=None)
        except TimeoutError as err:
            raise NexecurConnectionError(f"Timeout while calling {path}") from err
        except ClientError as err:
            raise NexecurConnectionError(f"Connection failed while calling {path}") from err
        except ValueError as err:
            raise NexecurConnectionError(f"Invalid response from {path}") from err
        # Only the service name and its numeric status: free-form server text
        # and response bodies may carry credentials.
        _LOGGER.debug("Nexecur %s: service status %s", path, data.get("status") if isinstance(data, dict) else "not-a-dict")
        return data if isinstance(data, dict) else {}

    async def _get_salt(self) -> str:
        # The salt is what the PIN is hashed with: this request must never carry
        # the PIN or the password in clear.
        payload = {
            "id_site": self._id_site,
            "id_device": self._id_device,
            "partage": "1",
        }
        data = await self._post_json(SALT_URI, json=payload)
        if data.get("message") != "OK" or data.get("status") != 0:
            # No credential was sent, so a failure here proves nothing about the PIN.
            raise NexecurUnavailableError("Unable to retrieve the authentication salt")
        salt = data.get("salt")
        if not salt:
            raise NexecurConnectionError("No salt in response")
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
        status = data.get("status")
        if status in SESSION_ERROR_STATUSES and self._token:
            # A stale token, not a bad PIN: drop it and authenticate from scratch once.
            self._token = ""
            data = await self._post_json(SITE_URI, json=payload)
            status = data.get("status")
        if status == ACCOUNT_LOCKED_STATUS:
            raise NexecurAccountLockedError(
                "The NEXECUR account is temporarily locked (site status 7)"
            )
        if status in SESSION_ERROR_STATUSES:
            raise NexecurAuthError(
                f"The connection code or PIN was rejected (site status {status})"
            )
        if status not in (0, 10):
            # Unlisted code: report an unavailability rather than claim a wrong PIN.
            raise NexecurUnavailableError(f"NEXECUR is unavailable (site status {status})")
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
        try:
            data = await self._post_json(PANEL_STATUS_URI, json=body, token=self._token or None)
        except NexecurConnectionError as err:
            # The service answers HTTP 500 or drops the connection even after
            # having accepted an order. Resending it could arm or disarm the
            # site twice, so wait for the queue to clear and report instead.
            _LOGGER.warning(
                "Nexecur did not confirm an alarm order; it will NOT be resent: %s", err
            )
            try:
                await self._wait_panel_done()
            except NexecurError:
                pass
            raise NexecurCommandError(
                "The order was sent but the panel did not confirm it"
            ) from err
        status = data.get("status")
        if data.get("message") != "OK" or status != 0:
            message = ACTION_ERRORS.get(status, "the alarm order was rejected")
            raise NexecurCommandError(f"{message} (service status {status})")
        # If pending, poll until done or timeout
        if int(data.get("pending", 0)) != 0:
            await self._wait_panel_done()

    async def _wait_panel_done(self) -> None:
        for i in range(MAX_WAIT_SECONDS // 2):
            data = await self._post_json(PANEL_CHECK_STATUS_URI, token=self._token or None)
            if int(data.get("still_pending", 0)) == 0:
                return
            await asyncio.sleep(2)
        raise NexecurCommandError("The alarm panel did not finish the order in time")

    async def _ensure_token_valid(self) -> None:
        if not self._token:
            await self._ensure_device()

    async def async_get_stream(self, device_serial: str) -> Optional[str]:
        """Get stream URL for a device by its serial number.
        
        Args:
            device_serial: Serial number of the device (camera)
            
        Returns:
            RTSP stream URL if successful, None if failed
        """
        await self._ensure_token_valid()
        
        # Try multiple request formats in case one is expected
        request_variations = [
            {"serial": device_serial},
            {"device": device_serial},
            {"device_serial": device_serial},
            {"id": device_serial},
        ]
        
        for i, payload in enumerate(request_variations):
            try:
                _LOGGER.debug("Requesting stream for device %s (attempt %d) with payload: %s", device_serial, i+1, payload)
                data = await self._post_json(STREAM_URI, json=payload, token=self._token)
                # Never log the response body or the URI: stream URLs may embed credentials
                _LOGGER.debug(
                    "Stream response for device %s (attempt %d): status=%s message=%s has_uri=%s",
                    device_serial, i+1, data.get("status"), data.get("message"), bool(data.get("uri")),
                )

                # Check for success response
                if data.get("message") == "OK" and data.get("status") == 0:
                    stream_url = data.get("uri")
                    if stream_url:
                        _LOGGER.debug("Stream URL found for device %s", device_serial)
                        return stream_url

                # Check for other possible success indicators
                if "uri" in data and data["uri"]:
                    stream_url = data["uri"]
                    _LOGGER.debug("Stream URL found for device %s (no status check)", device_serial)
                    return stream_url

                # If status indicates error, try next variation
                if data.get("status") != 0:
                    _LOGGER.debug("Status error (%s) for device %s attempt %d, trying next format", data.get("status"), device_serial, i+1)
                    continue
                else:
                    # Status is 0 but no URI, this might be the expected format but device doesn't support streaming
                    _LOGGER.debug("Device %s returned OK status but no URI - likely doesn't support streaming", device_serial)
                    return None
                    
            except Exception as err:
                _LOGGER.warning("Exception getting stream for device %s (attempt %d): %s", device_serial, i+1, err)
                if i == len(request_variations) - 1:  # Last attempt
                    return None
                continue
        
        _LOGGER.debug("All stream request formats failed for device %s", device_serial)
        return None

    # --- Properties ---
    @property
    def id_device(self) -> str:
        return self._id_device

    @property
    def token(self) -> str:
        return self._token
