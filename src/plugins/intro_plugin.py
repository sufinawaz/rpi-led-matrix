#!/usr/bin/env python
import os
import time
from PIL import Image
from rgbmatrix import graphics

from .base_plugin import DisplayPlugin
from ui.image import load_image

class IntroPlugin(DisplayPlugin):
    """Plugin for displaying an intro/splash screen

    Configuration options:
        display_time (int): Time to display the intro in seconds
        logo_path (str): Path to logo image
    """

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "intro"
        self.description = "Introduction screen"

        # Default configuration
        self.config.setdefault('display_time', 10)
        self.config.setdefault('logo_path', 'resources/images/wm.jpg')

        # Internal state
        self.display_time = 0
        self.logo_image = None

    def setup(self):
        """Set up the intro plugin"""
        # Load logo image
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        logo_path = os.path.join(project_root, self.config['logo_path'])
        self.logo_image = load_image(logo_path)

    def update(self, delta_time):
        """Update intro display"""
        # Update display time
        self.display_time += delta_time

        # Stop after configured time
        if self.display_time >= self.config['display_time']:
            self.stop()

    def render(self, canvas):
        """Render the intro display"""
        # Clear canvas
        canvas.Clear()

        # Display logo if loaded
        if self.logo_image:
            # Calculate position to center the image
            x = (self.matrix.width - self.logo_image.width) // 2
            y = (self.matrix.height - self.logo_image.height) // 2
            canvas.SetImage(self.logo_image, max(0, x), max(0, y))
        else:
            # Fallback - draw text
            font = graphics.Font()
            try:
                font.LoadFont("resources/fonts/7x13.bdf")
            except Exception as e:
                pass  # Use default font if loading fails

            text = "InfoCube"
            color = graphics.Color(0, 191, 255)  # Sky blue

            # Draw text centered
            x = (self.matrix.width - len(text) * 7) // 2  # Approximate width
            y = self.matrix.height // 2
            graphics.DrawText(canvas, font, x, y, color, text)