# ==========================================
# Hardware Abstraction Layer
# ==========================================
# Provides a unified interface for dispensing hardware.
# On Raspberry Pi: Uses RPi.GPIO to control servo motors.
# On Windows/Dev: Simulates dispensing with delays and console output.

import time
import platform
import logging

logger = logging.getLogger(__name__)


def is_raspberry_pi():
    """Detect if running on a Raspberry Pi."""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        return 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo
    except FileNotFoundError:
        return False


class HardwareController:
    """
    Controls the physical dispensing mechanism.
    Automatically detects whether running on Raspberry Pi or dev machine.
    """

    def __init__(self, servo_pins=None, simulation=None):
        """
        Args:
            servo_pins: Dict mapping slot numbers to GPIO pin numbers (BCM).
            simulation: Force simulation mode (True/False). Auto-detects if None.
        """
        from config import SERVO_PINS, SERVO_OPEN_ANGLE, SERVO_CLOSE_ANGLE

        self.servo_pins = servo_pins or SERVO_PINS
        self.open_angle = SERVO_OPEN_ANGLE
        self.close_angle = SERVO_CLOSE_ANGLE
        self.servos = {}

        if simulation is not None:
            self.simulation = simulation
        else:
            self.simulation = not is_raspberry_pi()

        if self.simulation:
            logger.info("🖥️  Hardware running in SIMULATION mode (no GPIO)")
        else:
            self._init_gpio()

    def _init_gpio(self):
        """Initialize GPIO pins for servo motors on Raspberry Pi."""
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            for slot, pin in self.servo_pins.items():
                GPIO.setup(pin, GPIO.OUT)
                pwm = GPIO.PWM(pin, 50)  # 50Hz for standard servos
                pwm.start(0)
                self.servos[slot] = pwm
                logger.info(f"✅ Servo initialized on GPIO {pin} for slot {slot}")

        except ImportError:
            logger.warning("RPi.GPIO not available, falling back to simulation")
            self.simulation = True
        except Exception as e:
            logger.error(f"GPIO init error: {e}, falling back to simulation")
            self.simulation = True

    def _angle_to_duty(self, angle):
        """Convert angle (0-180) to PWM duty cycle (2-12)."""
        return 2 + (angle / 18)

    def dispense(self, slot, quantity, progress_callback=None):
        """
        Dispense a given quantity of medicine from a slot.

        Args:
            slot: Slot number (int) for the medicine compartment.
            quantity: Number of units to dispense.
            progress_callback: Optional function(dispensed, total) called after each unit.

        Returns:
            dict with 'success', 'dispensed', 'slot' keys.
        """
        from config import DISPENSE_DELAY_PER_UNIT

        logger.info(f"💊 Dispensing {quantity} units from slot {slot}")

        if self.simulation:
            return self._simulate_dispense(slot, quantity, progress_callback)
        else:
            return self._gpio_dispense(slot, quantity, progress_callback)

    def _simulate_dispense(self, slot, quantity, progress_callback=None):
        """Simulate dispensing with time delays."""
        from config import DISPENSE_DELAY_PER_UNIT

        logger.info(f"  [SIM] Opening slot {slot} gate...")
        time.sleep(0.3)

        for i in range(1, quantity + 1):
            time.sleep(DISPENSE_DELAY_PER_UNIT)
            logger.info(f"  [SIM] Dispensed unit {i}/{quantity} from slot {slot}")
            if progress_callback:
                progress_callback(i, quantity)

        logger.info(f"  [SIM] Closing slot {slot} gate...")
        time.sleep(0.3)

        return {'success': True, 'dispensed': quantity, 'slot': slot}

    def _gpio_dispense(self, slot, quantity, progress_callback=None):
        """Dispense using actual servo motors."""
        from config import DISPENSE_DELAY_PER_UNIT

        if slot not in self.servos:
            logger.error(f"Slot {slot} not configured!")
            return {'success': False, 'dispensed': 0, 'slot': slot, 'error': 'Invalid slot'}

        pwm = self.servos[slot]

        try:
            # Open the gate
            duty = self._angle_to_duty(self.open_angle)
            pwm.ChangeDutyCycle(duty)
            time.sleep(0.5)

            for i in range(1, quantity + 1):
                # Pulse to release one unit
                pwm.ChangeDutyCycle(self._angle_to_duty(self.close_angle))
                time.sleep(DISPENSE_DELAY_PER_UNIT / 2)
                pwm.ChangeDutyCycle(self._angle_to_duty(self.open_angle))
                time.sleep(DISPENSE_DELAY_PER_UNIT / 2)

                logger.info(f"  [GPIO] Dispensed unit {i}/{quantity} from slot {slot}")
                if progress_callback:
                    progress_callback(i, quantity)

            # Close the gate
            pwm.ChangeDutyCycle(self._angle_to_duty(self.close_angle))
            time.sleep(0.3)
            pwm.ChangeDutyCycle(0)  # Stop signal to prevent jitter

            return {'success': True, 'dispensed': quantity, 'slot': slot}

        except Exception as e:
            logger.error(f"GPIO dispense error: {e}")
            pwm.ChangeDutyCycle(0)
            return {'success': False, 'dispensed': 0, 'slot': slot, 'error': str(e)}

    def cleanup(self):
        """Release GPIO resources."""
        if not self.simulation:
            try:
                for pwm in self.servos.values():
                    pwm.stop()
                self.GPIO.cleanup()
                logger.info("GPIO cleaned up")
            except Exception as e:
                logger.error(f"GPIO cleanup error: {e}")
