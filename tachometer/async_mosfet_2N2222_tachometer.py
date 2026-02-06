"""
Asynchronous MOSFET motor control with real-time tachometer feedback.
Ramps a 103 brushed motor from 0% to 100% and back down to 0%.
PWM frequency set to 60Hz.
Displays motor frequency (RPM) measured by IR sensor.
"""

from machine import Pin, PWM
import uasyncio as asyncio
import display_3461AS_async as sevenseg
import time
from IRChangeInterrupt import IRChangeMonitor

# Configuration
MOSFET_GATE_PIN = 17  # GPIO pin connected to MOSFET gate
IR_SENSOR_PIN = 22   # GPIO pin connected to IR sensor
PWM_FREQUENCY = 60    # Hz
RAMP_STEP = 1         # Increase/decrease PWM by 1% per step
STEP_DELAY_MS = 200   # Delay between steps in milliseconds (increased for measurements)
KICKSTART_MS = 50     # Brief full-power pulse before ramp
DUTY_HIGH = 0
DUTY_LOW = 65535

class IRTachometer:
    """Edge-based tachometer using IRChangeMonitor."""

    def __init__(self, gpio_pin, slots_per_revolution=1, buf_size=32):
        self._monitor = IRChangeMonitor(gpio_pin=gpio_pin, buf_size=buf_size)
        self._slots_per_rev = max(1, int(slots_per_revolution))
        self._last_rise_us = None
        self._frequency_hz = 0.0
        self._overflow = False

    async def run(self):
        async for value, overflow in self._monitor:
            if overflow:
                self._overflow = True
            if value == 1:
                now = time.ticks_us()
                if self._last_rise_us is not None:
                    dt_us = time.ticks_diff(now, self._last_rise_us)
                    if dt_us > 0:
                        edge_hz = 1_000_000 / dt_us
                        self._frequency_hz = edge_hz / self._slots_per_rev
                self._last_rise_us = now

    def get_frequency(self):
        return self._frequency_hz

    def pop_overflow(self):
        overflow = self._overflow
        self._overflow = False
        return overflow


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
            if sensor.pop_overflow():
                print("IRChangeMonitor IRQ buffer overflow")
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
    print(f"IR Tachometer: ENABLED (GPIO {IR_SENSOR_PIN})")
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
        # Kickstart motor before ramping
        motor_pwm.duty_u16(DUTY_HIGH)
        await asyncio.sleep_ms(KICKSTART_MS)
        motor_pwm.duty_u16(DUTY_LOW)
        await asyncio.sleep_ms(50)

        # RAMP UP: 30% to 100%
        print("Ramping UP from 30% to 100%...")
        print(f"{'PWM%':<8} {'Freq(Hz)':<12} {'Status':<20}")
        print("-" * 40)
        
        for duty_pct in range(30, 101, RAMP_STEP):
            # Set PWM
            duty_value = DUTY_LOW - int((duty_pct / 100) * DUTY_LOW)
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
            duty_value = DUTY_LOW - int((duty_pct / 100) * DUTY_LOW)
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
        motor_pwm.duty_u16(DUTY_LOW)
        motor_pwm.deinit()
        print("\nMotor stopped and PWM disabled.")


async def main():
    """Main async function - initializes sensor and runs tachometer test."""
    sensor_task = None
    try:
        # Initialize IR sensor
        print("Initializing IR sensor tachometer...")
        sensor = IRTachometer(gpio_pin=IR_SENSOR_PIN, slots_per_revolution=1, buf_size=32)
        sensor_task = asyncio.create_task(sensor.run())
        await asyncio.sleep_ms(500)
        print()
        
        # Run motor ramp with tachometer feedback
        await ramp_motor_with_tachometer(sensor)
    
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        try:
            if sensor_task is not None:
                sensor_task.cancel()
                await sensor_task
        except Exception:
            pass


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
