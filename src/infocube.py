#!/usr/bin/env python
import os
import sys
import argparse
import logging
import time
from rgbmatrix import RGBMatrix

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="RGB LED Matrix InfoCube")
    parser.add_argument("--display-mode", help="Display mode to start with", default=None)
    parser.add_argument("--gif-name", help="GIF to display (if display-mode is 'gif')", default="matrix")
    parser.add_argument("--config", help="Path to config file", default=None)
    args = parser.parse_args()

    # Check if running as root (required for GPIO access)
    if os.geteuid() != 0:
        logger.error("This program must be run as root (sudo) for GPIO access")
        sys.exit(1)

    logger.info("Starting InfoCube")

    try:
        # Initialize configuration manager
        from config_manager import ConfigManager
        config_manager = ConfigManager(args.config)
        print("Config loaded successfully:", config_manager.config)

        # Initialize display manager
        from display_manager import DisplayManager
        display_manager = DisplayManager(config_manager)

        # Set initial plugin if specified
        if args.display_mode:
            logger.info(f"Setting initial plugin: {args.display_mode}")

            # Special handling for gif plugin
            if args.display_mode == "gif":
                # Update gif plugin configuration
                gif_config = config_manager.get_plugin_config("gif")
                gif_config["current_gif"] = args.gif_name
                config_manager.set("plugins", "settings", {**config_manager.get("plugins", "settings", {}), "gif": gif_config})

            if not display_manager.set_plugin(args.display_mode):
                logger.warning(f"Plugin '{args.display_mode}' not available, using default")

        # Run the display manager
        display_manager.run()

    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        sys.exit(0)
    except Exception as e:
        import traceback
        print(f"Error details: {e}")
        traceback.print_exc()  # This will print the full stack trace
        sys.exit(1)

if __name__ == "__main__":
    main()