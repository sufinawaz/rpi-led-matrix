#!/usr/bin/env python
from abc import ABC, abstractmethod
import time

class Animation(ABC):
    """Base class for all animations"""

    def __init__(self, matrix_manager, fps=30):
        """
        Initialize the animation

        Args:
            matrix_manager: The MatrixManager instance
            fps: Target frames per second
        """
        self.matrix = matrix_manager
        self.fps = fps
        self.frame_duration = 1.0 / fps
        self.running = False

    @abstractmethod
    def update(self, delta_time):
        """
        Update the animation state

        Args:
            delta_time: Time elapsed since last update in seconds
        """
        pass

    @abstractmethod
    def render(self):
        """Render the current animation frame to the matrix"""
        pass

    def start(self, run_time=None):
        """
        Start the animation

        Args:
            run_time: Optional time limit in seconds, None for indefinite
        """
        self.running = True
        start_time = time.time()
        last_frame_time = start_time

        try:
            while self.running:
                current_time = time.time()

                # Check if we've hit the time limit
                if run_time is not None and current_time - start_time >= run_time:
                    self.running = False
                    break

                # Calculate delta time
                delta_time = current_time - last_frame_time

                # Update and render
                self.update(delta_time)
                self.render()

                # Swap the canvas
                self.matrix.swap()

                # Sleep to maintain FPS
                elapsed = time.time() - last_frame_time
                sleep_time = max(0, self.frame_duration - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

                last_frame_time = current_time
        except KeyboardInterrupt:
            print("Animation stopped by user")
        finally:
            self.cleanup()

    def stop(self):
        """Stop the animation"""
        self.running = False

    def cleanup(self):
        """Clean up resources"""
        self.matrix.clear()
        self.matrix.swap()