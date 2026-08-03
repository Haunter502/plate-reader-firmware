import time
import math
import board
import digitalio
import adafruit_aw9523
import adc  


# MATH HELPER

def log10(x):
  
    return math.log(x) / 2.302585092994046


# PLATE / DIODE LAYOUT

ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"]
COLUMNS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]


def get_diode_label(row_index, col_index): 
    """
    Converts row/column position into diode label.

    The board labels increase left-to-right across each row:

    Row A: D1   D2   D3   ... D12
    Row B: D13  D14  D15  ... D24
    Row C: D25  D26  D27  ... D36
    ...
    Row H: D85  D86  D87  ... D96

    Since the code scans by columns, column 1 outputs:
    D1, D13, D25, D37, D49, D61, D73, D85
    """
    diode_number = row_index * 12 + col_index + 1
    return f"D{diode_number}"


# HARDWARE PIN MAPPING

# ASSUMPTION:
# These AW9523 pins control the 12 LED columns.
COLUMN_LED_PINS = [
    0,   # column 1 LED
    1,   # column 2 LED
    2,   # column 3 LED
    3,   # column 4 LED
    4,   # column 5 LED
    5,   # column 6 LED
    6,   # column 7 LED
    7,   # column 8 LED
    8,   # column 9 LED
    9,   # column 10 LED
    10,  # column 11 LED
    11   # column 12 LED
]

# Indicator LEDs
INDICATOR_WAITING_PIN = 14
INDICATOR_MEASURING_PIN = 15

# Button on microcontroller pin A2
button = digitalio.DigitalInOut(board.A2)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP  # Active LOW

# I2C connection to AW9523 GPIO expander
i2c = board.STEMMA_I2C()
aw = adafruit_aw9523.AW9523(i2c)

# Set up the column LEDs
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

SETTLE_TIME = 0.05        # time for LED/sensor to stabilize
SENSOR_SAMPLES = 16       # number of readings adc.py averages per measurement
DARK_SAMPLES = 32         # number of readings adc.py averages for dark baseline
ABSORBANCE_CAP = 3.0      # used if almost no light reaches sensor


# HELPER FUNCTIONS


def wait_for_user(message):
    """
    Waits for user to press the button before continuing.
    """

    print("\n[ACTION REQUIRED]")
    print(message)
    print("Press button A2 when ready.")

    indicator_waiting.value = True

    while button.value:
        time.sleep(0.01)

    indicator_waiting.value = False
    time.sleep(0.5)  # debounce delay


def all_column_leds_off():
    """
    Turns off every column LED.
    """
    for led in column_leds:
        led.value = False


def read_all_row_sensors_averaged(samples=SENSOR_SAMPLES):
    """
    Reads all 8 row sensors using the updated adc.py file.

    Your adc.py should have this function:
        adc.read_all_sensors_averaged(samples=...)

    It should return 8 values in this order:
        [A, B, C, D, E, F, G, H]
    """

    readings = adc.read_all_sensors_averaged(samples=samples)

    if len(readings) != 8:
        raise RuntimeError("adc.read_all_sensors_averaged() must return exactly 8 readings.")

    return readings



# TEST LED MAPPING

def test_column_leds():
    """
    Turns on each column LED one at a time.

    Use this to figure out whether:
    AW9523 pin 0 really controls column 1,
    AW9523 pin 1 really controls column 2, etc.
    """


    print("TESTING COLUMN LEDS")
 

    for i in range(12):
        all_column_leds_off()

        print(f"Turning on AW9523 pin {COLUMN_LED_PINS[i]}. "
              f"Code thinks this is column {i + 1}.")

        column_leds[i].value = True
        time.sleep(1.0)

    all_column_leds_off()
    print("LED test complete.")


# MEASURE DARK BASELINE

def measure_dark_baseline():
    """
    Measures row sensor readings when all LEDs are off.

    This gives background noise / ambient light for each row sensor.
    The code subtracts this from later readings.
    """

    print("\nMeasuring dark baseline...")
    all_column_leds_off()
    time.sleep(SETTLE_TIME)

    dark_baseline = read_all_row_sensors_averaged(samples=DARK_SAMPLES)

    print("\nDark baseline readings:")
    for i in range(8):
        print(f"Row {ROWS[i]} dark baseline: {dark_baseline[i]}")

    return dark_baseline


# MEASURE ONE COLUMN

def measure_column(column_index, dark_baseline):
    """
    Turns on one column LED and reads all 8 row sensors.

    Example:
    If column_index = 0, this measures column 1.

    Since the diode labels go left-to-right by row, column 1 gives:
    Row A = D1
    Row B = D13
    Row C = D25
    Row D = D37
    Row E = D49
    Row F = D61
    Row G = D73
    Row H = D85
    """

    all_column_leds_off()

    print(f"\nMeasuring column {column_index + 1}...")

    # Turn on the LED for this column
    column_leds[column_index].value = True
    indicator_measuring.value = True

    # Wait for LED and sensors to stabilize
    time.sleep(SETTLE_TIME)

    # Read all 8 row sensors from adc.py
    raw_readings = read_all_row_sensors_averaged(samples=SENSOR_SAMPLES)

    # Turn LED off after reading
    column_leds[column_index].value = False
    indicator_measuring.value = False

    # Subtract dark baseline from each row reading
    net_readings = []

    for row_index in range(8):
        net_value = raw_readings[row_index] - dark_baseline[row_index]

        if net_value < 0:
            net_value = 0

        net_readings.append(net_value)

    return raw_readings, net_readings


# SCAN PLATE

def scan_plate(dark_baseline):
    """
    Scans the full plate.

    The code scans by column:
    - Turn on column 1 LED
    - Read all 8 row sensors
    - Turn off column 1 LED
    - Repeat for columns 2-12

    Returns:
        raw_grid = original ADC readings
        net_grid = readings after dark baseline subtraction
    """

    raw_grid = []
    net_grid = []

    for _ in range(8):
        raw_grid.append([0] * 12)
        net_grid.append([0] * 12)

    print("\nScanning plate by columns...")

    for col_index in range(12):
        raw_rows, net_rows = measure_column(col_index, dark_baseline)

        for row_index in range(8):
            raw_grid[row_index][col_index] = raw_rows[row_index]
            net_grid[row_index][col_index] = net_rows[row_index]

    all_column_leds_off()

    return raw_grid, net_grid


# CALCULATE ABSORBANCE

def calculate_absorbance(sample_net_grid, blank_net_grid):
    """
    Calculates absorbance for every diode/well.

    A = -log10(I_sample / I_blank)

    I_blank = net light reading from blank well
    I_sample = net light reading from sample well
    """

    absorbance_grid = []
    transmittance_grid = []

    for _ in range(8):
        absorbance_grid.append([0] * 12)
        transmittance_grid.append([0] * 12)

    for row_index in range(8):
        for col_index in range(12):

            i_blank = blank_net_grid[row_index][col_index]
            i_sample = sample_net_grid[row_index][col_index]

            if i_blank <= 0:
                absorbance_grid[row_index][col_index] = None
                transmittance_grid[row_index][col_index] = None

            elif i_sample <= 0:
                absorbance_grid[row_index][col_index] = ABSORBANCE_CAP
                transmittance_grid[row_index][col_index] = 0.0

            else:
                transmittance = i_sample / i_blank
                transmittance_pct = transmittance * 100.0
                absorbance = -log10(transmittance)

                # If sample is brighter than blank, absorbance becomes negative.
                # Do NOT hide this as 0. Report it as an error.
                if absorbance < 0:
                    absorbance_grid[row_index][col_index] = "ERROR_NEGATIVE_ABSORBANCE"
                    transmittance_grid[row_index][col_index] = transmittance_pct
                else:
                    absorbance_grid[row_index][col_index] = absorbance
                    transmittance_grid[row_index][col_index] = transmittance_pct

    return absorbance_grid, transmittance_grid


# PRINT RESULTS

def print_results(sample_raw_grid, sample_net_grid, blank_net_grid,
                  absorbance_grid, transmittance_grid):
    """
    Prints results in CSV format using diode labels D1-D96.

    Output order follows the scanning order:
    column 1 first, then column 2, etc.

    So the output starts:
    D1, D13, D25, D37, D49, D61, D73, D85,
    then D2, D14, D26, etc.
    """

    print("\n96-DIODE PLATE RESULTS")
    print("Diode,RawSample,NetSample,NetBlank,TransmittancePercent,AbsorbanceAU")

    # Column-first loop because the physical scan happens by column
    for col_index in range(12):
        for row_index in range(8):

            diode_name = get_diode_label(row_index, col_index)

            raw_sample = sample_raw_grid[row_index][col_index]
            net_sample = sample_net_grid[row_index][col_index]
            net_blank = blank_net_grid[row_index][col_index]
            transmittance = transmittance_grid[row_index][col_index]
            absorbance = absorbance_grid[row_index][col_index]

            if absorbance is None:
                print(f"{diode_name},{raw_sample},{net_sample},{net_blank},ERROR,ERROR")
            elif isinstance(absorbance, str):
                print(
                    f"{diode_name},"
                    f"{raw_sample},"
                    f"{net_sample},"
                    f"{net_blank},"
                    f"{transmittance:.2f},"
                    f"{absorbance}"
                )
            else:
                print(
                    f"{diode_name},"
                    f"{raw_sample},"
                    f"{net_sample},"
                    f"{net_blank},"
                    f"{transmittance:.2f},"
                    f"{absorbance:.4f}"
                )


def print_raw_diode_values(raw_grid):
    """
    Optional simple output:
    Prints only D-label = raw value.

    This matches what Alice asked for:
    D1 = value, D2 = value, etc.

    This prints in column-scanning order:
    D1, D13, D25... then D2, D14, D26...
    """

    print("\nRAW DIODE VALUES")
    for col_index in range(12):
        for row_index in range(8):
            diode_name = get_diode_label(row_index, col_index)
            value = raw_grid[row_index][col_index]
            print(f"{diode_name} = {value}")


# MAIN PLATE READER WORKFLOW


def run_plate_reader():
    print("      96-DIODE PLATE READER READY    ")

    # First time testing hardware, uncomment this line:
    # test_column_leds()

    dark_baseline = measure_dark_baseline()

    wait_for_user("Place the BLANK plate in the reader. Each well should contain blank solution, like water or buffer.")
    blank_raw_grid, blank_net_grid = scan_plate(dark_baseline)

    print("\nBlank plate calibration complete.")

    sample_number = 1

    while True:
        wait_for_user(f"Place SAMPLE plate #{sample_number} in the reader.")

        sample_raw_grid, sample_net_grid = scan_plate(dark_baseline)

        # Simple D1 = value output
        print_raw_diode_values(sample_raw_grid)

        # Full absorbance output
        absorbance_grid, transmittance_grid = calculate_absorbance(
            sample_net_grid,
            blank_net_grid
        )

        print_results(
            sample_raw_grid,
            sample_net_grid,
            blank_net_grid,
            absorbance_grid,
            transmittance_grid
        )

        sample_number += 1


# run_plate_reader()


# TEMPORARY 96-WELL PHOTODIODE / ROW SENSOR TEST


def test_96_well_photodiodes_only():

    print("     96-WELL PHOTODIODE TEST MODE    ")
 
    print("This tests the row photodiode/sensor readings only.")
    print("Try covering the sensor area, using room light, or shining light through the plate.")
    print("Stop the program when done.\n")

    while True:
        readings = read_all_row_sensors_averaged(samples=SENSOR_SAMPLES)

        print("Sensor readings:")
        for i in range(8):
            print(f"Row {ROWS[i]} sensor: {readings[i]}")

        print("------------------------------------")
        time.sleep(0.5)



# TEMPORARY 96-WELL PHOTODIODE + ABSORBANCE TEST

def test_96_well_photodiodes_absorbance_only():

    print("     96-WELL PHOTODIODE + ABSORBANCE TEST MODE    ")
    print("This tests the row photodiode/sensor readings AND absorbance calculation.")
    print("You will measure DARK, then BLANK, then SAMPLE.\n")

    # 1. DARK BASELINE
    wait_for_user("Block the light / cover the sensors for the DARK baseline.")
    dark_baseline = read_all_row_sensors_averaged(samples=DARK_SAMPLES)

    print("\nDark baseline readings:")
    for i in range(8):
        print(f"Row {ROWS[i]} dark: {dark_baseline[i]}")

    # 2. BLANK READING
    wait_for_user("Place the BLANK, like water or buffer, then press the button.")
    blank_raw = read_all_row_sensors_averaged(samples=SENSOR_SAMPLES)

    blank_net = []
    for i in range(8):
        net_value = blank_raw[i] - dark_baseline[i]
        if net_value < 0:
            net_value = 0
        blank_net.append(net_value)

    print("\nBlank readings:")
    for i in range(8):
        print(f"Row {ROWS[i]} blank raw: {blank_raw[i]}   blank net: {blank_net[i]}")

    # 3. SAMPLE READING
    wait_for_user("Place the SAMPLE, like dye solution, then press the button.")
    sample_raw = read_all_row_sensors_averaged(samples=SENSOR_SAMPLES)

    sample_net = []
    for i in range(8):
        net_value = sample_raw[i] - dark_baseline[i]
        if net_value < 0:
            net_value = 0
        sample_net.append(net_value)

    print("\nSample readings:")
    for i in range(8):
        print(f"Row {ROWS[i]} sample raw: {sample_raw[i]}   sample net: {sample_net[i]}")

    # 4. ABSORBANCE CALCULATION
    print("\nABSORBANCE RESULTS")
    print("Row,BlankNet,SampleNet,TransmittancePercent,AbsorbanceAU")

    for i in range(8):
        i_blank = blank_net[i]
        i_sample = sample_net[i]

        if i_blank <= 0:
            print(f"{ROWS[i]},{i_blank},{i_sample},ERROR,ERROR_BLANK_TOO_LOW")

        elif i_sample <= 0:
            print(f"{ROWS[i]},{i_blank},{i_sample},0.00,{ABSORBANCE_CAP}")

        else:
            transmittance = i_sample / i_blank
            transmittance_pct = transmittance * 100.0
            absorbance = -log10(transmittance)

            if absorbance < 0:
                print(f"{ROWS[i]},{i_blank},{i_sample},{transmittance_pct:.2f},ERROR_NEGATIVE_ABSORBANCE")
            else:
                print(f"{ROWS[i]},{i_blank},{i_sample},{transmittance_pct:.2f},{absorbance:.4f}")



# run_plate_reader()
# test_96_well_photodiodes_only()
test_96_well_photodiodes_absorbance_only()