import logging
import voluptuous as vol
import socket
import binascii
from threading import Lock

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "integration_blueprint"

CONF_NUM_RELAYS = "num_relays"

SWITCH_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=502): cv.port,
    vol.Required(CONF_NUM_RELAYS): vol.All(vol.Coerce(int), vol.Range(min=1, max=64)),  # Adjusted for up to 64 relays
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema(SWITCH_SCHEMA)
}, extra=vol.ALLOW_EXTRA)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Waveshare relay switch platform."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    num_relays = config[CONF_NUM_RELAYS]

    switches = [WaveshareRelaySwitch(host, port, relay_num, num_relays) for relay_num in range(1, num_relays + 1)]
    add_entities(switches, True)

class WaveshareRelaySwitch(SwitchEntity):
    """Representation of a Waveshare Relay switch."""

    def __init__(self, host, port, relay_number, total_relays):
        """Initialize the switch."""
        self._host = host
        self._port = port
        self._relay_number = relay_number
        self._total_relays = total_relays
        self._is_on = False
        self._lock = Lock()

    @property
    def name(self):
        """Return the name of the switch."""
        return f"Waveshare Relay {self._relay_number}"

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._is_on

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        rs485_command = bytes([0x01, 0x05, 0x00, self._relay_number, 0xFF, 0x00])
        crc = self.calculate_crc(rs485_command)
        rs485_command += crc
        response = self.send_command(rs485_command)
        if response and response[1] == 5:  # Check if the function code is correct
            self._is_on = True
        else:
            _LOGGER.error("Error in response or no response received when turning on: %s", response and binascii.hexlify(response).decode())

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        rs485_command = bytes([0x01, 0x05, 0x00, self._relay_number, 0x00, 0x00])
        crc = self.calculate_crc(rs485_command)
        rs485_command += crc
        response = self.send_command(rs485_command)
        if response and response[1] == 5:  # Check if the function code is correct
            self._is_on = False
        else:
            _LOGGER.error("Error in response or no response received when turning off: %s", response and binascii.hexlify(response).decode())

    def update(self):
        """Fetch the latest state of the switch."""
        num_bytes = (self._total_relays + 7) // 8
        rs485_command = bytes([0x01, 0x01, 0x00, 0x00, 0x00, self._total_relays])
        crc = self.calculate_crc(rs485_command)
        rs485_command += crc
        response = self.send_command(rs485_command)

        if response and response[1] == 1:  # Check if the function code is correct
            # Extract status of the relay
            status_bytes = response[3:3 + num_bytes]
            if len(status_bytes) != num_bytes:
                _LOGGER.error("Expected %d status bytes, but got %d", num_bytes, len(status_bytes))
                return

            _LOGGER.debug("Status bytes: %s", binascii.hexlify(status_bytes).decode())

            byte_index = (self._relay_number - 1) // 8
            bit_position = (self._relay_number - 1) % 8

            if byte_index >= len(status_bytes):
                _LOGGER.error("Byte index %d out of range for status bytes: %s", byte_index, binascii.hexlify(status_bytes).decode())
                return

            status_byte = status_bytes[byte_index]
            self._is_on = bool(status_byte & (1 << bit_position))
        else:
            _LOGGER.error("Error in response or no response received when updating status: %s", response and binascii.hexlify(response).decode())


    def send_command(self, command):
        """Send a command to the relay and return the response."""
        with self._lock:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.settimeout(10)
                    s.connect((self._host, self._port))
                    s.sendall(command)
                    response = s.recv(1024)
                    return response
                except (socket.error, socket.timeout) as e:
                    _LOGGER.error("Connection error: %s", e)
                    return None

    def calculate_crc(self, data):
        """Calculate CRC."""
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
