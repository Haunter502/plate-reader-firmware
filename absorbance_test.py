import time
import math
import board
import digitalio
import pwmio
import adafruit_aw9523
import adc  # Helper functions reading A0 for photodiode

# ==========================================================
# 1. HARDWARE CONFIGURATION & PIN MAPPING
# ==========================================================

# LED on QT Py Native Pin A1 (Leaves A0 free for ADC)
LED_PIN = board.A1
led_pwm = pwmio.PWMOut(LED_PIN, frequency=5000, duty_cycle=0)

# Target Brightness: 0 to 65535
TARGET_BRIGHTNESS = 65535  

# AW9523 Expander Setup
i2c = board.STEMMA_I2C()
aw = adafruit_aw9523.AW9523(i2c)
aw.pin_modes = 0x0000  # Push-pull mode

INDICATOR_1_PIN = 3    # Expander Pin 3: Prompt
INDICATOR_2_PIN = 4    # Expander Pin 4: Reading Active

indicator1 = aw.get_pin(INDICATOR_1_PIN)
indicator1.switch_to_output(value=False)

indicator2 = aw.get_pin(INDICATOR_2_PIN)
indicator2.switch_to_output(value=False)

# Physical Button on QT Py Pin A2
button = digitalio.DigitalInOut(board.A2)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP  # Active LOW

# Auto-calibrate dark baseline on boot with LED OFF
print("Calibrating Ambient Dark Baseline (LED OFF)...")
time.sleep(0.1)
DARK_BASELINE = adc.read_plate(32)
print(f"✓ Dynamic Dark Baseline set to: {DARK_BASELINE}")

# ==========================================================
# 2. HELPER FUNCTIONS
# ==========================================================

def turn_on_led():
    led_pwm.duty_cycle = TARGET_BRIGHTNESS

def turn_off_led():
    led_pwm.duty_cycle = 0

def wait_for_user(prompt_message):
    print(f"\n====================================")
    print(f"[ACTION REQUIRED] {prompt_message}")
    print("--> Insert cuvette and press physical button (A2)...")
    print("====================================")
    
    indicator1.value = True
    while button.value:
        time.sleep(0.01)
    indicator1.value = False
    time.sleep(0.3)

def flash_and_read():
    print(f"\n[Measuring...] Flashing LED on A1 (Brightness: {TARGET_BRIGHTNESS}/65535)...")
    
    turn_on_led()
    indicator2.value = True
    
    time.sleep(0.1)
    raw = adc.read_plate(32)
    
    turn_off_led()
    indicator2.value = False
    
    net_light = max(0, raw - DARK_BASELINE)
    return raw, net_light

def run_spectrometer():
    print("====================================")
    print("     SPECTROMETER SYSTEM READY      ")
    print(f"    Active Light Source: Pin A1 (PWM)")
    print("====================================")

    # STEP 1: CALIBRATION
    wait_for_user("Place your BLANK cuvette into the spectrometer.")

    raw_blank, i_blank = flash_and_read()

    print("------------------------------------")
    print(f"Dark Baseline (OFF)  : {DARK_BASELINE}")
    print(f"Blank Raw Reading    : {raw_blank}")
    print(f"Blank Net Signal (I0): {i_blank}")
    print("------------------------------------")

    if i_blank <= 0:
        print("\n[ERROR] Calibration failed: No light delta detected on photodiode!")
        return

    print("✓ Calibration complete! Baseline stored.")

    # STEP 2: TEST SAMPLES
    sample_num = 1
    while True:
        wait_for_user(f"Place TEST SAMPLE #{sample_num} cuvette into the spectrometer.")
        
        raw_sample, i_sample = flash_and_read()
        
        if i_sample <= 0:
            absorbance = 3.0
            transmittance_pct = 0.0
        else:
            transmittance = i_sample / i_blank
            transmittance_pct = transmittance * 100.0
            absorbance = -math.log(transmittance, 10)
            if absorbance < 0:
                absorbance = 0.0

        print("------------------------------------")
        print(f"Sample #{sample_num} Raw Reading   : {raw_sample}")
        print(f"Transmittance (%T)      : {transmittance_pct:.2f}%")
        print(f"Absorbance (A)          : {absorbance:.4f} AU")
        print("------------------------------------")
        
        sample_num += 1

if __name__ == "__main__":
    run_spectrometer()