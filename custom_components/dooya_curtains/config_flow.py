import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_DEVICE_ADDRESS, CONF_HOST, CONF_PORT, DEFAULT_PORT

class DooyaCurtainsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DOOYA Curtains."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DooyaCurtainsOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Perform validation and create the entry
            return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Required(CONF_DEVICE_ADDRESS): str,  # Device address should be a hex string
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

class DooyaCurtainsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema({
            vol.Optional(CONF_HOST, default=self.config_entry.data.get(CONF_HOST)): str,
            vol.Optional(CONF_PORT, default=self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Optional(CONF_DEVICE_ADDRESS, default=self.config_entry.data.get(CONF_DEVICE_ADDRESS)): str,
        })

        return self.async_show_form(step_id="init", data_schema=options_schema)
