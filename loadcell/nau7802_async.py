from machine import Pin, SoftI2C
from time import ticks_ms, ticks_diff
from array import array
import uasyncio as asyncio

async def _sleep_ms(ms: int):
    if hasattr(asyncio, "sleep_ms"):
        await asyncio.sleep_ms(ms)
    else:
        await asyncio.sleep(ms / 1000)


class NAU7802:
    # I2C address
    NAU7802_ADDR = 0x2A

    # Registers
    PU_CTRL = 0x00
    CTRL1 = 0x01
    CTRL2 = 0x02
    ADCO_B2 = 0x12
    ADCO_B1 = 0x13
    ADCO_B0 = 0x14
    ADC = 0x15
    PGA = 0x1B
    PGA_PWR = 0x1C

    # Config bits
    NAU7802_PU_CTRL_AVDDS = 7
    PGA_PWR_PGA_CAP_EN = 7
    CTRL2_CALS = 2
    PU_CTRL_RR = 0
    PU_CTRL_PUD = 1
    PU_CTRL_PUA = 2
    PU_CTRL_PUR = 3
    PU_CTRL_CR = 5

    # Calibration state
    CAL_SUCCESS = 0
    CAL_IN_PROGRESS = 1
    CAL_FAILURE = 2

    def __init__(self, i2c, addr=0x2A, max_samples=1000):
        self.i2c = i2c
        self.addr = addr
        self.max_samples = max_samples
        self.data_arr_i = array('i', [0] * self.max_samples)
        self.offset = 0.0
        self.calibration_factor = 1.0
        self.zero_deadband = 0.0
        self.init_ok = False
        self.last_error = ""

    # ---------- Low-level register helpers (sync, fast) ----------
    def reg_write(self, reg, data):
        self.i2c.writeto_mem(self.addr, reg, bytes([data]))

    def reg_read(self, reg, nbytes=1):
        if nbytes < 1:
            return bytearray()
        return self.i2c.readfrom_mem(self.addr, reg, nbytes)

    def set_bit(self, bit_number, register_address):
        value = self.reg_read(register_address, 1)[0]
        value |= (1 << bit_number)
        self.reg_write(register_address, value)

    def clear_bit(self, bit_number, register_address):
        value = self.reg_read(register_address, 1)[0]
        value &= ~(1 << bit_number)
        self.reg_write(register_address, value)

    def get_bit(self, bit_number, register_address):
        value = self.reg_read(register_address, 1)[0]
        return bool(value & (1 << bit_number))

    # ---------- Device setup ----------
    async def initialize(self, startup_timeout_ms=500):
        self.init_ok = False
        self.last_error = ""

        devices = self.i2c.scan()
        if self.addr not in devices:
            self.last_error = "NAU7802 not found. scan={} expected=0x{:02X}".format(devices, self.addr)
            return False

        if not await self.wait_for_device_ready(timeout_ms=startup_timeout_ms):
            self.last_error = "NAU7802 present but not ready for register access"
            return False

        self.reset()
        await _sleep_ms(50)

        if not await self.power_up_async(timeout_ms=200):
            self.last_error = "Power-up failed (PU_CTRL_PUR did not assert)"
            return False

        self.set_ldo_3v3()
        self.set_gain_128()
        self.set_sample_rate_80sps()
        self.set_adc_register()
        self.set_bit(self.PGA_PWR_PGA_CAP_EN, self.PGA_PWR)

        if not await self.calibrate_afe_async(timeout_ms=1000):
            self.last_error = "AFE calibration failed or timed out"
            return False

        self.init_ok = True
        return True

    async def wait_for_device_ready(self, timeout_ms=300, poll_ms=10):
        begin = ticks_ms()
        while ticks_diff(ticks_ms(), begin) <= timeout_ms:
            try:
                self.reg_read(self.PU_CTRL, 1)
                return True
            except OSError:
                await _sleep_ms(poll_ms)
        return False

    def reset(self):
        self.set_bit(self.PU_CTRL_RR, self.PU_CTRL)
        self.clear_bit(self.PU_CTRL_RR, self.PU_CTRL)

    async def power_up_async(self, timeout_ms=200, poll_ms=2):
        self.set_bit(self.PU_CTRL_PUD, self.PU_CTRL)
        self.set_bit(self.PU_CTRL_PUA, self.PU_CTRL)

        begin = ticks_ms()
        while ticks_diff(ticks_ms(), begin) <= timeout_ms:
            if self.get_bit(self.PU_CTRL_PUR, self.PU_CTRL):
                return True
            await _sleep_ms(poll_ms)
        return False

    def set_ldo_3v3(self):
        value = self.reg_read(self.CTRL1, 1)[0]
        value &= 0b11000111
        value |= 0b00100000
        self.reg_write(self.CTRL1, value)
        self.set_bit(self.NAU7802_PU_CTRL_AVDDS, self.PU_CTRL)

    def set_gain_128(self):
        value = self.reg_read(self.CTRL1, 1)[0]
        value &= 0b11111000
        value |= 0b00000111
        self.reg_write(self.CTRL1, value)

    def set_sample_rate_80sps(self):
        value = self.reg_read(self.CTRL2, 1)[0]
        value &= 0b10001111
        value |= 0b00110000
        self.reg_write(self.CTRL2, value)

    def set_adc_register(self):
        value = self.reg_read(self.PGA, 1)[0]
        value &= 0b01111111
        self.reg_write(self.PGA, value)

        value = self.reg_read(self.ADC, 1)[0]
        value &= 0b11001111
        value |= 0b00110000
        self.reg_write(self.ADC, value)

    # ---------- Calibration ----------
    def begin_calibrate_afe(self):
        self.set_bit(self.CTRL2_CALS, self.CTRL2)

    def cal_afe_status(self):
        if self.get_bit(2, self.CTRL2):
            return self.CAL_IN_PROGRESS
        if self.get_bit(3, self.CTRL2):
            return self.CAL_FAILURE
        return self.CAL_SUCCESS

    async def calibrate_afe_async(self, timeout_ms=1000, poll_ms=2):
        self.begin_calibrate_afe()
        begin = ticks_ms()

        while ticks_diff(ticks_ms(), begin) <= timeout_ms:
            state = self.cal_afe_status()
            if state == self.CAL_SUCCESS:
                return True
            if state == self.CAL_FAILURE:
                return False
            await _sleep_ms(poll_ms)

        return False

    # ---------- Data path ----------
    def available(self):
        return self.get_bit(self.PU_CTRL_CR, self.PU_CTRL)

    async def wait_available(self, timeout_ms=200, poll_ms=1):
        begin = ticks_ms()
        while ticks_diff(ticks_ms(), begin) <= timeout_ms:
            if self.available():
                return True
            await _sleep_ms(poll_ms)
        return False

    def get_reading(self):
        raw_data = self.reg_read(self.ADCO_B2, 3)
        value = (raw_data[0] << 16) | (raw_data[1] << 8) | raw_data[2]
        if value > ((1 << 23) - 1):
            value -= (1 << 24)
        return value

    async def get_reading_adv(self, times=100, timeout_ms=4000, poll_ms=1):
        if (times > self.max_samples) or (times < 1):
            return None

        i = 0
        begin = ticks_ms()
        while i < times:
            if ticks_diff(ticks_ms(), begin) > timeout_ms:
                return None

            if self.available():
                self.data_arr_i[i] = self.get_reading()
                i += 1
            else:
                await _sleep_ms(poll_ms)

        new_arr = self.data_arr_i[0:times]
        sorted_arr = sorted(new_arr)

        remove_each = 5 if times >= 20 else 0
        if (remove_each * 2) >= times:
            remove_each = 0

        if remove_each:
            sorted_arr = sorted_arr[remove_each:times - remove_each]

        return sum(sorted_arr) / len(sorted_arr)

    async def tare(self, times=200, timeout_ms=5000):
        reading = await self.get_reading_adv(times=times, timeout_ms=timeout_ms)
        if reading is None:
            return False
        self.offset = reading
        return True

    async def calibrate_with_known_mass(self, known_mass_grams, times=200, timeout_ms=5000):
        if known_mass_grams <= 0:
            self.last_error = "known_mass_grams must be > 0"
            return None

        reading = await self.get_reading_adv(times=times, timeout_ms=timeout_ms)
        if reading is None:
            self.last_error = "Calibration read timed out"
            return None

        delta_counts = reading - self.offset
        if abs(delta_counts) < 1:
            self.last_error = "Calibration delta too small. Put known mass on the load cell before calibrating"
            return None

        self.calibration_factor = known_mass_grams / delta_counts
        self.last_error = ""
        return self.calibration_factor

    async def read_weight(self, times=50, timeout_ms=2000):
        reading = await self.get_reading_adv(times=times, timeout_ms=timeout_ms)
        if reading is None:
            return None
        weight = (reading - self.offset) * self.calibration_factor
        if abs(weight) < self.zero_deadband:
            return 0.0
        return weight

