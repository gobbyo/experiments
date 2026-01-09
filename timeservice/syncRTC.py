from machine import RTC
import ntptime
import time

# Default values
DEFAULT_IP_ADDRESS = "00.000.000.000"
AUTO_TIMEZONE = "auto"

# Default time tuple values
DEFAULT_YEAR = 1970
DEFAULT_MONTH = 1
DEFAULT_DAY = 1
DEFAULT_WEEKDAY = 0
DEFAULT_HOUR = 0
DEFAULT_MINUTE = 0
DEFAULT_SECOND = 0
DEFAULT_SUBSECONDS = 0

# Config key constants
CONFIG_TIMEZONE_KEY = "timeZone"

# This class is used to sync the RTC with the WorldTimeAPI service
# It is also used to obtain the external IP address of the device
# in order to determine the timezone of the device
class syncRTC:

    def __init__(self, config=None):
        self._externalIPaddress = DEFAULT_IP_ADDRESS
        self.config = config
        self.timeZone = None
        if self.config:
            try:
                self.timeZone = self.config.read(CONFIG_TIMEZONE_KEY)
            except:
                self.timeZone = None

    @property
    def externalIPaddress(self):
        return self._externalIPaddress
    
    @externalIPaddress.setter
    def externalIPaddress(self, value):
        self._externalIPaddress = value
    
    def syncclock(self, rtc, max_retries=3, ntp_host="pool.ntp.org"):
        print("Sync clock using NTP")
        returnval = False

        try:
            # Set a default date/time
            rtc.datetime((DEFAULT_YEAR, DEFAULT_MONTH, DEFAULT_DAY, 
                         DEFAULT_WEEKDAY, DEFAULT_HOUR, DEFAULT_MINUTE, 
                         DEFAULT_SECOND, DEFAULT_SUBSECONDS))
            print("RTC set to default date/time")
            
            # Use NTP for time sync with retry logic
            print(f"Using NTP server: {ntp_host}")
            ntptime.host = ntp_host
            
            for attempt in range(1, max_retries + 1):
                try:
                    print(f"NTP sync attempt {attempt} of {max_retries}")
                    ntptime.settime()  # Sets RTC to UTC
                    print("NTP sync successful")
                    returnval = True
                    break
                    
                except Exception as retry_exc:
                    print(f"Attempt {attempt} failed: {retry_exc}")
                    if attempt < max_retries:
                        time.sleep(2)
                    else:
                        raise
            
        except Exception as e:
            print(f"NTP sync exception: {e}")
            returnval = False

        return returnval


