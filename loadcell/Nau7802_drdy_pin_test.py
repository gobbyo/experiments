from machine import Pin, SoftI2C
from time import ticks_ms, ticks_diff, sleep_ms

# ----- Configure for your board/wiring -----
DRDY_PIN = 10           # GPIO connected to NAU7802 DRDY
ONBOARD_LED_PIN = 25    # onboard status LED
USE_PULL_UP = True      # DRDY is typically open-drain/active-low on many boards
TEST_DURATION_MS = 30000
SUMMARY_EVERY_MS = 1000
POLL_INTERVAL_MS = 2

# Optional I2C presence check (not required for pin test)
SCL_PIN = 13
SDA_PIN = 12
I2C_FREQ = 400000
NAU7802_ADDR = 0x2A


irq_count = 0
last_irq_ms = 0


def on_drdy(_pin):
    global irq_count, last_irq_ms
    irq_count += 1
    last_irq_ms = ticks_ms()


def main():
    global irq_count

    led = Pin(ONBOARD_LED_PIN, Pin.OUT)
    led.value(0)

    # Optional bus scan to verify NAU7802 is present
    try:
        i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=I2C_FREQ)
        devices = i2c.scan()
        print("I2C scan:", devices)
        if NAU7802_ADDR in devices:
            print("NAU7802 detected at 0x{:02X}".format(NAU7802_ADDR))
        else:
            print("NAU7802 not detected on I2C (DRDY test can still run)")
    except Exception as exc:
        print("I2C scan failed:", exc)

    pull_mode = Pin.PULL_UP if USE_PULL_UP else None
    drdy = Pin(DRDY_PIN, Pin.IN, pull_mode)
    drdy.irq(trigger=Pin.IRQ_FALLING, handler=on_drdy)

    print("Testing DRDY on GPIO{} for {} ms".format(DRDY_PIN, TEST_DURATION_MS))
    print("Initial DRDY state:", drdy.value())

    start_ms = ticks_ms()
    last_summary_ms = start_ms
    last_state = drdy.value()
    state_change_count = 0
    led_state = 0

    while ticks_diff(ticks_ms(), start_ms) < TEST_DURATION_MS:
        now_ms = ticks_ms()
        state = drdy.value()

        # Polling-based edge visibility (independent of IRQ)
        if state != last_state:
            state_change_count += 1
            print("STATE CHANGED ->", state, "at", ticks_diff(now_ms, start_ms), "ms")
            last_state = state

        # Periodic summary
        if ticks_diff(now_ms, last_summary_ms) >= SUMMARY_EVERY_MS:
            led_state = 0 if led_state else 1
            led.value(led_state)
            print(
                "summary: irq_count={}, state_changes={}, current_state={}, last_irq_ago_ms={}".format(
                    irq_count,
                    state_change_count,
                    state,
                    ticks_diff(now_ms, last_irq_ms) if last_irq_ms else -1,
                )
            )
            last_summary_ms = now_ms

        sleep_ms(POLL_INTERVAL_MS)

    drdy.irq(handler=None)
    led.value(0)

    print("--- DRDY TEST COMPLETE ---")
    print("Total IRQ events:", irq_count)
    print("Total state changes:", state_change_count)
    if irq_count == 0 and state_change_count == 0:
        print("No DRDY activity detected. Check DRDY wiring, GPIO number, and pull-up setting.")
    elif irq_count == 0 and state_change_count > 0:
        print("Pin changes seen but IRQ not firing. Check IRQ trigger mode/pin capability.")
    else:
        print("DRDY activity detected.")


if __name__ == "__main__":
    main()
