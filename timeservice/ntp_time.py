import time
import ntptime
import simplewifiaccess as wifi_access


def sync_rtc_from_ntp(auto_disconnect=False, tz_offset_seconds=-8 * 3600, ntp_host="pool.ntp.org"):
    wlan = wifi_access.connect_wifi()
    try:
        ntptime.host = ntp_host
        ntptime.settime()  # sets RTC to UTC on the board
    finally:
        if auto_disconnect:
            wifi_access.disconnect_wifi(wlan)

    t = time.time() + tz_offset_seconds
    return time.localtime(t)


if __name__ == "__main__":
    local_time = sync_rtc_from_ntp(auto_disconnect=True)
    print("Local time:", local_time)
