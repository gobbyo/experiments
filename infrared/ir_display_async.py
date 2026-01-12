from machine import Pin
import uasyncio as asyncio
import time

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


class IRSensor:
    """Class to manage IR sensor initialization and frequency tracking."""

    def __init__(self, gpio_pin=26, slots_per_revolution=5):
        """
        Initialize the IR sensor.

        Args:
            gpio_pin: GPIO pin number for the IR sensor (default 26)
            slots_per_revolution: Number of slots in the encoder disc (default 5)
        """
        self.gpio_pin = gpio_pin
        self.slots_per_revolution = max(1, slots_per_revolution)

        # State tracking (lightweight for higher RPMs)
        self.frequency_hz = 0.0
        self._last_ts_us = None
        self._alpha_up = 0.18   # smoothing when frequency increasing
        self._alpha_down = 0.45 # faster decay when frequency decreasing
        self._max_jump_ratio = 1.2  # tighter clamp on spikes
        self._min_dt_us = 900       # ignore pulses faster than this (~1.1 kHz)
        self._inst_buf = []         # small buffer for median filtering

        # Setup the pin and interrupt
        self.ir_sensor = Pin(self.gpio_pin, Pin.IN)
        self.ir_sensor.irq(trigger=Pin.IRQ_FALLING, handler=self._interrupt_handler)

        print(f"IR sensor initialized on GPIO{self.gpio_pin}")
        print(f"Configuration: {self.slots_per_revolution} slots per revolution")

    def _interrupt_handler(self, pin):
        """Handle IR sensor interrupt on falling edge with minimal work."""
        ts = time.ticks_us()

        if self._last_ts_us is not None:
            dt = time.ticks_diff(ts, self._last_ts_us)
            if dt > self._min_dt_us:
                # Instantaneous frequency in Hz accounting for slots per revolution
                inst_hz = 1_000_000.0 / dt / self.slots_per_revolution

                # Median filter over last few instant readings to reject outliers
                self._inst_buf.append(inst_hz)
                if len(self._inst_buf) > 5:
                    self._inst_buf.pop(0)
                buf_sorted = sorted(self._inst_buf)
                mid = len(buf_sorted)//2
                if len(buf_sorted) % 2:
                    median_hz = buf_sorted[mid]
                else:
                    median_hz = 0.5 * (buf_sorted[mid-1] + buf_sorted[mid])

                # Guard against impossible spikes relative to current EMA
                if self.frequency_hz > 0 and median_hz > self.frequency_hz * self._max_jump_ratio:
                    median_hz = self.frequency_hz * self._max_jump_ratio

                # Exponential moving average to smooth jitter with asymmetric response
                alpha = self._alpha_up if median_hz >= self.frequency_hz else self._alpha_down
                if self.frequency_hz == 0.0:
                    self.frequency_hz = median_hz
                else:
                    self.frequency_hz = (1 - alpha) * self.frequency_hz + alpha * median_hz

        self._last_ts_us = ts

    def get_frequency(self):
        """Get the current measured frequency in Hz (rounded)."""
        return round(self.frequency_hz)

    def reset(self):
        """Reset all frequency data."""
        self.frequency_hz = 0.0
        self._last_ts_us = None


# Global variables to track IR sensor state (for backward compatibility)
detection_count = 0
last_trigger_time = 0
frequency_hz = 0.0
last_revolution_time = 0
previous_avg_hz = 0.0

# Configuration
SLOTS_PER_REVOLUTION = 5  # Number of slots in the encoder disc
slot_times = []  # Store timestamps of slot detections
frequency_readings = []  # Store last 60 frequency readings for averaging


# Interrupt handler function
def ir_interrupt_handler(pin):
    global detection_count, last_trigger_time, frequency_hz, slot_times, last_revolution_time, previous_avg_hz, current_value
    
    current_time = time.ticks_ms()
    
    last_trigger_time = current_time
    detection_count += 1
    slot_times.append(current_time)
    
    # Keep only last 15 slot times (3 full revolutions)
    if len(slot_times) > 15:
        slot_times.pop(0)
    
    # Calculate frequency after each complete revolution
    if detection_count % SLOTS_PER_REVOLUTION == 0:
        if len(slot_times) > SLOTS_PER_REVOLUTION:
            time_for_rev = time.ticks_diff(current_time, slot_times[-(SLOTS_PER_REVOLUTION + 1)])
            
            if time_for_rev > 0:
                # Hz = (1 revolution / time_in_ms) * 1000
                instant_hz = 1000.0 / time_for_rev
                frequency_readings.append(instant_hz)
                
                # Keep only last 40 readings for stable display
                if len(frequency_readings) > 40:
                    frequency_readings.pop(0)
                
                # Calculate average frequency
                avg_hz = sum(frequency_readings) / len(frequency_readings)
                frequency_hz = round(avg_hz)
                
                # Update display value (store full value, modulo happens in display)
                current_value = int(frequency_hz)
                
                # Only print if the average has changed
                if frequency_hz != previous_avg_hz:
                    #print(f"Revolution complete: {time_for_rev}ms = {round(instant_hz)} Hz (Avg: {frequency_hz} Hz, Display: {frequency_hz % 100})")
                    previous_avg_hz = frequency_hz
        
        last_revolution_time = current_time


async def display_task():
    """Continuously multiplex the two digits asynchronously."""
    global current_value
    try:
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
    finally:
        # Ensure display is blank when the task is cancelled or program exits
        try:
            for pin in pins:
                pin.value(0)
        except Exception:
            pass
        try:
            digits[0].value(1)
            digits[1].value(1)
        except Exception:
            pass


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
    
    # Setup IR infrared sensor on GPIO26 (no pull-up, to match working test)
    ir_sensor = Pin(26, Pin.IN)
    
    # Attach interrupt on falling edge only (one trigger per slot)
    # Using only one edge prevents double-counting
    ir_sensor.irq(trigger=Pin.IRQ_FALLING, 
                  handler=ir_interrupt_handler)
    
    print("IR infrared sensor initialized on GPIO26")
    print(f"Configuration: {SLOTS_PER_REVOLUTION} slots per revolution")
    print("Display shows frequency (0-99 Hz)")
    print("Waiting for optical interruptions...")
    
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
        print("\nProgram stopped")
