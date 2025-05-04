#!/usr/bin/env python
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from .animation_base import Animation
import sys
import os

# Add src directory to path to import moon_phase module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from moon_phase import get_moon_phase_image, calculate_moon_phase

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
    
    def update_moon_data(self):
        """Update the moon phase data and image"""
        # Get the current moon phase name and image
        moon_size = (self.matrix.width // 2, self.matrix.width // 2)
        self.phase_name, self.moon_image = get_moon_phase_image(
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
            date_width = self.font.getbbox(date_str)[2] - self.font.getbbox(date_str)[0]
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
                
            phase_width = self.font.getbbox(phase_text)[2] - self.font.getbbox(phase_text)[0]
            phase_x = (self.matrix.width - phase_width) // 2
            draw.text((phase_x, self.matrix.height - 7), phase_text, 
                      font=self.font, fill=self.color)
        
        # Display on the matrix
        self.matrix.set_image(image)