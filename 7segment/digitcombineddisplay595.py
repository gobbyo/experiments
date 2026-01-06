from machine import Pin
import time

#   4 digit 7 segmented LED
#
#       digit 1        digit 2        digit 3        digit 4
#        _a_            _a_            _a_            _a_
#     f |_g_| b      f |_g_| b      f |_g_| b      f |_g_| b
#     e |___| c _h   e |___| c _h   e |___| c _h   e |___| c _h
#         d              d              d              d
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

waitreps = 50
waitonpaint = 0.001
# The variable below can be any number of digits for a 7 segment display. 
# For example, a 2 digit 7 segment display is digitpins=[1,0], four digit 7 segment display is digitpins=[3,2,1,0], etc.
fourdigitpins = [3,2,1,0]
segnum = [0x3F,0x06,0x5B,0x4F,0x66,0x6D,0x7D,0x07,0x7F,0x67]
fourlatchpin = const(7) #RCLK
fourclockpin = const(6) #SRCLK
fourdatapin = const(8) #SER

twodigitpins = [21,16]
twoclockpin = const(27) #SRCLK
twodatapin = const(28) #SER
twolatchpin = const(26) #RCLK

class segdisplays:
    def __init__(self):
        self.twodigits = []
        for d in twodigitpins:
            pin = Pin(d, Pin.OUT)
            pin.high()
            self.twodigits.append(pin)
        self. fourdigits = []

        for d in fourdigitpins:
            pin = Pin(d, Pin.OUT)
            pin.high()
            self.fourdigits.append(pin)
    def __del__(self):
        for t in self.twodigits:
            set_register(0,twolatch,twoclock,twodata)
            t.low()
        for f in self.fourdigits:
            set_register(0,fourlatch,fourclock,fourdata)
            f.low()

    def getArray(self,val):
        a = [0,0,0,0,0,0,0,0]
        i = 0
        for s in a:
            a[i] = (val & (0x01 << i)) >> i
            i += 1
        return a

    def set_register(self,val,latch,clock,data):
        input = [0,0,0,0,0,0,0,0]
        #open latch for data
        clock.low()
        latch.low()
        clock.high()

        input = self.getArray(val)

        #load data in register
        for i in range(7, -1, -1):
            clock.low()
            if input[i] == 1:
                data.high()
            else:
                data.low()
            clock.high()

        #close latch for data
        clock.low()
        latch.high()
        clock.high()

    def paintdigit(self,val,digit,latch,clock,data):
        digit.low()
        #display the value
        self.set_register(val,latch,clock,data)
        #wait to see it
        time.sleep(waitonpaint)
        #clear the display
        self.set_register(0,latch,clock,data)
        digit.high()

    def printnum(self,d,digits,latch,clock,data):
        if d < 99:
            num = "{0}".format(d)
            d = len(digits)-1
            i = len(num)-1
            while i >= 0 & d >= 0:
                if(num[i].isdigit()):
                    val = segnum[int(num[i])]
                    self.paintdigit(val,digits[d],latch,clock,data)
                    d -= 1
                i -= 1

    def printfloat(self,f,digits,latch,clock,data):
        if f < 100: 
            num = "{:.2f}".format(f)
            i = len(num)-1
            decimal = False
            d = 3
            while i >= 0 & d >= 0:
                if(num[i].isdigit()):
                    val = segnum[int(num[i])]
                    if decimal:
                        val |= 0x01 << 7
                        decimal = False
                    self.paintdigit(val,digits[d],latch,clock,data)
                    d -= 1
                else:
                    decimal = True
                i -= 1

def main():
    fourlatch = Pin(fourlatchpin, Pin.OUT)
    fourclock = Pin(fourclockpin, Pin.OUT)
    fourdata = Pin(fourdatapin, Pin.OUT)
        
    twolatch = Pin(twolatchpin, Pin.OUT)
    twoclock = Pin(twoclockpin, Pin.OUT)
    twodata = Pin(twodatapin, Pin.OUT)
    
    segdisp = segdisplays()

    try:
        print("circuit test...")

        for d in segdisp.twodigits:
            for i in range(8):
                for w in range(waitreps):
                    val = 0x01 << i
                    segdisp.paintdigit(val,d,twolatch,twoclock,twodata)
        
        for d in segdisp.fourdigits:
            for i in range(8):
                for w in range(waitreps):
                    val = 0x01 << i
                    segdisp.paintdigit(val,d,fourlatch,fourclock,fourdata)

        print("display test...")
        i = 1
        while i <= 20:
            for w in range(waitreps):
                segdisp.printnum(round(i),segdisp.twodigits,twolatch,twoclock,twodata)
                segdisp.printfloat(i,segdisp.fourdigits,fourlatch,fourclock,fourdata)
            i += 1.125
    finally:
        print("test finished")

if __name__ == '__main__':
	main()