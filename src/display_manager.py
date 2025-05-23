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

        self.plugin_cycling = False
        self.cycle_plugins = []
        self.cycle_duration = 30  # Default: 30 seconds
        self.last_cycle_switch = time.time()

        # Load plugin cycling settings from config
        cycle_config = self.config.get("plugin_cycle", {})
        if cycle_config:
            self.plugin_cycling = cycle_config.get("enabled", False)
            self.cycle_plugins = cycle_config.get("plugins", [])
            self.cycle_duration = cycle_config.get("duration", 30)
            self.last_cycle_switch = cycle_config.get("last_switch", time.time())

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

    def _show_transition_screen(self, message=None):
        """
        Create a smooth sliding transition animation when switching between plugins.

        Instead of trying to read pixels from the current canvas (which isn't supported),
        this implementation creates a simple slide-out transition using a black screen.

        Args:
            message: Optional message to display during transition (not used in slide animation)
        """
        from PIL import Image, ImageDraw
        import time
        import math

        # Get display dimensions
        width = self.matrix.width
        height = self.matrix.height

        # Animation parameters
        steps = 15                 # Total animation frames
        transition_time = 0.3      # Total transition duration in seconds
        frame_time = transition_time / steps  # Time per frame

        # Create a black background image for the animation
        black_background = Image.new('RGB', (width, height), (0, 0, 0))

        # Perform the slide-out animation
        for step in range(steps + 1):
            # Calculate animation progress (0.0 to 1.0)
            progress = step / steps

            # Apply easing function for smoother motion (sine easing)
            eased_progress = math.sin(progress * math.pi / 2)

            # Calculate slide offset
            offset = int(width * eased_progress)

            # Create a transition image for this frame
            transition_image = Image.new('RGB', (width, height), (0, 0, 0))

            # Optional: Add subtle transition effects
            if step > 0:
                draw = ImageDraw.Draw(transition_image)
                # Draw a subtle gradient on the right side
                for x in range(width - offset, width):
                    intensity = int(30 * (1 - ((x - (width - offset)) / offset))) if offset > 0 else 0
                    draw.line([(x, 0), (x, height)], fill=(intensity, intensity, intensity))

            # Display the frame
            self.canvas.SetImage(transition_image)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)

            # Add a small delay based on desired frame rate
            time.sleep(max(0.01, frame_time))

    def set_plugin(self, plugin_name):
        """
        Switch to the specified plugin with a simple sliding transition.

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

                # Handle plugin cycling
                if self.plugin_cycling and self.cycle_plugins:
                    cycle_elapsed = current_time - self.last_cycle_switch
                    if cycle_elapsed >= self.cycle_duration:
                        # Time to switch to the next plugin
                        if self.current_plugin:
                            current_index = -1
                            current_name = self.current_plugin.name

                            try:
                                current_index = self.cycle_plugins.index(current_name)
                            except ValueError:
                                # Current plugin not in cycle list, start with first
                                current_index = -1

                            # Move to the next plugin in the cycle
                            next_index = (current_index + 1) % len(self.cycle_plugins)
                            next_plugin = self.cycle_plugins[next_index]

                            # Switch to the next plugin
                            if next_plugin in self.plugins and next_plugin != current_name:
                                logger.info(f"Cycling to plugin: {next_plugin}")
                                self.set_plugin(next_plugin)

                                # Update config with the last switch time
                                self.last_cycle_switch = current_time
                                self.config.set("plugin_cycle", "last_switch", int(self.last_cycle_switch))

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

    def set_plugin_cycling(self, enabled, plugins, duration):
        """Set plugin cycling configuration

        Args:
            enabled: Boolean to enable/disable cycling
            plugins: List of plugin names to cycle through
            duration: Number of seconds to display each plugin
        """
        self.plugin_cycling = enabled

        # Filter plugins to ensure they all exist
        self.cycle_plugins = [p for p in plugins if p in self.plugins]

        # Ensure duration is valid
        self.cycle_duration = max(10, min(3600, duration))

        # Reset timer
        self.last_cycle_switch = time.time()

        # Update config
        self.config.set("plugin_cycle", "enabled", enabled)
        self.config.set("plugin_cycle", "plugins", self.cycle_plugins)
        self.config.set("plugin_cycle", "duration", self.cycle_duration)
        self.config.set("plugin_cycle", "last_switch", int(self.last_cycle_switch))

        # If cycling is enabled and we have plugins, start with the first one
        if enabled and self.cycle_plugins:
            first_plugin = self.cycle_plugins[0]
            if first_plugin in self.plugins:
                self.set_plugin(first_plugin)

        logger.info(f"Plugin cycling {'enabled' if enabled else 'disabled'}")
        if enabled:
            logger.info(f"Cycling through: {', '.join(self.cycle_plugins)} every {self.cycle_duration}s")


