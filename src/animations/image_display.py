#!/usr/bin/env python
import time
import os
from PIL import Image
from .animation_base import Animation

class ImageDisplay(Animation):
    """Animation that displays static images or animated GIFs"""

    def __init__(self, matrix_manager, image_path, center=True, 
                 loop=True, fit=True, fps=30):
        """
        Initialize the image display animation

        Args:
            matrix_manager: The MatrixManager instance
            image_path: Path to the image or GIF file
            center: Center the image on the display if True
            loop: Loop animations if True
            fit: Resize image to fit the display if True
            fps: Target frame rate for animations
        """
        super().__init__(matrix_manager, fps=fps)

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        self.image_path = image_path
        self.center = center
        self.loop = loop
        self.fit = fit

        # Load the image
        self.image = Image.open(image_path)

        # Check if it's an animated GIF
        self.is_animated = getattr(self.image, "is_animated", False)
        self.frame_count = getattr(self.image, "n_frames", 1)
        self.current_frame = 0
        self.frames = []

        # For animated images, extract and prepare all frames
        if self.is_animated:
            for i in range(self.frame_count):
                self.image.seek(i)
                frame = self.image.copy()

                # Process the frame (resize/position)
                frame = self._process_image(frame)
                self.frames.append(frame)

            # Get frame durations if available
            self.frame_durations = []
            try:
                for i in range(self.frame_count):
                    self.image.seek(i)
                    duration = self.image.info.get('duration', 100)  # Default to 100ms
                    self.frame_durations.append(duration / 1000.0)  # Convert to seconds
            except:
                # If we can't get durations, use a default
                self.frame_durations = [0.1] * self.frame_count

            # Reset to first frame
            self.image.seek(0)

        else:
            # For static images, just process once
            self.image = self._process_image(self.image)

        self.frame_time = 0

    def _process_image(self, image):
        """
        Process an image (resize and position)

        Args:
            image: PIL Image to process

        Returns:
            Processed PIL Image
        """
        if self.fit:
            # Resize to fit the display while maintaining aspect ratio
            image.thumbnail((self.matrix.width, self.matrix.height), Image.ANTIALIAS)

        # Create a blank image for the matrix
        matrix_image = Image.new("RGB", (self.matrix.width, self.matrix.height))

        if self.center:
            # Center the image on the display
            position = ((self.matrix.width - image.width) // 2,
                        (self.matrix.height - image.height) // 2)
        else:
            # Position at top-left
            position = (0, 0)

        # Paste the image onto the matrix image
        matrix_image.paste(image, position)
        return matrix_image

    def update(self, delta_time):
        """Update the animation state"""
        if not self.is_animated:
            return

        self.frame_time += delta_time

        # Check if it's time to advance to the next frame
        if self.frame_time >= self.frame_durations[self.current_frame]:
            self.frame_time = 0
            self.current_frame += 1

            # Handle end of animation
            if self.current_frame >= self.frame_count:
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = self.frame_count - 1
                    self.stop()

    def render(self):
        """Render the current frame to the matrix"""
        if self.is_animated:
            # Display the current frame from our pre-processed frames
            self.matrix.set_image(self.frames[self.current_frame])
        else:
            # Static image - just display it
            self.matrix.set_image(self.image)