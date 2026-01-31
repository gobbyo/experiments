from machine import Pin
import neopixel
import time

MAX_BRIGHTNESS = 127  # Set to a value between 0 and 255

# For digital hall effect sensor (detects presence/absence)
def read_sensor():
    hall_sensor = Pin(26, Pin.IN, Pin.PULL_UP)
    light = Pin(23, Pin.OUT)   # change to your pin
    np = neopixel.NeoPixel(light, 1)

    last_state = None  # Track previous state
    
    while True:
        current_state = hall_sensor.value()
        
        # Only print when state changes
        if current_state != last_state:
            if current_state == 0:
                print("South pole detected")
                np[0] = (0, MAX_BRIGHTNESS, 0)  # Green
                np.write()
            else:
                print("No magnet")
                np[0] = (0, 0, 0)
                np.write()
            last_state = current_state
        
        time.sleep(0.005)  # Check more frequently for state changes


if __name__ == "__main__":
    read_sensor() 