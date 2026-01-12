import network
import time
import uasyncio as asyncio
import secrets  # contains WIFI_SSID and WIFI_PASSWORD

ASYNC_POLL_DELAY = 0.1


async def connect_wifi_async(timeout_s=10):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)

    deadline = time.ticks_add(time.ticks_ms(), int(timeout_s * 1000))
    while not wlan.isconnected() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        await asyncio.sleep(ASYNC_POLL_DELAY)

    if not wlan.isconnected():
        raise RuntimeError("WiFi connection failed (async)")

    print("Connected:", wlan.ifconfig())
    return wlan


async def disconnect_wifi_async(wlan=None, deactivate=True, timeout_s=2):
    wlan = wlan or network.WLAN(network.STA_IF)
    if not wlan.active():
        return

    if wlan.isconnected():
        wlan.disconnect()
        deadline = time.ticks_add(time.ticks_ms(), int(timeout_s * 1000))
        while wlan.isconnected() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            await asyncio.sleep(ASYNC_POLL_DELAY)

    if deactivate:
        wlan.active(False)

    print("Disconnected (async)")


async def main():
    wlan = await connect_wifi_async()
    await asyncio.sleep(5)
    await disconnect_wifi_async(wlan)


if __name__ == "__main__":
    asyncio.run(main())
