from machine import Pin, PWM
import uasyncio as asyncio

# Driver module for controlling two motors with PWM speed control using L293x Quadruple Half-H Drivers
# Provides `motorDriver` class and helper functions to create and test motors.
# Designed for use with MicroPython on microcontrollers.

# System constants
LED_PWM_FREQUENCY = 100  # Hz
MOTOR_PWM_FREQUENCY = 50  # Hz
# Default speed PWM pins (can be overridden by importing module)
SPEED1_PIN = 16  # primary speed pin for motor 1
SPEED2_PIN = 17  # default speed pin for motor 2 (adjust for your board)

# Motor tuples (CCW pin, CW pin)
motor1 = (12, 13)
motor2 = (14, 15)
motor_pins = [motor1, motor2]


def create_motors(speed1=SPEED1_PIN, speed2=SPEED2_PIN):
    """Create two `motorDriver` instances from the configured `motor_pins`.

    Returns (m1, m2).
    """
    ccw1, cw1 = motor_pins[0]
    ccw2, cw2 = motor_pins[1]
    m1 = motorDriver(speed1, cw1, ccw1)
    m2 = motorDriver(speed2, cw2, ccw2)
    return m1, m2


async def run_motor(motor, pause_ms=200, ramp_kwargs=None):
    """Run a single motor: ramp clockwise then counterclockwise."""
    if ramp_kwargs is None:
        ramp_kwargs = {}
    await motor.ramp('clockwise', **ramp_kwargs)
    await asyncio.sleep_ms(pause_ms)
    await motor.ramp('counterclockwise', **ramp_kwargs)
    motor.stop()


def test_motors():
    """Simplified test: run each motor (ramp CW then CCW) concurrently."""
    ramp_kwargs = {'steps': 40, 'step_ms': 50, 'max_pct': 100}

    async def _runner():
        m1, m2 = create_motors()
        t1 = asyncio.create_task(run_motor(m1, ramp_kwargs=ramp_kwargs))
        t2 = asyncio.create_task(run_motor(m2, ramp_kwargs=ramp_kwargs))
        await asyncio.gather(t1, t2)
        m1.stop()
        m2.stop()

    try:
        asyncio.run(_runner())
    finally:
        pass

class motorDriver:
    def __init__(self, speedPin, cwPin, ccwPin):
        self.speed = PWM(Pin(speedPin))
        self.speed.freq(MOTOR_PWM_FREQUENCY)
        self.cw = Pin(cwPin, Pin.OUT)
        self.ccw = Pin(ccwPin, Pin.OUT)
        self.stop()

    async def clockwise(self, motor_speed, waitTime):
        """Run motor clockwise at `motor_speed` (%) for `waitTime` seconds (async)."""
        try:
            self.speed.duty_u16(int((motor_speed / 100) * 65535))
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
            self.speed.duty_u16(int((motor_speed / 100) * 65535))
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
                self.speed.duty_u16(int((pct / 100) * 65535))
                await asyncio.sleep_ms(step_ms)

            # ramp down
            for i in range(steps, -1, -1):
                pct = (i / steps) * max_pct
                self.speed.duty_u16(int((pct / 100) * 65535))
                await asyncio.sleep_ms(step_ms)

        except Exception as e:
            print(f"ramp error: {e}")
        finally:
            self.stop()

    def stop(self):
        self.speed.duty_u16(0)
        self.cw.off()
        self.ccw.off()

if __name__ == '__main__':
    try:
        test_motors()
    finally:
        pass