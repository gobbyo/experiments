@echo on
set PORT=%1
esptool --chip esp32 --port %PORT% --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-20241129-v1.24.1.bin