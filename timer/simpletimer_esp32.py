from machine import Pin, Timer
import time

flash_cycles = 5

def tickAndData(timer, data):
    led.toggle()
    def cb(t):
        print(data)
    return cb

def tick(timer):
    global prev_ms, start_ms
    led.toggle()
    ms = time.ticks_ms()
    current = ms - prev_ms
    print(f"seconds since previous = {current/1000:.2f}, since start = {(ms - start_ms)/1000:.2f}")
    prev_ms = ms

def main():
    global tim0, tim1, prev_ms, start_ms
    start_ms = time.ticks_ms()
    tim0 = Timer(0)
    tim1 = Timer(1)
    global led
    led = Pin(25, Pin.OUT)
    prev_ms = time.ticks_ms()
    tim0.init(period=1000, mode=Timer.ONE_SHOT, callback=lambda t: tickAndData(tim0, "LED ON")(t))
    time.sleep(1)
    tim0.init(period=1000, mode=Timer.ONE_SHOT, callback=lambda t: tickAndData(tim0, "LED OFF")(t))
    time.sleep(2)
    tim0.deinit() # stop timer
    print("Starting periodic timer...")
    tim1.init(period=1000, mode=Timer.PERIODIC, callback=lambda t: tick(t))
    time.sleep(flash_cycles * 2) # flashes 5 on, 5 off
    tim1.deinit() # stop timer


if __name__ == "__main__":
    main()