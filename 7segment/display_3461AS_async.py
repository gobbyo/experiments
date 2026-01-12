import uasyncio as asyncio
from machine import Pin

# 3461AS is a common cathode 4-digit 7-segment display
# Segments: a, b, c, d, e, f, g, dp (decimal point)
# Digits: 1, 2, 3, 4

SEGMENT_PINS = {
    'a': 6,
    'b': 7,
    'c': 8,
    'd': 9,
    'e': 10,
    'f': 11,
    'g': 12,
    'dp': 13,
}

DIGIT_PINS = [2, 3, 4, 5]

# Segment patterns for digits 0-9 using hex (common cathode)
# Bit order: gfedcba (bit 6 to bit 0); dp is bit 7
DIGIT_PATTERNS = [
    0x3F,  # 0
    0x06,  # 1
    0x5B,  # 2
    0x4F,  # 3
    0x66,  # 4
    0x6D,  # 5
    0x7D,  # 6
    0x07,  # 7
    0x7F,  # 8
    0x67,  # 9
]

SEGMENT_BITS = {
    'a': 0,
    'b': 1,
    'c': 2,
    'd': 3,
    'e': 4,
    'f': 5,
    'g': 6,
    'dp': 7,
}


class AsyncDisplay3461AS:
    def __init__(self, segment_pins=SEGMENT_PINS, digit_pins=DIGIT_PINS, frame_ms=2):
        self.segments = {seg: Pin(pin_num, Pin.OUT) for seg, pin_num in segment_pins.items()}
        for seg in self.segments.values():
            seg.value(0)  # off (common cathode)

        self.digits = [Pin(pin_num, Pin.OUT) for pin_num in digit_pins]
        for d in self.digits:
            d.value(1)  # digit off (0 is on for common cathode)

        self.frame_ms = frame_ms
        self._value = "0000"
        self._show_dp = False
        self._task = None
        self._running = False

    def _clear(self):
        for d in self.digits:
            d.value(1)
        for s in self.segments.values():
            s.value(0)

    def set_number(self, number, show_dp=False):
        self._value = f"{number % 10000:04d}"
        self._show_dp = show_dp

    def _set_segments_for_digit(self, digit_char):
        pattern = DIGIT_PATTERNS[int(digit_char)]
        for seg, bit_pos in SEGMENT_BITS.items():
            if seg == 'dp':
                self.segments[seg].value(1 if self._show_dp else 0)
            else:
                bit_value = (pattern >> bit_pos) & 1
                self.segments[seg].value(bit_value)

    async def _run(self):
        try:
            while self._running:
                for idx in range(4):
                    # ensure this digit is off while updating its segments
                    self.digits[idx].value(1)

                    # set segments for this digit
                    self._set_segments_for_digit(self._value[idx])

                    # enable only this digit (active low)
                    self.digits[idx].value(0)

                    # short on-time
                    await asyncio.sleep_ms(self.frame_ms)

                    # turn this digit off before moving to next
                    self.digits[idx].value(1)
        finally:
            self._clear()

    def start(self):
        if self._task is None:
            self._running = True
            self._task = asyncio.create_task(self._run())

    async def stop(self):
        # Immediately blank digits to avoid leaving one on mid-refresh
        for d in self.digits:
            d.value(1)
        for s in self.segments.values():
            s.value(0)

        if self._task:
            self._running = False
            await self._task
            self._task = None

        # Brief pause then clear twice to ensure all digits are off
        await asyncio.sleep_ms(1)
        self._clear()
        await asyncio.sleep_ms(1)
        self._clear()


async def demo():
    display = AsyncDisplay3461AS()
    display.start()
    try:
        # Count 0-9 on each digit in sequence, then exit
        for digit_index in range(4):
            for n in range(10):
                # Build a value with digit_index showing n, others 0
                digits = ['0', '0', '0', '0']
                digits[digit_index] = str(n)
                display._value = ''.join(digits)
                await asyncio.sleep(0.5)
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Gracefully handle external stop/IDE cancel
        pass
    finally:
        await display.stop()
        display._clear()


if __name__ == "__main__":
    asyncio.run(demo())
