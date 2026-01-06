from machine import Pin
import uasyncio as asyncio

#   2 digit 7 segmented LED
#
#       digit 1        digit 2    
#        _a_            _a_        
#     f |_g_| b      f |_g_| b     
#     e |___| c _h   e |___| c _h   
#         d              d          
#
# num   hgfe dcba   hex
#
# 0 = 	0011 1111   0x3F
# 1 =	0000 0110   0x06
# 2 =	0101 1011   0x5B
# 3 =	0100 1111   0x4F
# 4 =	0110 0110   0x66
# 5 =	0110 1101   0x6D
# 6 =	0111 1101   0x7D
# 7 =	0000 0111   0x07
# 8 =   0111 1111   0x7F
# 9 =   0110 0111   0x67

digit_number = [4, 5]
pin_number = [6, 7, 8, 9, 10, 11, 12, 13]  # a,b,c,d,e,f,g,h
segnum = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x67]
digits = [Pin(digit_number[0], Pin.OUT), Pin(digit_number[1], Pin.OUT)]
pins = [Pin(pin_number[0], Pin.OUT), Pin(pin_number[1], Pin.OUT), Pin(pin_number[2], Pin.OUT), Pin(pin_number[3], Pin.OUT),
        Pin(pin_number[4], Pin.OUT), Pin(pin_number[5], Pin.OUT), Pin(pin_number[6], Pin.OUT), Pin(pin_number[7], Pin.OUT)]

# Global variable to hold the current display value
current_value = 0


def paintnumber(val, digit):
    """Display a single digit value on the specified digit."""
    digit.value(0)
    i = 0
    for pin in pins:
        pin.value((val & (0x01 << i)) >> i)
        i += 1
    digit.value(1)


async def display_task():
    """Continuously multiplex the two digits asynchronously."""
    global current_value
    
    while True:
        # Convert value to two digits (0-99)
        value = current_value % 100
        digit1 = value // 10
        digit2 = value % 10
        
        # Display digit 1 (tens place)
        if digit1 > 0 or value >= 10:  # Don't show leading zero
            # Clear all segments first
            for pin in pins:
                pin.value(0)
            
            digits[1].value(0)
            i = 0
            for pin in pins:
                pin.value((segnum[digit1] & (0x01 << i)) >> i)
                i += 1
            await asyncio.sleep_ms(5)
            digits[1].value(1)
        else:
            digits[1].value(1)
        
        # Blanking period to prevent ghosting
        for pin in pins:
            pin.value(0)
        await asyncio.sleep_ms(1)
        
        # Display digit 2 (ones place)
        digits[0].value(0)
        i = 0
        for pin in pins:
            pin.value((segnum[digit2] & (0x01 << i)) >> i)
            i += 1
        await asyncio.sleep_ms(5)
        digits[0].value(1)
        
        # Blanking period to prevent ghosting
        for pin in pins:
            pin.value(0)
        await asyncio.sleep_ms(1)


def set_value(value):
    """Set the value to be displayed (0-99)."""
    global current_value
    current_value = max(0, min(99, value))


def get_value():
    """Get the current displayed value."""
    global current_value
    return current_value


async def counter_task():
    """Count from 0 to 20, incrementing every 250ms."""
    global current_value
    
    while True:
        for i in range(21):  # 0 to 20
            current_value = i
            await asyncio.sleep_ms(250)


async def main():
    """Main async function to run display and other tasks."""
    print("--starting display of digits--")
    
    # Create the display task and counter task
    display = asyncio.create_task(display_task())
    counter = asyncio.create_task(counter_task())
    
    # Keep running both tasks
    await asyncio.gather(display, counter)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("")
        print("Program shut down by user")
    finally:
        for pin in pins:
            pin.value(0)
        for digit in digits:
            digit.value(1)
        print("GPIO cleaned up")