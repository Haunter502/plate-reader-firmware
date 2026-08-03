<<<<<<< HEAD
import board
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# I2C SETUP

i2c = board.STEMMA_I2C()

# ADC SETUP
# One ADS1115 has 4 analog input channels: P0, P1, P2, P3.
# To read 8 row sensors, we assume there are TWO ADS1115 boards.
#
# Common addresses:
# First ADS1115  = 0x48
# Second ADS1115 = 0x49
#
# If your second ADS1115 has a different address, change 0x49.

ads1 = ADS.ADS1115(i2c, address=0x48)
ads2 = ADS.ADS1115(i2c, address=0x49)

# SENSOR CHANNEL MAPPING
# Assumption:
# Row A-D sensors are connected to ADS1115 #1
# Row E-H sensors are connected to ADS1115 #2

row_A = AnalogIn(ads1, ADS.P0)
row_B = AnalogIn(ads1, ADS.P1)
row_C = AnalogIn(ads1, ADS.P2)
row_D = AnalogIn(ads1, ADS.P3)

row_E = AnalogIn(ads2, ADS.P0)
row_F = AnalogIn(ads2, ADS.P1)
row_G = AnalogIn(ads2, ADS.P2)
row_H = AnalogIn(ads2, ADS.P3)

row_sensors = [
    row_A,
    row_B,
    row_C,
    row_D,
    row_E,
    row_F,
    row_G,
    row_H,
]


# FUNCTIONS


def read_single_sensor():
    """
    Backwards-compatible function from your original spectrophotometer code.

    Reads only Row A / ADS1 P0.
    """
    return row_A.value


def read_plate(samples=128):
    """
    Backwards-compatible function from your original adc.py.

    This still reads only one sensor, Row A / ADS1 P0,
    but averages many readings to reduce noise.
    """
    total = 0

    for _ in range(samples):
        total += row_A.value

    return int(total / samples)


def read_all_sensors():
    """
    Reads all 8 row sensors once.

    Returns:
        list of 8 raw ADC readings in this order:
        [A, B, C, D, E, F, G, H]
    """
    readings = []

    for sensor in row_sensors:
        readings.append(sensor.value)

    return readings


def read_all_sensors_averaged(samples=16):
    """
    Reads all 8 row sensors multiple times and averages them.

    Returns:
        list of 8 averaged ADC readings in this order:
        [A, B, C, D, E, F, G, H]
    """
    totals = [0] * 8

    for _ in range(samples):
        readings = read_all_sensors()

        for i in range(8):
            totals[i] += readings[i]

    averages = []

    for i in range(8):
        averages.append(int(totals[i] / samples))

=======
import board
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# I2C SETUP

i2c = board.STEMMA_I2C()

# ADC SETUP
# One ADS1115 has 4 analog input channels: P0, P1, P2, P3.
# To read 8 row sensors, we assume there are TWO ADS1115 boards.
#
# Common addresses:
# First ADS1115  = 0x48
# Second ADS1115 = 0x49
#
# If your second ADS1115 has a different address, change 0x49.

ads1 = ADS.ADS1115(i2c, address=0x48)
ads2 = ADS.ADS1115(i2c, address=0x49)

# SENSOR CHANNEL MAPPING
# Assumption:
# Row A-D sensors are connected to ADS1115 #1
# Row E-H sensors are connected to ADS1115 #2

row_A = AnalogIn(ads1, ADS.P0)
row_B = AnalogIn(ads1, ADS.P1)
row_C = AnalogIn(ads1, ADS.P2)
row_D = AnalogIn(ads1, ADS.P3)

row_E = AnalogIn(ads2, ADS.P0)
row_F = AnalogIn(ads2, ADS.P1)
row_G = AnalogIn(ads2, ADS.P2)
row_H = AnalogIn(ads2, ADS.P3)

row_sensors = [
    row_A,
    row_B,
    row_C,
    row_D,
    row_E,
    row_F,
    row_G,
    row_H,
]


# FUNCTIONS


def read_single_sensor():
    """
    Backwards-compatible function from your original spectrophotometer code.

    Reads only Row A / ADS1 P0.
    """
    return row_A.value


def read_plate(samples=128):
    """
    Backwards-compatible function from your original adc.py.

    This still reads only one sensor, Row A / ADS1 P0,
    but averages many readings to reduce noise.
    """
    total = 0

    for _ in range(samples):
        total += row_A.value

    return int(total / samples)


def read_all_sensors():
    """
    Reads all 8 row sensors once.

    Returns:
        list of 8 raw ADC readings in this order:
        [A, B, C, D, E, F, G, H]
    """
    readings = []

    for sensor in row_sensors:
        readings.append(sensor.value)

    return readings


def read_all_sensors_averaged(samples=16):
    """
    Reads all 8 row sensors multiple times and averages them.

    Returns:
        list of 8 averaged ADC readings in this order:
        [A, B, C, D, E, F, G, H]
    """
    totals = [0] * 8

    for _ in range(samples):
        readings = read_all_sensors()

        for i in range(8):
            totals[i] += readings[i]

    averages = []

    for i in range(8):
        averages.append(int(totals[i] / samples))

>>>>>>> origin/main
    return averages