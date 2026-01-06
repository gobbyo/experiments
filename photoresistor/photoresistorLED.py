from machine import Pin, PWM
import utime

# Max value of the ADC is 65535
# ADC pins are 26, 27 & 28

ADCPin = const(26) #GP26
LEDPin = const(3) #GP3

PicoVoltage = const(3.3)
ADC16BitRange = const(65535)

photoresistor = machine.ADC(ADCPin)
voltagePerBitReading = PicoVoltage/ADC16BitRange

led = PWM(Pin(LEDPin))
led.freq(ADC16BitRange)      # Set the frequency value
led_value = 0       #LED brightness initial value

while True:
    photoResistorReading = photoresistor.read_u16()
    print("{:0d}(raw),{:.2f}v".format(photoResistorReading, photoResistorReading * VoltagePerBitReading))
    led.duty_u16(int(photoResistorReading))     # Set the duty cycle, between 0-65535
    utime.sleep(1)