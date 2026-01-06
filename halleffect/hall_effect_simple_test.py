from machine import Pin, ADC
import time

# For digital hall effect sensor (detects presence/absence)
def read_sensor():
    hall_sensor = Pin(26, Pin.IN, Pin.PULL_UP)
    last_state = None  # Track previous state
    
    while True:
        current_state = hall_sensor.value()
        
        # Only print when state changes
        if current_state != last_state:
            if current_state == 0:
                print("Magnet detected!")
            else:
                print("No magnet")
            last_state = current_state
        
        time.sleep(0.005)  # Check more frequently for state changes


if __name__ == "__main__":
    read_sensor() 