from machine import Pin
import shiftreg74HC595ic.shiftregister as shiftregister
import time

# the shift register is connected to the LED bar as follows:
#   Q0 = LED1
#   Q1 = LED2
#   Q2 = LED3
#   Q3 = LED4
#   Q4 = LED5
#   Q5 = LED6
#   Q6 = LED7
#   Q7 = LED8
#   Q8 = LED9
#   Q9 = LED10

def testLEDBar(shiftreg, pausetime):
    shiftreg.set_register()
    for i in range(len(shiftreg.register)):
        shiftreg.register[i] = 1
        shiftreg.set_register()
        time.sleep(pausetime)
    while i >= 0:
        shiftreg.register[i] = 0
        shiftreg.set_register()
        time.sleep(pausetime)
        i -= 1
    shiftreg.register = [0,0,0,0,0,0,0,0,0,0]
    shiftreg.set_register()
    
def main():
    try:
        onboardLED = Pin(25,Pin.OUT)
        onboardLED.high()
        time.sleep(2)
        onboardLED.low()

        r = shiftregister.shiftregister()
        r.set_registerSize(10)

        while True:
            testLEDBar(r,0.1)
            time.sleep(.25)
    except KeyboardInterrupt:
        print("stopping program")

    finally:
        print("Graceful exit")
if __name__ == '__main__':
    main()