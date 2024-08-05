import asyncio
import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "waveshare_relay"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("host"): cv.string,
                vol.Required("port"): cv.port,
                vol.Required("num_relays"): vol.Coerce(int),
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Waveshare Relay component."""
    hass.data[DOMAIN] = WaveshareRelayHub(config[DOMAIN])
    return True

class WaveshareRelayHub:
    """Hub to manage all the Waveshare Relays."""

    def __init__(self, config):
        self._host = config["host"]
        self._port = config["port"]
        self._num_relays = config["num_relays"]
        self._relay_states = [False] * self._num_relays
        self._lock = asyncio.Lock()
        self._timer = None

    async def set_relay_state(self, relay_number, state):
        async with self._lock:
            self._relay_states[relay_number - 1] = state
            if self._timer is not None:
                self._timer.cancel()
            self._timer = asyncio.get_event_loop().call_later(0.5, self._send_relay_states)

    async def _send_relay_states(self):
        async with self._lock:
            byte_count = (self._num_relays + 7) // 8
            relay_bytes = bytearray(byte_count)
            for i, state in enumerate(self._relay_states):
                if state:
                    relay_bytes[i // 8] |= (1 << (i % 8))
            rs485_command = bytes([0x01, 0x0F, 0x00, 0x00, 0x00, self._num_relays, byte_count]) + relay_bytes
            crc = self.calculate_crc(rs485_command)
            rs485_command += crc
            await self.send_command(rs485_command)

    async def send_command(self, command):
        reader, writer = await asyncio.open_connection(self._host, self._port)
        try:
            writer.write(command)
            await writer.drain()
            response = await reader.read(1024)
            return response
        except (asyncio.TimeoutError, ConnectionError) as e:
            _LOGGER.error("Connection error: %s", e)
            return None
        finally:
            writer.close()
            await writer.wait_closed()

    async def read_relay_status(self):
        """Read the status of all relays."""
        query_command = bytes([0x01, 0x01, 0x00, 0x00, 0x00, self._num_relays])
        crc = self.calculate_crc(query_command)
        query_command += crc
        response = await self.send_command(query_command)
        if response is None or len(response) < 5 + (self._num_relays + 7) // 8:
            _LOGGER.error("Invalid response length: %s", response)
            return None
        # Extract relay status bytes from the response
        return response[3:-2]  # Excluding address, function code, and CRC

    @staticmethod
    def calculate_crc(data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc.to_bytes(2, byteorder='little')
