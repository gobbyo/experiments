"""
MOSFET motor control with target frequency hold.
Ramps motor to a specific frequency, holds for HOLD_TIME_MS, then ramps down.
Includes real-time feedback via IR sensor tachometer.
"""

from machine import Pin, PWM
import uasyncio as asyncio
import display_3461AS_async as sevenseg
import time
import gc
from IRChangeInterrupt import IRChangeMonitor

# Configuration
MOSFET_GATE_PIN = 17      # GPIO pin connected to MOSFET gate
IR_SENSOR_PIN = 22        # GPIO pin connected to IR sensor
PWM_FREQUENCY = 60        # Hz
TARGET_FREQUENCY = 40     # Hz - Change this to set target motor speed
HOLD_TIME_MS = 1000 * 60  # How long to hold at target frequency
RAMP_STEP = 1             # Increase/decrease PWM by 1% per step
STEP_DELAY_MS = 200       # Delay between steps in milliseconds
FREQUENCY_TOLERANCE = 1   # Hz - How close to target before holding
SLOTS_PER_REV = 1         # Number of reflective slots on the encoder disk
KICKSTART_MS = 50          # Brief full-power pulse before ramp
CALIBRATION_PWM = 80       # Cap calibration PWM to avoid brownouts
CALIBRATION_SPINUP_MS = 2000  # Spin-up time before taking readings
DUTY_HIGH = 0
DUTY_LOW = 65535
MIN_RAMP_PWM = 30          # Minimum PWM percent for ramp start
MIN_EDGE_US = 80           # Reject IR edge intervals shorter than this (us)

# Globals
display = None
sensor = None
sensor_task = None


async def _sleep_with_heartbeat(total_ms, label=None, heartbeat_ms=1000):
    start = time.ticks_ms()
    last_beat = start

    print(f"_sleep_with_heartbeat: Sleeping for {total_ms/1000:.1f}s with heartbeat every {heartbeat_ms/1000:.1f}s...")
    while True:
        now = time.ticks_ms()
        elapsed = time.ticks_diff(now, start)
        if elapsed >= total_ms:
            break
        remaining = total_ms - elapsed
        await asyncio.sleep_ms(min(heartbeat_ms, remaining))
        if label:
            now = time.ticks_ms()
            if time.ticks_diff(now, last_beat) >= heartbeat_ms:
                print(f"  {label}... {time.ticks_diff(now, start) / 1000:.1f}s")
                last_beat = now


def _set_motor_pwm_pct(motor_pwm, duty_pct):
    duty_pct = max(0, min(100, int(duty_pct)))
    duty_value = DUTY_LOW - int((duty_pct / 100) * DUTY_LOW)
    motor_pwm.duty_u16(duty_value)


async def _ensure_sensor_task(sensor_instance):
    global sensor_task
    if sensor_task is None:
        sensor_task = asyncio.create_task(sensor_instance.run())
        await asyncio.sleep_ms(50)


class IRTachometer:
    """Edge-based tachometer using IRChangeMonitor."""

    def __init__(self, gpio_pin, slots_per_revolution=1, buf_size=32):
        self._monitor = IRChangeMonitor(gpio_pin=gpio_pin, buf_size=buf_size)
        self._slots_per_rev = max(1, int(slots_per_revolution))
        self._last_rise_us = None
        self._frequency_hz = 0.0
        self._overflow = False
        self._shutdown = False

    async def run(self):
        processed = 0
        try:
            async for value, overflow in self._monitor:
                if self._shutdown:
                    break
                if overflow:
                    self._overflow = True
                if value == 1:
                    now = time.ticks_us()
                    if self._last_rise_us is not None:
                        dt_us = time.ticks_diff(now, self._last_rise_us)
                        if dt_us >= MIN_EDGE_US:
                            edge_hz = 1_000_000 / dt_us
                            self._frequency_hz = edge_hz / self._slots_per_rev
                    self._last_rise_us = now
                processed += 1
                if processed % 50 == 0:
                    await asyncio.sleep_ms(0)
        except asyncio.CancelledError:
            pass

    def get_frequency(self):
        return self._frequency_hz

    def pop_overflow(self):
        overflow = self._overflow
        self._overflow = False
        return overflow

    def shutdown(self):
        self._shutdown = True
        for method_name in ("stop", "deinit", "close"):
            method = getattr(self._monitor, method_name, None)
            if method is not None:
                try:
                    method()
                except Exception:
                    pass
                break


async def frequency_monitor(sensor, stop_event):
    """
    Background task that updates display with frequency readings.
    
    Args:
        sensor: IRSensor instance
        stop_event: asyncio.Event that signals when to stop monitoring
    """
    try:
        while not stop_event.is_set():
            if sensor is None:
                await asyncio.sleep_ms(100)
                continue
            if sensor.pop_overflow():
                print("IRChangeMonitor IRQ buffer overflow")
            freq = sensor.get_frequency()
            await asyncio.sleep_ms(300)
    except asyncio.CancelledError:
        pass

async def calibrate_motor(motor_pwm, sensor):
    """
    Calibrate motor by running at 100% PWM and measuring max frequency.
    
    Args:
        motor_pwm: PWM instance for motor control
        sensor: IRSensor instance
    
    Returns:
        Max frequency measured at 100% PWM
    """
    print("=" * 50)
    print("MOTOR CALIBRATION")
    print("=" * 50)
    print(f"Setting motor to {CALIBRATION_PWM}% PWM to measure maximum frequency...")
    print()

    gc.collect()
    
    # Set to calibration PWM
    _set_motor_pwm_pct(motor_pwm, CALIBRATION_PWM)
    
    print("line 151: Waiting for motor to spin up...")
    # Let motor spin up
    await _sleep_with_heartbeat(CALIBRATION_SPINUP_MS, label="Spinup")

    await _ensure_sensor_task(sensor)
    
    # Collect frequency readings
    max_freq = 0
    readings = []

    gc.collect()
    
    print(f"Collecting frequency readings at {CALIBRATION_PWM}% PWM:")
    for i in range(10):
        freq = sensor.get_frequency()
        readings.append(freq)
        max_freq = max(max_freq, freq)
        print(f"  Reading {i+1}: {int(freq)}Hz")
        if display:
            display.set_number(int(freq))
        if i % 2 == 1:
            gc.collect()
        await asyncio.sleep_ms(1000)
    
    # Calculate average
    avg_freq = sum(readings) / len(readings)
    
    print()
    print(f"Maximum Frequency: {int(max_freq)}Hz")
    print(f"Average Frequency: {int(avg_freq)}Hz")
    print()
    
    # Stop motor
    print("Stopping motor...")
    motor_pwm.duty_u16(DUTY_LOW)
    await asyncio.sleep_ms(3000)
    
    print()
    print("=" * 50)
    print("Calibration Complete!")
    print("=" * 50)
    print()
    
    return max_freq


async def ramp_to_target(motor_pwm, sensor, target_hz, tolerance_hz=FREQUENCY_TOLERANCE):
    """
    Ramp motor PWM until target frequency is reached within tolerance.
    Uses feedback control to adjust PWM.
    
    Args:
        motor_pwm: PWM instance for motor control
        sensor: IRSensor instance
        target_hz: Target frequency in Hz
        tolerance_hz: Acceptable error in Hz
    
    Returns:
        Tuple of (final_pwm_pct, achieved_freq)
    """
    print(f"Ramping to target frequency of {target_hz}Hz (±{tolerance_hz}Hz tolerance)...")
    
    current_pwm = MIN_RAMP_PWM  # Start at minimum effective PWM
    max_iterations = 100
    iteration = 0
    
    while iteration < max_iterations:
        if iteration % 10 == 0:
            gc.collect()
        _set_motor_pwm_pct(motor_pwm, current_pwm)
        await asyncio.sleep_ms(STEP_DELAY_MS)
        
        freq = sensor.get_frequency()
        
        if iteration % 5 == 0:  # Print every 5 iterations
            print(f"  PWM: {current_pwm:3d}% -> {int(freq):3d}Hz")
            if display:
                display.set_number(int(freq))
        
        # Check if we're within tolerance of target
        if abs(freq - target_hz) <= tolerance_hz:
            print(f"  ✓ Target frequency reached: {int(freq)}Hz at PWM {current_pwm}%")
            return current_pwm, freq
        
        # Adjust PWM based on error
        if freq < target_hz - tolerance_hz:
            # Too slow, increase PWM
            current_pwm = min(100, current_pwm + RAMP_STEP)
        else:
            # Too fast, decrease PWM
            current_pwm = max(MIN_RAMP_PWM, current_pwm - RAMP_STEP)
        
        iteration += 1
    
    # If we reach here, we couldn't hit the target exactly
    print(f"  Warning: Could not reach exact target, settled at {int(freq)}Hz")
    return current_pwm, freq


async def ramp_to_target_from_calibration(motor_pwm, sensor, max_freq_hz, target_hz, tolerance_hz=FREQUENCY_TOLERANCE):
    """
    Ramp motor to target frequency using calibration data.
    Calculates starting PWM from max frequency and ramps to target.

    Args:
        motor_pwm: PWM instance for motor control
        sensor: IRSensor instance
        max_freq_hz: Maximum frequency measured during calibration
        target_hz: Target frequency in Hz
        tolerance_hz: Acceptable error in Hz

    Returns:
        Tuple of (final_pwm_pct, achieved_freq)
    """
    print(f"Ramping to target frequency of {target_hz}Hz (using calibration max at {CALIBRATION_PWM}% PWM: {int(max_freq_hz)}Hz)...")
    print()

    # Calculate starting PWM based on target Hz as percentage of max
    if max_freq_hz > 0:
        estimated_pwm = max(MIN_RAMP_PWM, int((target_hz / max_freq_hz) * CALIBRATION_PWM))
    else:
        estimated_pwm = 5

    print(f"Calculated starting PWM: {estimated_pwm}% (target {target_hz}Hz / max {int(max_freq_hz)}Hz)")
    print()

    current_pwm = max(MIN_RAMP_PWM, estimated_pwm - 10)  # Start 10% below estimated
    max_iterations = 50
    iteration = 0

    while iteration < max_iterations:
        if iteration % 10 == 0:
            gc.collect()
        _set_motor_pwm_pct(motor_pwm, current_pwm)
        await asyncio.sleep_ms(STEP_DELAY_MS)

        freq = sensor.get_frequency()

        if iteration % 3 == 0:  # Print every 3 iterations
            print(f"  PWM: {current_pwm:3d}% -> {int(freq):3d}Hz")
            if display:
                display.set_number(int(freq))

        # Check if we're within tolerance of target
        if abs(freq - target_hz) <= tolerance_hz:
            print(f"  ✓ Target frequency reached: {int(freq)}Hz at PWM {current_pwm}%")
            return current_pwm, freq

        # Adjust PWM based on error
        if freq < target_hz - tolerance_hz:
            # Too slow, increase PWM
            current_pwm = min(100, current_pwm + RAMP_STEP)
        else:
            # Too fast, decrease PWM
            current_pwm = max(MIN_RAMP_PWM, current_pwm - RAMP_STEP)

        iteration += 1

    # If we reach here, we couldn't hit the target exactly
    print(f"  Warning: Could not reach exact target, settled at {int(freq)}Hz at PWM {current_pwm}%")
    return current_pwm, freq


async def hold_frequency(motor_pwm, sensor, hold_pwm_pct, target_hz, hold_ms=HOLD_TIME_MS):
    """
    Hold motor at target frequency using proportional feedback control.
    Uses gentle adjustments to compensate for motor drift without oscillating.
    
    Args:
        motor_pwm: PWM instance for motor control
        sensor: IRSensor instance
        hold_pwm_pct: Starting PWM percentage
        target_hz: Target frequency to maintain
        hold_ms: How long to hold in milliseconds
    
    Returns:
        Final adjusted PWM percentage
    """
    print(f"\nHolding at target {target_hz}Hz for {hold_ms/1000:.1f} seconds (starting PWM: {hold_pwm_pct}%)...")
    print(f"Using proportional feedback control to maintain stability.")
    print()
    
    elapsed = 0
    current_pwm = float(hold_pwm_pct)
    adjustment_interval = 200  # Adjust every 200ms for tighter control
    last_adjustment = -adjustment_interval  # Allow immediate first adjustment
    freq_readings = []
    error_history = []
    
    # Calculate 1% tolerance in Hz (tighter tracking)
    tolerance_hz = (target_hz * 1) / 100
    
    while elapsed < hold_ms:
        if elapsed % 2000 == 0:
            gc.collect()
        freq = sensor.get_frequency()
        freq_readings.append(freq)
        
        # Calculate error (positive when too slow, negative when too fast)
        error = target_hz - freq
        error_history.append(error)
        
        # Adjust more frequently for better stability
        if elapsed - last_adjustment >= adjustment_interval:
            # Use proportional control: adjust based on error magnitude
            # Small adjustments for small errors, larger for large errors
            
            if abs(error) > tolerance_hz * 3:
                # Large error (>~3% of target): more aggressive
                adjustment = 0.7 * (error / 10)  # 0.7% per Hz
            elif abs(error) > tolerance_hz:
                # Medium error (>~1% of target): moderate correction
                adjustment = 0.35 * (error / 10)  # 0.35% per Hz
            else:
                # Small error (<~1% of target): minimal adjustment
                adjustment = 0.15 * (error / 10)  # 0.15% per Hz
            
            # Apply damping to prevent oscillation when error changes sign
            if len(error_history) >= 2:
                prev_error = error_history[-2]
                if (error > 0 and prev_error < 0) or (error < 0 and prev_error > 0):
                    # Error changed sign: reduce adjustment strength by 25%
                    adjustment *= 0.75
            
            # Apply adjustment with bounds checking
            new_pwm = current_pwm + adjustment
            new_pwm = max(1, min(100, new_pwm))
            
            # Only print and apply if adjustment is significant (> 0.1%)
            if abs(new_pwm - current_pwm) > 0.1:
                old_pwm = current_pwm
                current_pwm = new_pwm
                _set_motor_pwm_pct(motor_pwm, current_pwm)
                print(f"  [Adjust] Error {error:+5.1f}Hz -> PWM {old_pwm:5.1f}% -> {current_pwm:5.1f}% ({adjustment:+.2f}%)")
                if display:
                    display.set_number(int(freq))
            
            last_adjustment = elapsed
        
        # Print status every 1 second
        if elapsed % 1000 == 0:
            remaining = (hold_ms - elapsed) / 1000
            status = "✓" if abs(error) <= tolerance_hz else "~"
            print(f"  {status}  {int(freq):3d}Hz @ PWM {current_pwm:5.1f}% (target: {target_hz}Hz, error: {error:+5.1f}Hz, {remaining:.1f}s remaining)")
            if display:
                display.set_number(int(freq))
        
        await asyncio.sleep_ms(100)
        elapsed += 100
    
    # Print summary statistics
    if freq_readings:
        avg_freq = sum(freq_readings) / len(freq_readings)
        min_freq = min(freq_readings)
        max_freq = max(freq_readings)
        
        # Count how many readings were within tolerance
        good_readings = sum(1 for f in freq_readings if abs(f - target_hz) <= tolerance_hz)
        success_pct = (good_readings / len(freq_readings)) * 100
        
        print()
        print(f"Hold phase summary:")
        print(f"  Average: {int(avg_freq)}Hz (target: {target_hz}Hz, error: {int(avg_freq - target_hz):+d}Hz)")
        print(f"  Range: {int(min_freq)}-{int(max_freq)}Hz (±{int((max_freq - min_freq) / 2)}Hz)")
        print(f"  Within 2% tolerance: {success_pct:.1f}% ({good_readings}/{len(freq_readings)} readings)")
        print(f"  Final PWM: {current_pwm:.1f}% (started at {hold_pwm_pct}%)")
    
    return current_pwm


async def ramp_down(motor_pwm, sensor, current_pwm, target_pwm):
    """
    Slowly ramp down from current PWM to 0.
    Starts from the lower of current_pwm or target_pwm to prevent speed-up.
    
    Args:
        motor_pwm: PWM instance for motor control
        sensor: IRSensor instance
        current_pwm: Current PWM percentage after hold phase
        target_pwm: Target PWM percentage calculated from calibration
    """
    # Start from the lower value to avoid initial speed increase
    start_pwm = min(int(current_pwm), int(target_pwm))
    print(f"\nRamping down from {start_pwm}% to 0% (current: {int(current_pwm)}%, target: {int(target_pwm)}%)...")
    
    for pwm_step in range(start_pwm, -1, -RAMP_STEP):
        _set_motor_pwm_pct(motor_pwm, pwm_step)
        await asyncio.sleep_ms(STEP_DELAY_MS)
        
        freq = sensor.get_frequency()
        
        if pwm_step % 10 == 0:
            status = "↓" if pwm_step > 0 else "◼"
            print(f"  {status} PWM: {pwm_step:3d}% -> {int(freq):3d}Hz")
            if display:
                display.set_number(int(freq))
    
    print(f"  Motor stopped")


async def run_frequency_hold_test(target_hz=TARGET_FREQUENCY):
    """
    Main test function: ramp to target frequency, hold, then ramp down.
    
    Args:
        target_hz: Target frequency in Hz
    """
    
    # Initialize PWM on MOSFET gate pin
    motor_pwm = PWM(Pin(MOSFET_GATE_PIN))
    motor_pwm.freq(PWM_FREQUENCY)
    
    print(f"Target Frequency Hold Test")
    print(f"=" * 50)
    print(f"Target Frequency: {target_hz}Hz")
    print(f"Hold Duration: {HOLD_TIME_MS/1000:.1f} seconds")
    print(f"PWM Frequency: {PWM_FREQUENCY}Hz")
    print(f"MOSFET Gate Pin: GPIO{MOSFET_GATE_PIN}")
    print(f"Encoder Slots/Rev: {SLOTS_PER_REV} (target {target_hz}Hz)")
    print(f"=" * 50)
    print()

    # Initialize 4-digit display
    global display
    gc.collect()
    display = sevenseg.AsyncDisplay3461AS()
    display.start()
    
    # Create event to control monitoring task
    stop_monitoring = asyncio.Event()
    monitor_task = asyncio.create_task(frequency_monitor(sensor, stop_monitoring))
    
    try:
        # PHASE 0: Calibrate at 100% to determine max Hz
        max_frequency = await calibrate_motor(motor_pwm, sensor)

        # Ensure motor is stopped before ramping
        motor_pwm.duty_u16(DUTY_LOW)
        await asyncio.sleep_ms(300)

        # Kickstart motor before ramping
        motor_pwm.duty_u16(DUTY_HIGH)
        await asyncio.sleep_ms(KICKSTART_MS)
        motor_pwm.duty_u16(DUTY_LOW)
        await asyncio.sleep_ms(50)

        # PHASE 1: Ramp up to target frequency using calibration data
        hold_pwm_pct, achieved_freq = await ramp_to_target_from_calibration(
            motor_pwm, sensor, max_frequency, target_hz, FREQUENCY_TOLERANCE
        )
        
        # Calculate target PWM from calibration for ramp-down reference
        target_pwm = int((target_hz / max_frequency) * 100) if max_frequency > 0 else hold_pwm_pct
        
        # PHASE 2: Hold at target frequency
        final_pwm = await hold_frequency(
            motor_pwm, sensor, hold_pwm_pct, target_hz, HOLD_TIME_MS
        )
        
        # PHASE 3: Ramp down to stop (start from lower of final or target PWM)
        await ramp_down(motor_pwm, sensor, final_pwm, target_pwm)
        
        print()
        print("=" * 50)
        print("Test Complete!")
        print("=" * 50)
        
    except Exception as e:
        try:
            motor_pwm.duty_u16(DUTY_LOW)
        except Exception:
            pass
        print(f"Error during test: {e}")
    
    finally:
        # Clean up
        stop_monitoring.set()
        try:
            motor_pwm.duty_u16(DUTY_LOW)
            motor_pwm.deinit()
        except Exception:
            pass

        monitor_task.cancel()
        try:
            await monitor_task
        except Exception:
            pass

        if display:
            try:
                await display.stop()
                display._clear()
            except Exception:
                pass
            display = None
        
        print("Motor stopped and PWM disabled.")


async def main():
    """Main async function - initializes sensor and runs test."""
    test_task = None
    try:
        # Initialize IR sensor
        print("Initializing IR sensor tachometer...")
        global sensor
        sensor = IRTachometer(gpio_pin=IR_SENSOR_PIN, slots_per_revolution=SLOTS_PER_REV)
        print(f"Slots per revolution: {SLOTS_PER_REV}")
        await asyncio.sleep_ms(500)
        print()
        
        # Run the frequency hold test
        test_task = asyncio.create_task(run_frequency_hold_test(TARGET_FREQUENCY))
        await test_task

    except MemoryError as e:
        gc.collect()
        print(f"Fatal error: {e}")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        try:
            if sensor_task is not None:
                sensor.shutdown()
                await sensor_task
        except Exception:
            pass


def run_test(target_hz=TARGET_FREQUENCY):
    """
    Run the frequency hold test.
    
    Args:
        target_hz: Target frequency in Hz (default: TARGET_FREQUENCY constant)
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except MemoryError as e:
        gc.collect()
        print(f"Test failed: {e}")
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == '__main__':
    # Modify TARGET_FREQUENCY constant above to set desired frequency
    run_test()
