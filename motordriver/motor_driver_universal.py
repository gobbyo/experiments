from machine import Pin, PWM
import uasyncio as asyncio

# Driver module for controlling motors with PWM speed control
# Supports both L293x (dual motor) and L9110 (single motor) drivers
# Provides `motorDriver` class and helper functions to create and test motors.
# Designed for use with MicroPython on microcontrollers.

# System constants
MOTOR_PWM_FREQUENCY = 20  # Hz (lowered from 50Hz for better low-speed control)

# ========== CONFIGURATION ==========
# Select driver type: 'L293x' for dual motors or 'L9110' for single motor
DRIVER_TYPE = 'L9110'  # Change to 'L9110' for single motor configuration

# L293x Configuration (Dual Motor)
if DRIVER_TYPE == 'L293x':
    # Default speed PWM pins (can be overridden by importing module)
    SPEED1_PIN = 20  # primary speed pin for motor 1
    SPEED2_PIN = 21  # default speed pin for motor 2
    
    # Motor tuples (CCW pin, CW pin)
    motor1 = (16, 17)
    motor2 = (18, 19)
    motor_pins = [motor1, motor2]

# L9110 Configuration (Single Motor)
elif DRIVER_TYPE == 'L9110':
    # L9110 pins for single motor
    # Motor tuples (CCW pin, CW pin)
    motor1 = (17, 16)
    motor_pins = [motor1]


def create_motors(speed1=None, speed2=None):
    """Create `motorDriver` instance(s) based on configured driver type.
    
    For L293x: Returns (m1, m2) - two motor instances
    For L9110: Returns m1 - single motor instance
    """
    if DRIVER_TYPE == 'L293x':
        if speed1 is None:
            speed1 = SPEED1_PIN
        if speed2 is None:
            speed2 = SPEED2_PIN
        
        ccw1, cw1 = motor_pins[0]
        ccw2, cw2 = motor_pins[1]
        m1 = motorDriver(speed1, cw1, ccw1)
        m2 = motorDriver(speed2, cw2, ccw2)
        return m1, m2
    
    elif DRIVER_TYPE == 'L9110':
        ccw, cw = motor_pins[0]
        m1 = motorDriver(speed1, cw, ccw)
        return m1


async def run_motor(motor, pause_ms=200, ramp_kwargs=None):
    """Run a single motor: ramp clockwise then counterclockwise."""
    if ramp_kwargs is None:
        ramp_kwargs = {}
    await motor.ramp('clockwise', **ramp_kwargs)
    await asyncio.sleep_ms(pause_ms)
    await motor.ramp('counterclockwise', **ramp_kwargs)
    motor.stop()


def test_motors():
    """Test: run motor(s) based on driver type."""
    ramp_kwargs = {'steps': 40, 'step_ms': 50, 'max_pct': 1}

    async def _runner():
        if DRIVER_TYPE == 'L293x':
            m1, m2 = create_motors()
            t1 = asyncio.create_task(run_motor(m1, ramp_kwargs=ramp_kwargs))
            t2 = asyncio.create_task(run_motor(m2, ramp_kwargs=ramp_kwargs))
            await asyncio.gather(t1, t2)
            m1.stop()
            m2.stop()
        
        elif DRIVER_TYPE == 'L9110':
            m1 = create_motors()
            t1 = asyncio.create_task(run_motor(m1, ramp_kwargs=ramp_kwargs))
            await asyncio.gather(t1)
            m1.stop()

    try:
        asyncio.run(_runner())
    finally:
        pass


class motorDriver:
    def __init__(self, speedPin, cwPin, ccwPin):
        # For L9110, speedPin can be None - use cwPin for PWM control
        # For L293x, speedPin is required
        # remember pins
        self._speed_pin = speedPin if speedPin is not None else cwPin
        self._cw_pin = cwPin
        self._ccw_pin = ccwPin

        # create PWM on the speed pin
        self.speed = PWM(Pin(self._speed_pin))
        self.speed.freq(MOTOR_PWM_FREQUENCY)

        # create direction pins
        self.cw = Pin(cwPin, Pin.OUT)
        self.ccw = Pin(ccwPin, Pin.OUT)

        # track current speed percentage
        self._current_pct = 0.0

        # ensure motors start stopped
        self.stop()

    def set_speed(self, pct):
        """Set motor speed as percentage (0-100)."""
        try:
            self.speed.duty_u16(int((pct / 100) * 65535))
            # remember current percent
            try:
                self._current_pct = float(pct)
            except Exception:
                self._current_pct = 0.0
        except Exception:
            pass

    async def clockwise(self, motor_speed, waitTime):
        """Run motor clockwise at `motor_speed` (%) for `waitTime` seconds (async)."""
        try:
            self.set_speed(motor_speed)
            self.ccw.off()
            self.cw.on()
            await asyncio.sleep(waitTime)
        except Exception as e:
            print(f"clockwise error: {e}")
        finally:
            self.stop()

    async def counterclockwise(self, motor_speed, waitTime):
        """Run motor counter-clockwise at `motor_speed` (%) for `waitTime` seconds (async)."""
        try:
            self.set_speed(motor_speed)
            self.cw.off()
            self.ccw.on()
            await asyncio.sleep(waitTime)
        except Exception as e:
            print(f"counterclockwise error: {e}")
        finally:
            self.stop()

    async def ramp(self, direction='clockwise', steps=40, step_ms=50, max_pct=100):
        """Async smooth ramp: ramp up to `max_pct` then back down.

        direction: 'clockwise' or 'counterclockwise'
        steps: number of discrete steps for ramp up (and down)
        step_ms: delay between steps in milliseconds
        max_pct: peak speed percentage (0-100)
        """
        try:
            if direction == 'clockwise':
                self.ccw.off()
                self.cw.on()
            else:
                self.cw.off()
                self.ccw.on()

            # ramp up
            for i in range(steps + 1):
                pct = (i / steps) * max_pct
                self.set_speed(pct)
                await asyncio.sleep_ms(step_ms)

            # ramp down
            for i in range(steps, -1, -1):
                pct = (i / steps) * max_pct
                self.set_speed(pct)
                await asyncio.sleep_ms(step_ms)

        except Exception as e:
            print(f"ramp error: {e}")
        finally:
            self.stop()

    def stop(self):
        # set duty to zero; keep PWM object alive so it can be reused
        try:
            self.speed.duty_u16(0)
            try:
                self._current_pct = 0.0
            except Exception:
                pass
        except Exception:
            pass

        # force direction pins low
        try:
            self.cw.off()
        except Exception:
            pass
        try:
            self.ccw.off()
        except Exception:
            pass


if __name__ == '__main__':
    try:
        test_motors()
    finally:
        pass
