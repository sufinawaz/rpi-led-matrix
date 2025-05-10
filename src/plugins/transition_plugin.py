#!/usr/bin/env python
from PIL import Image, ImageDraw, ImageFont
from rgbmatrix import graphics
import time
import os

from .base_plugin import DisplayPlugin

class TransitionPlugin(DisplayPlugin):
    """Plugin for displaying transitions between plugins in cycling mode"""

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "transition"
        self.description = "Transition effect for plugin cycling"

        # Default configuration
        self.config.setdefault('duration', 1.0)  # Transition duration in seconds
        self.config.setdefault('effect', 'slide')  # Transition effect (slide, fade, etc.)
        self.config.setdefault('from_plugin', '')  # Name of the previous plugin
        self.config.setdefault('to_plugin', '')  # Name of the next plugin

        # Internal state
        self.transition_start = time.time()
        self.transition_complete = False
        self.direction = 'left'  # Direction for slide effect

        # Font loading
        self.font = None

    def setup(self):
        """Set up the transition plugin"""
        try:
            # Load font for text rendering
            self.font = graphics.Font()
            self.font.LoadFont("resources/fonts/7x13.bdf")
        except Exception as e:
            print(f"Error loading font: {e}")
            self.font = None

    def update(self, delta_time):
        """Update transition state"""
        # Check if transition is complete
        elapsed = time.time() - self.transition_start
        if elapsed >= self.config['duration']:
            self.transition_complete = True
            self.stop()

    def render(self, canvas):
        """Render the transition effect"""
        # Clear canvas
        canvas.Clear()

        # Calculate transition progress (0.0 to 1.0)
        elapsed = time.time() - self.transition_start
        progress = min(1.0, elapsed / self.config['duration'])

        # Get dimension for convenience
        width = self.matrix.width
        height = self.matrix.height

        # Render based on selected effect
        effect = self.config.get('effect', 'slide')

        if effect == 'slide':
            # Create sliding panel effect
            offset = int(width * progress)

            # Draw "from" plugin name
            if self.font:
                from_plugin = self.config.get('from_plugin', '')
                if from_plugin:
                    x_pos = width - offset
                    y_pos = height // 2
                    graphics.DrawText(canvas, self.font, x_pos, y_pos,
                                     graphics.Color(100, 100, 100), from_plugin)

            # Draw "to" plugin name
            if self.font:
                to_plugin = self.config.get('to_plugin', '')
                if to_plugin:
                    x_pos = width - offset + width
                    y_pos = height // 2
                    graphics.DrawText(canvas, self.font, x_pos, y_pos,
                                     graphics.Color(255, 255, 255), to_plugin)

        elif effect == 'fade':
            # Create a fading effect
            if self.font:
                # Draw text labels with fading colors
                from_plugin = self.config.get('from_plugin', '')
                to_plugin = self.config.get('to_plugin', '')

                # Calculate colors based on progress
                from_intensity = int(255 * (1.0 - progress))
                to_intensity = int(255 * progress)

                # Render the labels
                if from_plugin:
                    from_color = graphics.Color(from_intensity, from_intensity, from_intensity)
                    x_pos = (width - len(from_plugin) * 7) // 2  # Approximate width
                    y_pos = height // 3
                    graphics.DrawText(canvas, self.font, x_pos, y_pos, from_color, from_plugin)

                if to_plugin:
                    to_color = graphics.Color(to_intensity, to_intensity, to_intensity)
                    x_pos = (width - len(to_plugin) * 7) // 2  # Approximate width
                    y_pos = 2 * height // 3
                    graphics.DrawText(canvas, self.font, x_pos, y_pos, to_color, to_plugin)

        else:
            # Simple effect - just show text
            if self.font:
                from_plugin = self.config.get('from_plugin', '')
                to_plugin = self.config.get('to_plugin', '')

                text = f"{from_plugin} → {to_plugin}"
                x_pos = (width - len(text) * 7) // 2  # Approximate width
                y_pos = height // 2
                graphics.DrawText(canvas, self.font, x_pos, y_pos,
                                 graphics.Color(255, 255, 255), text)