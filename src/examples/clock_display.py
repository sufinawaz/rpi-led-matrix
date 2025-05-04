#!/usr/bin/env python
import sys
import os

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.matrix_manager import MatrixManager
from src.animations.clock import Clock

def main():
    # Initialize the matrix
    matrix = MatrixManager(
        rows=32,
        cols=32,
        chain_length=1,
        brightness=50,
        hardware_mapping="adafruit-hat"
    )

    # Create a clock animation
    clock = Clock(
        matrix,
        color=(0, 191, 255),  # Deep sky blue
        show_seconds=True,
        format_24h=True
    )

    # Start the clock - will run until Ctrl+C is pressed
    clock.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)