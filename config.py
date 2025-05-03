#!/usr/bin/env python

# Matrix configuration
MATRIX_CONFIG = {
    'rows': 32,
    'cols': 32,
    'chain_length': 1,
    'parallel': 1,
    'brightness': 70,
    'hardware_mapping': 'adafruit-hat',
    'gpio_slowdown': 2
}

# API Keys
API_KEYS = {
    'openweathermap': 'YOUR_API_KEY_HERE',
    'newsapi': 'YOUR_API_KEY_HERE'
}

# Default settings
DEFAULT_SCROLL_SPEED = 20
DEFAULT_FPS = 30
DEFAULT_FONT = '7x13.bdf'
DEFAULT_COLOR = (255, 255, 255)  # White

# Path settings
FONT_PATH = '/usr/local/share/fonts'
IMAGE_PATH = './images'