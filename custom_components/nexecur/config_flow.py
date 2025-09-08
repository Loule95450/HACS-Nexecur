from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_ID_SITE, CONF_PASSWORD, CONF_DEVICE_NAME
from .nexecur_api import NexecurClient, NexecurAuthError

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID_SITE): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_DEVICE_NAME, default="Home Assistant"): str,
    }
)

class NexecurConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
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
                await self.async_set_unique_id(user_input[CONF_ID_SITE])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Nexecur {user_input[CONF_ID_SITE]}", data=user_input)
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    @callback
    def async_get_options_flow(self, config_entry):
        return NexecurOptionsFlow(config_entry)

class NexecurOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
