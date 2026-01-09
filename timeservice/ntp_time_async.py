import time
import ntptime
import uasyncio as asyncio
import simplewifiaccess_async as wifi_access

RAW_OFFSET = -28800 # http://worldtimeapi.org/api/ip/45.115.204.194

async def sync_rtc_from_ntp_async(auto_disconnect=False, tz_offset_seconds=RAW_OFFSET, ntp_host="pool.ntp.org"):
    wlan = await wifi_access.connect_wifi_async()
    try:
        ntptime.host = ntp_host
        ntptime.settime()  # sets RTC to UTC on the board
    finally:
        if auto_disconnect:
            await wifi_access.disconnect_wifi_async(wlan)

    t = time.time() + tz_offset_seconds
    return time.localtime(t)


async def main():
    local_time = await sync_rtc_from_ntp_async(auto_disconnect=True)
    print("Local time:", local_time)


if __name__ == "__main__":
    asyncio.run(main())
