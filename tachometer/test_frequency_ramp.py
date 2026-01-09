"""
Test to slowly ramp up motor speed by 5Hz increments starting at 20Hz 
until reaching 100% motor speed.

Uses the IR sensor (tachometer) to measure actual motor frequency and 
adjusts PWM percentage to achieve target frequency steps.
"""


import uasyncio as asyncio
import time
from motor_driver_universal import create_motors
from ir_display_async import display_task, IRSensor
import ir_display_async


async def frequency_ramp_test(start_hz=20, increment_hz=5, hold_time_ms=10000):
    """
    Test PWM control by checking if different PWM levels produce different frequencies.
    
    Args:
        start_hz: Starting frequency in Hz (default 20) - informational only
        increment_hz: Frequency increment per step in Hz (default 5) - informational only
        hold_time_ms: Time to hold each PWM step in milliseconds (default 10000 for stability)
    """
    # Initialize motor
    motor = create_motors()
    
    # Initialize IR sensor using the IRSensor class
    sensor = IRSensor(gpio_pin=26, slots_per_revolution=5)
    
    # Start display task for real-time feedback
    display_task_handle = asyncio.create_task(display_task())
    
    try:
        print(f"Starting PWM control diagnostic test...")
        print()
        
        # INITIALIZATION: Apply aggressive braking to stop motor completely
        print("Initialization: Applying aggressive braking to stop motor...")
        
        # Apply strong braking by running in opposite direction
        motor.cw.off()
        motor.ccw.on()
        motor.set_speed(100)  # Full power braking
        await asyncio.sleep_ms(2000)  # 2 seconds of strong braking
        
        # Stop the motor
        motor.ccw.off()
        motor.cw.off()
        motor.stop()
        
        # Extended wait for motor to fully stop and vibrations to settle
        await asyncio.sleep_ms(5000)
        
        # Reset sensor data
        sensor.reset()
        await asyncio.sleep_ms(1000)
        
        # Verify motor is stopped
        print("Motor stopped. Baseline frequency: 0Hz")
        print()
        
        # Now start the diagnostic test
        print("PWM Control Diagnostic Test")
        print("="*50)
        
        # Start motor in clockwise direction
        motor.cw.on()
        motor.ccw.off()
        
        # Test specific PWM values to see if PWM affects frequency
        test_pwm_values = [5, 20, 50, 75, 100]
        measured_frequencies = []
        
        for test_pct in test_pwm_values:
            motor.set_speed(test_pct)
            
            # Wait for motor to respond
            await asyncio.sleep_ms(hold_time_ms)
            
            # Measure frequency
            current_hz = sensor.get_frequency()
            ir_display_async.current_value = int(current_hz)
            measured_frequencies.append(current_hz)
            
            print(f"PWM {test_pct:3d}% -> {current_hz:3d}Hz")
        
        print("="*50)
        print()
        
        # Analyze results - compare actual measured frequencies
        min_freq = min(measured_frequencies)
        max_freq = max(measured_frequencies)
        freq_range = max_freq - min_freq
        
        print("Diagnostic Summary:")
        print(f"Frequency range: {min_freq}Hz to {max_freq}Hz (difference: {freq_range}Hz)")
        
        if freq_range > 10:
            print("✓ PWM control is WORKING - frequency increases with PWM")
        else:
            print("✗ PWM control is NOT WORKING - frequency does not respond to PWM changes")
            print("  Motor is stuck at constant speed regardless of PWM")
            print("  Possible issues:")
            print("  1. Motor driver PWM output is stuck")
            print("  2. Motor has reached mechanical speed limit")
            print("  3. Power supply is too high (motor running at full speed)")
            print("  4. PWM signal is not connected to motor driver correctly")
        
        # Gradually stop the motor
        print("\nStopping motor...")
        for pct in range(100, -1, -5):
            motor.set_speed(max(0, pct))
            await asyncio.sleep_ms(50)
        
        motor.stop()
        print("Motor stopped.")
        
    except Exception as e:
        print(f"Error during frequency ramp test: {e}")
        motor.stop()
    finally:
        # Clean up
        display_task_handle.cancel()
        try:
            await display_task_handle
        except asyncio.CancelledError:
            pass


def run_test():
    """Run the frequency ramp test."""
    try:
        asyncio.run(frequency_ramp_test())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == '__main__':
    run_test()
