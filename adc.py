# This file acts as a driver for your ADS1115 ADC 
# (Analog-to-Digital Converter) chip. Because microcontrollers only 
# understand digital binary numbers (1s and 0s), this chip takes the 
# raw continuous voltage coming off your photodiode and converts it 
# into a digital number between 0, 32, 767

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize I2C bus via STEMMA QT / Qwiic
i2c = board.STEMMA_I2C()

# Initialize ADS1115 ADC (Address 0x48)
ads = ADS.ADS1115(i2c)

# Map Channel A0
chan0 = AnalogIn(ads, ADS.P0)

def read_single_sensor():
    """Takes a single raw 16-bit measurement from A0."""
    return chan0.value

def read_plate(samples=128):
    """Averages multiple raw readings to reduce signal noise."""
    total = 0
    for _ in range(samples):
        total += chan0.value
    return int(total / samples)