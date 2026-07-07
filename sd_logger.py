# Note: This file was developed with the assistance of AI code generation tools.

"""SD card CSV logging helper for the particulate matter station."""

import machine
import errno
import os


class SDCardLogger:
    def __init__(
        self,
        *,
        sck_pin,
        miso_pin,
        mosi_pin,
        cs_pin,
        header,
        mount_path="/sd",
        filename_prefix="telemetry",
        spi_slot=2,
        frequency=10000000,
    ):
        self.enabled = False
        self.file_path = None
        self.mount_path = mount_path
        self.header = header

        try:
            try:
                os.mkdir(mount_path)
            except OSError:
                pass

            sd_card = machine.SDCard(
                slot=spi_slot,
                sck=sck_pin,
                miso=miso_pin,
                mosi=mosi_pin,
                cs=cs_pin,
                freq=frequency,
            )
            self._mount(sd_card)

            self.file_path = self._next_file_path(filename_prefix)
            self._append_row(header)
            self.enabled = True
            print("SD card logging to {}".format(self.file_path))
        except Exception as error:
            print("SD card logging unavailable: {}".format(error))

    def _mount(self, sd_card):
        try:
            os.mount(sd_card, self.mount_path)
        except OSError as error:
            code = error.args[0] if error.args else None
            if code != getattr(errno, "EBUSY", 16):
                raise

    def _next_file_path(self, filename_prefix):
        existing_files = set(os.listdir(self.mount_path))
        for index in range(1000):
            filename = "{}_{:03d}.csv".format(filename_prefix, index)
            if filename not in existing_files:
                return "{}/{}".format(self.mount_path, filename)

        return "{}/{}_overflow.csv".format(self.mount_path, filename_prefix)

    def _append_row(self, row):
        with open(self.file_path, "a") as log_file:
            log_file.write(",".join(self._csv_cell(value) for value in row))
            log_file.write("\n")

    def log(self, uptime_ms, row):
        if not self.enabled:
            return

        try:
            self._append_row([uptime_ms] + list(row))
        except Exception as error:
            self.enabled = False
            print("SD card logging stopped: {}".format(error))

    def _csv_cell(self, value):
        text = str(value)
        if "," not in text and '"' not in text and "\n" not in text and "\r" not in text:
            return text
        return '"{}"'.format(text.replace('"', '""'))
