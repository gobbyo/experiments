"""
MOSFET motor control with target frequency hold.
Ramps motor to a specific frequency, holds for 5 seconds, then ramps down.
Includes real-time feedback via IR sensor tachometer.
"""

from machine import Pin, PWM
import uasyncio as asyncio
import sys
import os
from ir_display_async import IRSensor, display_task
import ir_display_async

# Configuration
MOSFET_GATE_PIN = 17      # GPIO pin connected to MOSFET gate
PWM_FREQUENCY = 60        # Hz
TARGET_FREQUENCY = 50     # Hz - Change this to set target motor speed
HOLD_TIME_MS = 1000 * 60  # How long to hold at target frequency (10 seconds)
RAMP_STEP = 1             # Increase/decrease PWM by 1% per step
STEP_DELAY_MS = 200       # Delay between steps in milliseconds
FREQUENCY_TOLERANCE = 1   # Hz - How close to target before holding


async def frequency_monitor(sensor, stop_event):
    """
    Background task that updates display with frequency readings.
    
    Args:
        sensor: IRSensor instance
        stop_event: asyncio.Event that signals when to stop monitoring
    """
    try:
        while not stop_event.is_set():
            freq = sensor.get_frequency()
            ir_display_async.current_value = int(freq)
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
    print("Setting motor to 100% PWM to measure maximum frequency...")
    print()
    
    # Set to 100% PWM
    motor_pwm.duty_u16(65535)
    
    # Let motor spin up
    await asyncio.sleep_ms(2000)
    
    # Collect frequency readings
    max_freq = 0
    readings = []
    
    print("Collecting frequency readings at 100% PWM:")
    for i in range(10):
        freq = sensor.get_frequency()
        ir_display_async.current_value = int(freq)
        readings.append(freq)
        max_freq = max(max_freq, freq)
        print(f"  Reading {i+1}: {int(freq)}Hz")
        await asyncio.sleep_ms(1000)
    
    # Calculate average
    avg_freq = sum(readings) / len(readings)
    
    print()
    print(f"Maximum Frequency: {int(max_freq)}Hz")
    print(f"Average Frequency: {int(avg_freq)}Hz")
    print()
    
    # Stop motor
    print("Stopping motor...")
    motor_pwm.duty_u16(0)
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
    
    current_pwm = 5  # Start at 5% PWM
    max_iterations = 100
    iteration = 0
    
    while iteration < max_iterations:
        motor_pwm.duty_u16(int((current_pwm / 100) * 65535))
        await asyncio.sleep_ms(STEP_DELAY_MS)
        
        freq = sensor.get_frequency()
        ir_display_async.current_value = int(freq)
        
        if iteration % 5 == 0:  # Print every 5 iterations
            print(f"  PWM: {current_pwm:3d}% -> {int(freq):3d}Hz")
        
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
            current_pwm = max(1, current_pwm - RAMP_STEP)
        
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
    print(f"Ramping to target frequency of {target_hz}Hz (using calibration max: {int(max_freq_hz)}Hz)...")
    print()

    # Calculate starting PWM based on target Hz as percentage of max
    if max_freq_hz > 0:
        estimated_pwm = max(5, int((target_hz / max_freq_hz) * 100))
    else:
        estimated_pwm = 5

    print(f"Calculated starting PWM: {estimated_pwm}% (target {target_hz}Hz / max {int(max_freq_hz)}Hz)")
    print()

    current_pwm = max(5, estimated_pwm - 10)  # Start 10% below estimated
    max_iterations = 50
    iteration = 0

    while iteration < max_iterations:
        motor_pwm.duty_u16(int((current_pwm / 100) * 65535))
        await asyncio.sleep_ms(STEP_DELAY_MS)

        freq = sensor.get_frequency()
        ir_display_async.current_value = int(freq)

        if iteration % 3 == 0:  # Print every 3 iterations
            print(f"  PWM: {current_pwm:3d}% -> {int(freq):3d}Hz")

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
            current_pwm = max(1, current_pwm - RAMP_STEP)

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
    adjustment_interval = 500  # Adjust every 500ms for responsive control
    last_adjustment = -adjustment_interval  # Allow immediate first adjustment
    freq_readings = []
    error_history = []
    
    # Calculate 2% tolerance in Hz (2% of target)
    tolerance_hz = (target_hz * 2) / 100  # 1Hz for 50Hz target
    
    while elapsed < hold_ms:
        freq = sensor.get_frequency()
        ir_display_async.current_value = int(freq)
        freq_readings.append(freq)
        
        # Calculate error (positive when too slow, negative when too fast)
        error = target_hz - freq
        error_history.append(error)
        
        # Adjust more frequently for better stability
        if elapsed - last_adjustment >= adjustment_interval:
            # Use proportional control: adjust based on error magnitude
            # Small adjustments for small errors, larger for large errors
            
            if abs(error) > tolerance_hz * 3:
                # Large error (>3Hz): more aggressive
                adjustment = 0.5 * (error / 10)  # 0.5% per Hz
            elif abs(error) > tolerance_hz:
                # Medium error (1-3Hz): moderate correction
                adjustment = 0.25 * (error / 10)  # 0.25% per Hz
            else:
                # Small error (<1Hz): minimal adjustment
                adjustment = 0.1 * (error / 10)  # 0.1% per Hz
            
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
                motor_pwm.duty_u16(int((current_pwm / 100) * 65535))
                print(f"  [Adjust] Error {error:+5.1f}Hz -> PWM {old_pwm:5.1f}% -> {current_pwm:5.1f}% ({adjustment:+.2f}%)")
            
            last_adjustment = elapsed
        
        # Print status every 1 second
        if elapsed % 1000 == 0:
            remaining = (hold_ms - elapsed) / 1000
            status = "✓" if abs(error) <= tolerance_hz else "~"
            print(f"  {status}  {int(freq):3d}Hz @ PWM {current_pwm:5.1f}% (target: {target_hz}Hz, error: {error:+5.1f}Hz, {remaining:.1f}s remaining)")
        
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
        motor_pwm.duty_u16(int((pwm_step / 100) * 65535))
        await asyncio.sleep_ms(STEP_DELAY_MS)
        
        freq = sensor.get_frequency()
        ir_display_async.current_value = int(freq)
        
        if pwm_step % 10 == 0:
            status = "↓" if pwm_step > 0 else "◼"
            print(f"  {status} PWM: {pwm_step:3d}% -> {int(freq):3d}Hz")
    
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
    print(f"=" * 50)
    print()
    
    # Create event to control monitoring task
    stop_monitoring = asyncio.Event()
    monitor_task = asyncio.create_task(frequency_monitor(sensor, stop_monitoring))
    
    # Start the display task to show frequency on 7-segment display
    display_task_handle = asyncio.create_task(display_task())
    
    try:
        # PHASE 0: Calibrate at 100% to determine max Hz
        max_frequency = await calibrate_motor(motor_pwm, sensor)

        # Ensure motor is stopped before ramping
        motor_pwm.duty_u16(0)
        await asyncio.sleep_ms(300)

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
        print(f"Error during test: {e}")
    
    finally:
        # Clean up
        stop_monitoring.set()
        motor_pwm.duty_u16(0)
        motor_pwm.deinit()
        
        monitor_task.cancel()
        display_task_handle.cancel()
        try:
            await monitor_task
            await display_task_handle
        except asyncio.CancelledError:
            pass
        
        print("Motor stopped and PWM disabled.")


async def main():
    """Main async function - initializes sensor and runs test."""
    try:
        # Initialize IR sensor
        print("Initializing IR sensor tachometer...")
        global sensor
        sensor = IRSensor(gpio_pin=26, slots_per_revolution=5)
        await asyncio.sleep_ms(500)
        print()
        
        # Run the frequency hold test
        await run_frequency_hold_test(TARGET_FREQUENCY)
    
    except Exception as e:
        print(f"Fatal error: {e}")


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
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == '__main__':
    # Modify TARGET_FREQUENCY constant above to set desired frequency
    run_test()
