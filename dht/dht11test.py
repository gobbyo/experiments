from dht import DHT11
from machine import Pin
import time

def main():
    # Initialize DHT11 on GPIO 27 (change pin if needed)
    t = DHT11(Pin(27, Pin.IN, Pin.PULL_UP))
    
    # Wait for sensor to stabilize
    time.sleep(2)
    
    # Retry logic for measurement
    max_retries = 3
    for attempt in range(max_retries):
        try:
            t.measure()
            temp = t.temperature()
            humid = t.humidity()
            f = '{0:02}'.format(int(round((9/5)*temp+32,0)))
            print(f"Temperature: {f}F")
            print(f"Temperature: {temp}C")
            print(f"Humidity: {round(humid,0)}%")
            break  # Success, exit retry loop
        except OSError as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print("Failed to read sensor after multiple attempts")
                print("Check wiring and connections")

# Example usage
if __name__ == "__main__":
    main()