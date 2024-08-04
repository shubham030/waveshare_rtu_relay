import logging
import socket
from homeassistant.components.cover import (
    CoverEntity,
    SUPPORT_OPEN,
    SUPPORT_CLOSE,
    SUPPORT_STOP,
    SUPPORT_SET_POSITION,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from .const import DOMAIN, CONF_DEVICE_ADDRESS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the DOOYA Curtains cover platform from a config entry."""
    host = config_entry.data[CONF_HOST]
    port = config_entry.data[CONF_PORT]
    device_address = bytes.fromhex(config_entry.data[CONF_DEVICE_ADDRESS])
    name = f"Dooya Curtain {device_address.hex()}"

    async_add_entities([DooyaCurtainCover(name, host, port, device_address)])

class DooyaCurtainCover(CoverEntity):
    _attr_supported_features = (
        SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP | SUPPORT_SET_POSITION
    )

    def __init__(self, name, host, port, device_address):
        self._name = name
        self._host = host
        self._port = port
        self._device_address = device_address
        self._position = None
        self._is_opening = False
        self._is_closing = False
        self._attr_is_closed = None

    @property
    def name(self):
        return self._name

    @property
    def is_opening(self):
        return self._is_opening

    @property
    def is_closing(self):
        return self._is_closing

    @property
    def current_cover_position(self):
        return self._position

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._attr_is_closed

    def open_cover(self, **kwargs):
        self._send_command(0x01)
        self._is_opening = True
        self._is_closing = False
        self._attr_is_closed = False
        _LOGGER.info("Sending open command to %s", self._name)

    def close_cover(self, **kwargs):
        self._send_command(0x02)
        self._is_opening = False
        self._is_closing = True
        self._attr_is_closed = True
        _LOGGER.info("Sending close command to %s", self._name)

    def stop_cover(self, **kwargs):
        self._send_command(0x03)
        self._is_opening = False
        self._is_closing = False
        _LOGGER.info("Sending stop command to %s", self._name)

    def set_cover_position(self, **kwargs):
        position = kwargs.get('position', 0)
        if position < 0 or position > 100:
            _LOGGER.error("Invalid position: %d. Must be between 0 and 100.", position)
            return
        self._send_command(0x04, [position])
        self._position = position
        self._attr_is_closed = position == 0
        _LOGGER.info("Setting position to %d%% for %s", position, self._name)

    def _send_command(self, command, data=None):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self._host, self._port))
                message = self._build_message(command, data)
                _LOGGER.debug("Sending message: %s", message.hex())
                sock.sendall(message)
                response = sock.recv(1024)
                _LOGGER.info("Received response: %s", response.hex())
        except Exception as e:
            _LOGGER.error("Error sending command: %s", e)

    def _build_message(self, command, data):
        start_code = 0x55
        function_code = 0x03
        message = bytearray([start_code, *self._device_address, function_code, command])
        if data:
            message.extend(data)
        crc = self.calculate_crc(message)
        message.extend(crc)
        _LOGGER.debug("Built message: %s", message.hex())
        return message

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
