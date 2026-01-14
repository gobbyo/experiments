from machine import Pin, PWM
import utime

LEDPIN = 25 #pico = 25, picow = 0
MAX_VALUE = 100

def LEDindicator():
    print("LED Fading Effect")
    led = PWM(Pin(LEDPIN))
    led.duty_u16(int(0))  # Start with LED off
    led.freq(1000)      # Set the frequency value
    led_speed = 5       # Speed of fading effect
    number_of_cycles =  5
    max_iterations = int((MAX_VALUE / led_speed) * 2) 
    
    print("Starting LED fade in and out")
    for cycle in range(0, number_of_cycles, 1):
        print("Cycle:", cycle + 1)
        led_value = 0       # LED brightness initial value
        for i in range(0, max_iterations, 1):    
            led.duty_u16(int(655.35 * led_value))     # Set the duty cycle, between 0-65535
            utime.sleep_ms(100)                        
            if led_value >= MAX_VALUE:
                print("fading out")
                led_value = MAX_VALUE
                led_speed = -5
            elif led_value <= 0:
                print("brightening up")
                led_value = 0
                led_speed = 5
            led_value += led_speed

    led.duty_u16(int(0))

def main():
    LEDindicator()

if __name__ == '__main__':
    main()