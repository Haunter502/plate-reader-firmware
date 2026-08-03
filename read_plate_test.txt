import time
import board 
import digitalio
from adc import read_plate

# Map the active LED pins for array cycling (Update pins as needed)
pins = (board.A2,)  # Updated to match your current single LED control pin
leds = tuple(digitalio.DigitalInOut(pin) for pin in pins)

# Initialize control pins
for led in leds:
    led.direction = digitalio.Direction.OUTPUT
    led.value = False

# Turn on the primary test LED
leds[0].value = True

print("Starting averaged plate reading stream...")

while True:
    # Takes an averaged reading over 128 samples
    avg_value = read_plate(128)
    print(f"Averaged Plate Value: {avg_value}")
    time.sleep(1)