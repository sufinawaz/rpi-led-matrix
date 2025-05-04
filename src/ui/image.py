#!/usr/bin/env python
import os
from PIL import Image
import logging
from .component import UIComponent

logger = logging.getLogger(__name__)

def load_image(image_path, size=None):
    """Load an image with error handling and optional resizing

    Args:
        image_path: Path to image file
        size: Optional (width, height) tuple to resize to

    Returns:
        PIL Image object or None if loading failed
    """
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return None

    try:
        # Open with transparency preserved, then explicitly convert to RGB with background 
        if image_path.lower().endswith(('.png', '.gif')):
            # For image formats that might have transparency
            image = Image.open(image_path).convert('RGBA')

            # Create a black background image
            background = Image.new('RGBA', image.size, (0, 0, 0, 255))

            # Paste the image on the background, using alpha as mask
            image = Image.alpha_composite(background, image).convert('RGB')
        else:
            # For image formats without transparency (like JPG)
            image = Image.open(image_path).convert('RGB')

        if size:
            # Use LANCZOS for best quality resizing
            image.thumbnail(size, Image.LANCZOS)

        return image
    except Exception as e:
        logger.error(f"Error loading image {image_path}: {e}")
        return None

class ImageComponent(UIComponent):
    """Component for displaying images

    The ImageComponent renders an image on the matrix at a specific position.
    """

    def __init__(self, x, y, image_path=None, size=None):
        """Initialize the image component

        Args:
            x: X position
            y: Y position
            image_path: Path to image file
            size: Optional (width, height) tuple to resize to
        """
        super().__init__(x, y)
        self.image_path = image_path
        self.size = size
        self.image = None

        if image_path:
            self.load_image(image_path)

    def load_image(self, image_path, size=None):
        """Load image from file

        Args:
            image_path: Path to image file
            size: Optional (width, height) tuple to resize to
        """
        if size is None:
            size = self.size

        self.image_path = image_path
        self.image = load_image(image_path, size)

        if self.image:
            self.width = self.image.width
            self.height = self.image.height

    def render(self, canvas):
        """Render the image to the canvas

        Args:
            canvas: RGB Matrix canvas to render to
        """
        if not self.visible or not self.image:
            return

        # Get absolute position
        x, y = self.get_absolute_position()

        # Draw image
        canvas.SetImage(self.image, x, y)

class AnimatedImageComponent(ImageComponent):
    """Component for displaying animated images

    The AnimatedImageComponent renders animated GIFs on the matrix.
    """

    def __init__(self, x, y, image_path=None, size=None, fps=10, loop=True):
        """Initialize the animated image component

        Args:
            x: X position
            y: Y position
            image_path: Path to image file
            size: Optional (width, height) tuple to resize to
            fps: Frames per second
            loop: Whether to loop the animation
        """
        super().__init__(x, y, None, size)
        self.fps = fps
        self.loop = loop
        self.frame_duration = 1.0 / fps
        self.current_frame = 0
        self.frame_time = 0
        self.frame_count = 1
        self.frames = []

        if image_path:
            self.load_animation(image_path)

    def load_animation(self, image_path, size=None):
        """Load animated image from file

        Args:
            image_path: Path to animated GIF file
            size: Optional (width, height) tuple to resize to
        """
        if size is None:
            size = self.size

        self.image_path = image_path

        try:
            self.image = Image.open(image_path)

            # Check if it's an animated image
            self.frame_count = getattr(self.image, "n_frames", 1)

            if self.frame_count > 1:
                # Extract frames
                self.frames = []
                for i in range(self.frame_count):
                    self.image.seek(i)
                    frame = self.image.copy()

                    # Resize if needed
                    if size:
                        frame.thumbnail(size, Image.LANCZOS)

                    self.frames.append(frame)

                # Set dimensions from first frame
                self.width = self.frames[0].width
                self.height = self.frames[0].height
            else:
                # Not animated, use as static image
                super().load_image(image_path, size)
        except Exception as e:
            logger.error(f"Error loading animation {image_path}: {e}")

    def update(self, delta_time):
        """Update animation state

        Args:
            delta_time: Time elapsed since last update in seconds
        """
        if self.frame_count <= 1:
            return

        self.frame_time += delta_time

        if self.frame_time >= self.frame_duration:
            self.frame_time = 0
            self.current_frame += 1

            if self.current_frame >= self.frame_count:
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = self.frame_count - 1

    def render(self, canvas):
        """Render current frame to canvas

        Args:
            canvas: RGB Matrix canvas to render to
        """
        if not self.visible:
            return

        # Get absolute position
        x, y = self.get_absolute_position()

        if self.frame_count > 1 and len(self.frames) > self.current_frame:
            # Render current frame of animation
            canvas.SetImage(self.frames[self.current_frame], x, y)
        elif self.image:
            # Render static image
            canvas.SetImage(self.image, x, y)