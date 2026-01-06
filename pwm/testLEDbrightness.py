from machine import Pin, PWM
import time

def main():
    led = PWM(Pin(18))
    led.freq(1000)      # Set the frequency value
    led_value = 20      # LED 20% brightness
    led.duty_u16(int(led_value * 500)) 
    time.sleep(5)
    led.duty_u16(int(0))

if __name__ == '__main__':
    main()