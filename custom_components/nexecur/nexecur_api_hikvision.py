"""Hikvision/GuardingVision API client for Nexecur alarm systems."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)

GLOBAL_API_URL = "https://apiieu.guardingvision.com"


class NexecurError(Exception):
    """Base exception for Nexecur API errors."""


class NexecurAuthError(NexecurError):
    """Authentication error."""


@dataclass
class NexecurState:
    """Represents the current state of the alarm."""
    status: int  # 0 = disarmed, 1 = armed_home/stay, 2 = armed_away
    panel_sp1_available: bool
    panel_sp2_available: bool
    raw: Dict[str, Any]


class NexecurHikvisionClient:
    """Client for the Hikvision/GuardingVision cloud API."""

    def __init__(
        self,
        phone: str,
        password: str,
        country_code: str = "33",
        ssid: str = "",
        device_name: str = "Home Assistant",
        session: Optional[ClientSession] = None,
    ) -> None:
        self._account = self._format_account(country_code, phone)
        self._password = password
        self._ssid = ssid
        self._device_name = device_name
        self._feature_code = self._generate_feature_code()
        self._session: Optional[ClientSession] = session
        self._base_url = GLOBAL_API_URL
        self._session_id: str = ""
        self._user_info: Dict[str, Any] = {}
        self._security_info: Dict[str, Any] = {}
        self._devices: List[Dict[str, Any]] = []
        self._current_device_serial: str = ""
        self._last_known_state: Optional[NexecurState] = None

    @staticmethod
    def _format_account(country_code: str, account: str) -> str:
        """Format account (phone or email) for API.

        If the account contains '@', it's an email and returned as-is.
        Otherwise, it's a phone number and formatted with country code.
        Note: For French phone numbers, this API expects the full number
        WITH the leading 0. Example: 33 + 0612345678 = 330612345678
        """
        clean_account = account.strip()

        # If it's an email, return as-is (no country code)
        if "@" in clean_account:
            return clean_account

        # It's a phone number, format with country code
        clean_phone = clean_account.replace(" ", "").replace("-", "").replace(".", "")
        clean_code = country_code.strip().lstrip("+")
        return f"{clean_code}{clean_phone}"

    @staticmethod
    def _generate_feature_code() -> str:
        """Generate a unique feature code."""
        return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

    @staticmethod
    def _md5(s: str) -> str:
        """Compute MD5 hash of a string."""
        return hashlib.md5(s.encode()).hexdigest()

    def _get_headers(self) -> Dict[str, str]:
        """Get standard API headers."""
        headers = {
            "Host": "apiieu.guardingvision.com",
            "appId": "Nexecur",
            "lang": "fr-FR",
            "clientType": "1183",  # iOS
            "User-Agent": "HikConnect/1.0.2 (iPhone; iOS 26.2; Scale/3.00)",
            "clientVersion": "1.0.2.20250404",
            "ssid": self._ssid,  # WiFi network name
            "netType": "WIFI",
            "Connection": "keep-alive",
            "Accept-Language": "fr-FR;q=1, io-FR;q=0.9",
            "featureCode": self._feature_code,
            "osVersion": "26.2",
            "Accept": "*/*",
        }
        if self._session_id:
            headers["sessionId"] = self._session_id
        if "customno" in self._user_info:
            headers["customno"] = self._user_info["customno"]
        if "areaId" in self._user_info:
            headers["areaId"] = str(self._user_info["areaId"])
        return headers

    async def _session_ensure(self) -> ClientSession:
        """Ensure a valid session exists."""
        if self._session is None or self._session.closed:
            self._session = ClientSession()
        return self._session

    async def async_close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def async_login(self) -> None:
        """Authenticate with the Hikvision cloud."""
        session = await self._session_ensure()
        url = f"{self._base_url}/v3/users/login/v2"

        data = {
            "account": self._account,
            "password": self._md5(self._password),
            "featureCode": self._feature_code,
            "cuName": "aVBob25l",  # Base64 for "iPhone"
            "pushExtJson": '{\n  "language" : "zh"\n}',
            "pushRegisterJson": "[]",
            "bizType": "",
            "imageCode": "",
            "latitude": "",
            "longitude": "",
            "redirect": "",
            "smsCode": "",
            "smsToken": "",
        }

        _LOGGER.debug("Logging in to Hikvision cloud with account: %s", self._account)

        try:
            async with session.post(url, data=data, headers=self._get_headers(), timeout=30) as resp:
                resp.raise_for_status()
                res_json = await resp.json()

            _LOGGER.debug("Login response: %s", res_json)

            meta = res_json.get("meta", {})
            if str(meta.get("code")) != "200":
                error_msg = meta.get("message", "Unknown error")
                _LOGGER.error("Login failed: %s", error_msg)
                raise NexecurAuthError(f"Login failed: {error_msg}")

            self._session_id = res_json["loginSession"]["sessionId"]
            self._user_info = res_json.get("loginUser", {})

            # Update base URL if redirected
            login_area = res_json.get("loginArea", {})
            if login_area.get("apiDomain"):
                domain = login_area["apiDomain"]
                self._base_url = f"https://{domain}" if not domain.startswith("http") else domain

            _LOGGER.info("Hikvision login successful for user: %s", self._user_info.get("username", "unknown"))

            # Fetch devices
            await self._fetch_devices()

        except NexecurAuthError:
            raise
        except Exception as err:
            _LOGGER.error("Login error: %s", err)
            raise NexecurAuthError(f"Login error: {err}") from err

    async def _fetch_devices(self) -> None:
        """Fetch the list of devices from the cloud."""
        session = await self._session_ensure()
        url = f"{self._base_url}/v3/userdevices/v1/devices/pagelist"
        params = {
            "groupId": -1,
            "limit": 20,
            "offset": 0,
            "filter": "CLOUD,TIME_PLAN,CONNECTION,SWITCH,STATUS,WIFI,STATUS_EXT,NODISTURB,P2P,TTS,KMS,HIDDNS",
        }

        try:
            async with session.get(url, params=params, headers=self._get_headers(), timeout=30) as resp:
                resp.raise_for_status()
                data = await resp.json()

            self._devices = data.get("deviceInfos", [])
            if self._devices:
                self._current_device_serial = self._devices[0].get("deviceSerial", "")
                _LOGGER.info("Found %d device(s). Primary: %s", len(self._devices), self._current_device_serial)
            else:
                _LOGGER.warning("No devices found in account")

        except Exception as err:
            _LOGGER.error("Error fetching devices: %s", err)
            raise NexecurError(f"Error fetching devices: {err}") from err

    async def _get_security_info(self, device_serial: str) -> tuple[Optional[str], Optional[str]]:
        """Fetch security info (nonce, realm, salts) from the device."""
        username = self._user_info.get("username", "")
        payload = {
            "GetUserInfoByType": {
                "mode": "userName",
                "UserNameMode": {"userName": username},
            }
        }

        uri = "/ISAPI/Security/CloudUserManage/users/byType?format=json"
        _LOGGER.debug("Fetching security info for device %s...", device_serial)

        response = await self._send_isapi(device_serial, "POST", uri, payload)

        raw_data = response.get("data", "")
        meta = response.get("meta", {})
        if meta.get("code") == 200 and raw_data:
            # Parse the response
            if "HTTP/1.1 200 OK" in raw_data:
                body_match = re.search(r"\r\n\r\n({.*})", raw_data, re.DOTALL)
                json_body = body_match.group(1) if body_match else raw_data
            else:
                json_body = raw_data

            try:
                data_obj = json.loads(json_body)
                nonce = data_obj.get("nonce")
                realm = data_obj.get("realm", "DVRNVRDVS")

                # Extract salts
                salt = None
                salt2 = None
                auth_hash = None
                if "List" in data_obj and len(data_obj["List"]) > 0:
                    cum = data_obj["List"][0].get("CloudUserManage", {})
                    salt = cum.get("salt")
                    salt2 = cum.get("salt2")
                    auth_hash = cum.get("userNameSessionAuthInfo")

                self._security_info = {
                    "nonce": nonce,
                    "realm": realm,
                    "salt": salt,
                    "salt2": salt2,
                    "auth_hash": auth_hash,
                }

                _LOGGER.debug("Security info obtained - Nonce: %s, Realm: %s", nonce, realm)
                return nonce, realm

            except json.JSONDecodeError as err:
                _LOGGER.error("Failed to parse security info JSON: %s", err)

        _LOGGER.warning("Failed to retrieve security info")
        return None, None

    def _calculate_digest_auth(self, method: str, uri: str, nonce: str, realm: str) -> str:
        """Calculate digest authentication header."""
        username = self._user_info.get("username", self._account)

        # Derive password using salts
        auth_password = self._security_info.get("auth_hash")
        salt1 = self._security_info.get("salt")
        salt2 = self._security_info.get("salt2")

        if not auth_password and salt1 and salt2:
            # Compute salted hash
            md5_pass = hashlib.md5(self._password.encode()).hexdigest().lower()
            h1_input = f"{username}{salt1}{md5_pass}"
            h1 = hashlib.sha256(h1_input.encode()).hexdigest().lower()

            h2_input = f"{username}{salt2}{h1}"
            auth_password = hashlib.sha256(h2_input.encode()).hexdigest().lower()

        if not auth_password:
            auth_password = self._password

        # Standard Digest Authentication
        ha1 = hashlib.md5(f"{username}:{realm}:{auth_password}".encode()).hexdigest().lower()
        ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest().lower()
        response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest().lower()

        return (
            f'Digest username="{username}", realm="{realm}", nonce="{nonce}", '
            f'uri="{uri}", response="{response}", UserType="Operator"'
        )

    async def _send_isapi(
        self,
        device_serial: str,
        method: str,
        uri: str,
        payload: Optional[Dict[str, Any]] = None,
        digest_auth: Optional[str] = None,
        _retry: bool = True,
    ) -> Dict[str, Any]:
        """Send an ISAPI command through the cloud tunnel."""
        session = await self._session_ensure()
        tunnel_url = f"{self._base_url}/v3/userdevices/v1/isapi"

        inner_headers = f"{method} {uri} HTTP/1.1\r\n"
        inner_headers += "UserType: Operator\r\n"
        if digest_auth:
            inner_headers += f"Authorization: {digest_auth}\r\n"
        inner_headers += "\r\n"

        inner_body = json.dumps(payload) if payload else ""
        api_data = inner_headers + inner_body

        body_params = {
            "deviceSerial": device_serial,
            "apiKey": "todo",
            "apiData": api_data,
        }

        _LOGGER.debug("ISAPI tunnel request: %s %s", method, uri)

        try:
            async with session.post(tunnel_url, data=body_params, headers=self._get_headers(), timeout=30) as resp:
                # Handle session expiration (401)
                if resp.status == 401 and _retry:
                    _LOGGER.warning("Session expired (401), attempting re-authentication...")
                    self._session_id = ""  # Reset session
                    try:
                        await self.async_login()  # Re-authenticate
                        # Verify login succeeded
                        if not self._session_id:
                            _LOGGER.error("Re-authentication failed: no session ID obtained")
                            return {"meta": {"code": 401}, "data": "", "error": "Re-authentication failed: no session ID"}
                    except Exception as login_err:
                        _LOGGER.error("Re-authentication failed: %s", login_err)
                        return {"meta": {"code": 401}, "data": "", "error": f"Re-authentication failed: {login_err}"}
                    # Retry once after successful re-authentication
                    return await self._send_isapi(device_serial, method, uri, payload, digest_auth, _retry=False)
                
                resp.raise_for_status()
                return await resp.json()
        except asyncio.TimeoutError:
            _LOGGER.error("ISAPI tunnel timeout for %s %s", method, uri)
            return {"meta": {"code": 504}, "data": "", "error": "timeout"}
        except Exception as err:
            _LOGGER.error("ISAPI tunnel error: %s", err)
            return {"meta": {"code": 500}, "data": "", "error": str(err)}

    async def _execute_isapi_command(
        self,
        device_serial: str,
        method: str,
        uri: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        """Execute an authenticated ISAPI command."""
        nonce, realm = await self._get_security_info(device_serial)

        auth_header = None
        if nonce and realm:
            auth_header = self._calculate_digest_auth(method, uri, nonce, realm)

        response = await self._send_isapi(device_serial, method, uri, payload, auth_header)

        raw_response = response.get("data", "")
        status_code = 0
        match = re.search(r"HTTP/1\.1 (\d+)", raw_response)
        if match:
            status_code = int(match.group(1))

        if status_code in [200, 201, 204] and "Unauthorized" not in raw_response:
            return True, raw_response

        return False, raw_response

    async def async_get_status(self) -> NexecurState:
        """Get the current alarm status."""
        if not self._session_id:
            await self.async_login()

        if not self._current_device_serial:
            _LOGGER.warning("No device serial available")
            # Return last known state if available
            if self._last_known_state:
                _LOGGER.debug("Returning last known state due to missing device serial")
                return self._last_known_state
            # No device serial and no previous state, raise exception
            raise NexecurError("No device serial available and no previous state available")

        payload = {
            "AlarmHostStatusCond": {
                "communiStatus": True,
                "subSys": True,
                "hostStatus": True,
                "battery": True,
            }
        }

        success, raw_response = await self._execute_isapi_command(
            self._current_device_serial,
            "POST",
            "/ISAPI/SecurityCP/status/host?format=json",
            payload,
        )

        raw_data: Dict[str, Any] = {"devices": self._devices}

        # On failure, return last known state
        if not success:
            _LOGGER.warning("Failed to get status from API, returning last known state")
            if self._last_known_state:
                # Update raw_data but keep the previous status
                last_raw = self._last_known_state.raw or {}
                return NexecurState(
                    status=self._last_known_state.status,
                    panel_sp1_available=self._last_known_state.panel_sp1_available,
                    panel_sp2_available=self._last_known_state.panel_sp2_available,
                    raw={**last_raw, "api_error": True},
                )
            # No previous state available, raise exception for coordinator to handle
            raise NexecurError("Failed to get alarm status and no previous state available")

        # Parse the status from response
        status = 0  # Default: disarmed
        
        try:
            # Find JSON in the response
            json_match = re.search(r"\r\n\r\n({.*})", raw_response, re.DOTALL)
            if json_match:
                status_data = json.loads(json_match.group(1))
                raw_data["status_response"] = status_data

                # Parse subsystem status
                # The API returns "arming" field with values: "disarm", "away", "stay"
                sub_sys_list = status_data.get("AlarmHostStatus", {}).get("SubSysList", [])
                if sub_sys_list:
                    for sub_sys in sub_sys_list:
                        arm_status = sub_sys.get("SubSys", {}).get("arming", "")
                        _LOGGER.debug("SubSys arming status: %s", arm_status)
                        if arm_status == "away":
                            status = 2
                            break
                        elif arm_status == "stay":
                            status = 1
                            break
                        elif arm_status == "disarm":
                            status = 0

                _LOGGER.debug("Parsed alarm status: %d", status)
        except (json.JSONDecodeError, KeyError) as err:
            _LOGGER.warning("Could not parse status response: %s", err)
            # On parsing error, use last known state
            if self._last_known_state:
                _LOGGER.debug("Using last known state due to parsing error")
                return self._last_known_state
            # No previous state available, raise exception
            raise NexecurError(f"Failed to parse status response and no previous state available: {err}")

        # Create new state
        new_state = NexecurState(
            status=status,
            panel_sp1_available=True,
            panel_sp2_available=True,
            raw=raw_data,
        )
        
        # Save as last known state
        self._last_known_state = new_state

        return new_state

    async def async_set_armed(self, armed: bool) -> None:
        """Arm or disarm the alarm (legacy method)."""
        if armed:
            await self.async_set_armed_away()
        else:
            await self._disarm()

    async def async_set_armed_home(self) -> None:
        """Set alarm to home/stay mode."""
        if not self._session_id:
            await self.async_login()

        if not self._current_device_serial:
            raise NexecurError("No device available")

        payload = {"subSysArmList": [{"armType": "stay", "operationMode": "all"}]}

        success, response = await self._execute_isapi_command(
            self._current_device_serial,
            "POST",
            "/ISAPI/SecurityCP/ArmAndsystemFault?format=json",
            payload,
        )

        if not success:
            _LOGGER.error("Failed to arm stay: %s", response)
            raise NexecurError("Failed to arm stay")

        _LOGGER.info("Alarm armed in stay mode")

    async def async_set_armed_away(self) -> None:
        """Set alarm to away mode."""
        if not self._session_id:
            await self.async_login()

        if not self._current_device_serial:
            raise NexecurError("No device available")

        payload = {"subSysArmList": [{"armType": "away", "operationMode": "all"}]}

        success, response = await self._execute_isapi_command(
            self._current_device_serial,
            "POST",
            "/ISAPI/SecurityCP/ArmAndsystemFault?format=json",
            payload,
        )

        if not success:
            _LOGGER.error("Failed to arm away: %s", response)
            raise NexecurError("Failed to arm away")

        _LOGGER.info("Alarm armed in away mode")

    async def _disarm(self) -> None:
        """Disarm the alarm."""
        if not self._session_id:
            await self.async_login()

        if not self._current_device_serial:
            raise NexecurError("No device available")

        payload = {"SubSysList": [{"SubSys": {"id": 1}}]}

        success, response = await self._execute_isapi_command(
            self._current_device_serial,
            "PUT",
            "/ISAPI/SecurityCP/control/disarm?format=json",
            payload,
        )

        if not success:
            _LOGGER.error("Failed to disarm: %s", response)
            raise NexecurError("Failed to disarm")

        _LOGGER.info("Alarm disarmed")

    async def async_get_stream(self, device_serial: str) -> Optional[str]:
        """Get stream URL for a camera device.

        Note: Camera streaming is not yet implemented for Hikvision.
        This is a placeholder for future implementation.
        """
        _LOGGER.warning("Camera streaming not yet implemented for Hikvision panels")
        return None

    @property
    def id_device(self) -> str:
        """Return the current device serial."""
        return self._current_device_serial

    @property
    def token(self) -> str:
        """Return the session ID."""
        return self._session_id

    @property
    def devices(self) -> List[Dict[str, Any]]:
        """Return the list of devices."""
        return self._devices
