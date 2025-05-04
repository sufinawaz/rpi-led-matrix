#!/usr/bin/env python
import time
import os
import sys
from PIL import Image, ImageDraw
import logging
from src.matrix_manager import MatrixManager
from src.moon_phase import get_moon_phase_image, calculate_moon_phase

def display_moon_phase(matrix_manager):
    """Display the current moon phase on the LED matrix
    
    Args:
        matrix_manager: Instance of MatrixManager
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting moon phase display")
    
    # Update interval in seconds
    update_interval = 3600  # Update every hour
    last_update = 0
    
    try:
        while True:
            # Get current time
            current_time = time.time()
            
            # Check if it's time to update the moon display
            if current_time - last_update >= update_interval:
                # Get the current moon phase and image
                moon_size = (matrix_manager.width // 2, matrix_manager.width // 2)
                phase_name, moon_image = get_moon_phase_image(
                    size=moon_size,
                    color=(220, 220, 255),  # Slightly blue-white color for the moon
                    bg_color=(0, 0, 0)      # Black background
                )
                
                logger.info(f"Current moon phase: {phase_name}")
                last_update = current_time
            
            # Create a new image for the matrix
            display_image = Image.new("RGB", (matrix_manager.width, matrix_manager.height), (0, 0, 0))
            
            # Calculate position to place the moon image (centered)
            if moon_image:
                moon_pos_x = (matrix_manager.width - moon_image.width) // 2
                moon_pos_y = 2  # Position near the top to leave room for text
                
                # Paste the moon image
                display_image.paste(moon_image, (moon_pos_x, moon_pos_y))
            
            # Display the image
            matrix_manager.clear()
            matrix_manager.set_image(display_image)
            matrix_manager.swap()
            
            # Sleep to maintain a reasonable frame rate
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        logger.info("Moon phase display stopped by user")
        matrix_manager.clear()
        matrix_manager.swap()
    except Exception as e:
        logger.error(f"Error in moon phase display: {e}")
        raise

# You can use this as a standalone script
if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )
    
    # Initialize the matrix
    matrix = MatrixManager(
        rows=32,
        cols=32,
        chain_length=1,
        brightness=70,
        hardware_mapping="adafruit-hat"
    )
    
    # Start the moon phase display
    display_moon_phase(matrix)
