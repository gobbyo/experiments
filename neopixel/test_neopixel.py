import machine
import neopixel
import time

# Pin where your NeoPixel data line is connected
# 23 is the pin on the cheap rp2040 boards from china

MAX_BRIGHTNESS = 32  # Set to a value between 0 and 255

pin = machine.Pin(23)   # change to your pin
n = 1                  # number of pixels

np = neopixel.NeoPixel(pin, n)

# Red
np[0] = (MAX_BRIGHTNESS, 0, 0)
np.write()
time.sleep(1)

# white
np[0] = (MAX_BRIGHTNESS, MAX_BRIGHTNESS, MAX_BRIGHTNESS)
np.write()
time.sleep(1)

# blue
np[0] = (0, 0, MAX_BRIGHTNESS)
np.write()
time.sleep(1)

np[0] = (0, 0, 0)
np.write()
time.sleep(1)