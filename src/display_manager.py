#!/usr/bin/env python
import time
import logging
import os
import importlib
import pkgutil
from rgbmatrix import RGBMatrixOptions, RGBMatrix
# Import the base plugin class
from plugins.base_plugin import DisplayPlugin
# Import our new API server
from api_server import APIServer

logger = logging.getLogger(__name__)

class DisplayManager:
    """Manages the LED matrix display and plugins"""

    def __init__(self, config_manager):
        """Initialize the display manager

        Args:
            config_manager: ConfigManager instance
        """
        self.config = config_manager
        self.plugins = {}
        self.current_plugin = None

        # Initialize matrix
        self._init_matrix()

        # Load plugins
        self.load_plugins()

        # Initialize API server
        self.api_server = APIServer(self)
        self.api_server.start()

    def _init_matrix(self):
        """Initialize the RGB matrix"""
        # Get matrix configuration
        matrix_config = self.config.get("matrix")
        if not isinstance(matrix_config, dict):
            matrix_config = {}

        # Set up matrix options
        options = RGBMatrixOptions()
        options.rows = matrix_config.get("rows", 32)
        options.cols = matrix_config.get("cols", 32)
        options.chain_length = matrix_config.get("chain_length", 1)
        options.parallel = matrix_config.get("parallel", 1)
        options.brightness = matrix_config.get("brightness", 70)
        options.hardware_mapping = matrix_config.get("hardware_mapping", "adafruit-hat")
        options.gpio_slowdown = matrix_config.get("gpio_slowdown", 2)
        options.led_rgb_sequence = 'RBG'

        # Initialize matrix and canvas
        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()

    def load_plugins(self):
        """Load all enabled plugins"""
        # Get list of enabled plugins from config
        enabled_plugins = self.config.get("plugins", "enabled", [])
        if not enabled_plugins:
            logger.warning("No plugins enabled in configuration")
            return

        logger.info(f"Loading enabled plugins: {enabled_plugins}")

        try:
            # Import and load each plugin
            for plugin_name in enabled_plugins:
                try:
                    # Try to dynamically import the plugin module
                    # Directly use 'plugins' module instead of 'src.plugins'
                    module_name = f"{plugin_name}_plugin"
                    plugin_module = importlib.import_module(f"plugins.{module_name}")

                    # Find plugin class in module
                    for attr_name in dir(plugin_module):
                        attr = getattr(plugin_module, attr_name)

                        # Check if it's a DisplayPlugin subclass
                        if (isinstance(attr, type) and 
                            issubclass(attr, DisplayPlugin) and 
                            attr != DisplayPlugin):

                            # Get plugin config
                            plugin_config = self.config.get_plugin_config(plugin_name)

                            # Create plugin instance
                            plugin = attr(self.matrix, plugin_config)
                            self.plugins[plugin_name] = plugin
                            logger.info(f"Loaded plugin: {plugin_name}")
                            break
                    else:
                        logger.warning(f"No plugin class found for {plugin_name}")
                except Exception as e:
                    logger.error(f"Error loading plugin {plugin_name}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(f"Error loading plugins: {e}")
            import traceback
            logger.error(traceback.format_exc())

        logger.info(f"Loaded {len(self.plugins)} plugins")

    def set_plugin(self, plugin_name):
        """
        Switch to the specified plugin with a smooth slide transition.

        This method handles the complete plugin switching process including:
        1. Checking if the plugin exists
        2. Setting up the new plugin before stopping the current one
        3. Running the transition animation between plugins
        4. Performing proper cleanup of the old plugin
        5. Starting the new plugin and saving state

        Args:
            plugin_name: Name of the plugin to activate

        Returns:
            True if successful, False otherwise
        """
        # Validate that the requested plugin exists
        if plugin_name not in self.plugins:
            logger.error(f"Plugin not found: {plugin_name}")
            return False

        # Skip the whole process if it's already the active plugin
        if self.current_plugin and self.current_plugin.name == plugin_name:
            logger.info(f"Plugin {plugin_name} is already active")
            return True

        logger.info(f"Switching to plugin: {plugin_name}")

        try:
            # Step 1: Set up the new plugin first to prevent delays during transition
            new_plugin = self.plugins[plugin_name]
            new_plugin.setup()

            # Step 2: Run the sliding transition animation
            self._show_transition_screen()

            # Step 3: Clean up the current plugin properly
            if self.current_plugin:
                self.current_plugin.stop()
                self.current_plugin.cleanup()

            # Step 4: Activate the new plugin
            self.current_plugin = new_plugin
            self.current_plugin.start()

            # Step 5: Update saved state
            # Save plugin-specific settings for GIF mode
            if plugin_name == 'gif':
                # Save current GIF name for GIF plugin
                gif_name = self.current_plugin.config.get('current_gif', '')
                if gif_name:
                    self.config.set("current_state", "current_gif", gif_name)

            # Save current plugin name
            self.config.set("current_state", "current_plugin", plugin_name)

            # Force immediate render of the new content
            self.canvas.Clear()
            self.current_plugin.render(self.canvas)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)

            return True

        except Exception as e:
            logger.error(f"Error setting plugin {plugin_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def run(self):
        """Main display loop"""
        if not self.plugins:
            logger.error("No plugins available")
            return

        # Set default plugin if none active
        if not self.current_plugin:
            # Try to restore last state from config
            last_plugin = self.config.get("current_state", "current_plugin", "")

            if last_plugin in self.plugins:
                # Try to restore previous state
                if last_plugin == 'gif':
                    # For GIF plugin, also restore GIF name
                    gif_name = self.config.get("current_state", "current_gif", "")
                    if gif_name:
                        gif_plugin = self.plugins.get('gif')
                        if gif_plugin:
                            gif_plugin.config['current_gif'] = gif_name

                if not self.set_plugin(last_plugin):
                    # Fall back to default if restoration fails
                    self._set_default_plugin()
            else:
                # No valid saved state, use default
                self._set_default_plugin()

        logger.info("Starting main display loop")

        try:
            last_time = time.time()
            while True:
                current_time = time.time()
                delta_time = current_time - last_time
                last_time = current_time

                # Update plugin state
                self.current_plugin.update(delta_time)

                # Clear canvas
                self.canvas.Clear()

                # Render plugin
                self.current_plugin.render(self.canvas)

                # Swap canvas
                self.canvas = self.matrix.SwapOnVSync(self.canvas)

                # Sleep to maintain reasonable framerate
                time.sleep(0.01)
        except KeyboardInterrupt:
            logger.info("Display loop interrupted by user")
        except Exception as e:
            logger.error(f"Error in display loop: {e}")
        finally:
            # Stop API server
            if hasattr(self, 'api_server'):
                self.api_server.stop()

            # Clean up plugins
            if self.current_plugin:
                self.current_plugin.stop()
                self.current_plugin.cleanup()

    def _set_default_plugin(self):
        """Set the default plugin based on configuration"""
        default_plugin = self.config.get("plugins", "default", "clock")
        if not self.set_plugin(default_plugin):
            # Use first available plugin if default not available
            first_plugin = next(iter(self.plugins.keys()))
            logger.warning(f"Default plugin '{default_plugin}' not available, using '{first_plugin}'")
            self.set_plugin(first_plugin)

    def _show_transition_screen(self, message=None):
        """
        Create a smooth sliding transition animation when switching between plugins.

        This transition slides the current content off to the left while the new
        content appears from the right, creating an intuitive visual effect.

        Args:
            message: Optional message to display during transition (not used in slide animation)
        """
        from PIL import Image
        import time
        import math

        # Get display dimensions
        width = self.matrix.width
        height = self.matrix.height

        # Step 1: Capture current display content before transition
        current_display = Image.new('RGB', (width, height), (0, 0, 0))

        # Only attempt to capture current display if we have an active plugin
        if self.current_plugin:
            # Force a fresh render to make sure we have the latest content
            self.canvas.Clear()
            self.current_plugin.render(self.canvas)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)

            # Convert canvas content to PIL Image for animation
            for y in range(height):
                for x in range(width):
                    r, g, b = self.canvas.GetPixel(x, y)
                    current_display.putpixel((x, y), (r, g, b))

        # Step 2: Configure animation parameters
        steps = 20                # Total animation frames
        transition_time = 0.4     # Total transition duration in seconds
        frame_time = transition_time / steps  # Time per frame

        # Create a blank image for the transition frames
        transition_image = Image.new('RGB', (width, height), (0, 0, 0))

        # Step 3: Perform the slide animation
        for step in range(steps + 1):
            # Calculate animation progress (0.0 to 1.0)
            progress = step / steps

            # Apply easing function for smoother motion (sine easing)
            # This makes the animation start and end more gradually
            eased_progress = math.sin(progress * math.pi / 2)

            # Calculate pixel offset for sliding
            offset = int(width * eased_progress)

            # Clear the transition image for this frame
            transition_image = Image.new('RGB', (width, height), (0, 0, 0))

            # Slide current content to the left
            transition_image.paste(current_display, (-offset, 0))

            # Display the frame
            self.canvas.SetImage(transition_image)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)

            # Add a small delay based on desired frame rate
            # Adjust timing for smoother animation at start/end points
            sleep_time = frame_time
            if progress < 0.2 or progress > 0.8:
                # Slow down at beginning and end for smoother appearance
                sleep_time *= 1.2

            time.sleep(max(0.001, sleep_time))  # Ensure minimum delay
