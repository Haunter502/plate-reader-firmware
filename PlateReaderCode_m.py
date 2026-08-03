import time
import math
import board
import adafruit_aw9523
import adc


# MATH HELPER

def log10(x):
    return math.log(x) / 2.302585092994046


# ROW LAYOUT

ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"]


# HARDWARE PIN MAPPING

COLUMN_LED_PINS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
INDICATOR_WAITING_PIN = 14
INDICATOR_MEASURING_PIN = 15


# I2C connection to AW9523 GPIO expander

i2c = board.STEMMA_I2C()
aw = adafruit_aw9523.AW9523(i2c)


# Set up column LEDs

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


# MEASUREMENT SETTINGS

SETTLE_TIME = 0.05
SENSOR_SAMPLES = 16
DARK_SAMPLES = 32
LIGHT_CALIBRATION_SAMPLES = 32
READ_INTERVAL = 1.0
ABSORBANCE_CAP = 3.0


# HELPER FUNCTIONS

def all_column_leds_off():
    for led in column_leds:
        led.value = False


def read_all_row_sensors_raw_and_voltage_averaged(samples=SENSOR_SAMPLES):
    raw_readings, voltage_readings = adc.read_all_sensors_raw_and_voltage_averaged(samples=samples)

    if len(raw_readings) != 8:
        raise RuntimeError("raw_readings must have exactly 8 values.")

    if len(voltage_readings) != 8:
        raise RuntimeError("voltage_readings must have exactly 8 values.")

    return raw_readings, voltage_readings


def countdown(message, seconds):
    print("\n[ACTION REQUIRED]")
    print(message)

    indicator_waiting.value = True

    for seconds_left in range(seconds, 0, -1):
        print("Starting in", seconds_left)
        time.sleep(1)

    indicator_waiting.value = False
    print("Measuring now.")


# BASELINE + LIGHT CALIBRATION

def measure_dark_baseline_raw_voltage():
    print("\nMeasuring dark baseline...")

    all_column_leds_off()
    time.sleep(SETTLE_TIME)

    dark_raw, dark_voltage = read_all_row_sensors_raw_and_voltage_averaged(samples=DARK_SAMPLES)

    print("\nDark baseline readings:")
    print("Row,DarkRawADC,DarkVoltageV")

    for i in range(8):
        print(f"{ROWS[i]},{dark_raw[i]},{dark_voltage[i]:.6f}")

    return dark_raw, dark_voltage


def measure_light_calibration_raw_voltage():
    print("\nMeasuring light calibration...")

    all_column_leds_off()
    time.sleep(SETTLE_TIME)

    light_raw, light_voltage = read_all_row_sensors_raw_and_voltage_averaged(samples=LIGHT_CALIBRATION_SAMPLES)

    print("\nLight calibration readings:")
    print("Row,LightRawADC,LightVoltageV")

    for i in range(8):
        print(f"{ROWS[i]},{light_raw[i]},{light_voltage[i]:.6f}")

    return light_raw, light_voltage


def calibrate_signal_direction(dark_raw, light_raw, dark_voltage, light_voltage):
    """
    Figures out whether each row increases or decreases with light.
    direction = 1 means use RawADC - DarkRawADC.
    direction = -1 means use DarkRawADC - RawADC.
    """

    raw_directions = []
    voltage_directions = []

    print("\nSignal direction calibration:")
    print("Row,RawDirection,VoltageDirection,RawChangeFromDark,VoltageChangeFromDark")

    for row_index in range(8):
        raw_change = light_raw[row_index] - dark_raw[row_index]
        voltage_change = light_voltage[row_index] - dark_voltage[row_index]

        if raw_change >= 0:
            raw_direction = 1
            raw_direction_name = "RawMinusDark"
        else:
            raw_direction = -1
            raw_direction_name = "DarkMinusRaw"

        if voltage_change >= 0:
            voltage_direction = 1
            voltage_direction_name = "VoltageMinusDark"
        else:
            voltage_direction = -1
            voltage_direction_name = "DarkMinusVoltage"

        raw_directions.append(raw_direction)
        voltage_directions.append(voltage_direction)

        print(f"{ROWS[row_index]},{raw_direction_name},{voltage_direction_name},{raw_change},{voltage_change:.6f}")

    return raw_directions, voltage_directions


# SIGNAL MATH

def calculate_row_light_signal(raw_reading, dark_reading, raw_direction=None):
    return abs(raw_reading - dark_reading)


def calculate_row_voltage_signal(voltage_reading, dark_voltage, voltage_direction=None):
    return abs(voltage_reading - dark_voltage)

# READ 8 ROWS ONLY

def measure_8_rows_raw_voltage_signal(dark_raw, dark_voltage, raw_directions, voltage_directions):
    """
    Reads the 8 row ADC/photodiode channels all at once.
    This does NOT scan columns.
    This does NOT print D1-D96.
    """

    all_column_leds_off()

    indicator_measuring.value = True
    time.sleep(SETTLE_TIME)

    raw_rows, voltage_rows = read_all_row_sensors_raw_and_voltage_averaged(samples=SENSOR_SAMPLES)

    indicator_measuring.value = False

    light_rows = []
    voltage_signal_rows = []

    for row_index in range(8):
        light_value = calculate_row_light_signal(
            raw_rows[row_index],
            dark_raw[row_index],
            raw_directions[row_index]
        )

        voltage_signal = calculate_row_voltage_signal(
            voltage_rows[row_index],
            dark_voltage[row_index],
            voltage_directions[row_index]
        )

        light_rows.append(light_value)
        voltage_signal_rows.append(voltage_signal)

    return raw_rows, voltage_rows, light_rows, voltage_signal_rows


# ABSORBANCE CALCULATION FOR 8 ROWS

def calculate_8_row_absorbance(sample_light_rows, blank_light_rows):
    absorbance_rows = []
    transmittance_rows = []

    for row_index in range(8):
        i_blank = blank_light_rows[row_index]
        i_sample = sample_light_rows[row_index]

        if i_blank <= 0:
            absorbance_rows.append(None)
            transmittance_rows.append(None)

        elif i_sample <= 0:
            absorbance_rows.append(ABSORBANCE_CAP)
            transmittance_rows.append(0.0)

        else:
            transmittance = i_sample / i_blank
            transmittance_pct = transmittance * 100.0
            absorbance = -log10(transmittance)

            if absorbance < 0:
                absorbance_rows.append("ERROR_NEGATIVE_ABSORBANCE")
                transmittance_rows.append(transmittance_pct)
            else:
                absorbance_rows.append(absorbance)
                transmittance_rows.append(transmittance_pct)

    return absorbance_rows, transmittance_rows


# PRINT RESULTS

def print_8_row_sensor_results(raw_rows, voltage_rows, light_rows, voltage_signal_rows, dark_raw, dark_voltage, raw_directions):
    print("\n8-ROW PHOTODIODE READINGS")
    print("Row,Direction,DarkRawADC,RawADC,RawChangeFromDark,LightSignal,DarkVoltageV,VoltageV,LightSignalVoltageV")

    for row_index in range(8):
        row_name = ROWS[row_index]

        raw_value = raw_rows[row_index]
        voltage_value = voltage_rows[row_index]

        raw_change_from_dark = raw_value - dark_raw[row_index]

        if raw_directions[row_index] == 1:
            direction_name = "RawMinusDark"
        else:
            direction_name = "DarkMinusRaw"

        print(f"{row_name},{direction_name},{dark_raw[row_index]},{raw_value},{raw_change_from_dark},{light_rows[row_index]},{dark_voltage[row_index]:.6f},{voltage_value:.6f},{voltage_signal_rows[row_index]:.6f}")


def print_8_row_absorbance_results(
    blank_raw_rows,
    sample_raw_rows,
    blank_voltage_rows,
    sample_voltage_rows,
    blank_light_rows,
    sample_light_rows,
    blank_voltage_signal_rows,
    sample_voltage_signal_rows,
    absorbance_rows,
    transmittance_rows
):
    print("\n8-ROW ABSORBANCE RESULTS")
    print("Row,BlankRawADC,SampleRawADC,BlankVoltageV,SampleVoltageV,BlankLightSignal,SampleLightSignal,BlankLightSignalVoltageV,SampleLightSignalVoltageV,TransmittancePercent,AbsorbanceAU")

    for row_index in range(8):
        row_name = ROWS[row_index]

        blank_raw = blank_raw_rows[row_index]
        sample_raw = sample_raw_rows[row_index]

        blank_voltage = blank_voltage_rows[row_index]
        sample_voltage = sample_voltage_rows[row_index]

        blank_light = blank_light_rows[row_index]
        sample_light = sample_light_rows[row_index]

        blank_voltage_signal = blank_voltage_signal_rows[row_index]
        sample_voltage_signal = sample_voltage_signal_rows[row_index]

        transmittance = transmittance_rows[row_index]
        absorbance = absorbance_rows[row_index]

        if absorbance is None:
            print(f"{row_name},{blank_raw},{sample_raw},{blank_voltage:.6f},{sample_voltage:.6f},{blank_light},{sample_light},{blank_voltage_signal:.6f},{sample_voltage_signal:.6f},ERROR,ERROR_BLANK_TOO_LOW")

        elif isinstance(absorbance, str):
            print(f"{row_name},{blank_raw},{sample_raw},{blank_voltage:.6f},{sample_voltage:.6f},{blank_light},{sample_light},{blank_voltage_signal:.6f},{sample_voltage_signal:.6f},{transmittance:.2f},{absorbance}")

        else:
            print(f"{row_name},{blank_raw},{sample_raw},{blank_voltage:.6f},{sample_voltage:.6f},{blank_light},{sample_light},{blank_voltage_signal:.6f},{sample_voltage_signal:.6f},{transmittance:.2f},{absorbance:.4f}")


# TEST MODES

def test_8_row_photodiodes_auto():
    print("     8-ROW AUTOMATIC PHOTODIODE TEST MODE     ")
    print("This reads the 8 row ADC/photodiode channels automatically.")
    print("No button press is needed.")
    print("It does NOT scan columns and does NOT print D1-D96.")
    print()
    print("This version calibrates each row separately because some rows increase with light and some decrease with light.")
    print("After calibration, LightSignal should increase when more light hits each photodiode.")
    print()

    countdown("Cover the photodiodes completely for the DARK baseline.", 5)
    dark_raw, dark_voltage = measure_dark_baseline_raw_voltage()

    countdown("Shine light on the photodiodes for LIGHT calibration.", 5)
    light_raw, light_voltage = measure_light_calibration_raw_voltage()

    raw_directions, voltage_directions = calibrate_signal_direction(
        dark_raw,
        light_raw,
        dark_voltage,
        light_voltage
    )

    print("\nNow readings will print automatically every second.")
    print("Try room light, covered/dark, and flashlight to compare.")
    print("Focus on LightSignal. It should increase with more light.")

    while True:
        raw_rows, voltage_rows, light_rows, voltage_signal_rows = measure_8_rows_raw_voltage_signal(
            dark_raw,
            dark_voltage,
            raw_directions,
            voltage_directions
        )

        print_8_row_sensor_results(
            raw_rows,
            voltage_rows,
            light_rows,
            voltage_signal_rows,
            dark_raw,
            dark_voltage,
            raw_directions
        )

        time.sleep(READ_INTERVAL)


def test_8_row_absorbance_auto():
    print("     8-ROW AUTOMATIC ABSORBANCE TEST MODE     ")
    print("This reads absorbance from the 8 row ADC/photodiode channels.")
    print("No button press is needed.")
    print("It does NOT scan columns and does NOT print D1-D96.")
    print("You will measure DARK, LIGHT CALIBRATION, BLANK, then SAMPLE.")
    print()

    countdown("Cover the photodiodes completely for the DARK baseline.", 5)
    dark_raw, dark_voltage = measure_dark_baseline_raw_voltage()

    countdown("Shine light on the photodiodes for LIGHT calibration.", 5)
    light_raw, light_voltage = measure_light_calibration_raw_voltage()

    raw_directions, voltage_directions = calibrate_signal_direction(
        dark_raw,
        light_raw,
        dark_voltage,
        light_voltage
    )

    countdown("Place the BLANK setup.", 5)

    blank_raw_rows, blank_voltage_rows, blank_light_rows, blank_voltage_signal_rows = measure_8_rows_raw_voltage_signal(
        dark_raw,
        dark_voltage,
        raw_directions,
        voltage_directions
    )

    print("\nBlank readings:")

    print_8_row_sensor_results(
        blank_raw_rows,
        blank_voltage_rows,
        blank_light_rows,
        blank_voltage_signal_rows,
        dark_raw,
        dark_voltage,
        raw_directions
    )

    sample_number = 1

    while True:
        countdown(f"Place SAMPLE setup #{sample_number}.", 5)

        sample_raw_rows, sample_voltage_rows, sample_light_rows, sample_voltage_signal_rows = measure_8_rows_raw_voltage_signal(
            dark_raw,
            dark_voltage,
            raw_directions,
            voltage_directions
        )

        print("\nSample readings:")

        print_8_row_sensor_results(
            sample_raw_rows,
            sample_voltage_rows,
            sample_light_rows,
            sample_voltage_signal_rows,
            dark_raw,
            dark_voltage,
            raw_directions
        )

        absorbance_rows, transmittance_rows = calculate_8_row_absorbance(
            sample_light_rows,
            blank_light_rows
        )

        print_8_row_absorbance_results(
            blank_raw_rows,
            sample_raw_rows,
            blank_voltage_rows,
            sample_voltage_rows,
            blank_light_rows,
            sample_light_rows,
            blank_voltage_signal_rows,
            sample_voltage_signal_rows,
            absorbance_rows,
            transmittance_rows
        )

        sample_number += 1




test_8_row_photodiodes_auto()

# test_8_row_absorbance_auto()