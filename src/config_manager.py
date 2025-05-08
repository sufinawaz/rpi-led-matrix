#!/usr/bin/env python
import os
import json
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration for the InfoCube"""

    def __init__(self, config_file=None, project_root=None):
        """Initialize the configuration manager

        Args:
            config_file: Path to the configuration file
            project_root: Project root directory
        """
        self.project_root = project_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..')
        )

        self.config_file = config_file or os.path.join(
            self.project_root, "config.json"
        )

        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                return self._create_default_config()
        else:
            logger.info(f"Config file not found, creating default: {self.config_file}")
            return self._create_default_config()

    def _create_default_config(self):
        """Create default configuration"""
        config = {
            "matrix": {
                "rows": 32,
                "cols": 32,
                "chain_length": 1,
                "brightness": 70,
                "hardware_mapping": "adafruit-hat",
                "gpio_slowdown": 2
            },
            "api_keys": {
                "openweathermap": os.getenv('WEATHER_APP_ID', ''),
                "newsapi": ""
            },
            "defaults": {
                "scroll_speed": 20,
                "fps": 30,
                "font": "7x13.bdf",
                "color": [255, 255, 255]
            },
            "plugins": {
                "enabled": ["clock", "weather", "prayer", "gif", "moon"],
                "default": "clock",
                "settings": {
                    "weather": {
                        "update_interval": 3600,
                        "city_id": 4791160,
                        "units": "imperial"
                    },
                    "prayer": {
                        "latitude": 38.903481,
                        "longitude": -77.262817,
                        "method": 1
                    },
                    "clock": {
                        "show_seconds": False,
                        "format_24h": True
                    },
                    "gif": {
                        "directory": "resources/images/gifs"
                    },
                    "moon": {
                        "update_interval": 3600
                    }
                }
            },
            "current_state": {
                "current_plugin": "clock",
                "current_gif": ""
            }
        }

        # Save the default config
        self.save_config(config)

        return config

    def save_config(self, config=None):
        """Save configuration to file

        Args:
            config: Configuration to save, uses self.config if None
        """
        if config is None:
            config = self.config

        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False

    def get(self, section, key=None, default=None):
        """Get configuration value

        Args:
            section: Configuration section
            key: Configuration key, or None for entire section
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        if key is None:
            return self.config.get(section, default)

        section_data = self.config.get(section, {})

        if isinstance(section_data, dict):
            try:
                return section_data.get(key, default)
            except TypeError as e:
                logger.error(f"TypeError in get: section={section}, key={key}, default={default}")
                logger.error(f"Error: {e}")
                # Return default as a fallback
                return default
        return default

    def set(self, section, key, value):
        """Set configuration value

        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        if section not in self.config:
            self.config[section] = {}

        self.config[section][key] = value
        return self.save_config()

    def get_plugin_config(self, plugin_name):
        """Get configuration for a specific plugin

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin configuration dictionary
        """
        return self.get("plugins", "settings", {}).get(plugin_name, {})