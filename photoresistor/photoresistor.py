import machine
import utime

# Max value of the ADC is 65535

ADCPin = const(26) #GP26

PicoVoltage = const(3.3)
ADC16BitRange = const(65536)

photoresistor = machine.ADC(ADCPin)
voltagePerDegree =  PicoVoltage / ADC16BitRange 

while True:
    photoResistorReading = photoresistor.read_u16()
    print("{:.2f}v".format(photoResistorReading * voltagePerDegree))
    utime.sleep(.125)