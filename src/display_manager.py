#!/usr/bin/env python
import time
import logging
import os
import importlib
import pkgutil
from rgbmatrix import RGBMatrixOptions, RGBMatrix
# Import the base plugin class
from plugins.base_plugin import DisplayPlugin

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
        """Switch to the specified plugin

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
            # Clean up current plugin if active
            if self.current_plugin:
                self.current_plugin.stop()
                self.current_plugin.cleanup()

            # Initialize and activate new plugin
            self.current_plugin = self.plugins[plugin_name]
            self.current_plugin.setup()
            self.current_plugin.start()

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
            default_plugin = self.config.get("plugins", "default", "clock")
            if not self.set_plugin(default_plugin):
                # Use first available plugin if default not available
                first_plugin = next(iter(self.plugins.keys()))
                logger.warning(f"Default plugin '{default_plugin}' not available, using '{first_plugin}'")
                self.set_plugin(first_plugin)

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
            # Clean up
            if self.current_plugin:
                self.current_plugin.stop()
                self.current_plugin