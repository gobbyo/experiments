from machine import Pin
from utime import sleep_ms
ir=Pin(26,Pin.IN)

prev_value = -1
sensor_slots = 5
count = 0

# Main loop to monitor IR sensor
# Simple polling method to verify wiring and functionality of sensor
# Not using interrupts for tachometer-like functionality
while True:
    try:
        current_value = ir.value()
        if current_value != prev_value:
            print(current_value)
            prev_value = current_value
            if current_value == 1:
                count += 1
                if count >= sensor_slots: #just in case it exceeds
                    print("Revolution complete")
                    count = 0
        sleep_ms(100)
        
    except KeyboardInterrupt:
        break