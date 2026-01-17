from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_ALARM_VERSION,
    CONF_ID_SITE,
    CONF_PASSWORD,
    CONF_DEVICE_NAME,
    CONF_PHONE,
    CONF_EMAIL,
    CONF_ACCOUNT,
    CONF_COUNTRY_CODE,
    CONF_SSID,
    CONF_LOGIN_METHOD,
    ALARM_VERSION_VIDEOFIED,
    ALARM_VERSION_HIKVISION,
    LOGIN_METHOD_PHONE,
    LOGIN_METHOD_EMAIL,
)
from .nexecur_api import NexecurClient, NexecurAuthError

# Step 1: Choose alarm version
VERSION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ALARM_VERSION, default=ALARM_VERSION_VIDEOFIED): vol.In(
            {
                ALARM_VERSION_VIDEOFIED: "Videofied (ancienne version)",
                ALARM_VERSION_HIKVISION: "Hikvision (nouvelle version)",
            }
        ),
    }
)

# Step 2a: Videofied credentials
VIDEOFIED_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID_SITE): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_DEVICE_NAME, default="Home Assistant"): str,
    }
)

# Step 2b: Hikvision - Choose login method
HIKVISION_METHOD_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LOGIN_METHOD, default=LOGIN_METHOD_PHONE): vol.In(
            {
                LOGIN_METHOD_PHONE: "Téléphone",
                LOGIN_METHOD_EMAIL: "Email",
            }
        ),
    }
)

# Step 3a: Hikvision - Phone credentials
HIKVISION_PHONE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PHONE): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_COUNTRY_CODE, default="33"): str,
        vol.Optional(CONF_SSID, default=""): str,
        vol.Optional(CONF_DEVICE_NAME, default="Home Assistant"): str,
    }
)

# Step 3b: Hikvision - Email credentials
HIKVISION_EMAIL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SSID, default=""): str,
        vol.Optional(CONF_DEVICE_NAME, default="Home Assistant"): str,
    }
)


class NexecurConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self._alarm_version: str = ""
        self._login_method: str = ""
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Choose alarm version."""
        errors = {}
        if user_input is not None:
            self._alarm_version = user_input[CONF_ALARM_VERSION]
            self._data[CONF_ALARM_VERSION] = self._alarm_version

            if self._alarm_version == ALARM_VERSION_VIDEOFIED:
                return await self.async_step_videofied()
            else:
                return await self.async_step_hikvision_method()

        return self.async_show_form(
            step_id="user",
            data_schema=VERSION_SCHEMA,
            errors=errors,
        )

    async def async_step_videofied(self, user_input=None):
        """Step 2a: Configure Videofied alarm."""
        errors = {}
        if user_input is not None:
            client = NexecurClient(
                id_site=user_input[CONF_ID_SITE],
                password=user_input[CONF_PASSWORD],
                device_name=user_input.get(CONF_DEVICE_NAME, "Home Assistant"),
            )
            try:
                await client.async_login()
            except NexecurAuthError:
                errors["base"] = "auth"
            except Exception:
                errors["base"] = "unknown"
            else:
                self._data.update(user_input)
                await self.async_set_unique_id(f"videofied_{user_input[CONF_ID_SITE]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Nexecur Videofied {user_input[CONF_ID_SITE]}",
                    data=self._data,
                )

        return self.async_show_form(
            step_id="videofied",
            data_schema=VIDEOFIED_SCHEMA,
            errors=errors,
        )

    async def async_step_hikvision_method(self, user_input=None):
        """Step 2b: Choose Hikvision login method (phone or email)."""
        errors = {}
        if user_input is not None:
            self._login_method = user_input[CONF_LOGIN_METHOD]
            self._data[CONF_LOGIN_METHOD] = self._login_method

            if self._login_method == LOGIN_METHOD_PHONE:
                return await self.async_step_hikvision_phone()
            else:
                return await self.async_step_hikvision_email()

        return self.async_show_form(
            step_id="hikvision_method",
            data_schema=HIKVISION_METHOD_SCHEMA,
            errors=errors,
        )

    async def async_step_hikvision_phone(self, user_input=None):
        """Step 3a: Configure Hikvision with phone number."""
        errors = {}
        if user_input is not None:
            from .nexecur_api_hikvision import NexecurHikvisionClient, NexecurAuthError as HikAuthError

            client = NexecurHikvisionClient(
                phone=user_input[CONF_PHONE],
                password=user_input[CONF_PASSWORD],
                country_code=user_input.get(CONF_COUNTRY_CODE, "33"),
                ssid=user_input.get(CONF_SSID, ""),
                device_name=user_input.get(CONF_DEVICE_NAME, "Home Assistant"),
            )
            try:
                await client.async_login()
            except HikAuthError:
                errors["base"] = "auth"
            except Exception:
                errors["base"] = "unknown"
            else:
                self._data.update(user_input)
                # Store account for unified access
                self._data[CONF_ACCOUNT] = user_input[CONF_PHONE]
                await self.async_set_unique_id(f"hikvision_{user_input[CONF_PHONE]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Nexecur Hikvision {user_input[CONF_PHONE]}",
                    data=self._data,
                )
            finally:
                await client.async_close()

        return self.async_show_form(
            step_id="hikvision_phone",
            data_schema=HIKVISION_PHONE_SCHEMA,
            errors=errors,
        )

    async def async_step_hikvision_email(self, user_input=None):
        """Step 3b: Configure Hikvision with email."""
        errors = {}
        if user_input is not None:
            from .nexecur_api_hikvision import NexecurHikvisionClient, NexecurAuthError as HikAuthError

            client = NexecurHikvisionClient(
                phone=user_input[CONF_EMAIL],  # API uses same param
                password=user_input[CONF_PASSWORD],
                country_code="",  # Not needed for email
                ssid=user_input.get(CONF_SSID, ""),
                device_name=user_input.get(CONF_DEVICE_NAME, "Home Assistant"),
            )
            try:
                await client.async_login()
            except HikAuthError:
                errors["base"] = "auth"
            except Exception:
                errors["base"] = "unknown"
            else:
                self._data.update(user_input)
                # Store account for unified access
                self._data[CONF_ACCOUNT] = user_input[CONF_EMAIL]
                await self.async_set_unique_id(f"hikvision_{user_input[CONF_EMAIL]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Nexecur Hikvision {user_input[CONF_EMAIL]}",
                    data=self._data,
                )
            finally:
                await client.async_close()

        return self.async_show_form(
            step_id="hikvision_email",
            data_schema=HIKVISION_EMAIL_SCHEMA,
            errors=errors,
        )

    @callback
    def async_get_options_flow(self, config_entry):
        return NexecurOptionsFlow(config_entry)


class NexecurOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
