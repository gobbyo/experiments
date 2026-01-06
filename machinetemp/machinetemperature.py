import machine
import utime

# Voltage per degree derived using the formula for slope = y-y1=m(x-x1)
# Temperature in Celsius = TemperatureBaselineInCelsius - (reading-VoltageAtTemperatureBaseline / VoltagePerDegree = 0.001721)
 
AINSEL = const(4) # AINSEL = 5th ADC Channel for the temperature sensor on a Pico
PiVoltage = const(3.3)
ADC16BitRange = const(65535)
TemperatureBaselineInCelsius = const(27)
VoltageAtTemperatureBaseline = const(0.706)
Deviation = 4

tempADC = machine.ADC(AINSEL)
VoltagePerDegree = 0.001721

while True:
    reading = tempADC.read_u16() * (PiVoltage / ADC16BitRange)
    celsius = (TemperatureBaselineInCelsius + Deviation) - ((reading - VoltageAtTemperatureBaseline) / VoltagePerDegree)
    print("{0} c, {1} f".format(celsius, celsius * (9/5) + 32))
    utime.sleep(2)