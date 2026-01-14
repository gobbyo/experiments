from machine import Pin, Timer
import time

flash_cycles = 5

def tickAndData(timer, data):
    led.toggle()
    def cb(t):
        print(data)
    return cb

def tick(timer):
    global prev_ms, start_ms, led_state
    led.value(led_state) # set LED to current state
    ms = time.ticks_ms()
    current = ms - prev_ms
    if(led_state):
        s = "LED ON "
    else:
        s = "LED OFF"
    print(f"{s} since previous = {current/1000:.2f}s, since start = {(ms - start_ms)/1000:.2f}s")
    prev_ms = ms # update previous time
    led_state = not led_state  # toggle state for next time

def main():
    global led, tim0, tim1, prev_ms, start_ms, led_state
    start_ms = time.ticks_ms()
    t = Timer()
    led = Pin(15, Pin.OUT)
    prev_ms = time.ticks_ms()
    t.init(period=1000, mode=Timer.ONE_SHOT, callback=lambda t: tickAndData(t, "LED ON")(t))
    time.sleep(1)
    t.init(period=1000, mode=Timer.ONE_SHOT, callback=lambda t: tickAndData(t, "LED OFF")(t))
    time.sleep(2)
    led_state = True
    print("Starting periodic timer...")
    p_ms = 1000
    t.init(period=p_ms, mode=Timer.PERIODIC, callback=lambda t: tick(t))
    time.sleep((p_ms/1000) * flash_cycles * 2) # flashes 5 on, 5 off
    t.deinit() # stop timer

if __name__ == "__main__":
    main()