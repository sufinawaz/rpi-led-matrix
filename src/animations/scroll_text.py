#!/usr/bin/env python
import time
from PIL import Image, ImageDraw, ImageFont
from .animation_base import Animation

class ScrollText(Animation):
    """Animation that scrolls text across the display"""
    
    def __init__(self, matrix_manager, text, font=None, color=(255, 255, 255), 
                 scroll_speed=30, y_position=None):
        """
        Initialize the scrolling text animation
        
        Args:
            matrix_manager: The MatrixManager instance
            text: Text to scroll
            font: Optional PIL ImageFont to use
            color: RGB color tuple for the text
            scroll_speed: Pixels per second to scroll
            y_position: Y position to scroll at (None for centered)
        """
        super().__init__(matrix_manager, fps=30)
        self.text = text
        self.color = color
        self.scroll_speed = scroll_speed
        self.font = font or ImageFont.load_default()
        
        # Create the text image
        self.text_image = self._create_text_image()
        self.text_width = self.text_image.width
        
        # Position variables
        self.x_pos = self.matrix.width
        if y_position is None:
            # Center text vertically
            self.y_pos = (self.matrix.height - self.text_image.height) // 2
        else:
            self.y_pos = y_position
    
    def _create_text_image(self):
        """Create an image containing the rendered text"""
        # First, create a dummy image to calculate the text size
        dummy = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(dummy)
        text_width, text_height = draw.textsize(self.text, font=self.font)
        
        # Now create the properly sized image
        image = Image.new('RGB', (text_width, text_height))
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), self.text, font=self.font, fill=self.color)
        return image
    
    def update(self, delta_time):
        """Update the animation state"""
        # Move the text position by the scroll speed
        self.x_pos -= self.scroll_speed * delta_time
        
        # Reset position when the text is completely off the screen
        if self.x_pos < -self.text_width:
            self.x_pos = self.matrix.width
    
    def render(self):
        """Render the current frame to the matrix"""
        # Clear the canvas
        self.matrix.clear()
        
        # Draw the text at the current position
        offset_x = int(self.x_pos)
        offset_y = self.y_pos
        
        # Create a blank image for the matrix
        image = Image.new("RGB", (self.matrix.width, self.matrix.height))
        
        # Paste the text image at the current position
        image.paste(self.text_image, (offset_x, offset_y))
        
        # If the text is scrolling off the left edge, draw it again from the right
        if offset_x < 0:
            wrap_x = offset_x + self.text_width
            if wrap_x < self.matrix.width:
                image.paste(self.text_image, (wrap_x, offset_y))
        
        # Display the image on the matrix
        self.matrix.set_image(image)