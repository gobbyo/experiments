from machine import Pin
import shiftreg74HC595ic.shiftregister as sr
import time

def main():
    print("main")
    shift = sr.shiftregister()
    shift.set_registerSize(8)
    shift.set_pins(17,16,18)
    shift.register = [0,0,0,0,0,0,0,0]
    shift.set_register()

    try:
        for i in range(0,len(shift.register)):
            shift.register[i] = 1
            shift.set_register()
            time.sleep(.5)
        print("register = {0}".format(shift.register))
        time.sleep(3)
        shift.register = [0,0,0,0,0,0,0,0]
        shift.set_register()
        print("register = {0}".format(shift.register))
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    finally:
        print('Done')

if __name__ == '__main__':
    main()