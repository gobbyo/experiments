from machine import Pin, ADC
import shiftreg74HC595ic.shiftregister as shiftregister

ADCLowVoltPin = 26 #GP26
ADCMaxVoltPin = 27 #GP27
PicoMaxADCVoltage = 3.3
ADC16BitRange = 65536
LEDMeterRange = 10
ClearRegister = [0,0,0,0,0,0,0,0,0,0]

def main():
    batterySizeL = 1.5
    batterySizeH = 3.0

    try:
        batteryLowVoltage = ADC(ADCLowVoltPin)
        batteryHighVoltage = ADC(ADCMaxVoltPin)
        voltagePerDegree =  PicoMaxADCVoltage / ADC16BitRange

        r = shiftregister.shiftregister()
        r.set_registerSize(LEDMeterRange)
        r.register = ClearRegister
        r.set_register()
        

        while True:
            percentageOfBattery = 0
            batteryVoltage = voltagePerDegree * batteryLowVoltage.read_u16()
            if int(batteryVoltage) > 0:
                percentageOfBattery = batteryVoltage/batterySizeL
            else:
                batteryVoltage = voltagePerDegree * batteryHighVoltage.read_u16()
                percentageOfBattery = batteryVoltage/batterySizeH
            
            LEDdisplay = int(percentageOfBattery*LEDMeterRange)
            if LEDdisplay > LEDMeterRange:
                LEDdisplay = LEDMeterRange

            #set the shift register
            i = 0
            while i < LEDMeterRange:
                if i < LEDdisplay:
                    r.register[i] = 1
                else:
                    r.register[i] = 0
                i += 1
            #print("LEDdisplay = {0}, batteryVoltage voltage = {1}, register = {2}".format(LEDdisplay, batteryLowV, r.register))
            r.set_register()

    except KeyboardInterrupt:
        print("stopping program")

    finally:
        print("Graceful exit")

if __name__ == '__main__':
    main()