from machine import Pin
import uasyncio as asyncio
import time

# Global variables to track hall sensor state
detection_count = 0
last_trigger_time = 0
frequency_hz = 0.0
last_revolution_time = 0
previous_avg_hz = 0.0

# Configuration
MAGNETS_PER_REVOLUTION = 5
magnet_times = []  # Store timestamps of magnet detections
frequency_readings = []  # Store last 60 frequency readings for averaging

# Two-digit display configuration
#   2 digit 7 segmented LED
#
#       digit 1        digit 2    
#        _a_            _a_        
#     f |_g_| b      f |_g_| b     
#     e |___| c _h   e |___| c _h   
#         d              d          
#
# num   hgfe dcba   hex
#
# 0 = 	0011 1111   0x3F
# 1 =	0000 0110   0x06
# 2 =	0101 1011   0x5B
# 3 =	0100 1111   0x4F
# 4 =	0110 0110   0x66
# 5 =	0110 1101   0x6D
# 6 =	0111 1101   0x7D
# 7 =	0000 0111   0x07
# 8 =   0111 1111   0x7F
# 9 =   0110 0111   0x67

digit_number = [4, 5]
pin_number = [6, 7, 8, 9, 10, 11, 12, 13]  # a,b,c,d,e,f,g,h
segnum = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x67]
digits = [Pin(digit_number[0], Pin.OUT), Pin(digit_number[1], Pin.OUT)]
pins = [Pin(pin_number[0], Pin.OUT), Pin(pin_number[1], Pin.OUT), Pin(pin_number[2], Pin.OUT), Pin(pin_number[3], Pin.OUT),
        Pin(pin_number[4], Pin.OUT), Pin(pin_number[5], Pin.OUT), Pin(pin_number[6], Pin.OUT), Pin(pin_number[7], Pin.OUT)]

# Global variable to hold the current display value
current_value = 0


# Interrupt handler function
def hall_interrupt_handler(pin):
    global detection_count, last_trigger_time, frequency_hz, magnet_times, last_revolution_time, previous_avg_hz, current_value
    
    # Debounce to prevent false triggers from noise/bouncing
    # 2ms allows for frequencies up to ~100 Hz with 5 magnets
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_trigger_time) < 2:
        return
    
    last_trigger_time = current_time
    detection_count += 1
    magnet_times.append(current_time)
    
    # Keep only last 15 magnet times (3 full revolutions)
    if len(magnet_times) > 15:
        magnet_times.pop(0)
    
    # Calculate frequency after each complete revolution
    if detection_count % MAGNETS_PER_REVOLUTION == 0:
        if len(magnet_times) > MAGNETS_PER_REVOLUTION:
            time_for_rev = time.ticks_diff(current_time, magnet_times[-(MAGNETS_PER_REVOLUTION + 1)])
            
            if time_for_rev > 0:
                # Hz = (1 revolution / time_in_ms) * 1000
                instant_hz = 1000.0 / time_for_rev
                frequency_readings.append(instant_hz)
                
                # Keep only last 60 readings
                if len(frequency_readings) > 60:
                    frequency_readings.pop(0)
                
                # Calculate average frequency and round to nearest whole number
                frequency_hz = round(sum(frequency_readings) / len(frequency_readings))
                
                # Update display value
                current_value = int(frequency_hz)
                
                # Only print if the average has changed
                if frequency_hz != previous_avg_hz:
                    print(f"Revolution complete: {time_for_rev}ms = {round(instant_hz)} Hz (Avg: {frequency_hz} Hz)")
                    previous_avg_hz = frequency_hz
        
        last_revolution_time = current_time


async def display_task():
    """Continuously multiplex the two digits asynchronously."""
    global current_value
    
    while True:
        # Convert value to two digits (0-99)
        value = current_value % 100
        digit1 = value // 10
        digit2 = value % 10
        
        # Display digit 1 (tens place)
        if digit1 > 0 or value >= 10:  # Don't show leading zero
            # Clear all segments first
            for pin in pins:
                pin.value(0)
            
            digits[1].value(0)
            i = 0
            for pin in pins:
                pin.value((segnum[digit1] & (0x01 << i)) >> i)
                i += 1
            await asyncio.sleep_ms(5)
            digits[1].value(1)
        else:
            digits[1].value(1)
        
        # Blanking period to prevent ghosting
        for pin in pins:
            pin.value(0)
        await asyncio.sleep_ms(1)
        
        # Display digit 2 (ones place)
        digits[0].value(0)
        i = 0
        for pin in pins:
            pin.value((segnum[digit2] & (0x01 << i)) >> i)
            i += 1
        await asyncio.sleep_ms(5)
        digits[0].value(1)
        
        # Blanking period to prevent ghosting
        for pin in pins:
            pin.value(0)
        await asyncio.sleep_ms(1)


async def monitor_task():
    """Monitor for rotation stop and update display."""
    global frequency_hz, current_value, last_trigger_time
    
    while True:
        # Check if rotation has stopped (no detections for 2 seconds)
        current_time = time.ticks_ms()
        time_since_last_trigger = time.ticks_diff(current_time, last_trigger_time)
        
        if time_since_last_trigger > 2000 and frequency_hz > 0:
            frequency_hz = 0.0
            current_value = 0
            print("Rotation stopped")
        
        await asyncio.sleep_ms(100)


def set_value(value):
    """Set the value to be displayed (0-99)."""
    global current_value
    current_value = max(0, min(99, value))


def get_value():
    """Get the current displayed value."""
    global current_value
    return current_value


async def main():
    """Main async function to run display and monitoring tasks."""
    global last_trigger_time
    
    # Setup hall effect sensor on GPIO26
    hall_sensor = Pin(26, Pin.IN, Pin.PULL_UP)
    
    # Attach interrupt ONLY on falling edge (magnet detected)
    hall_sensor.irq(trigger=Pin.IRQ_FALLING, 
                    handler=hall_interrupt_handler)
    
    print("Hall effect sensor initialized on GPIO26")
    print(f"Configuration: {MAGNETS_PER_REVOLUTION} magnets per revolution")
    print("Display shows frequency (0-99 Hz)")
    print("Waiting for magnetic field changes...")
    
    # Initialize timer
    last_trigger_time = time.ticks_ms()
    
    # Create the display task and monitor task
    display = asyncio.create_task(display_task())
    monitor = asyncio.create_task(monitor_task())
    
    # Keep running both tasks
    await asyncio.gather(display, monitor)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("")
        print("Program shut down by user")
    finally:
        for pin in pins:
            pin.value(0)
        for digit in digits:
            digit.value(1)
        print("GPIO cleaned up")
