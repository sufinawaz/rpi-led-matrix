#!/usr/bin/env python3
"""
Configuration validation module to ensure config values are valid and safe.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Valid configuration schemas
CONFIG_SCHEMA = {
    'matrix': {
        'rows': {'type': int, 'min': 8, 'max': 128, 'required': True},
        'cols': {'type': int, 'min': 8, 'max': 256, 'required': True},
        'chain_length': {'type': int, 'min': 1, 'max': 8, 'required': True},
        'brightness': {'type': int, 'min': 1, 'max': 100, 'required': True},
        'hardware_mapping': {'type': str, 'allowed': ['regular', 'adafruit-hat', 'adafruit-hat-pwm'], 'required': True},
        'gpio_slowdown': {'type': int, 'min': 0, 'max': 10, 'required': False}
    },
    'defaults': {
        'scroll_speed': {'type': int, 'min': 1, 'max': 100, 'required': False},
        'fps': {'type': int, 'min': 1, 'max': 60, 'required': False},
        'font': {'type': str, 'pattern': r'^[a-zA-Z0-9_.-]+\.bdf$', 'required': False},
        'color': {'type': list, 'length': 3, 'item_type': int, 'item_min': 0, 'item_max': 255, 'required': False}
    },
    'plugins': {
        'enabled': {'type': list, 'item_type': str, 'required': False},
        'default': {'type': str, 'required': False},
        'settings': {'type': dict, 'required': False}
    }
}

# Valid plugin names
VALID_PLUGINS = {
    'clock', 'weather', 'prayer', 'gif', 'moon', 'intro', 'stock', 'wmata'
}

def validate_value(value: Any, schema: Dict[str, Any], field_name: str = '') -> tuple[bool, str]:
    """
    Validate a single value against its schema.

    Args:
        value: Value to validate
        schema: Schema definition for the value
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if required
    if schema.get('required', False) and value is None:
        return False, f"{field_name} is required but not provided"

    if value is None:
        return True, ""  # Optional field not provided

    # Check type
    expected_type = schema.get('type')
    if expected_type and not isinstance(value, expected_type):
        return False, f"{field_name} must be of type {expected_type.__name__}, got {type(value).__name__}"

    # Type-specific validations
    if expected_type == int:
        if 'min' in schema and value < schema['min']:
            return False, f"{field_name} must be >= {schema['min']}, got {value}"
        if 'max' in schema and value > schema['max']:
            return False, f"{field_name} must be <= {schema['max']}, got {value}"

    elif expected_type == str:
        if 'pattern' in schema:
            if not re.match(schema['pattern'], value):
                return False, f"{field_name} does not match required pattern {schema['pattern']}"
        if 'allowed' in schema:
            if value not in schema['allowed']:
                return False, f"{field_name} must be one of {schema['allowed']}, got '{value}'"

    elif expected_type == list:
        if 'length' in schema and len(value) != schema['length']:
            return False, f"{field_name} must have length {schema['length']}, got {len(value)}"
        if 'item_type' in schema:
            item_type = schema['item_type']
            for i, item in enumerate(value):
                if not isinstance(item, item_type):
                    return False, f"{field_name}[{i}] must be of type {item_type.__name__}, got {type(item).__name__}"
                if item_type == int:
                    if 'item_min' in schema and item < schema['item_min']:
                        return False, f"{field_name}[{i}] must be >= {schema['item_min']}, got {item}"
                    if 'item_max' in schema and item > schema['item_max']:
                        return False, f"{field_name}[{i}] must be <= {schema['item_max']}, got {item}"

    return True, ""

def validate_plugin_settings(plugin_name: str, settings: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate plugin-specific settings.

    Args:
        plugin_name: Name of the plugin
        settings: Plugin settings to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if plugin_name not in VALID_PLUGINS:
        errors.append(f"Unknown plugin: {plugin_name}")
        return False, errors

    # Plugin-specific validation
    if plugin_name == 'weather':
        if 'city_id' in settings:
            city_id = settings['city_id']
            if not isinstance(city_id, int) or city_id <= 0:
                errors.append("weather.city_id must be a positive integer")

        if 'units' in settings:
            units = settings['units']
            if units not in ['metric', 'imperial', 'kelvin']:
                errors.append("weather.units must be 'metric', 'imperial', or 'kelvin'")

    elif plugin_name == 'prayer':
        if 'latitude' in settings:
            lat = settings['latitude']
            if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
                errors.append("prayer.latitude must be a number between -90 and 90")

        if 'longitude' in settings:
            lon = settings['longitude']
            if not isinstance(lon, (int, float)) or lon < -180 or lon > 180:
                errors.append("prayer.longitude must be a number between -180 and 180")

    elif plugin_name == 'stock':
        if 'symbols' in settings:
            symbols = settings['symbols']
            if not isinstance(symbols, list):
                errors.append("stock.symbols must be a list")
            else:
                for symbol in symbols:
                    if not isinstance(symbol, str) or not re.match(r'^[A-Z]{1,5}$', symbol):
                        errors.append(f"Invalid stock symbol: {symbol}. Must be 1-5 uppercase letters")

    elif plugin_name == 'wmata':
        if 'stations' in settings:
            stations = settings['stations']
            if not isinstance(stations, list):
                errors.append("wmata.stations must be a list")
            else:
                for station in stations:
                    if not isinstance(station, str) or not re.match(r'^[A-Z][0-9]{2}$', station):
                        errors.append(f"Invalid WMATA station code: {station}. Must be format like 'A01'")

    # Common validations for all plugins
    if 'update_interval' in settings:
        interval = settings['update_interval']
        if not isinstance(interval, int) or interval < 10:
            errors.append(f"{plugin_name}.update_interval must be an integer >= 10 seconds")

    return len(errors) == 0, errors

def validate_configuration(config: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate entire configuration against schema.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Validate top-level sections
    for section_name, section_schema in CONFIG_SCHEMA.items():
        section_data = config.get(section_name, {})

        # Validate each field in the section
        for field_name, field_schema in section_schema.items():
            field_value = section_data.get(field_name)
            is_valid, error_msg = validate_value(field_value, field_schema, f"{section_name}.{field_name}")
            if not is_valid:
                errors.append(error_msg)

    # Special validation for plugins
    if 'plugins' in config:
        plugins_config = config['plugins']

        # Validate enabled plugins list
        if 'enabled' in plugins_config:
            enabled = plugins_config['enabled']
            if isinstance(enabled, list):
                for plugin in enabled:
                    if plugin not in VALID_PLUGINS:
                        errors.append(f"Unknown plugin in enabled list: {plugin}")

        # Validate plugin settings
        if 'settings' in plugins_config:
            settings = plugins_config['settings']
            if isinstance(settings, dict):
                for plugin_name, plugin_settings in settings.items():
                    if plugin_name in VALID_PLUGINS:
                        is_valid, plugin_errors = validate_plugin_settings(plugin_name, plugin_settings)
                        errors.extend(plugin_errors)

    return len(errors) == 0, errors

def sanitize_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize configuration by removing invalid values and applying defaults.

    Args:
        config: Configuration to sanitize

    Returns:
        Sanitized configuration
    """
    sanitized = config.copy()

    # Ensure matrix section has required fields with safe defaults
    if 'matrix' not in sanitized:
        sanitized['matrix'] = {}

    matrix = sanitized['matrix']
    matrix.setdefault('rows', 32)
    matrix.setdefault('cols', 64)
    matrix.setdefault('chain_length', 1)
    matrix.setdefault('brightness', 50)  # Safe default
    matrix.setdefault('hardware_mapping', 'regular')

    # Clamp values to safe ranges
    matrix['rows'] = max(8, min(128, matrix.get('rows', 32)))
    matrix['cols'] = max(8, min(256, matrix.get('cols', 64)))
    matrix['brightness'] = max(1, min(100, matrix.get('brightness', 50)))

    # Ensure plugins section exists
    if 'plugins' not in sanitized:
        sanitized['plugins'] = {}

    plugins = sanitized['plugins']
    plugins.setdefault('enabled', ['clock'])
    plugins.setdefault('default', 'clock')
    plugins.setdefault('settings', {})

    # Filter out invalid plugins
    if 'enabled' in plugins and isinstance(plugins['enabled'], list):
        plugins['enabled'] = [p for p in plugins['enabled'] if p in VALID_PLUGINS]
        if not plugins['enabled']:
            plugins['enabled'] = ['clock']  # Fallback to clock

    logger.info("Configuration sanitized successfully")
    return sanitized