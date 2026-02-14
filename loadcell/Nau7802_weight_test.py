from nau7802_async import NAU7802, _sleep_ms
from machine import Pin, SoftI2C
import asyncio

async def main():
    i2c = SoftI2C(scl=Pin(13), sda=Pin(12), freq=400000)
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

    while True:
        weight = await scale.read_weight(times=100)
        if weight is None:
            print("Read timeout")
        else:
            print("{:.2f} g".format(weight))
        await _sleep_ms(50)

if __name__ == "__main__":
    asyncio.run(main())