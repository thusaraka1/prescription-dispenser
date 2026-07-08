# ==========================================
# SMD Kiosk Configuration
# ==========================================

# Firebase Realtime Database URL (same as the Doctor's Dashboard)
FIREBASE_URL = 'https://doctor-438b7-default-rtdb.asia-southeast1.firebasedatabase.app'

# Flask server settings
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = True

# Hardware settings
# GPIO pin mapping for dispensing servo motors (BCM numbering)
# Each slot corresponds to a medicine compartment in the dispenser
SERVO_PINS = {
    0: 17,   # Slot 0 → GPIO 17
    1: 27,   # Slot 1 → GPIO 27
    2: 22,   # Slot 2 → GPIO 22
    3: 23,   # Slot 3 → GPIO 23
    4: 24,   # Slot 4 → GPIO 24
    5: 25,   # Slot 5 → GPIO 25
}

# Dispensing timing (seconds)
DISPENSE_DELAY_PER_UNIT = 0.8      # Time to dispense one pill/unit
DISPENSE_SLOT_TRANSITION = 0.5     # Delay between switching slots
SERVO_OPEN_ANGLE = 90              # Servo angle to open gate
SERVO_CLOSE_ANGLE = 0              # Servo angle to close gate

# Kiosk behavior
AUTO_RETURN_TIMEOUT = 10           # Seconds before auto-returning to home screen
SCAN_INPUT_TIMEOUT = 30            # Seconds to wait for barcode scan

# Manual dispense limits
MANUAL_MIN_QUANTITY = 2
MANUAL_MAX_QUANTITY = 18
