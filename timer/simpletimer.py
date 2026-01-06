from machine import Pin, Timer

led = Pin(25, Pin.OUT)
tmr = Timer()

def tick(timer):
    global led
    led.toggle()

tmr.init(freq=2.5, mode=Timer.PERIODIC, callback=tick)