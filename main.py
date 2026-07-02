import machine
import sys
import time
import uselect

from adafruit_sht4x import Mode, SHT4x
from pms5003 import PMS5003
from thermistor import Thermistor


# Pins and sensor settings
HEATER_PIN = 25
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21
THERMISTOR_PIN = 34
PMS_UART_ID = 2
PMS_TX_PIN = 17
PMS_RX_PIN = 16

SHT_HUMIDITY_TRIGGER = 40
THERMISTOR_CUTOFF_C = 45.0
HEATER_ON_MS = 5_000
HEATER_COOLDOWN_MS = 35_000
READ_INTERVAL_MS = 2_000

THERMISTOR_BETA = 3950
THERMISTOR_R0 = 10_000.0
THERMISTOR_T0_K = 298.15
THERMISTOR_RESISTOR = 10_000.0

MODE_AUTOMATIC = "AUTOMATIC"
MODE_MANUAL = "MANUAL"


class ADC16Adapter:
    """Gives ESP32 ADC.read() the read_u16() API used by thermistor.py."""

    def __init__(self, adc):
        self.adc = adc

    def read_u16(self):
        if hasattr(self.adc, "read_u16"):
            return self.adc.read_u16()
        return int(self.adc.read() * 65535 / 4095)


class CircuitPythonI2CAdapter:
    """Gives machine.I2C the small CircuitPython API expected by BusDevice."""

    def __init__(self, i2c):
        self.i2c = i2c

    def try_lock(self):
        return True

    def unlock(self):
        pass

    def writeto(self, address, buffer, *, start=0, end=None):
        if end is None:
            end = len(buffer)
        self.i2c.writeto(address, buffer[start:end])

    def readfrom_into(self, address, buffer, *, start=0, end=None):
        if end is None:
            end = len(buffer)

        if start == 0 and end == len(buffer):
            self.i2c.readfrom_into(address, buffer)
            return

        read_buffer = bytearray(end - start)
        self.i2c.readfrom_into(address, read_buffer)
        buffer[start:end] = read_buffer

    def writeto_then_readfrom(
        self,
        address,
        out_buffer,
        in_buffer,
        *,
        out_start=0,
        out_end=None,
        in_start=0,
        in_end=None
    ):
        if out_end is None:
            out_end = len(out_buffer)
        if in_end is None:
            in_end = len(in_buffer)

        self.writeto(address, out_buffer, start=out_start, end=out_end)
        self.readfrom_into(address, in_buffer, start=in_start, end=in_end)


heater = machine.Pin(HEATER_PIN, machine.Pin.OUT)
heater.value(0)

sht_i2c = machine.I2C(
    0,
    scl=machine.Pin(I2C_SCL_PIN),
    sda=machine.Pin(I2C_SDA_PIN),
)
sht_sensor = SHT4x(CircuitPythonI2CAdapter(sht_i2c))
sht_sensor.mode = Mode.NOHEAT_HIGHPRECISION

thermistor_adc = machine.ADC(machine.Pin(THERMISTOR_PIN))
thermistor_adc.atten(machine.ADC.ATTN_11DB)
thermistor = Thermistor(
    ADC16Adapter(thermistor_adc),
    THERMISTOR_BETA,
    THERMISTOR_R0,
    THERMISTOR_T0_K,
    THERMISTOR_RESISTOR,
)

pms_uart = machine.UART(
    PMS_UART_ID,
    9600,
    tx=PMS_TX_PIN,
    rx=PMS_RX_PIN,
    timeout=1000,
)
pms_sensor = PMS5003(pms_uart, pin_reset=None, pin_enable=None, mode="active", retries=3)

stdin_poll = uselect.poll()
stdin_poll.register(sys.stdin, uselect.POLLIN)

mode = MODE_MANUAL
heater_is_on = False
heater_started_at = 0
cooldown_started_at = 0
cooldown_active = False
last_read_at = 0

last_pm = {
    "pm1": 0,
    "pm25": 0,
    "pm10": 0,
    "raw03": 0,
    "raw05": 0,
    "raw10": 0,
    "raw25": 0,
    "raw50": 0,
    "raw100": 0,
}
last_thermistor_c = 0.0


def set_heater(enabled, now=None):
    global heater_is_on, heater_started_at

    if enabled and not heater_is_on:
        heater_started_at = time.ticks_ms() if now is None else now

    heater.value(1 if enabled else 0)
    heater_is_on = enabled


def read_command():
    if not stdin_poll.poll(10):
        return None
    return sys.stdin.readline().strip().lower()


def handle_command(command, now):
    global mode, cooldown_active

    if command == "auto":
        mode = MODE_AUTOMATIC
    elif command == "manual":
        mode = MODE_MANUAL
        cooldown_active = False
        set_heater(False)
    elif command == "high" and mode == MODE_MANUAL:
        set_heater(True, now)
    elif command == "low" and mode == MODE_MANUAL:
        set_heater(False)


def update_cooldown(now):
    global cooldown_active, cooldown_started_at

    if (
        mode == MODE_AUTOMATIC
        and heater_is_on
        and time.ticks_diff(now, heater_started_at) >= HEATER_ON_MS
    ):
        set_heater(False)
        cooldown_active = True
        cooldown_started_at = now

    if cooldown_active and time.ticks_diff(now, cooldown_started_at) >= HEATER_COOLDOWN_MS:
        cooldown_active = False


def read_sht41():
    try:
        return sht_sensor.measurements
    except Exception:
        return "Err", "Err"


def read_thermistor_c():
    global last_thermistor_c

    try:
        last_thermistor_c = Thermistor.toC(thermistor.temperature())
    except Exception:
        pass

    return last_thermistor_c


def read_particulate_matter():
    global last_pm

    try:
        if not pms_sensor.data_available():
            return last_pm

        reading = pms_sensor.read()
        last_pm = {
            "pm1": reading.pm_ug_per_m3(1.0),
            "pm25": reading.pm_ug_per_m3(2.5),
            "pm10": reading.pm_ug_per_m3(10),
            "raw03": reading.pm_per_1l_air(0.3),
            "raw05": reading.pm_per_1l_air(0.5),
            "raw10": reading.pm_per_1l_air(1.0),
            "raw25": reading.pm_per_1l_air(2.5),
            "raw50": reading.pm_per_1l_air(5),
            "raw100": reading.pm_per_1l_air(10),
        }
    except Exception:
        pass

    return last_pm


def should_heat(sht_humidity, thermistor_c):
    if mode == MODE_MANUAL:
        target = heater_is_on
    else:
        target = sht_humidity != "Err" and sht_humidity > SHT_HUMIDITY_TRIGGER

    if thermistor_c >= THERMISTOR_CUTOFF_C:
        target = False
    if cooldown_active:
        target = False

    return target


def heater_status():
    if cooldown_active:
        return "COOLDOWN"
    if heater.value() == 1:
        return "ON"
    return "OFF"


def print_data(sht_temp, sht_humidity, thermistor_c, pm):
    print(
        "DATA:{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(
            mode,
            heater_status(),
            sht_temp,
            sht_humidity,
            round(thermistor_c, 1),
            pm["pm1"],
            pm["pm25"],
            pm["pm10"],
            pm["raw03"],
            pm["raw05"],
            pm["raw10"],
            pm["raw25"],
            pm["raw50"],
            pm["raw100"],
        )
    )


while True:
    now = time.ticks_ms()

    command = read_command()
    if command:
        handle_command(command, now)

    update_cooldown(now)

    if time.ticks_diff(now, last_read_at) >= READ_INTERVAL_MS:
        last_read_at = now

        sht_temp, sht_humidity = read_sht41()
        thermistor_c = read_thermistor_c()
        pm = read_particulate_matter()

        set_heater(should_heat(sht_humidity, thermistor_c), now)
        print_data(sht_temp, sht_humidity, thermistor_c, pm)

    time.sleep(0.1)
