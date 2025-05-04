#!/usr/bin/env python
from rgbmatrix import graphics
from .component import UIComponent

class TextComponent(UIComponent):
    """Component for displaying text

    The TextComponent renders text on the matrix at a specific position,
    with configurable font and color.
    """

    def __init__(self, x, y, text="", font=None, color=(255, 255, 255)):
        """Initialize the text component

        Args:
            x: X position
            y: Y position
            text: Text to display
            font: Font to use (RGBMatrix font)
            color: RGB color tuple
        """
        super().__init__(x, y)
        self.text = text
        self.font = font
        self.color = color

        # Measure text dimensions if font is provided
        if font:
            # This is an approximation since RGBMatrix doesn't provide text measurement
            self.width = len(text) * font.height() / 2
            self.height = font.height()

    def render(self, canvas):
        """Render the text to the canvas

        Args:
            canvas: RGB Matrix canvas to render to
        """
        if not self.visible or not self.text or not self.font:
            return

        # Get absolute position
        x, y = self.get_absolute_position()

        # Convert color tuple to graphics.Color
        if isinstance(self.color, tuple) and len(self.color) == 3:
            color = graphics.Color(*self.color)
        else:
            color = self.color

        # Draw text
        graphics.DrawText(canvas, self.font, x, y, color, self.text)