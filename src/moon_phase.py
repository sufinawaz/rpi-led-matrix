#!/usr/bin/env python
import math
from datetime import datetime, date
from PIL import Image, ImageDraw

def calculate_moon_phase(date_time=None):
    """
    Calculate the current phase of the moon.

    Args:
        date_time: datetime object (defaults to current time if None)

    Returns:
        phase_name: String name of the phase
        phase_index: Integer index (0-7) representing the phase
        phase_fraction: Float between 0 and 1 representing how complete the cycle is
    """
    if date_time is None:
        date_time = datetime.now()

    # Calculate days since known new moon (2000-01-06)
    known_new_moon = datetime(2000, 1, 6, 18, 14, 0)
    days_since = (date_time - known_new_moon).total_seconds() / (24.0 * 3600)

    # Moon cycle is approximately 29.53 days
    lunar_cycle = 29.53058867

    # Calculate phase as a fraction [0,1)
    phase_fraction = (days_since % lunar_cycle) / lunar_cycle

    # Determine the phase name and index
    # We divide the cycle into 8 phases
    phase_index = int((phase_fraction * 8) % 8)

    phase_names = [
        "New Moon",           # 0
        "Waxing Crescent",    # 1
        "First Quarter",      # 2
        "Waxing Gibbous",     # 3
        "Full Moon",          # 4
        "Waning Gibbous",     # 5
        "Last Quarter",       # 6
        "Waning Crescent"     # 7
    ]

    return phase_names[phase_index], phase_index, phase_fraction

def create_moon_image(size, phase_fraction, color=(255, 255, 255), bg_color=(0, 0, 0)):
    """
    Generate an image of the moon at the specified phase.

    Args:
        size: Size of the image (width, height)
        phase_fraction: Float between 0 and 1 representing phase
        color: RGB color tuple for the moon
        bg_color: RGB color tuple for the background

    Returns:
        PIL Image object
    """
    width, height = size
    image = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    # The moon is drawn as a circle with a parabola masking part of it
    # depending on the phase
    center_x, center_y = width // 2, height // 2
    radius = min(width, height) // 2 - 1

    # Draw full circle for the moon
    draw.ellipse(
        (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
        fill=color
    )

    # Adjust phase_fraction to match visual appearance
    # (0 = new, 0.25 = first quarter, 0.5 = full, 0.75 = last quarter)
    adjusted_phase = phase_fraction * 2 * math.pi

    # For new to full moon (phase 0-0.5), mask right side of circle
    # For full to new moon (phase 0.5-1), mask left side of circle
    is_waxing = phase_fraction < 0.5

    # Calculate which side to mask
    if is_waxing:
        # Waxing: mask right side with different shapes according to phase
        terminator_offset = radius * math.sin(adjusted_phase)

        # Mask using a rectangle and a parabola
        points = []

        # Start with right side of circle
        points.append((center_x, center_y - radius))  # Top point

        # Add parabola points
        for y in range(-radius, radius + 1):
            # Calculate x for a parabola or ellipse
            x = terminator_offset * math.cos(math.asin(y / radius))
            points.append((center_x + x, center_y + y))

        points.append((center_x, center_y + radius))  # Bottom point
        points.append((center_x + radius, center_y + radius))  # Bottom right
        points.append((center_x + radius, center_y - radius))  # Top right

        draw.polygon(points, fill=bg_color)
    else:
        # Waning: mask left side with different shapes according to phase
        terminator_offset = radius * math.sin(adjusted_phase - math.pi)

        # Mask using a rectangle and a parabola
        points = []

        # Start with left side of circle
        points.append((center_x, center_y - radius))  # Top point

        # Add parabola points
        for y in range(-radius, radius + 1):
            # Calculate x for a parabola or ellipse
            x = terminator_offset * math.cos(math.asin(y / radius))
            points.append((center_x + x, center_y + y))

        points.append((center_x, center_y + radius))  # Bottom point
        points.append((center_x - radius, center_y + radius))  # Bottom left
        points.append((center_x - radius, center_y - radius))  # Top left

        draw.polygon(points, fill=bg_color)

    return image

def get_moon_phase_image(size=(32, 32), color=(255, 255, 255), bg_color=(0, 0, 0), date_time=None):
    """
    Get an image of the current moon phase.

    Args:
        size: Size of the image (width, height)
        color: RGB color tuple for the moon
        bg_color: RGB color tuple for the background
        date_time: datetime object (defaults to current time if None)

    Returns:
        phase_name: String name of the phase
        image: PIL Image object of the moon
    """
    phase_name, phase_index, phase_fraction = calculate_moon_phase(date_time)
    image = create_moon_image(size, phase_fraction, color, bg_color)
    return phase_name, image

# Testing function
if __name__ == "__main__":
    phase_name, phase_index, phase_fraction = calculate_moon_phase()
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Current moon phase: {phase_name}")
    logger.info(f"Phase index: {phase_index}")
    logger.info(f"Phase fraction: {phase_fraction:.3f}")

    # Create and save a test image
    phase_name, image = get_moon_phase_image((100, 100))
    image.save(f"moon_{phase_name.lower().replace(' ', '_')}.png")
    logger.info(f"Saved moon phase image as moon_{phase_name.lower().replace(' ', '_')}.png")
