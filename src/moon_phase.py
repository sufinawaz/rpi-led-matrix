#!/usr/bin/env python
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from .animation_base import Animation
import sys
import os
import math

class MoonPhase(Animation):
    """Animation that displays the current phase of the moon"""

    def __init__(self, matrix_manager, font=None, color=(255, 255, 255), 
                 bg_color=(0, 0, 0), show_text=True, update_interval=3600):
        """
        Initialize the moon phase animation

        Args:
            matrix_manager: The MatrixManager instance
            font: Optional PIL ImageFont to use for text
            color: RGB color tuple for the moon
            bg_color: RGB color tuple for the background
            show_text: Whether to display the phase name text
            update_interval: How often to update the phase (in seconds)
        """
        super().__init__(matrix_manager, fps=1)  # Update once per second is sufficient
        self.color = color
        self.bg_color = bg_color
        self.font = font or ImageFont.load_default()
        self.show_text = show_text
        self.update_interval = update_interval

        # Initialize
        self.last_update = 0
        self.phase_name = ""
        self.moon_image = None
        self.update_moon_data()

    def calculate_moon_phase(self, date_time=None):
        """
        Calculate the current phase of the moon.

        Args:
            date_time: datetime object (defaults to current time if None)

        Returns:
            phase_name: String name of the phase
            phase_index: Integer index (0-7) representing the phase
            phase_fraction: Float between 0 and 1 representing how complete the cycle is
        """
        if date_time is None:
            date_time = datetime.now()

        # Calculate days since known new moon (2000-01-06)
        known_new_moon = datetime(2000, 1, 6, 18, 14, 0)
        days_since = (date_time - known_new_moon).total_seconds() / (24.0 * 3600)

        # Moon cycle is approximately 29.53 days
        lunar_cycle = 29.53058867

        # Calculate phase as a fraction [0,1)
        phase_fraction = (days_since % lunar_cycle) / lunar_cycle

        # Determine the phase name and index
        # We divide the cycle into 8 phases
        phase_index = int((phase_fraction * 8) % 8)

        phase_names = [
            "New Moon",           # 0
            "Waxing Crescent",    # 1
            "First Quarter",      # 2
            "Waxing Gibbous",     # 3
            "Full Moon",          # 4
            "Waning Gibbous",     # 5
            "Last Quarter",       # 6
            "Waning Crescent"     # 7
        ]

        return phase_names[phase_index], phase_index, phase_fraction

    def create_moon_image(self, size, phase_fraction, color=(255, 255, 255), bg_color=(0, 0, 0)):
        """
        Generate an image of the moon at the specified phase.

        Args:
            size: Size of the image (width, height)
            phase_fraction: Float between 0 and 1 representing phase
            color: RGB color tuple for the moon
            bg_color: RGB color tuple for the background

        Returns:
            PIL Image object
        """
        width, height = size
        image = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(image)

        # The moon is drawn as a circle with a parabola masking part of it
        # depending on the phase
        center_x, center_y = width // 2, height // 2
        radius = min(width, height) // 2 - 1

        # Draw full circle for the moon
        draw.ellipse(
            (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            fill=color
        )

        # Adjust phase_fraction to match visual appearance
        # (0 = new, 0.25 = first quarter, 0.5 = full, 0.75 = last quarter)
        adjusted_phase = phase_fraction * 2 * math.pi

        # For new to full moon (phase 0-0.5), mask right side of circle
        # For full to new moon (phase 0.5-1), mask left side of circle
        is_waxing = phase_fraction < 0.5

        # Calculate which side to mask
        if is_waxing:
            # Waxing: mask right side with different shapes according to phase
            terminator_offset = radius * math.sin(adjusted_phase)

            # Mask using a rectangle and a parabola
            points = []

            # Start with right side of circle
            points.append((center_x, center_y - radius))  # Top point

            # Add parabola points
            for y in range(-radius, radius + 1):
                # Calculate x for a parabola or ellipse
                if abs(y / radius) <= 1:  # Check to avoid math domain error
                    x = terminator_offset * math.cos(math.asin(y / radius))
                    points.append((center_x + x, center_y + y))

            points.append((center_x, center_y + radius))  # Bottom point
            points.append((center_x + radius, center_y + radius))  # Bottom right
            points.append((center_x + radius, center_y - radius))  # Top right

            draw.polygon(points, fill=bg_color)
        else:
            # Waning: mask left side with different shapes according to phase
            terminator_offset = radius * math.sin(adjusted_phase - math.pi)

            # Mask using a rectangle and a parabola
            points = []

            # Start with left side of circle
            points.append((center_x, center_y - radius))  # Top point

            # Add parabola points
            for y in range(-radius, radius + 1):
                # Calculate x for a parabola or ellipse
                if abs(y / radius) <= 1:  # Check to avoid math domain error
                    x = terminator_offset * math.cos(math.asin(y / radius))
                    points.append((center_x + x, center_y + y))

            points.append((center_x, center_y + radius))  # Bottom point
            points.append((center_x - radius, center_y + radius))  # Bottom left
            points.append((center_x - radius, center_y - radius))  # Top left

            draw.polygon(points, fill=bg_color)

        return image

    def get_moon_phase_image(self, size=(32, 32), color=(255, 255, 255), bg_color=(0, 0, 0), date_time=None):
        """
        Get an image of the current moon phase.

        Args:
            size: Size of the image (width, height)
            color: RGB color tuple for the moon
            bg_color: RGB color tuple for the background
            date_time: datetime object (defaults to current time if None)

        Returns:
            phase_name: String name of the phase
            image: PIL Image object of the moon
        """
        phase_name, phase_index, phase_fraction = self.calculate_moon_phase(date_time)
        image = self.create_moon_image(size, phase_fraction, color, bg_color)
        return phase_name, image

    def update_moon_data(self):
        """Update the moon phase data and image"""
        # Get the current moon phase name and image
        moon_size = (self.matrix.width // 2, self.matrix.width // 2)
        self.phase_name, self.moon_image = self.get_moon_phase_image(
            size=moon_size, 
            color=self.color, 
            bg_color=self.bg_color
        )

    def update(self, delta_time):
        """Update the animation"""
        self.last_update += delta_time

        # Check if it's time to update the moon phase data
        if self.last_update >= self.update_interval:
            self.update_moon_data()
            self.last_update = 0

    def render(self):
        """Render the moon phase to the matrix"""
        # Create a new image for the matrix
        image = Image.new("RGB", (self.matrix.width, self.matrix.height), self.bg_color)

        # Calculate position to place the moon image (centered)
        moon_pos_x = (self.matrix.width - self.moon_image.width) // 2
        moon_pos_y = 2 if self.show_text else (self.matrix.height - self.moon_image.height) // 2

        # Paste the moon image onto the main image
        image.paste(self.moon_image, (moon_pos_x, moon_pos_y))

        # Add date and phase text if requested
        if self.show_text:
            draw = ImageDraw.Draw(image)

            # Current date
            date_str = datetime.now().strftime("%b %d")

            # Check if the font has getbbox method (newer PIL versions)
            if hasattr(self.font, 'getbbox'):
                date_bbox = self.font.getbbox(date_str)
                date_width = date_bbox[2] - date_bbox[0]
            else:
                # Fallback for older PIL versions
                date_width, _ = self.font.getsize(date_str)

            date_x = (self.matrix.width - date_width) // 2
            draw.text((date_x, self.matrix.height - 14), date_str, 
                      font=self.font, fill=self.color)

            # Phase name - display in bottom row
            # We'll abbreviate the phase name to fit
            if self.phase_name == "New Moon":
                phase_text = "New"
            elif self.phase_name == "Full Moon":
                phase_text = "Full"
            elif self.phase_name == "First Quarter":
                phase_text = "1st Qtr"
            elif self.phase_name == "Last Quarter":
                phase_text = "3rd Qtr"
            elif "Waxing" in self.phase_name:
                phase_text = "Waxing"
            elif "Waning" in self.phase_name:
                phase_text = "Waning"
            else:
                phase_text = self.phase_name

            # Check if the font has getbbox method (newer PIL versions)
            if hasattr(self.font, 'getbbox'):
                phase_bbox = self.font.getbbox(phase_text)
                phase_width = phase_bbox[2] - phase_bbox[0]
            else:
                # Fallback for older PIL versions
                phase_width, _ = self.font.getsize(phase_text)

            phase_x = (self.matrix.width - phase_width) // 2
            draw.text((phase_x, self.matrix.height - 7), phase_text, 
                      font=self.font, fill=self.color)

        # Display on the matrix
        self.matrix.set_image(image)