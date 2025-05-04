#!/usr/bin/env python
import time
from datetime import datetime
from PIL import Image, ImageDraw
from rgbmatrix import graphics

from .base_plugin import DisplayPlugin

class MoonPlugin(DisplayPlugin):
    """Plugin for displaying the current phase of the moon

    Configuration options:
        update_interval (int): How often to update the moon phase in seconds
        show_text (bool): Whether to display the phase name text
        color (list): RGB color for the moon
        bg_color (list): RGB color for the background
    """

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "moon"
        self.description = "Moon phase display"

        # Default configuration
        self.config.setdefault('update_interval', 3600)
        self.config.setdefault('show_text', True)
        self.config.setdefault('color', [220, 220, 255])
        self.config.setdefault('bg_color', [0, 0, 0])

        # Internal state
        self.last_update = 0
        self.phase_name = ""
        self.moon_image = None

        # Font loading
        self.font = graphics.Font()
        self.font_small = graphics.Font()

        # Colors
        self.colors = {
            'white': graphics.Color(255, 255, 255),
            'skyBlue': graphics.Color(0, 191, 255)
        }

    def setup(self):
        """Set up the moon phase plugin"""
        # Load fonts
        try:
            self.font_small.LoadFont("resources/fonts/4x6.bdf")
            self.font.LoadFont("resources/fonts/7x13.bdf") 
        except Exception as e:
            print(f"Error loading fonts: {e}")

        # Initial moon phase calculation
        self._update_moon_data()

    def _update_moon_data(self):
        """Update the moon phase data and image"""
        try:
            # Import moon phase module
            from src.moon_phase import get_moon_phase_image

            # Get the current moon phase name and image
            moon_size = (self.matrix.width // 2, self.matrix.width // 2)
            self.phase_name, self.moon_image = get_moon_phase_image(
                size=moon_size, 
                color=tuple(self.config['color']), 
                bg_color=tuple(self.config['bg_color'])
            )

            print(f"Current moon phase: {self.phase_name}")
        except Exception as e:
            print(f"Error updating moon data: {e}")

    def update(self, delta_time):
        """Update moon phase display"""
        self.last_update += delta_time

        # Check if it's time to update the moon phase data
        if self.last_update >= self.config['update_interval']:
            self._update_moon_data()
            self.last_update = 0

    def render(self, canvas):
        """Render the moon phase display"""
        # Clear canvas
        canvas.Clear()

        # Display the moon image
        if self.moon_image:
            # Calculate position to center the moon
            moon_pos_x = (self.matrix.width - self.moon_image.width) // 2
            moon_pos_y = 2 if self.config['show_text'] else (self.matrix.height - self.moon_image.height) // 2

            # Set the moon image on the canvas
            canvas.SetImage(self.moon_image, moon_pos_x, moon_pos_y)

            # Add text if enabled
            if self.config['show_text']:
                # Get current date
                now = datetime.now()
                date_str = now.strftime("%b %d")

                # Display date
                graphics.DrawText(canvas, self.font_small, 3, 
                                 self.matrix.height - 7, 
                                 self.colors['skyBlue'], date_str)

                # Display phase name (shortened if necessary)
                phase_text = self.phase_name
                if len(phase_text) > 10:  # Shorten long phase names
                    if "Waxing" in phase_text:
                        phase_text = "Waxing"
                    elif "Waning" in phase_text:
                        phase_text = "Waning"

                graphics.DrawText(canvas, self.font_small, 3, 
                                 self.matrix.height - 14, 
                                 self.colors['white'], phase_text)