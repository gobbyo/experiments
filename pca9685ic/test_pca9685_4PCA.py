import asyncio
#from platform import machine
from machine import Pin, I2C
from micropython_pca9685 import PCA9685
import ujson
import uio
import os
import neopixel
import random
import utime

PWM_FREQUENCY = 1024  # PWM frequency for PCA9685

BOARD_TYPE = "XIAO_RP2040"  # Options: "RP2040_ZERO", "XIAO_RP2040", "ESP32C3", "S2_MINI"

# Set I2C pins based on board type
if BOARD_TYPE == "XIAO_RP2040":
    SDA_PIN = 6  # SDA pin for I2C on Xiao RP2040
    SCL_PIN = 7  # SCL pin for I2C on Xiao RP2040
    XIAO_POWER_PIN = 11  # Power pin for Xiao RP2040
    XIAO_LED_PIN = 12  # RGB LED pin for Xiao RP2040
    from ws2812 import WS2812
    PCA_SWITCH_PIN = 28  # Pin to control the PCA9685 modules
    SLEEPLEN_MOD = 1.0
    WAIT_TIME_MOD = 1.0
elif BOARD_TYPE == "ESP32C3":
    PCA_SWITCH_PIN = 0  # Pin to control the PCA9685 modules
    SDA_PIN = 6  # SDA pin for I2C on Xiao RP2040
    SCL_PIN = 7  # SCL pin for I2C on Xiao RP2040
    LED_PIN = 10  # Pin connected to the internal LED
elif BOARD_TYPE == "S2_MINI":
    SDA_PIN = 4  # SDA pin for I2C on S2 Mini
    SCL_PIN = 5  # SCL pin for I2C on S2 Mini
    LED_PIN = 15  # Pin connected to the internal LED
    PCA_SWITCH_PIN = 1  # Pin to control the PCA9685 modules
    SLEEPLEN_MOD = 2.0
    WAIT_TIME_MOD = 1.9
else:  # Default to RP2040_ZERO
    SDA_PIN = 2  # SDA pin for I2C on RP2040 Zero
    SCL_PIN = 3  # SCL pin for I2C on RP2040 Zero
    NEOPIXEL_PIN = 16  # Pin connected to the NeoPixel LED
    from ws2812 import WS2812
    PCA_SWITCH_PIN = 28  # Pin to control the PCA9685 modules
    SLEEPLEN_MOD = 1.0
    WAIT_TIME_MOD = 1.0

SHORT = 0.125
LONG = 0.5
BLINK_SLEEP = 0.25
RED = (255, 0, 0)  # Color for the NeoPixel LED
GREEN = (0, 255, 0)  # Color for the NeoPixel LED
BLUE = (0, 0, 255)  # Color for the NeoPixel LED
LED_OFF = (0, 0, 0)  # Color to turn off the NeoPixel LED


STATIC_CHOICES = [("a", 2), ("c", 14), ("c", 2), ("d", 2), ("b", 2), ("b", 13)]

async def blink_LED(duration, color=RED):
    if BOARD_TYPE == "XIAO_RP2040":
        power = Pin(XIAO_POWER_PIN, Pin.OUT)
        led = WS2812(XIAO_LED_PIN,1)
        power.value(1)
        led.pixels_fill(color)  # Set the color of the NeoPixel
        led.pixels_show()
        await asyncio.sleep(duration)
        power.value(0)
    elif BOARD_TYPE == "S2_MINI": # ignore color as S2_MINI uses a different LED
        led = Pin(LED_PIN, Pin.OUT)
        led.value(1)  # Turn on the LED
        await asyncio.sleep(duration)
        led.value(0)  # Turn off the LED
    else:
        led = neopixel.NeoPixel(Pin(NEOPIXEL_PIN), 1)
        led[0] = color  # Set the color of the NeoPixel
        led.write()
        await asyncio.sleep(duration)
        led[0] = LED_OFF  # Set the color of the NeoPixel
        led.write()  # Turn off the LED

async def run_sequence(pca, file_name):
    try:
        with uio.open("sequences/" + file_name, "r") as f:
            json_data = ujson.load(f)
            
        end = len(json_data)
        #print(f"Running sequence from file: {file_name}, total entries: {end}")

        # Keep track of the last channel and module
        last_ch = None
        last_module = None
        is_static = False

        if file_name.startswith("static"):
            is_static = True
        
        static_substitutions = random.choice(STATIC_CHOICES)

        for i in range(end):
            
            #print(f"json_data[{i}]={json_data[i]}")

            if is_static:
                #print(f"static_substitutions={static_substitutions}")
                m = static_substitutions[0]
                ch = static_substitutions[1]
            else:
                m = json_data[i]['m']
                ch = json_data[i]['ch']

            #print(f"is_static={is_static}, ch={ch}, m={m}")
            module = ord(m) - ord('a')
            
            # Safety check: ensure module index is valid (0-3 for pca modules a-d)
            if module < 0 or module >= len(pca):
                #print(f"Invalid module '{m}' (index {module}), skipping")
                continue
                
            brightness = json_data[i]['lu']
            sleeplen = json_data[i]['s']
            
            # Skip creating a fade task (tail) if this is the same channel and module as the last one
            if last_ch != ch or last_module != module:
                #print(f"fade module={module} ch={ch}, brightness={brightness}, sleep={sleeplen}")
                asyncio.create_task(fade(pca[module], ch, brightness, sleeplen)) # Create a task for each LED
            else:
                #print(f"fade module={module} ch={ch}, brightness={brightness}, sleep={sleeplen}")
                pca[module].channels[ch].duty_cycle = percentage_to_duty_cycle(brightness)
                #pca.channels[ch].duty_cycle = percentage_to_duty_cycle(brightness)
                await asyncio.sleep(sleeplen * SLEEPLEN_MOD)
                
            # Update the last channel and module
            last_ch = ch
            last_module = module

            await asyncio.sleep(json_data[i]['w'] * WAIT_TIME_MOD)
        return True
    except OSError as e:
        #print(f"Error opening file {file_name}: {e}")
        await blink_LED(LONG, RED)  # Changed to use proper function name and single duration
        return False
    except ujson.JSONDecodeError:
        await blink_LED(SHORT, RED)  # Changed to use proper function name and single duration
        #print(f"Error parsing JSON in file {file_name}")
        return False
    except Exception as e:
        await blink_LED(LONG, RED)  # Changed to use proper function name and single duration
        #print(f"Unexpected error: {e}")
        return False

def percentage_to_duty_cycle(percentage):
    return int((percentage / 100) * 0xFFFF)

async def fade(pca, ch, brightness, sleeplen=0.25, fadevalue=0.01):
    iterations = max(1, int(sleeplen/fadevalue))  # Renamed from 'iter' and added safety check
    dimval = brightness/iterations
    for i in range(iterations):
        pca.channels[ch].duty_cycle = percentage_to_duty_cycle((i+1)*dimval)
        await asyncio.sleep(fadevalue)
    #print(f"LED {ch} brightness at {(int)((i+1)*dimval)}%")
    for i in range(iterations):
        pca.channels[ch].duty_cycle = percentage_to_duty_cycle(brightness - ((i+1)*dimval))
        await asyncio.sleep(fadevalue)
    #print(f"LED {ch} brightness at {brightness - (int)((i+1)*dimval)}%")
    pca.channels[ch].duty_cycle = percentage_to_duty_cycle(0)

async def run_static_sequences_continuously(pca, stop_event):
    static_files = ["static_longthrob_sequence.json", "static_shortthrob_sequence.json"]
    while not stop_event.is_set():
        for file_name in static_files:
            await run_sequence(pca, file_name)
            await asyncio.sleep(0)  # Yield to event loop

# Define the main function to run the event loop
async def main():
    if BOARD_TYPE == "RP2040_ZERO":
        red = (255, 0, 0)
        green = (0, 255, 0)
        blue = (0, 0, 255)
        led = neopixel.NeoPixel(Pin(16), 1)  # Using internal NeoPixel on Pin 16

    slow = [1, 1]
    walk = [0.5, 0.25]
    med = [0.19, 0.1]
    fast = [0.14, 0.07]
    veryfast = [0.125, 0.05]
    brightness = 20 #percent

    pcaswitch = Pin(PCA_SWITCH_PIN, Pin.OUT)
    pcaswitch.off()  # PNP, turn on the PCA9685 modules
    await asyncio.sleep(1)  # Wait for the PCA9685 modules to initialize

    i2c = I2C(1, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN))  # Correct I2C pins for RP2040
    pca_A = PCA9685(i2c, address=0x40)
    pca_B = PCA9685(i2c, address=0x41)
    pca_C = PCA9685(i2c, address=0x42)
    pca_D = PCA9685(i2c, address=0x43)

    pca_A.frequency = pca_B.frequency = pca_C.frequency = pca_D.frequency = PWM_FREQUENCY
    pca = [pca_A, pca_B, pca_C, pca_D] 
    module = ['a', 'b', 'c', 'd']
    
    # Test code - Set to True to enable testing
    if False: # Set to True to Test all LEDs on all modules
        for i in range(len(pca)):
            for j in range(16):
                print(f"mod:{module[i]},{j}")
                asyncio.create_task(fade(pca[i], j, brightness, walk[0])) # Create a task for each LED
                await asyncio.sleep(walk[1])

    if False: # Set to True to SLOWLY Test all LEDs on all modules
        for i in range(len(pca)):
            for j in range(16):
                print(f"mod:{module[i]},{j}")
                asyncio.create_task(fade(pca[i], j, brightness, slow[0])) # Create a task for each LED
                await asyncio.sleep(0.5)
    
    # Main sequence loop
    # while True:
    if True:  # Set to True to run the main sequence loop
        dir = "sequences/"
        files = os.listdir(dir)
        # files = ["A_LED_sequence.json"]
        # Remove static files from the list to avoid double-running
        static_files = {"static_longthrob_sequence.json", "static_shortthrob_sequence.json"}
        sequence_files = [f for f in files if f not in static_files]

        stop_event = asyncio.Event()
        static_task = asyncio.create_task(run_static_sequences_continuously(pca, stop_event))

        try:
            for f in sequence_files:
                await blink_LED(LONG, GREEN)  # Flash the LED green to indicate start
                print(f"Running sequence from file: {f}")
                await run_sequence(pca, f) # Run the sequence from the JSON file
                await asyncio.sleep(1)
        finally:
            stop_event.set()
            await static_task  # Wait for static task to finish

    pcaswitch.off()

if __name__ == "__main__":
    # Create and run the event loop
    loop = asyncio.get_event_loop()  
    loop.create_task(main())  # Create a task to run the main function
    loop.run_forever()  # Run the event loop indefinitely