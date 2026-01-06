from machine import Pin, PWM
import utime

def LEDindicator():
    #pico = 25, picow = 0
    led = PWM(Pin("LED"))
    led.freq(1000)      # Set the frequency value
    led_value = 0       #LED brightness initial value
    led_speed = 5      # Change brightness in increments of 5

    for i in range(75):                            
        led_value += led_speed           
        led.duty_u16(int(led_value * 500))     # Set the duty cycle, between 0-65535
        utime.sleep_ms(100)
        if led_value >= 100:
            led_value = 100
            led_speed = -5
        elif led_value <= 0:
            led_value = 0
            led_speed = 5
    
    led.duty_u16(int(0))

def main():
    #LEDindicator()
    led = Pin(26, Pin.OUT)
    led.off()
    led.on()
    utime.sleep_ms(1000)
    led.off()

if __name__ == '__main__':
    main()