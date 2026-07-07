# Note: This file was developed with the assistance of AI code generation tools.

"""AI-assisted DATA line formatting helper."""


SPS30_FIELDS = (
    "pm1",
    "pm25",
    "pm4",
    "pm10",
    "count05",
    "count10",
    "count25",
    "count40",
    "count100",
    "typical_particle_size",
)

PLANTOWER_FIELDS = (
    "pm1_standard",
    "pm25_standard",
    "pm10_standard",
    "pm1_env",
    "pm25_env",
    "pm10_env",
    "count03",
    "count05",
    "count10",
    "count25",
    "count50",
    "count100",
)


def print_data(mode, heater_status, readings):
    sensirion_pm = readings["sensirion_pm"]
    plantower_pm = readings["plantower_pm"]
    row = [
        mode,
        heater_status,
        readings["ambient_temp"],
        readings["ambient_humidity"],
        readings["conditioned_temp"],
        readings["conditioned_humidity"],
        round(readings["thermistor_c"], 1),
    ]
    row.extend(sensirion_pm[field] for field in SPS30_FIELDS)
    row.extend(plantower_pm[field] for field in PLANTOWER_FIELDS)

    print("DATA:{}".format(",".join(str(value) for value in row)))
