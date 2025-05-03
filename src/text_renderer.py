#!/usr/bin/env python
from PIL import Image, ImageDraw, ImageFont
import os

class TextRenderer:
    """Utility class to render text on the LED matrix"""
    
    def __init__(self, matrix_manager):
        """
        Initialize the text renderer with a matrix manager
        
        Args:
            matrix_manager: Instance of MatrixManager
        """
        self.matrix = matrix_manager
        
        # Try to find fonts directory from the rgb-matrix library
        # This assumes the library is installed and the fonts are available
        font_path = "/usr/local/share/fonts"
        self.default_font = self._load_font('7x13.bdf', font_path)
        
    def _load_font(self, font_name, font_dir):
        """
        Load a BDF font file
        
        Args:
            font_name: Name of the font file
            font_dir: Directory containing the font
            
        Returns:
            PIL ImageFont object
        """
        try:
            # Try to load from rpi-rgb-led-matrix fonts directory
            font_path = os.path.join(font_dir, font_name)
            if os.path.exists(font_path):
                return ImageFont.load(font_path)
            
            # Fallback to searching in common system directories
            for directory in [
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.local/share/fonts"),
                # Add path to the rgb-matrix library fonts
                os.path.join(os.path.dirname(__file__), "..", "..", "fonts")
            ]:
                font_path = os.path.join(directory, font_name)
                if os.path.exists(font_path):
                    return ImageFont.load(font_path)
                
            # Last resort: use a default PIL font
            return ImageFont.load_default()
        except Exception as e:
            print(f"Error loading font: {e}")
            return ImageFont.load_default()
    
    def draw_text(self, text, x=0, y=0, color=(255, 255, 255), font=None):
        """
        Draw text at the specified position
        
        Args:
            text: String to display
            x: X position
            y: Y position
            color: RGB color tuple (r,g,b)
            font: Optional font to use instead of default
        """
        image = Image.new("RGB", (self.matrix.width, self.matrix.height))
        draw = ImageDraw.Draw(image)
        font = font or self.default_font
        
        draw.text((x, y), text, font=font, fill=color)
        self.matrix.set_image(image)
        self.matrix.swap()
        
    def draw_centered_text(self, text, color=(255, 255, 255), font=None):
        """
        Draw text centered on the display
        
        Args:
            text: String to display
            color: RGB color tuple (r,g,b)
            font: Optional font to use instead of default
        """
        image = Image.new("RGB", (self.matrix.width, self.matrix.height))
        draw = ImageDraw.Draw(image)
        font = font or self.default_font
        
        # Calculate text size to center it
        text_width, text_height = draw.textsize(text, font=font)
        position = ((self.matrix.width - text_width) // 2, 
                    (self.matrix.height - text_height) // 2)
        
        draw.text(position, text, font=font, fill=color)
        self.matrix.set_image(image)
        self.matrix.swap()