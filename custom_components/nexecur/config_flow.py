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
    CONF_COUNTRY_CODE,
    CONF_SSID,
    ALARM_VERSION_VIDEOFIED,
    ALARM_VERSION_HIKVISION,
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

# Step 2b: Hikvision credentials
HIKVISION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PHONE): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_COUNTRY_CODE, default="33"): str,
        vol.Optional(CONF_SSID, default=""): str,
        vol.Optional(CONF_DEVICE_NAME, default="Home Assistant"): str,
    }
)


class NexecurConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self._alarm_version: str = ""
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
                return await self.async_step_hikvision()

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

    async def async_step_hikvision(self, user_input=None):
        """Step 2b: Configure Hikvision alarm."""
        errors = {}
        if user_input is not None:
            # Import Hikvision client
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
                await self.async_set_unique_id(f"hikvision_{user_input[CONF_PHONE]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Nexecur Hikvision {user_input[CONF_PHONE]}",
                    data=self._data,
                )
            finally:
                await client.async_close()

        return self.async_show_form(
            step_id="hikvision",
            data_schema=HIKVISION_SCHEMA,
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
