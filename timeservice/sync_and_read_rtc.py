import machine
import time
from syncRTC import syncRTC
import simplewifiaccess as wifi_access


def sync_and_get_time(auto_disconnect=False):
    """Connect to WiFi, sync RTC, get current time, optionally disconnect"""
    wlan = wifi_access.connect_wifi()
    
    # Give DNS and connection time to fully stabilize
    time.sleep(3)
    
    try:
        # Create RTC instance
        rtc = machine.RTC()
        
        # Create syncRTC instance and sync the clock
        sync = syncRTC()
        success = sync.syncclock(rtc)
        
        if not success:
            raise RuntimeError("Failed to sync RTC")
        
        # Get the current time from RTC
        dt = rtc.datetime()
        
        # Convert RTC tuple to readable format
        # RTC.datetime() returns: (year, month, day, weekday, hours, minutes, seconds, subseconds)
        year, month, day, weekday, hour, minute, second, subsecond = dt
        
        print("RTC synced successfully")
        print("Date: {}/{}/{}".format(year, month, day))
        print("Time: {:02d}:{:02d}:{:02d}".format(hour, minute, second))
        
        return dt
        
    finally:
        if auto_disconnect:
            wifi_access.disconnect_wifi(wlan)


if __name__ == "__main__":
    current_time = sync_and_get_time(auto_disconnect=True)
    print("Current RTC datetime:", current_time)
