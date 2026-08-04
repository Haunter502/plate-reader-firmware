import time
import board
import adafruit_aw9523
import adc


COLUMN_PINS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
INDICATOR_WAITING_PIN = 14
INDICATOR_MEASURING_PIN = 15

SETTLE_TIME = 0.05

SENSOR_SAMPLES = 8
DARK_SAMPLES = 8


i2c = board.STEMMA_I2C()
aw = adafruit_aw9523.AW9523(i2c)


column_pins = []

for pin_num in COLUMN_PINS:
    pin = aw.get_pin(pin_num)
    pin.switch_to_output(value=False)
    column_pins.append(pin)


indicator_waiting = aw.get_pin(INDICATOR_WAITING_PIN)
indicator_waiting.switch_to_output(value=False)

indicator_measuring = aw.get_pin(INDICATOR_MEASURING_PIN)
indicator_measuring.switch_to_output(value=False)


def all_columns_low():
    for pin in column_pins:
        pin.value = False


def select_column(column_index):
    all_columns_low()
    time.sleep(SETTLE_TIME)

    column_pins[column_index].value = True
    time.sleep(SETTLE_TIME)


def read_8_rows(samples=SENSOR_SAMPLES):
    raw_rows, voltage_rows = adc.read_all_sensors_raw_and_voltage_averaged(samples=samples)

    if len(raw_rows) != 8:
        raise RuntimeError("raw_rows must have exactly 8 values.")

    if len(voltage_rows) != 8:
        raise RuntimeError("voltage_rows must have exactly 8 values.")

    return raw_rows, voltage_rows


def diode_name(column_index, row_index):
    diode_number = row_index * 12 + column_index + 1
    return "D" + str(diode_number)


def countdown(message, seconds):
    print("")
    print("[ACTION REQUIRED]")
    print(message)

    indicator_waiting.value = True

    for seconds_left in range(seconds, 0, -1):
        print("Starting in", seconds_left)
        time.sleep(1)

    indicator_waiting.value = False
    print("Measuring now.")


def measure_dark_baseline_96():
    print("")
    print("Measuring DARK baseline for all 96 photodiodes...")

    dark_raw_grid = []
    dark_voltage_grid = []

    indicator_measuring.value = True

    for column_index in range(12):
        print("Measuring dark baseline for column", column_index + 1, "of 12")

        select_column(column_index)

        dark_raw_rows, dark_voltage_rows = read_8_rows(samples=DARK_SAMPLES)

        dark_raw_grid.append(dark_raw_rows)
        dark_voltage_grid.append(dark_voltage_rows)

        print("Finished dark baseline for column", column_index + 1)

    indicator_measuring.value = False
    all_columns_low()

    print("")
    print("DARK BASELINE COMPLETE")
    print("Photodiode,ColumnNumber,DarkRawADC,DarkVoltageV")

    for column_index in range(12):
        column_number = column_index + 1

        for row_index in range(8):
            name = diode_name(column_index, row_index)
            dark_raw = dark_raw_grid[column_index][row_index]
            dark_voltage = dark_voltage_grid[column_index][row_index]

            print(f"{name},{column_number},{dark_raw},{dark_voltage:.6f}")

    return dark_raw_grid, dark_voltage_grid


def scan_96_condition(dark_raw_grid, dark_voltage_grid, condition_name):
    print("")
    print("Measuring", condition_name, "for all 96 photodiodes...")

    raw_grid = []
    voltage_grid = []
    light_signal_grid = []
    voltage_signal_grid = []

    indicator_measuring.value = True

    for column_index in range(12):
        print("Measuring", condition_name, "for column", column_index + 1, "of 12")

        select_column(column_index)

        raw_rows, voltage_rows = read_8_rows(samples=SENSOR_SAMPLES)

        light_signal_rows = []
        voltage_signal_rows = []

        for row_index in range(8):
            dark_raw = dark_raw_grid[column_index][row_index]
            dark_voltage = dark_voltage_grid[column_index][row_index]

            raw_value = raw_rows[row_index]
            voltage_value = voltage_rows[row_index]

            light_signal = abs(raw_value - dark_raw)
            voltage_signal = abs(voltage_value - dark_voltage)

            light_signal_rows.append(light_signal)
            voltage_signal_rows.append(voltage_signal)

        raw_grid.append(raw_rows)
        voltage_grid.append(voltage_rows)
        light_signal_grid.append(light_signal_rows)
        voltage_signal_grid.append(voltage_signal_rows)

        print("Finished", condition_name, "for column", column_index + 1)

    indicator_measuring.value = False
    all_columns_low()

    return raw_grid, voltage_grid, light_signal_grid, voltage_signal_grid


def print_96_condition_results(condition_name, raw_grid, voltage_grid, light_signal_grid, voltage_signal_grid, dark_raw_grid, dark_voltage_grid):
    print("")
    print(condition_name, "RESULTS")
    print("Condition,Photodiode,ColumnNumber,DarkRawADC,RawADC,RawChangeFromDark,LightSignal,DarkVoltageV,VoltageV,LightSignalVoltageV")

    for column_index in range(12):
        column_number = column_index + 1

        for row_index in range(8):
            name = diode_name(column_index, row_index)

            dark_raw = dark_raw_grid[column_index][row_index]
            raw_value = raw_grid[column_index][row_index]
            raw_change_from_dark = raw_value - dark_raw

            dark_voltage = dark_voltage_grid[column_index][row_index]
            voltage_value = voltage_grid[column_index][row_index]

            light_signal = light_signal_grid[column_index][row_index]
            voltage_signal = voltage_signal_grid[column_index][row_index]

            print(f"{condition_name},{name},{column_number},{dark_raw},{raw_value},{raw_change_from_dark},{light_signal},{dark_voltage:.6f},{voltage_value:.6f},{voltage_signal:.6f}")


def run_96_dark_natural_led_test():
    print("96-PHOTODIODE DARK / NATURAL LIGHT / LED TEST")
    print("This scans 12 columns.")
    print("For each column, it reads 8 photodiodes.")
    print("No light calibration.")
    print("It will measure DARK first, then NATURAL LIGHT, then LED ON TOP.")

    countdown("Cover the photodiodes completely for DARK baseline.", 7)

    dark_raw_grid, dark_voltage_grid = measure_dark_baseline_96()

    countdown("Uncover the photodiodes and leave them under NATURAL / ROOM LIGHT.", 7)

    natural_raw_grid, natural_voltage_grid, natural_light_grid, natural_voltage_signal_grid = scan_96_condition(
        dark_raw_grid,
        dark_voltage_grid,
        "NATURAL_LIGHT"
    )

    print_96_condition_results(
        "NATURAL_LIGHT",
        natural_raw_grid,
        natural_voltage_grid,
        natural_light_grid,
        natural_voltage_signal_grid,
        dark_raw_grid,
        dark_voltage_grid
    )



    
    countdown("Shine the LED or flashlight on top of the photodiodes.", 7)

    led_raw_grid, led_voltage_grid, led_light_grid, led_voltage_signal_grid = scan_96_condition(
        dark_raw_grid,
        dark_voltage_grid,
        "LED_ON_TOP"
    )
    
    print_96_condition_results(
        "LED_ON_TOP",
        led_raw_grid,
        led_voltage_grid,
        led_light_grid,
        led_voltage_signal_grid,
        dark_raw_grid,
        dark_voltage_grid
    )

    print("")
    print("TEST COMPLETE")
    print("Compare LightSignal values:")
    print("Dark baseline should be lowest.")
    print("Natural light should be higher.")
    print("LED on top should usually be highest.")


run_96_dark_natural_led_test()