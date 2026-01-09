from machine import Pin
import time

# 3461AS is a common cathode 4-digit 7-segment display
# Segments: a, b, c, d, e, f, g, dp (decimal point)
# Digits: 1, 2, 3, 4

# Pin definitions - adjust these to match your wiring
SEGMENT_PINS = {
    'a': 6,   # segment a
    'b': 7,   # segment b
    'c': 8,   # segment c
    'd': 9,   # segment d
    'e': 10,  # segment e
    'f': 11,  # segment f
    'g': 12,  # segment g
    'dp': 13  # decimal point
}

DIGIT_PINS = [2, 3, 4, 5]  # digit 1, 2, 3, 4

# Segment patterns for digits 0-9 using hex (common cathode pattern)
# Bit order: gfedcba (bit 6 to bit 0)
DIGIT_PATTERNS = [
    0x3F,  # 0 = 0011 1111
    0x06,  # 1 = 0000 0110
    0x5B,  # 2 = 0101 1011
    0x4F,  # 3 = 0100 1111
    0x66,  # 4 = 0110 0110
    0x6D,  # 5 = 0110 1101
    0x7D,  # 6 = 0111 1101
    0x07,  # 7 = 0000 0111
    0x7F,  # 8 = 0111 1111
    0x67,  # 9 = 0110 0111
]

# Segment bit positions in the hex pattern
SEGMENT_BITS = {
    'a': 0,
    'b': 1,
    'c': 2,
    'd': 3,
    'e': 4,
    'f': 5,
    'g': 6,
    'dp': 7
}


class Display3461AS:
    def __init__(self, segment_pins=SEGMENT_PINS, digit_pins=DIGIT_PINS):
        # Initialize segment pins
        self.segments = {}
        for seg, pin_num in segment_pins.items():
            self.segments[seg] = Pin(pin_num, Pin.OUT)
            self.segments[seg].value(0)  # Off for common cathode (active high)
        
        # Initialize digit pins (common cathode digits: 1=off, 0=on)
        self.digits = []
        for pin_num in digit_pins:
            digit = Pin(pin_num, Pin.OUT)
            digit.value(1)  # Off
            self.digits.append(digit)
    
    def clear(self):
        """Turn off all digits"""
        for digit in self.digits:
            digit.value(1)
    
    def show_digit(self, digit_index, number, show_dp=False):
        """Display a single digit at the specified position"""
        if digit_index < 0 or digit_index >= len(self.digits):
            return
        
        if number < 0 or number > 9:
            return
        
        # Get the hex pattern for this number
        pattern = DIGIT_PATTERNS[number]
        
        # Set segments by extracting bits from the hex pattern (common cathode: 1=on)
        for seg, bit_pos in SEGMENT_BITS.items():
            if seg == 'dp':
                # Decimal point controlled separately (active high)
                self.segments[seg].value(1 if show_dp else 0)
            else:
                # Extract bit (1=on for common cathode)
                bit_value = (pattern >> bit_pos) & 1
                self.segments[seg].value(bit_value)
        
        # Enable this digit
        self.digits[digit_index].value(0)
    
    def display_number(self, number, duration_ms=5):
        """Display a number (0-9999) using multiplexing"""
        # Convert to 4-digit string with leading zeros
        num_str = "{:04d}".format(number % 10000)
        
        # Multiplex through each digit
        for i in range(4):
            self.clear()
            digit_value = int(num_str[i])
            self.show_digit(i, digit_value)
            time.sleep_ms(duration_ms)
        
        self.clear()


def test_digit_segments(digit_index=3):
    """Test each segment on a specific digit (default: digit 4)
    This helps verify wiring by lighting each segment one at a time"""
    display = Display3461AS()
    
    # Segment order to test
    segments = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'dp']
    
    print(f"Testing digit {digit_index + 1} (index {digit_index})")
    print("Each segment will light for 1 second")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            for seg in segments:
                display.clear()
                print(f"Lighting segment: {seg}")
                
                # Turn on only this digit (0=on, 1=off for common cathode digit pin)
                display.digits[digit_index].value(0)
                
                # Turn on only this segment (common cathode: 1=on, 0=off)
                for s in segments:
                    display.segments[s].value(0)  # All off
                display.segments[seg].value(1)  # This one on
                
                time.sleep(1)
            
            print("--- Cycle complete ---\n")
            
    except KeyboardInterrupt:
        display.clear()
        print("\nTest stopped")


def demo():
    """Demo showing numbers 0-9999"""
    display = Display3461AS()
    print("Displaying 0-9999, press Ctrl+C to stop")
    
    try:
        counter = 0
        while True:
            # Display the number for ~100ms total (multiplex 20 times)
            for _ in range(20):
                display.display_number(counter)
            
            counter = (counter + 1) % 10000
            
    except KeyboardInterrupt:
        display.clear()
        print("\nDemo stopped")


if __name__ == "__main__":
    # Uncomment the test you want to run:
    demo()
    #test_digit_segments(3)  # Test digit 4 (index 3)
    # demo()  # Count 0-9999
