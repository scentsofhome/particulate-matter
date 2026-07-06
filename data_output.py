# Note: This file was developed with the assistance of AI code generation tools.


def print_data(mode, heater_status, readings):
    sensirion_pm = readings["sensirion_pm"]
    plantower_pm = readings["plantower_pm"]

    print(
        "DATA:{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(
            mode,
            heater_status,
            readings["ambient_temp"],
            readings["ambient_humidity"],
            readings["conditioned_temp"],
            readings["conditioned_humidity"],
            round(readings["thermistor_c"], 1),
            sensirion_pm["pm1"],
            sensirion_pm["pm25"],
            sensirion_pm["pm10"],
            sensirion_pm["raw03"],
            sensirion_pm["raw05"],
            sensirion_pm["raw10"],
            sensirion_pm["raw25"],
            sensirion_pm["raw50"],
            sensirion_pm["raw100"],
            plantower_pm["pm1"],
            plantower_pm["pm25"],
            plantower_pm["pm10"],
            plantower_pm["raw03"],
            plantower_pm["raw05"],
            plantower_pm["raw10"],
            plantower_pm["raw25"],
            plantower_pm["raw50"],
            plantower_pm["raw100"],
        )
    )
