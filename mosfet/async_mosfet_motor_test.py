"""
Asynchronous PWM motor control via MOSFET gate.
Ramps a 103 brushed motor from 0% to 100% and back down to 0%.
PWM frequency set to 60Hz.
"""

from machine import Pin, PWM
import uasyncio as asyncio

# Configuration
BJT_GATE_PIN = 4  # GPIO pin connected to BJT gate (adjust as needed)
PWM_FREQUENCY = 60    # Hz
RAMP_STEP = 1         # Increase/decrease PWM by 1% per step
STEP_DELAY_MS = 100   # Delay between steps in milliseconds
MAX_DUTY = 65535     # Maximum duty cycle value for 16-bit resolution

async def ramp_motor():
    """
    Ramp motor speed from 0% to 100% and back down to 0%.
    """
    
    # Initialize PWM on BJT gate pin
    motor_pwm = PWM(Pin(BJT_GATE_PIN))
    motor_pwm.freq(PWM_FREQUENCY)
    
    print(f"Starting asynchronous motor ramp test")
    print(f"PWM Frequency: {PWM_FREQUENCY}Hz")
    print(f"BJT Gate Pin: GPIO{BJT_GATE_PIN}")
    
    
    try:
        # RAMP UP: 0% to 100%
        print("Ramping UP from 0% to 100%...")
        
        for duty_pct in range(0, 101, RAMP_STEP):
            # Set PWM
            duty_value = MAX_DUTY - int((duty_pct / 100) * MAX_DUTY)
            motor_pwm.duty_u16(duty_value)
            
            # Print progress every 10%
            if duty_pct % 10 == 0:
                print(f"  PWM: {duty_pct}%")
            
            await asyncio.sleep_ms(STEP_DELAY_MS)
        
        print("  PWM: 100% (maximum)")
        print()
        
        # Hold at 100% for a moment
        await asyncio.sleep_ms(1000)
        
        # RAMP DOWN: 100% to 0%
        print("Ramping DOWN from 100% to 0%...")
        
        for duty_pct in range(100, -1, -RAMP_STEP):
            # Set PWM
            duty_value = MAX_DUTY - int((duty_pct / 100) * MAX_DUTY)
            motor_pwm.duty_u16(duty_value)
            
            # Print progress every 10%
            if duty_pct % 10 == 0:
                print(f"  PWM: {duty_pct}%")
            
            await asyncio.sleep_ms(STEP_DELAY_MS)
        
        print("  PWM: 0% (stopped)")
        print()
        
    except Exception as e:
        print(f"Error during motor ramp: {e}")
    
    finally:
        # Ensure motor is stopped
        motor_pwm.duty_u16(MAX_DUTY)
        motor_pwm.deinit()
        print("Motor stopped and PWM disabled.")


def run_test():
    """Run the asynchronous motor ramp test."""
    try:
        asyncio.run(ramp_motor())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == '__main__':
    run_test()
