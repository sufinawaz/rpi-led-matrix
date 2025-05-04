#!/usr/bin/env python
import time
import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from src.matrix_manager import MatrixManager
from src.text_renderer import TextRenderer

def main():
    # Initialize the matrix
    matrix = MatrixManager(
        rows=32,           # Number of rows (height)
        cols=32,           # Number of columns (width)
        chain_length=1,    # Number of matrices chained together
        brightness=50,     # Brightness (0-100)
        hardware_mapping="adafruit-hat"  # Hardware mapping for Adafruit HAT
    )

    # Create a text renderer
    text = TextRenderer(matrix)

    # Display a centered message
    text.draw_centered_text("Hello!", color=(255, 0, 0))
    time.sleep(2)

    # Display another message in a different color
    text.draw_centered_text("RGB Matrix", color=(0, 255, 0))
    time.sleep(2)

    # Display a message in a specific position
    text.draw_text("Position", x=2, y=5, color=(0, 0, 255))
    time.sleep(2)

    # Clear the display when done
    matrix.clear()
    matrix.swap()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)