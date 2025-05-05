#!/usr/bin/env python
import os
import time
from PIL import Image
from rgbmatrix import graphics

from .base_plugin import DisplayPlugin
from ui.image import AnimatedImageComponent

class GifPlugin(DisplayPlugin):
    """Plugin for displaying animated GIFs

    Configuration options:
        directory (str): Directory containing GIF files
        current_gif (str): Name of the current GIF to display
        show_clock (bool): Whether to show a clock overlay on the GIF
    """

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "gif"
        self.description = "Animated GIF display"

        # Default configuration
        self.config.setdefault('directory', 'resources/images/gifs')
        self.config.setdefault('current_gif', 'matrix')
        self.config.setdefault('show_clock', True)

        # Font loading
        self.font = graphics.Font()

        # Colors
        self.colors = {
            'white': graphics.Color(255, 255, 255),
            'black': graphics.Color(0, 0, 0)
        }

        # Create animated image component
        self.gif_component = None

        # Track errors to avoid constant logging
        self.reported_error = False

    def setup(self):
        """Set up the GIF plugin"""
        # Load font
        try:
            self.font.LoadFont("resources/fonts/7x13.bdf")
        except Exception as e:
            print(f"Error loading font: {e}")

        # Load the GIF
        self._load_gif()

        # Reset error reporting flag
        self.reported_error = False

    def _load_gif(self):
        """Load the current GIF"""
        # Determine GIF path
        gif_name = self.config['current_gif']
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        gif_dir = os.path.join(project_root, self.config['directory'])
        gif_path = os.path.join(gif_dir, f"{gif_name}.gif")

        # Check if file exists
        if not os.path.exists(gif_path):
            print(f"GIF file not found: {gif_path}")
            return

        try:
            # Create animated image component with proper error handling
            self.gif_component = AnimatedImageComponent(0, 0, gif_path, fps=10)
            print(f"Successfully loaded GIF: {gif_path}")

            # Verify all frames are in RGB mode
            if hasattr(self.gif_component, 'frames') and self.gif_component.frames:
                for i, frame in enumerate(self.gif_component.frames):
                    if frame.mode != 'RGB':
                        print(f"Converting frame {i} from {frame.mode} to RGB")
                        self.gif_component.frames[i] = frame.convert('RGB')
        except Exception as e:
            print(f"Error loading GIF: {e}")

    def update(self, delta_time):
        """Update GIF animation"""
        if self.gif_component:
            try:
                self.gif_component.update(delta_time)
            except Exception as e:
                if not self.reported_error:
                    print(f"Error updating GIF: {e}")
                    self.reported_error = True

    def render(self, canvas):
        """Render the GIF display"""
        # Clear canvas
        canvas.Clear()

        # Render GIF
        if self.gif_component:
            try:
                # Additional safety check before rendering
                if hasattr(self.gif_component, 'frames') and self.gif_component.frames:
                    current_frame_idx = self.gif_component.current_frame
                    if 0 <= current_frame_idx < len(self.gif_component.frames):
                        current_frame = self.gif_component.frames[current_frame_idx]
                        if current_frame.mode != 'RGB':
                            current_frame = current_frame.convert('RGB')
                            self.gif_component.frames[current_frame_idx] = current_frame

                # Now render the component
                self.gif_component.render(canvas)
            except Exception as e:
                if not self.reported_error:
                    print(f"Error rendering GIF: {e}")
                    self.reported_error = True

                # Try to recover - draw an error message
                text = "GIF Error"
                text_width = len(text) * 7  # Approximate width per character
                x_pos = (canvas.width - text_width) // 2
                y_pos = canvas.height // 2
                graphics.DrawText(canvas, self.font, x_pos, y_pos, self.colors['white'], text)
                return

        # Overlay clock if enabled
        if self.config['show_clock']:
            import datetime
            now = datetime.datetime.now()

            # Format time string
            if self.config.get('format_24h', True):
                time_str = now.strftime("%H:%M")
            else:
                time_str = now.strftime("%I:%M%p").lower()

            # Measure approximate width to center
            text_width = len(time_str) * 7  # Approximate width per character
            x_pos = (canvas.width - text_width) // 2
            y_pos = canvas.height // 2

            # Draw text with black outline for visibility
            for offset_x in [-1, 0, 1]:
                for offset_y in [-1, 0, 1]:
                    if offset_x != 0 or offset_y != 0:
                        graphics.DrawText(canvas, self.font, 
                                        x_pos + offset_x, 
                                        y_pos + offset_y, 
                                        self.colors['black'], 
                                        time_str)

            # Draw the main text
            graphics.DrawText(canvas, self.font, 
                             x_pos, y_pos, 
                             self.colors['white'], 
                             time_str)