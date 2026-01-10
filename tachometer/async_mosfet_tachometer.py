"""
Asynchronous MOSFET motor control with real-time tachometer feedback.
Ramps a 103 brushed motor from 0% to 100% and back down to 0%.
PWM frequency set to 60Hz.
Displays motor frequency (RPM) measured by IR sensor.
"""

from machine import Pin, PWM
import uasyncio as asyncio
import display_3461AS_async as sevenseg
from ir_display_async import IRSensor

# Configuration
MOSFET_GATE_PIN = 17  # GPIO pin connected to MOSFET gate
PWM_FREQUENCY = 60    # Hz
RAMP_STEP = 1         # Increase/decrease PWM by 1% per step
STEP_DELAY_MS = 200   # Delay between steps in milliseconds (increased for measurements)


async def display_frequency_monitor(sensor, display, stop_event):
    """
    Background task that continuously updates display with frequency readings.
    Runs until stop_event is set.
    
    Args:
        sensor: IRSensor instance
        stop_event: asyncio.Event that signals when to stop monitoring
    """
    try:
        while not stop_event.is_set():
            freq = sensor.get_frequency()
            display.set_number(int(freq))
            await asyncio.sleep_ms(500)
    except asyncio.CancelledError:
        pass


async def ramp_motor_with_tachometer(sensor):
    """
    Ramp motor speed from 0% to 100% and back down to 0%.
    Displays motor frequency in real-time via IR sensor tachometer.
    """
    
    # Initialize PWM on MOSFET gate pin
    motor_pwm = PWM(Pin(MOSFET_GATE_PIN))
    motor_pwm.freq(PWM_FREQUENCY)
    
    print(f"Starting asynchronous motor ramp test with tachometer")
    print(f"PWM Frequency: {PWM_FREQUENCY}Hz")
    print(f"MOSFET Gate Pin: GPIO{MOSFET_GATE_PIN}")
    print(f"IR Tachometer: ENABLED (GPIO 26)")
    print()
    
    # Initialize 4-digit display
    display = sevenseg.AsyncDisplay3461AS()
    display.start()

    # Create event to control monitoring task
    stop_monitoring = asyncio.Event()
    monitor_task = asyncio.create_task(display_frequency_monitor(sensor, display, stop_monitoring))
    
    # Data collection for analysis
    ramp_data = {
        'up': [],      # [(pwm_pct, freq_hz), ...]
        'down': []
    }
    
    try:
        # RAMP UP: 0% to 100%
        print("Ramping UP from 0% to 100%...")
        print(f"{'PWM%':<8} {'Freq(Hz)':<12} {'Status':<20}")
        print("-" * 40)
        
        for duty_pct in range(0, 101, RAMP_STEP):
            # Set PWM
            duty_value = int((duty_pct / 100) * 65535)
            motor_pwm.duty_u16(duty_value)
            
            # Wait for motor to respond
            await asyncio.sleep_ms(STEP_DELAY_MS)
            
            # Get frequency reading
            freq = sensor.get_frequency()
            ramp_data['up'].append((duty_pct, freq))
            
            # Print progress every 5%
            if duty_pct % 5 == 0:
                status = "↑ Accelerating" if duty_pct < 100 else "→ Maximum"
                print(f"{duty_pct:<8} {int(freq):<12} {status:<20}")
        
        print("-" * 40)
        print()
        
        # Hold at 100% for a moment
        print("Holding at 100% PWM...")
        await asyncio.sleep_ms(2000)
        freq = sensor.get_frequency()
        print(f"Final speed: {int(freq)}Hz")
        print()
        
        # RAMP DOWN: 100% to 0%
        print("Ramping DOWN from 100% to 0%...")
        print(f"{'PWM%':<8} {'Freq(Hz)':<12} {'Status':<20}")
        print("-" * 40)
        
        for duty_pct in range(100, -1, -RAMP_STEP):
            # Set PWM
            duty_value = int((duty_pct / 100) * 65535)
            motor_pwm.duty_u16(duty_value)
            
            # Wait for motor to respond
            await asyncio.sleep_ms(STEP_DELAY_MS)
            
            # Get frequency reading
            freq = sensor.get_frequency()
            ramp_data['down'].append((duty_pct, freq))
            
            # Print progress every 5%
            if duty_pct % 5 == 0:
                status = "↓ Decelerating" if duty_pct > 0 else "◼ Stopped"
                print(f"{duty_pct:<8} {int(freq):<12} {status:<20}")
        
        print("-" * 40)
        print()
        
        # Print summary statistics
        if ramp_data['up'] and ramp_data['down']:
            print("="*50)
            print("TACHOMETER DATA SUMMARY")
            print("="*50)
            
            up_freqs = [f for _, f in ramp_data['up']]
            down_freqs = [f for _, f in ramp_data['down']]
            
            print(f"\nRamp Up (0% to 100%):")
            print(f"  Starting frequency: {int(up_freqs[0])}Hz")
            print(f"  Maximum frequency: {int(max(up_freqs))}Hz")
            print(f"  Ending frequency: {int(up_freqs[-1])}Hz")
            
            print(f"\nRamp Down (100% to 0%):")
            print(f"  Starting frequency: {int(down_freqs[0])}Hz")
            print(f"  Minimum frequency: {int(min(down_freqs))}Hz")
            print(f"  Ending frequency: {int(down_freqs[-1])}Hz")
            
            print(f"\nPWM Responsiveness:")
            # Find where frequency starts to increase significantly
            for i in range(len(up_freqs)-1):
                if up_freqs[i+1] > up_freqs[i] + 5:
                    print(f"  Frequency starts increasing at ~{i*RAMP_STEP}% PWM")
                    break
            
            print("="*50)
        
    except Exception as e:
        print(f"Error during motor ramp: {e}")
    
    finally:
        # Stop monitoring
        stop_monitoring.set()
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Stop display
        try:
            await display.stop()
        except Exception:
            pass
        
        # Ensure motor is stopped
        motor_pwm.duty_u16(0)
        motor_pwm.deinit()
        print("\nMotor stopped and PWM disabled.")


async def main():
    """Main async function - initializes sensor and runs tachometer test."""
    try:
        # Initialize IR sensor
        print("Initializing IR sensor tachometer...")
        sensor = IRSensor(gpio_pin=26, slots_per_revolution=1)
        await asyncio.sleep_ms(500)
        print()
        
        # Run motor ramp with tachometer feedback
        await ramp_motor_with_tachometer(sensor)
    
    except Exception as e:
        print(f"Fatal error: {e}")


def run_test():
    """Run the asynchronous motor tachometer test."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == '__main__':
    run_test()
