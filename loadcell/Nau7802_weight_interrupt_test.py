from nau7802_async import NAU7802, _sleep_ms
from machine import Pin, SoftI2C
import uasyncio as asyncio
from time import ticks_ms, ticks_diff

# Update these pins to your wiring
SCL_PIN = 13
SDA_PIN = 12
DRDY_PIN = 11  # NAU7802 DRDY pin wired to this GPIO
ONBOARD_LED_PIN = 25

I2C_FREQ = 400000
READ_SAMPLES = 60
TARE_SAMPLES = 300
CAL_SAMPLES = 300
SETTLE_MS = 1500
KNOWN_MASS_G = 222.0
AUTO_TARE_WAIT_MS = 3000
AUTO_CAL_WAIT_MS = 5000

# Print only when weight changes by at least this amount
CHANGE_THRESHOLD_G = 2.0
DRDY_TIMEOUT_MS = 500


async def blink_for_duration(led, duration_ms, on_ms=120, off_ms=120):
    elapsed = 0
    while elapsed < duration_ms:
        led.value(1)
        await _sleep_ms(on_ms)
        elapsed += on_ms
        if elapsed >= duration_ms:
            break
        led.value(0)
        await _sleep_ms(off_ms)
        elapsed += off_ms
    led.value(0)


async def blink_count(led, count, on_ms=100, off_ms=100):
    for _ in range(count):
        led.value(1)
        await _sleep_ms(on_ms)
        led.value(0)
        await _sleep_ms(off_ms)


async def main():
    i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=I2C_FREQ)
    led = Pin(ONBOARD_LED_PIN, Pin.OUT)
    led.value(0)
    scale = NAU7802(i2c=i2c)

    ok = await scale.initialize()
    if not ok:
        print("NAU7802 init failed:", scale.last_error)
        await blink_count(led, 6, on_ms=80, off_ms=80)
        return

    await _sleep_ms(SETTLE_MS)

    print("Remove all weight from scale. Taring in {} ms...".format(AUTO_TARE_WAIT_MS))
    await blink_for_duration(led, AUTO_TARE_WAIT_MS, on_ms=250, off_ms=250)
    if not await scale.tare(times=TARE_SAMPLES):
        print("Tare failed:", scale.last_error)
        await blink_count(led, 6, on_ms=80, off_ms=80)
        return
    print("Tare offset:", scale.offset)
    await blink_count(led, 2, on_ms=180, off_ms=120)

    known_mass = float(KNOWN_MASS_G)
    if known_mass <= 0:
        print("Known mass must be > 0")
        await blink_count(led, 6, on_ms=80, off_ms=80)
        return

    print("Place {} g on the scale. Calibrating in {} ms...".format(known_mass, AUTO_CAL_WAIT_MS))
    await blink_for_duration(led, AUTO_CAL_WAIT_MS, on_ms=100, off_ms=100)

    factor = await scale.calibrate_with_known_mass(known_mass, times=CAL_SAMPLES)
    if factor is None:
        print("Calibration failed:", scale.last_error)
        await blink_count(led, 6, on_ms=80, off_ms=80)
        return

    print("Calibration factor (g/count):", factor)
    await blink_count(led, 3, on_ms=150, off_ms=100)

    scale.zero_deadband = CHANGE_THRESHOLD_G / 2

    flag = asyncio.ThreadSafeFlag()
    last_reported = None

    def on_drdy(_pin):
        try:
            flag.set()
        except Exception:
            pass

    drdy = Pin(DRDY_PIN, Pin.IN, Pin.PULL_UP)
    drdy.irq(trigger=Pin.IRQ_FALLING, handler=on_drdy)

    print("Listening for weight changes via DRDY interrupt...")
    print("Threshold: +/- {:.2f} g".format(CHANGE_THRESHOLD_G))
    print("DRDY pin {} initial state: {}".format(DRDY_PIN, drdy.value()))
    led.value(1)
    fallback_notice_printed = False

    while True:
        got_interrupt = False

        if hasattr(asyncio, "wait_for_ms"):
            try:
                await asyncio.wait_for_ms(flag.wait(), DRDY_TIMEOUT_MS)
                got_interrupt = True
            except Exception:
                got_interrupt = False
        else:
            begin = ticks_ms()
            while ticks_diff(ticks_ms(), begin) < DRDY_TIMEOUT_MS:
                if scale.available():
                    break
                await _sleep_ms(2)

        if not got_interrupt and not scale.available():
            continue

        if (not got_interrupt) and (not fallback_notice_printed):
            print("WARN: No DRDY interrupts seen. Using conversion-ready fallback; check DRDY wiring/pin.")
            fallback_notice_printed = True

        weight = await scale.read_weight(times=READ_SAMPLES, timeout_ms=1000)
        if weight is None:
            continue

        if last_reported is None or abs(weight - last_reported) >= CHANGE_THRESHOLD_G:
            print("{:.2f} g".format(weight))
            last_reported = weight


if __name__ == "__main__":
    asyncio.run(main())
