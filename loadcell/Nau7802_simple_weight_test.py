from nau7802_async import NAU7802, _sleep_ms
from machine import Pin, SoftI2C
import asyncio

SCL_PIN = 13
SDA_PIN = 12
I2C_FREQ = 100000

READ_SAMPLES = 100
READ_INTERVAL_MS = 50
READ_TIMEOUT_MS = 2000

I2C_ERROR_BACKOFF_MS = 20
MAX_CONSECUTIVE_I2C_ERRORS = 30

async def main():
    i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=I2C_FREQ)
    scale = NAU7802(i2c=i2c)

    ok = await scale.initialize()
    if not ok:
        print("NAU7802 init failed:", scale.last_error)
        return

    await _sleep_ms(1500)

    if not await scale.tare(times=300):
        print("Tare failed")
        return

    scale.zero_deadband = 2.0
    print("Tare offset:", scale.offset)

    calibrate = input("Calibrate with known mass now? (y/n): ").strip().lower()
    if calibrate == "y":
        known_mass_text = input("Known mass in grams (e.g. 500): ").strip()
        try:
            known_mass = float(known_mass_text)
        except ValueError:
            print("Invalid mass input")
            return

        factor = await scale.calibrate_with_known_mass(known_mass, times=300)
        if factor is None:
            print("Calibration failed:", scale.last_error)
            return
        print("Calibration factor (g/count):", factor)
    else:
        print("Skipping known-mass calibration; readings may not be grams yet")

    total_i2c_errors = 0
    consecutive_i2c_errors = 0

    while True:
        try:
            weight = await scale.read_weight(times=READ_SAMPLES, timeout_ms=READ_TIMEOUT_MS)
            consecutive_i2c_errors = 0
        except OSError as exc:
            total_i2c_errors += 1
            consecutive_i2c_errors += 1
            if total_i2c_errors == 1 or (total_i2c_errors % 10) == 0:
                print(
                    "WARN: I2C error during read_weight: {} (count={}, consecutive={})".format(
                        exc, total_i2c_errors, consecutive_i2c_errors
                    )
                )

            if consecutive_i2c_errors >= MAX_CONSECUTIVE_I2C_ERRORS:
                print("WARN: attempting NAU7802 re-initialize after repeated I2C errors...")
                ok = await scale.initialize()
                if ok:
                    print("NAU7802 re-initialized")
                    consecutive_i2c_errors = 0
                else:
                    print("Re-init failed:", scale.last_error)

            await _sleep_ms(I2C_ERROR_BACKOFF_MS)
            continue

        if weight is None:
            print("Read timeout")
        else:
            print("{:.2f} g".format(weight))
        await _sleep_ms(READ_INTERVAL_MS)

if __name__ == "__main__":
    asyncio.run(main())