from machine import Pin, ADC

ADCLowVoltPin = 26 #GP26
ADCMaxVoltPin = 27 #GP27
PicoVoltage = 3.3
ADC16BitRange = 65536
LEDMeterRange = 10
batterySmallVolt = 1.5 #1.5V
batteryHighVolt = 3.0 #9V

def main():

    LEDSegDisplay = []

    try:
        batteryLowVoltage = ADC(ADCLowVoltPin)
        batteryHighVoltage = ADC(ADCMaxVoltPin)
        voltagePerDegree =  PicoVoltage / ADC16BitRange

        for i in range(LEDMeterRange):
            LEDSegDisplay.append(Pin(i+1, Pin.OUT))
        
        while True:
            percentageOfBattery = 0
            batteryVoltage = voltagePerDegree * batteryLowVoltage.read_u16()
            percentageOfBattery = batteryVoltage/batterySmallVolt

            if percentageOfBattery*10 < 1:
                batteryVoltage = voltagePerDegree * batteryHighVoltage.read_u16()
                percentageOfBattery = batteryVoltage/batteryHighVolt
            
            LEDdisplay = int(percentageOfBattery*LEDMeterRange)
            if LEDdisplay > LEDMeterRange:
                LEDdisplay = LEDMeterRange

            for i in range(LEDMeterRange):
                if i < LEDdisplay:
                    LEDSegDisplay[i].high()
                else:
                    LEDSegDisplay[i].low()

    except KeyboardInterrupt:
        print("stopping program")
    
    finally:
        print("Graceful exit")
        for i in range(LEDMeterRange):
            LEDSegDisplay[i].low()

if __name__ == '__main__':
    main()