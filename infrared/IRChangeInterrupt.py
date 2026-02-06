"""IRChangeMonitor: async IRQ-driven edge reader for IR/digital sensors.

Overview
    IRChangeMonitor attaches a GPIO interrupt on both rising and falling edges,
    then pushes each sampled value into a small ring buffer. An asyncio task
    consumes those buffered values using an async iterator interface, so you
    can write "async for value, overflow in monitor" without polling.

Why this is reusable
    - No app-specific timing logic: the class only reports edge changes.
    - IRQ handler stays minimal to avoid interrupt latency issues.
    - Async iterator interface composes cleanly with other asyncio tasks.

Key behaviors
    - Each yielded item is a tuple: (value, overflow).
    - value is the GPIO level (0 or 1) captured at the edge.
    - overflow is True if the ring buffer filled before it was drained.

How to use
    1) Pick GPIO pins and a buffer size (see GPIO_A, GPIO_B, BUF_SIZE).
    2) Create one IRChangeMonitor per pin.
    3) Consume it with "async for" inside an asyncio task.
    4) Use asyncio.gather() to run multiple monitors concurrently.

Example
    monitor = IRChangeMonitor(gpio_pin=22, buf_size=32)
    async for value, overflow in monitor:
        if overflow:
            print("overflow")
        print(value)

Notes
    - This is MicroPython-specific (machine.Pin, uasyncio).
    - For noisy sensors, add debouncing in your consumer task.
"""

from array import array
from machine import Pin
import uasyncio as asyncio

GPIO_A = 22
GPIO_B = 26
BUF_SIZE = 32


class IRChangeMonitor:
    """Async IRQ-based edge monitor for a digital input pin."""

    def __init__(self, gpio_pin, buf_size=32):
        self.gpio_pin = gpio_pin
        self.buf_size = max(4, buf_size)

        self._buf = array('b', [0] * self.buf_size)
        self._head = 0
        self._tail = 0
        self._overflow = 0
        self._flag = asyncio.ThreadSafeFlag()
        self._pin = Pin(self.gpio_pin, Pin.IN)
        self._prev_value = self._pin.value()
        self._stopped = False

        self._pin.irq(
            trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
            handler=self._irq_handler,
        )

    def stop(self):
        if self._stopped:
            return
        self._stopped = True
        try:
            self._pin.irq(handler=None)
        except Exception:
            pass
        self._flag.set()

    def _irq_handler(self, pin):
        value = pin.value()
        next_head = self._head + 1
        if next_head >= self.buf_size:
            next_head = 0

        if next_head != self._tail:
            self._buf[self._head] = value
            self._head = next_head
        else:
            self._overflow = 1

        self._flag.set()

    def __aiter__(self):
        return self

    async def __anext__(self):
        while True:
            if self._stopped:
                raise StopAsyncIteration
            if self._tail != self._head:
                current_value = self._buf[self._tail]
                self._tail += 1
                if self._tail >= self.buf_size:
                    self._tail = 0

                if current_value != self._prev_value:
                    self._prev_value = current_value
                    overflow = self._overflow
                    self._overflow = 0
                    return current_value, overflow

            await self._flag.wait()


async def _log_changes(name, monitor):
    ones_count = 0
    async for value, overflow in monitor:
        if overflow:
            print(f"{name} IRQ buffer overflow")
        if value == 1:
            ones_count += 1
            print(f"{name} {ones_count}")


async def demo_multiple():
    monitor_a = IRChangeMonitor(gpio_pin=GPIO_A, buf_size=BUF_SIZE)
    monitor_b = IRChangeMonitor(gpio_pin=GPIO_B, buf_size=BUF_SIZE)
    print("IR sensor async monitors started")
    print(f"GPIO{GPIO_A} -> A, GPIO{GPIO_B} -> B")
    await asyncio.gather(
        _log_changes("A", monitor_a),
        _log_changes("B", monitor_b),
    )


if __name__ == "__main__":
    try:
        asyncio.run(demo_multiple())
    except KeyboardInterrupt:
        print("\nProgram stopped")
