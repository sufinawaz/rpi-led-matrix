#!/usr/bin/env python
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from .animation_base import Animation

class Clock(Animation):
    """Animation that displays a digital clock"""
    
    def __init__(self, matrix_manager, font=None, color=(255, 255, 255), 
                 show_seconds=True, format_24h=True):
        """
        Initialize the clock animation
        
        Args:
            matrix_manager: The MatrixManager instance
            font: Optional PIL ImageFont to use
            color: RGB color tuple for the text
            show_seconds: Whether to show seconds
            format_24h: Use 24-hour format if True, 12-hour if False
        """
        super().__init__(matrix_manager, fps=1)  # Update once per second is sufficient
        self.color = color
        self.font = font or ImageFont.load_default()
        self.show_seconds = show_seconds
        self.format_24h = format_24h
        self.last_time = ""
    
    def update(self, delta_time):
        """Update the clock"""
        # Nothing to update here - we'll get the current time in render()
        pass
    
    def render(self):
        """Render the current time to the matrix"""
        # Get current time
        now = datetime.now()
        
        # Format the time string
        if self.format_24h:
            if self.show_seconds:
                time_str = now.strftime("%H:%M:%S")
            else:
                time_str = now.strftime("%H:%M")
        else:
            if self.show_seconds:
                time_str = now.strftime("%I:%M:%S %p")
            else:
                time_str = now.strftime("%I:%M %p")
        
        # Skip rendering if the time hasn't changed
        if time_str == self.last_time:
            return
            
        self.last_time = time_str
        
        # Create a new image for the matrix
        image = Image.new("RGB", (self.matrix.width, self.matrix.height))
        draw = ImageDraw.Draw(image)
        
        # Calculate text size to center it
        text_width, text_height = draw.textsize(time_str, font=self.font)
        position = ((self.matrix.width - text_width) // 2, 
                   (self.matrix.height - text_height) // 2)
        
        # Draw the text
        draw.text(position, time_str, font=self.font, fill=self.color)
        
        # Display on the matrix
        self.matrix.set_image(image)