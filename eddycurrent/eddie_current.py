from machine import Pin
import time

# Global variables to track state
detection_count = 0
last_trigger_time = 0
frequency_hz = 0.0
last_revolution_time = 0
previous_avg_hz = 0.0
revolutions_per_minute = 0
minute_start_time = 0
minute_start_revolutions = 0

# Configuration
MAGNETS_PER_REVOLUTION = 5
magnet_times = []  # Store timestamps of magnet detections
frequency_readings = []  # Store last 60 frequency readings for averaging

# Interrupt handler function
def hall_interrupt_handler(pin):
    global detection_count, last_trigger_time, frequency_hz, magnet_times, last_revolution_time, previous_avg_hz
    
    # Debounce to prevent false triggers from noise/bouncing
    # 2ms allows for frequencies up to ~100 Hz with 5 magnets (2ms between detections at 100 Hz)
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
        # Use last full revolution for instant frequency
        # Need at least (MAGNETS_PER_REVOLUTION + 1) readings to measure time
        if len(magnet_times) > MAGNETS_PER_REVOLUTION:
            # Time for last complete revolution - from start of previous revolution to now
            # We need -(MAGNETS_PER_REVOLUTION + 1) because we want the time BEFORE the previous revolution started
            # However, we want from the PREVIOUS complete cycle to THIS one, which is exactly MAGNETS_PER_REVOLUTION intervals
            # So we need to go back (MAGNETS_PER_REVOLUTION) positions from before we added current_time
            # Since we already added current_time, we need index -(MAGNETS_PER_REVOLUTION + 1)
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
                
                # Only print if the average has changed
                if frequency_hz != previous_avg_hz:
                    print(f"Revolution complete: {time_for_rev}ms = {round(instant_hz)} Hz (Avg: {frequency_hz} Hz)")
                    previous_avg_hz = frequency_hz
        
        last_revolution_time = current_time

# Setup hall effect sensor on GPIO26
hall_sensor = Pin(26, Pin.IN, Pin.PULL_UP)

# Attach interrupt ONLY on falling edge (magnet detected)
# This prevents double-counting and improves accuracy
hall_sensor.irq(trigger=Pin.IRQ_FALLING, 
                handler=hall_interrupt_handler)

print("Hall effect sensor initialized on GPIO26")
print(f"Configuration: {MAGNETS_PER_REVOLUTION} magnets per revolution")
print("Waiting for magnetic field changes...")

last_displayed_hz = -1  # Track last displayed frequency to avoid duplicate prints
minute_start_time = time.ticks_ms()  # Initialize timer for 60-second counter

# Main loop - can do other things while interrupt handles sensor
while True:
    # Main program can do other things here
    # The interrupt will fire automatically when sensor state changes
    
    # Check if rotation has stopped (no detections for 2 seconds)
    current_time = time.ticks_ms()
    time_since_last_trigger = time.ticks_diff(current_time, last_trigger_time)
    
    if time_since_last_trigger > 2000 and frequency_hz > 0:
        frequency_hz = 0.0
        print("Rotation stopped")
    
    # Display frequency and status
    revolutions = detection_count // MAGNETS_PER_REVOLUTION
    magnets_in_current_rev = detection_count % MAGNETS_PER_REVOLUTION
    
    # Check if 60 seconds have elapsed
    time_since_minute_start = time.ticks_diff(current_time, minute_start_time)
    if time_since_minute_start >= 60000:  # 60 seconds = 60000 ms
        revolutions_per_minute = revolutions - minute_start_revolutions
        minute_start_revolutions = revolutions  # Track starting point for next period
        minute_start_time = current_time
        print(f"--- 60-second period complete: {revolutions_per_minute} revolutions ({revolutions_per_minute/60:.1f} Hz avg) ---")
    
    # Only print if the frequency has changed
    if frequency_hz != last_displayed_hz:
        revolutions_in_current_period = revolutions - minute_start_revolutions
        print(f"Frequency: {frequency_hz} Hz | Revolutions (60s): {revolutions_in_current_period} | Current: {magnets_in_current_rev}/{MAGNETS_PER_REVOLUTION} magnets")
        last_displayed_hz = frequency_hz
    
    time.sleep(1)
