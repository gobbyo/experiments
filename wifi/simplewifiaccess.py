import network
import time
import secrets  # contains WIFI_SSID and WIFI_PASSWORD
import urequests

MAX_RETRIES = 5
RETRY_DELAY_SEC = 2

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    attempt = 0
    while attempt < MAX_RETRIES:
        attempt += 1
        wlan.connect(secrets.usr, secrets.pwd)

        # Wait for status change with small sleeps to avoid busy-wait
        for _ in range(20):  # ~2s total
            if wlan.isconnected():
                break
            time.sleep(0.1)

        if wlan.isconnected():
            break

        # On some boards, status() returns negative values for errors
        status = wlan.status()
        print("Retry", attempt, "status", status)
        time.sleep(RETRY_DELAY_SEC)

    if not wlan.isconnected():
        raise RuntimeError("WiFi connection failed after retries")

    print("Connected:", wlan.ifconfig())
    return wlan


def disconnect_wifi(wlan=None, deactivate=True):
    # Disconnect and optionally power down the interface
    wlan = wlan or network.WLAN(network.STA_IF)
    if not wlan.active():
        return

    if wlan.isconnected():
        wlan.disconnect()
        for _ in range(20):  # ~2s max
            if not wlan.isconnected():
                break
            time.sleep(0.1)

    if deactivate:
        wlan.active(False)

    print("Disconnected")


async def connect_wifi_async(timeout_s=10):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    attempt = 0
    while attempt < MAX_RETRIES:
        attempt += 1
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)

        # Wait for status change with small sleeps to avoid busy-wait
        for _ in range(20):  # ~2s total
            if wlan.isconnected():
                break
            time.sleep(0.1)

        if wlan.isconnected():
            break

        # On some boards, status() returns negative values for errors
        status = wlan.status()
        print("Retry", attempt, "status", status)
        time.sleep(RETRY_DELAY_SEC)

    if not wlan.isconnected():
        raise RuntimeError("WiFi connection failed after retries")

    print("Connected:", wlan.ifconfig())
    return wlan

if __name__ == "__main__":
    wlan = connect_wifi()
    time.sleep(1)  # Give connection time to stabilize
    response = urequests.get("http://api.ipify.org")
    print("Public IP:", response.text)
    #disconnect_wifi()