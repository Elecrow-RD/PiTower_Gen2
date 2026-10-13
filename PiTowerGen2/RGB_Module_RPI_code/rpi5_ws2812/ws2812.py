from abc import ABC, abstractmethod
from collections import namedtuple

import numpy as np
from spidev import SpiDev

Color = namedtuple("Color", ["r", "g", "b"])


class Strip:
    """
    A class to control a WS2812B LED strip.
    """

    def __init__(self, backend: "WS2812StripDriver"):
        self._led_count = backend.get_led_count()
        self._brightness = 1.0
        self._pixels: list[Color] = [Color(0, 0, 0)] * self._led_count
        self._backend = backend

    def set_pixel_color(self, i: int, color: Color) -> None:
        """
        Set the color of a single pixel in the buffer. It is not written to the LED strip until show() is called.
        :param i: The index of the pixel
        :param color: The color to set the pixel to
        """
        if 0 <= i < self._led_count:
            self._pixels[i] = color

    def show(self) -> None:
        """
        Write the current pixel colors to the LED strip.
        """
        buffer = np.array(
            [
                np.array([pixel.g * self._brightness, pixel.r * self._brightness, pixel.b * self._brightness])
                for pixel in self._pixels
            ],
            dtype=np.uint8,
        )
        self._backend.write(buffer)

    def clear(self) -> None:
        """
        Clear the LED strip and the buffer by setting all pixels to off.
        """
        self._pixels = [Color(0, 0, 0)] * self._led_count
        self._backend.clear()

    def set_brightness(self, brightness: float) -> None:
        """
        Set the brightness of the LED strip. The brightness is a float between 0.0 and 1.0.
        """
        self._brightness = max(min(brightness, 1.0), 0.0)

    def num_pixels(self) -> int:
        """
        Get the number of pixels in the LED strip.
        :return: The number of pixels.
        """
        return self._led_count

    def get_brightness(self) -> float:
        """
        Get the current brightness of the LED strip.
        :return: The brightness as a float between 0.0 and 1.0."""
        return self._brightness

    def set_all_pixels(self, color: Color) -> None:
        """
        Set all pixels to the same color. The colors are not written to the LED strip until show() is called.
        :param color: The color to set all pixels to.
        """
        self._pixels = [color] * self._led_count


class WS2812StripDriver(ABC):
    """
    Abstract base class for drivers
    """

    @abstractmethod
    def write(self, colors: np.ndarray) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def get_led_count(self) -> int:
        pass

    def get_strip(self) -> Strip:
        return Strip(self)


class WS2812SpiDriver(WS2812StripDriver):
    """
    Driver for WS2812B LED strips using the SPI interface.

    WS2812B Timing Requirements (from XL-1615RGBC-WS2812B datasheet):
    - T0H (0-code high): 0.3us - 0.9us
    - T0L (0-code low): >0.9us  
    - T1H (1-code high): >0.9us
    - T1L (1-code low): 0.3us - 0.9us
    - Total bit period: 1.2us typical
    - RESET: >200us low (CRITICAL!)

    Using SPI at 6.5MHz with 8-bit encoding per WS2812B bit:
    - 0-code: 0b1100_0000 (0xC0) - 2 high (308ns) + 6 low (924ns)
    - 1-code: 0b1111_1100 (0xFC) - 6 high (924ns) + 2 low (308ns)

    CRITICAL FIX: Added proper RESET timing (>200us low) after each frame
    to ensure data is latched correctly.
    """

    # WS2812B SPI encoding - 8 bits per WS2812B bit
    LED_ZERO: int = 0b1100_0000  # 0xC0: T0H=0.3us, T0L=0.9us
    LED_ONE: int = 0b1111_1100   # 0xFC: T1H=0.9us, T1L=0.3us

    # Preamble bytes for signal stabilization
    PREAMBLE: int = 42

    # RESET timing: WS2812B requires >200us low
    # At 6.5MHz, we need enough bytes to ensure >200us low time
    # 6.5MHz = 154ns per bit, 8 bits per byte = 1.23us per byte
    # Need at least 200us / 1.23us = 163 bytes minimum
    # Using 200 bytes to be safe (~246us)
    RESET_BYTES: int = 200

    def __init__(self, spi_bus: int, spi_device: int, led_count: int):
        self._device = SpiDev()
        self._device.open(spi_bus, spi_device)

        # SPI configuration for WS2812B
        self._device.max_speed_hz = 6_500_000  # 6.5MHz
        self._device.mode = 0b00  # CPOL=0, CPHA=0
        self._device.lsbfirst = False  # MSB first

        # Pre-compute clear buffer (all zeros) with proper RESET
        clear_data_len = led_count * 24
        total_clear_len = WS2812SpiDriver.PREAMBLE + clear_data_len + WS2812SpiDriver.RESET_BYTES
        
        self._clear_buffer = np.zeros(total_clear_len, dtype=np.uint8)
        # Data section: all zeros (LED_ZERO for all bits = all black)
        self._clear_buffer[WS2812SpiDriver.PREAMBLE : WS2812SpiDriver.PREAMBLE + clear_data_len] = \
            np.full(clear_data_len, WS2812SpiDriver.LED_ZERO, dtype=np.uint8)
        # RESET section: already zeros (trailing bytes ensure >200us low)

        # Working buffer for pixel data (includes space for RESET)
        self._buffer = np.zeros(total_clear_len, dtype=np.uint8)
        
        # Pre-fill preamble
        self._buffer[:WS2812SpiDriver.PREAMBLE] = np.zeros(WS2812SpiDriver.PREAMBLE, dtype=np.uint8)

        self._led_count = led_count
        self._data_len = clear_data_len

    def _encode_pixels(self, colors: np.ndarray) -> np.ndarray:
        """
        Encode pixel colors to WS2812B SPI format.
        :param colors: GRB color array
        :return: Encoded SPI bytes
        """
        # Flatten the GRB color data
        flattened = colors.ravel()
        
        # Convert to bits
        bits = np.unpackbits(flattened)
        
        # Map bits to SPI bytes (0->LED_ZERO, 1->LED_ONE)
        return np.where(bits == 1, WS2812SpiDriver.LED_ONE, WS2812SpiDriver.LED_ZERO)

    def write(self, colors: np.ndarray) -> None:
        """
        Write colors to the LED strip with proper RESET timing.
        :param colors: A 2D numpy array of shape (num_leds, 3) where the last dimension is the GRB values
        """
        # Encode pixel data
        encoded = self._encode_pixels(colors)
        
        # Fill data section (after preamble, before RESET)
        data_start = WS2812SpiDriver.PREAMBLE
        data_end = data_start + len(encoded)
        self._buffer[data_start:data_end] = encoded
        
        # RESET section is already zeros (at the end of buffer)
        # This ensures >200us low time after data transmission
        
        # Send complete frame (preamble + data + RESET)
        self._device.writebytes2(self._buffer)
        
    def clear(self) -> None:
        """
        Reset all LEDs to off (black) with proper RESET timing.
        """
        self._device.writebytes2(self._clear_buffer)

    def get_led_count(self) -> int:
        return self._led_count
