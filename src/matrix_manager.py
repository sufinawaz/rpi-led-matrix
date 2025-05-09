#!/usr/bin/env python
import os
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

class MatrixManager:
    """Core class to manage the RGB LED Matrix"""

    def __init__(self, 
                 rows=32, 
                 cols=64, 
                 chain_length=1, 
                 parallel=1, 
                 brightness=30,
                 hardware_mapping="adafruit-hat",
                 gpio_slowdown=2):
        """
        Initialize the LED matrix with the given parameters

        Args:
            rows: Number of rows (typically 32 or 64)
            cols: Number of columns (typically 32 or 64)
            chain_length: Number of displays daisy-chained together
            parallel: Number of parallel chains
            brightness: Brightness level (0-100)
            hardware_mapping: Type of hardware mapping ('regular' or 'adafruit-hat')
            gpio_slowdown: Slowdown factor for GPIO (1-4)
        """
        if os.geteuid() != 0:
            raise PermissionError("This library requires root privileges to access GPIO. Run with sudo.")

        self.options = RGBMatrixOptions()
        self.options.rows = rows
        self.options.cols = cols
        self.options.chain_length = chain_length
        self.options.parallel = parallel
        self.options.brightness = brightness
        self.options.hardware_mapping = hardware_mapping
        self.options.gpio_slowdown = gpio_slowdown

        # Create and initialize the matrix
        self.matrix = RGBMatrix(options=self.options)
        self.canvas = self.matrix.CreateFrameCanvas()

        # Store dimensions for convenience
        self.width = self.matrix.width
        self.height = self.matrix.height

    def clear(self):
        """Clear the display"""
        self.canvas.Clear()

    def fill(self, r, g, b):
        """Fill the entire display with a single color"""
        self.canvas.Fill(r, g, b)

    def set_pixel(self, x, y, r, g, b):
        """Set a single pixel to the specified color"""
        self.canvas.SetPixel(x, y, r, g, b)

    def set_image(self, image):
        """Display a PIL Image on the matrix"""
        self.canvas.SetImage(image)

    def swap(self):
        """Update the display by swapping the canvas"""
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def set_brightness(self, brightness):
        """Set the brightness of the LED matrix

        Args:
            brightness: Brightness level (0-100)
        """
        # Ensure brightness is within valid range
        brightness = max(0, min(100, brightness))

        # Update options
        self.options.brightness = brightness

        # Apply brightness setting directly to the matrix
        try:
            # Method 1: If matrix has a setBrightness method
            if hasattr(self.matrix, 'setBrightness'):
                self.matrix.setBrightness(brightness)
                return True
            # Method 2: Try to access brightness property directly
            elif hasattr(self.matrix, 'brightness'):
                self.matrix.brightness = brightness
                return True
            # Method 3: Try rpi-rgb-led-matrix specific methods
            elif hasattr(self.matrix, 'luminanceCorrect'):
                self.matrix.luminanceCorrect(brightness/100.0)
                return True
        except Exception as e:
            print(f"Error setting brightness: {e}")
            return False

        # Can't set brightness directly - matrix might need to be reinitialized
        return False

    def __del__(self):
        """Clean up by clearing the display when done"""
        if hasattr(self, 'matrix'):
            self.matrix.Clear()