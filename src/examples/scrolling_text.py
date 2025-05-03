#!/usr/bin/env python
import sys
import os

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.matrix_manager import MatrixManager
from src.animations.scroll_text import ScrollText

def main():
    # Initialize the matrix
    matrix = MatrixManager(
        rows=32,
        cols=32,
        chain_length=1,
        brightness=50,
        hardware_mapping="adafruit-hat"
    )
    
    # Create a scrolling text animation
    scroll = ScrollText(
        matrix,
        text="This is a scrolling text example!",
        color=(255, 165, 0),  # Orange
        scroll_speed=20  # Pixels per second
    )
    
    # Start the animation - will run until Ctrl+C is pressed
    scroll.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)