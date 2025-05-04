#!/usr/bin/env python
import sys
import os
import argparse

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.matrix_manager import MatrixManager
from src.animations.image_display import ImageDisplay

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Display an image on the LED matrix')
    parser.add_argument('image_path', help='Path to the image or GIF file')
    parser.add_argument('--no-center', action='store_false', dest='center',
                        help='Do not center the image')
    parser.add_argument('--no-loop', action='store_false', dest='loop',
                        help='Do not loop animated GIFs')
    parser.add_argument('--no-fit', action='store_false', dest='fit',
                        help='Do not resize image to fit the display')
    parser.add_argument('--fps', type=int, default=30,
                        help='Target frame rate for animations')
    args = parser.parse_args()

    # Initialize the matrix
    matrix = MatrixManager(
        rows=32,
        cols=32,
        chain_length=1,
        brightness=70,
        hardware_mapping="adafruit-hat"
    )

    # Create an image display animation
    image_display = ImageDisplay(
        matrix,
        image_path=args.image_path,
        center=args.center,
        loop=args.loop,
        fit=args.fit,
        fps=args.fps
    )

    # Start the animation - will run until Ctrl+C is pressed
    # or until the end of a non-looping animation
    image_display.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)