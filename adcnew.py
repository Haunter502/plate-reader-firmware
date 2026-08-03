import board
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize I2C bus
i2c = board.STEMMA_I2C()

# First ADS1115 board
ads1 = ADS.ADS1115(i2c, address=0x48)

# Second ADS1115 board
ads2 = ADS.ADS1115(i2c, address=0x49)

# Map 8 photodiode channels
chan0 = AnalogIn(ads1, ADS.P0)  # Row A?
chan1 = AnalogIn(ads1, ADS.P1)  # Row B?
chan2 = AnalogIn(ads1, ADS.P2)  # Row C?
chan3 = AnalogIn(ads1, ADS.P3)  # Row D?

chan4 = AnalogIn(ads2, ADS.P0)  # Row E?
chan5 = AnalogIn(ads2, ADS.P1)  # Row F?
chan6 = AnalogIn(ads2, ADS.P2)  # Row G?
chan7 = AnalogIn(ads2, ADS.P3)  # Row H?

channels = [chan0, chan1, chan2, chan3, chan4, chan5, chan6, chan7]


def read_single_sensor():
    """Takes one raw reading from the first photodiode channel."""
    return chan0.value


def read_plate(samples=128):
    """Old compatibility function: reads only the first channel."""
    total = 0
    for _ in range(samples):
        total += chan0.value
    return int(total / samples)


def read_all_sensors():
    """Reads all 8 photodiode channels once."""
    return [channel.value for channel in channels]


def read_all_sensor_voltages():
    """Reads voltage from all 8 photodiode channels once."""
    return [channel.voltage for channel in channels]


def read_all_sensors_averaged(samples=16):
    """Reads all 8 photodiode channels and averages raw ADC values."""
    totals = [0, 0, 0, 0, 0, 0, 0, 0]

    for _ in range(samples):
        for i, channel in enumerate(channels):
            totals[i] += channel.value

    return [int(total / samples) for total in totals]


def read_all_sensors_raw_and_voltage_averaged(samples=16):
    """Reads all 8 photodiode channels and returns averaged raw ADC and voltage values."""
    raw_totals = [0, 0, 0, 0, 0, 0, 0, 0]
    voltage_totals = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    for _ in range(samples):
        for i, channel in enumerate(channels):
            raw_totals[i] += channel.value
            voltage_totals[i] += channel.voltage

    raw_readings = [int(total / samples) for total in raw_totals]
    voltage_readings = [total / samples for total in voltage_totals]

    return raw_readings, voltage_readings