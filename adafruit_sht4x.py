# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 ladyada for Adafruit
#
# SPDX-License-Identifier: MIT
#
# Adapted from:
# https://github.com/adafruit/Adafruit_CircuitPython_SHT4x

import struct
import time

try:
    from micropython import const
except ImportError:
    const = lambda value: value


_SHT4X_DEFAULT_ADDR = const(0x44)
_SHT4X_READSERIAL = const(0x89)
_SHT4X_SOFTRESET = const(0x94)


class Mode:
    NOHEAT_HIGHPRECISION = const(0xFD)
    NOHEAT_MEDPRECISION = const(0xF6)
    NOHEAT_LOWPRECISION = const(0xE0)
    HIGHHEAT_1S = const(0x39)
    HIGHHEAT_100MS = const(0x32)
    MEDHEAT_1S = const(0x2F)
    MEDHEAT_100MS = const(0x24)
    LOWHEAT_1S = const(0x1E)
    LOWHEAT_100MS = const(0x15)

    delay = {
        NOHEAT_HIGHPRECISION: 0.01,
        NOHEAT_MEDPRECISION: 0.005,
        NOHEAT_LOWPRECISION: 0.002,
        HIGHHEAT_1S: 1.1,
        HIGHHEAT_100MS: 0.11,
        MEDHEAT_1S: 1.1,
        MEDHEAT_100MS: 0.11,
        LOWHEAT_1S: 1.1,
        LOWHEAT_100MS: 0.11,
    }

    string = {
        NOHEAT_HIGHPRECISION: "No heater, high precision",
        NOHEAT_MEDPRECISION: "No heater, med precision",
        NOHEAT_LOWPRECISION: "No heater, low precision",
        HIGHHEAT_1S: "High heat, 1 second",
        HIGHHEAT_100MS: "High heat, 0.1 second",
        MEDHEAT_1S: "Med heat, 1 second",
        MEDHEAT_100MS: "Med heat, 0.1 second",
        LOWHEAT_1S: "Low heat, 1 second",
        LOWHEAT_100MS: "Low heat, 0.1 second",
    }

    @classmethod
    def is_valid(cls, value):
        return value in cls.string


class SHT4x:
    def __init__(self, i2c_bus, address=_SHT4X_DEFAULT_ADDR):
        self.i2c_bus = i2c_bus
        self.address = address
        self._buffer = bytearray(6)
        self.reset()
        self._mode = Mode.NOHEAT_HIGHPRECISION

    def _write_command(self, command):
        self.i2c_bus.writeto(self.address, bytes([command]))

    @property
    def serial_number(self):
        self._write_command(_SHT4X_READSERIAL)
        time.sleep(0.01)
        self._buffer = bytearray(self.i2c_bus.readfrom(self.address, 6))

        ser1 = self._buffer[0:2]
        ser1_crc = self._buffer[2]
        ser2 = self._buffer[3:5]
        ser2_crc = self._buffer[5]

        if ser1_crc != self._crc8(ser1) or ser2_crc != self._crc8(ser2):
            raise RuntimeError("Invalid CRC calculated")

        return (ser1[0] << 24) + (ser1[1] << 16) + (ser2[0] << 8) + ser2[1]

    def reset(self):
        self._write_command(_SHT4X_SOFTRESET)
        time.sleep(0.001)

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, new_mode):
        if not Mode.is_valid(new_mode):
            raise AttributeError("mode must be a Mode")
        self._mode = new_mode

    @property
    def relative_humidity(self):
        return self.measurements[1]

    @property
    def temperature(self):
        return self.measurements[0]

    @property
    def measurements(self):
        self._write_command(self._mode)
        time.sleep(Mode.delay[self._mode])
        self._buffer = bytearray(self.i2c_bus.readfrom(self.address, 6))

        temp_data = self._buffer[0:2]
        temp_crc = self._buffer[2]
        humidity_data = self._buffer[3:5]
        humidity_crc = self._buffer[5]

        if temp_crc != self._crc8(temp_data) or humidity_crc != self._crc8(humidity_data):
            raise RuntimeError("Invalid CRC calculated")

        temperature = struct.unpack_from(">H", temp_data)[0]
        temperature = -45.0 + 175.0 * temperature / 65535.0

        humidity = struct.unpack_from(">H", humidity_data)[0]
        humidity = -6.0 + 125.0 * humidity / 65535.0
        humidity = max(min(humidity, 100), 0)

        return temperature, humidity

    @staticmethod
    def _crc8(buffer):
        crc = 0xFF
        for byte in buffer:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc <<= 1
        return crc & 0xFF
