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
        """Switch to the specified plugin with improved transition handling

        Args:
            plugin_name: Name of the plugin to activate

        Returns:
            True if successful, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin not found: {plugin_name}")
            return False

        logger.info(f"Switching to plugin: {plugin_name}")

        try:
            # Create a transitional fade effect first
            self._show_transition_screen("Loading...")

            # Initialize the new plugin before shutting down the old one
            new_plugin = self.plugins[plugin_name]
            new_plugin.setup()

            # Now clean up current plugin if active
            if self.current_plugin:
                self.current_plugin.stop()
                self.current_plugin.cleanup()

            # Activate the new plugin
            self.current_plugin = new_plugin
            self.current_plugin.start()

            # Save the current plugin to the config
            last_plugin_name = getattr(self.current_plugin, 'name', plugin_name)
            if last_plugin_name == 'gif':
                # Save GIF name for GIF plugin
                gif_name = self.current_plugin.config.get('current_gif', '')
                if gif_name:
                    self.config.set("current_state", "current_gif", gif_name)

            # Save current plugin
            self.config.set("current_state", "current_plugin", last_plugin_name)

            return True
        except Exception as e:
            logger.error(f"Error setting plugin {plugin_name}: {e}")
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

    def _show_transition_screen(self, message="Loading..."):
        """Display a transition screen with a loading indicator

        Args:
            message: Message to display during transition
        """
        from PIL import Image, ImageDraw, ImageFont
        import time

        # Create a new image for the transition screen
        width = self.matrix.width
        height = self.matrix.height
        image = Image.new('RGB', (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Try to load a font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
        except:
            # Use default font if custom font not available
            font = ImageFont.load_default()

        # Draw the message
        message_width = font.getbbox(message)[2] if hasattr(font, 'getbbox') else len(message) * 6
        x = (width - message_width) // 2
        draw.text((x, height // 2 - 4), message, font=font, fill=(255, 255, 255))

        # Draw a simple animated loading bar
        bar_width = width // 2
        bar_x = (width - bar_width) // 2
        bar_y = height // 2 + 6

        # Draw the empty bar outline
        draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + 4], outline=(255, 255, 255), fill=(0, 0, 0))

        # Display the initial frame
        self.canvas.SetImage(image)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

        # Animate the loading bar (short animation to avoid long delay)
        for i in range(1, 6):
            # Update progress bar
            progress = i / 5
            fill_width = int(bar_width * progress)
            draw.rectangle([bar_x + 1, bar_y + 1, bar_x + fill_width - 1, bar_y + 3], fill=(0, 255, 0))

            # Update display
            self.canvas.SetImage(image)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)

            # Short delay for animation
            time.sleep(0.05)