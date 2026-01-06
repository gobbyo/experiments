from machine import Pin
import time

def main():
    yellowswpin = 15
    blueswpin = 16

    try:
        yellowbutton=Pin(yellowswpin,Pin.IN,Pin.PULL_DOWN)
        bluebutton=Pin(blueswpin,Pin.IN,Pin.PULL_DOWN)
        picopin = Pin(25,Pin.OUT)
        prevyellowon = False
        prevyellowoff = False
        prevblueon = False
        prevblueoff = False

        print("starting program")
        while True:
            if yellowbutton.value() == 1:
                if prevyellowon != True:
                    print("Yellow button on")
                    prevyellowon = True
                    prevyellowoff = False
                    picopin.high()
            else:
                if prevyellowoff != True:
                    print("Yellow button off")
                    prevyellowoff = True
                    prevyellowon = False
                    picopin.low()

            if bluebutton.value() == 1:
                if prevblueon != True:
                    print("Blue button on")
                    prevblueon = True
                    prevblueoff = False
                    picopin.high()
            else:
                if prevblueoff != True:
                    print("Blue button off")
                    prevblueoff = True
                    prevblueon = False
                    picopin.low()
            time.sleep(.025)
    except KeyboardInterrupt:
        print("Program shut down by user")
    finally:
        print("Cleaning up and shutting down")
if __name__ == '__main__':
    main()