@echo on
set PORT=%1
esptool --chip esp32 --port %PORT% erase_flash