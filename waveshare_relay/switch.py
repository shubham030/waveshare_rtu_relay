import logging
from homeassistant.components.switch import SwitchEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Waveshare relay switches."""
    _LOGGER.debug("Setting up Waveshare relay switches")
    hub = hass.data[DOMAIN]
    switches = [WaveshareRelaySwitch(hub, relay_num) for relay_num in range(1, hub._num_relays + 1)]
    async_add_entities(switches, True)

class WaveshareRelaySwitch(SwitchEntity):
    """Representation of a Waveshare Relay switch."""

    def __init__(self, hub, relay_number):
        """Initialize the switch."""
        self._hub = hub
        self._relay_number = relay_number
        self._is_on = False

    @property
    def name(self):
        """Return the name of the switch."""
        return f"Waveshare Relay {self._relay_number}"

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self._hub.set_relay_state(self._relay_number, True)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self._hub.set_relay_state(self._relay_number, False)
        self._is_on = False
        self.async_write_ha_state()

    async def async_update(self):
        """Fetch the latest state of the switch."""
        status_bytes = await self._hub.read_relay_status()
        if status_bytes is not None:
            byte_index = (self._relay_number - 1) // 8
            bit_index = (self._relay_number - 1) % 8
            self._is_on = bool(status_bytes[byte_index] & (1 << bit_index))
            self.async_write_ha_state()
