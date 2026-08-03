import time
import math
import board
import adafruit_aw9523
import adc


ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"]

COLUMN_LED_PINS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
INDICATOR_WAITING_PIN = 14
INDICATOR_MEASURING_PIN = 15

SETTLE_TIME = 0.05
SENSOR_SAMPLES = 16
DARK_SAMPLES = 32
READ_INTERVAL = 1.0
ABSORBANCE_CAP = 3.0


# Set up AW9523
i2c = board.STEMMA_I2C()
aw = adafruit_aw9523.AW9523(i2c)


# Set up LED pins
column_leds = []

for pin_num in COLUMN_LED_PINS:
    led = aw.get_pin(pin_num)
    led.switch_to_output(value=False)
    column_leds.append(led)


# Set up indicator LEDs
indicator_waiting = aw.get_pin(INDICATOR_WAITING_PIN)
indicator_waiting.switch_to_output(value=False)

indicator_measuring = aw.get_pin(INDICATOR_MEASURING_PIN)
indicator_measuring.switch_to_output(value=False)


def log10(x):
    return math.log(x) / 2.302585092994046


def all_column_leds_off():
    for led in column_leds:
        led.value = False


def all_column_leds_on():
    for led in column_leds:
        led.value = True


def read_8_rows(samples=SENSOR_SAMPLES):
    raw_rows, voltage_rows = adc.read_all_sensors_raw_and_voltage_averaged(samples=samples)

    if len(raw_rows) != 8:
        raise RuntimeError("raw_rows must have exactly 8 values.")

    if len(voltage_rows) != 8:
        raise RuntimeError("voltage_rows must have exactly 8 values.")

    return raw_rows, voltage_rows


def countdown(message, seconds):
    print(message)

    indicator_waiting.value = True

    for seconds_left in range(seconds, 0, -1):
        print("Starting in", seconds_left)
        time.sleep(1)

    indicator_waiting.value = False
    print("Measuring now.")


def measure_dark_baseline():
    print("\nMeasuring DARK baseline...")

    all_column_leds_off()
    time.sleep(SETTLE_TIME)

    dark_raw, dark_voltage = read_8_rows(samples=DARK_SAMPLES)

    print("\nDARK BASELINE COMPLETE")
    print("Row,DarkRawADC,DarkVoltageV")

    for row_index in range(8):
        print(f"{ROWS[row_index]},{dark_raw[row_index]},{dark_voltage[row_index]:.6f}")

    return dark_raw, dark_voltage


def measure_current_reading(dark_raw, dark_voltage, use_plate_leds=False):
    if use_plate_leds:
        all_column_leds_on()
    else:
        all_column_leds_off()

    indicator_measuring.value = True
    time.sleep(SETTLE_TIME)

    raw_rows, voltage_rows = read_8_rows(samples=SENSOR_SAMPLES)

    indicator_measuring.value = False
    all_column_leds_off()

    light_signal_rows = []
    voltage_signal_rows = []

    for row_index in range(8):
        # Main math:
        # how much the photodiode changed from dark
        light_signal = abs(raw_rows[row_index] - dark_raw[row_index])
        voltage_signal = abs(voltage_rows[row_index] - dark_voltage[row_index])

        light_signal_rows.append(light_signal)
        voltage_signal_rows.append(voltage_signal)

    return raw_rows, voltage_rows, light_signal_rows, voltage_signal_rows


def calculate_absorbance(sample_signal, blank_signal):
    """
    Calculates absorbance from one sample signal and one blank signal.

    Formula:
    transmittance = sample_signal / blank_signal
    absorbance = -log10(transmittance)
    """

    if blank_signal <= 0:
        return None, None

    if sample_signal <= 0:
        return ABSORBANCE_CAP, 0.0

    transmittance = sample_signal / blank_signal
    transmittance_percent = transmittance * 100.0
    absorbance = -log10(transmittance)

    if absorbance < 0:
        return "ERROR_SAMPLE_BRIGHTER_THAN_BLANK", transmittance_percent

    return absorbance, transmittance_percent


def calculate_8_row_absorbance(sample_light_rows, blank_light_rows):
    absorbance_rows = []
    transmittance_rows = []

    for row_index in range(8):
        absorbance, transmittance_percent = calculate_absorbance(
            sample_light_rows[row_index],
            blank_light_rows[row_index]
        )

        absorbance_rows.append(absorbance)
        transmittance_rows.append(transmittance_percent)

    return absorbance_rows, transmittance_rows


def print_8_row_results(raw_rows, voltage_rows, light_signal_rows, voltage_signal_rows, dark_raw, dark_voltage):
    print("\n8-ROW PHOTODIODE READINGS")
    print("Row,DarkRawADC,RawADC,RawChangeFromDark,LightSignal,DarkVoltageV,VoltageV,LightSignalVoltageV")

    for row_index in range(8):
        row_name = ROWS[row_index]
        raw_value = raw_rows[row_index]
        voltage_value = voltage_rows[row_index]
        raw_change_from_dark = raw_value - dark_raw[row_index]
        light_signal = light_signal_rows[row_index]
        voltage_signal = voltage_signal_rows[row_index]

        print(
            f"{row_name},"
            f"{dark_raw[row_index]},"
            f"{raw_value},"
            f"{raw_change_from_dark},"
            f"{light_signal},"
            f"{dark_voltage[row_index]:.6f},"
            f"{voltage_value:.6f},"
            f"{voltage_signal:.6f}"
        )


def print_8_row_absorbance_results(blank_light_rows, sample_light_rows, absorbance_rows, transmittance_rows):
    print("\n8-ROW ABSORBANCE RESULTS")
    print("Row,BlankLightSignal,SampleLightSignal,TransmittancePercent,AbsorbanceAU")

    for row_index in range(8):
        row_name = ROWS[row_index]
        absorbance = absorbance_rows[row_index]
        transmittance = transmittance_rows[row_index]

        if absorbance is None:
            print(f"{row_name},{blank_light_rows[row_index]},{sample_light_rows[row_index]},ERROR,ERROR_BLANK_TOO_LOW")

        elif isinstance(absorbance, str):
            print(f"{row_name},{blank_light_rows[row_index]},{sample_light_rows[row_index]},{transmittance:.2f},{absorbance}")

        else:
            print(f"{row_name},{blank_light_rows[row_index]},{sample_light_rows[row_index]},{transmittance:.2f},{absorbance:.4f}")


def run_photodiode_test():
    print("SIMPLE 8-ROW PHOTODIODE TEST")
    print("This measures dark baseline once.")
    print("Then it automatically prints readings every second.")
    print("Focus on LightSignal.")
    print("Expected: dark = low, room light = higher, flashlight = highest.")

    countdown("Cover the photodiodes for DARK baseline.", 7)

    dark_raw, dark_voltage = measure_dark_baseline()

    print("\nNow readings will print automatically every second.")

    while True:
        raw_rows, voltage_rows, light_signal_rows, voltage_signal_rows = measure_current_reading(
            dark_raw,
            dark_voltage,
            use_plate_leds=False
        )

        print_8_row_results(
            raw_rows,
            voltage_rows,
            light_signal_rows,
            voltage_signal_rows,
            dark_raw,
            dark_voltage
        )

        time.sleep(READ_INTERVAL)


def run_absorbance_test_once():
    print("8-ROW ABSORBANCE TEST")
    print("This measures DARK, then BLANK, then SAMPLE.")
    print("Use this later inside the full housing.")

    countdown("Cover the photodiodes for DARK baseline.", 7)
    dark_raw, dark_voltage = measure_dark_baseline()

    countdown("Place the BLANK setup in the housing.", 7)

    blank_raw, blank_voltage, blank_light, blank_voltage_signal = measure_current_reading(
        dark_raw,
        dark_voltage,
        use_plate_leds=True
    )

    print("\nBLANK READINGS")
    print_8_row_results(
        blank_raw,
        blank_voltage,
        blank_light,
        blank_voltage_signal,
        dark_raw,
        dark_voltage
    )

    countdown("Place the SAMPLE setup in the housing.", 7)

    sample_raw, sample_voltage, sample_light, sample_voltage_signal = measure_current_reading(
        dark_raw,
        dark_voltage,
        use_plate_leds=True
    )

    print("\nSAMPLE READINGS")
    print_8_row_results(
        sample_raw,
        sample_voltage,
        sample_light,
        sample_voltage_signal,
        dark_raw,
        dark_voltage
    )

    absorbance_rows, transmittance_rows = calculate_8_row_absorbance(
        sample_light,
        blank_light
    )

    print_8_row_absorbance_results(
        blank_light,
        sample_light,
        absorbance_rows,
        transmittance_rows
    )


run_photodiode_test()

# For absorbance later, comment out the line above and uncomment this:
# run_absorbance_test_once()