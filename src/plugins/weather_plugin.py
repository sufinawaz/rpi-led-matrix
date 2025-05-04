#!/usr/bin/env python
import time
from datetime import datetime
from PIL import Image, ImageDraw
from rgbmatrix import graphics

from .base_plugin import DisplayPlugin
from api_service import WeatherService

class WeatherPlugin(DisplayPlugin):
    """Plugin for displaying detailed weather information

    Configuration options:
        city_id (int): OpenWeatherMap city ID
        units (str): 'metric' or 'imperial'
        update_interval (int): How often to update weather in seconds
    """

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "weather"
        self.description = "Detailed weather display"

        # Default configuration
        self.config.setdefault('city_id', 4791160)
        self.config.setdefault('units', 'imperial')
        self.config.setdefault('update_interval', 3600)

        # Internal state
        self.last_update = 0
        self.weather_data = None
        self.weather_image = None
        self.current_page = 0
        self.page_time = 0
        self.page_duration = 5  # Seconds per page

        # Font loading
        self.font = graphics.Font()
        self.font_small = graphics.Font()

        # Colors
        self.colors = {
            'white': graphics.Color(255, 255, 255),
            'skyBlue': graphics.Color(0, 191, 255),
            'yellow': graphics.Color(255, 255, 0),
            'lime': graphics.Color(173, 255, 47),
            'pink': graphics.Color(255, 114, 118),
            'lightBlue': graphics.Color(173, 216, 230),
            'error': graphics.Color(255, 0, 0)
        }

        # API service
        self.weather_service = None

    def setup(self):
        """Set up the weather plugin"""
        # Load fonts
        try:
            self.font_small.LoadFont("resources/fonts/4x6.bdf")
            self.font.LoadFont("resources/fonts/7x13.bdf") 
        except Exception as e:
            print(f"Error loading fonts: {e}")

        # Initialize service if not already
        if self.weather_service is None:
            from api_service import APIService
            api_service = APIService(None)  # We'll need to pass config
            self.weather_service = WeatherService(api_service)

        # Initial data fetch
        self._update_weather()

    def _update_weather(self):
        """Update weather data from API"""
        if self.weather_service:
            data = self.weather_service.get_current_weather(
                self.config['city_id'],
                self.config['units']
            )

            if data:
                self.weather_data = {
                    'city': data['name'],
                    'temp': round(data['main']['temp']),
                    'temp_min': round(data['main']['temp_min']),
                    'temp_max': round(data['main']['temp_max']),
                    'description': data['weather'][0]['description'],
                    'humidity': data['main']['humidity'],
                    'pressure': data['main']['pressure'],
                    'wind_speed': data['wind']['speed'],
                    'wind_deg': data.get('wind', {}).get('deg', 0),
                    'clouds': data.get('clouds', {}).get('all', 0),
                    'icon': data['weather'][0]['icon']
                }

                # Load weather icon
                from ui.image import load_image
                icon_path = f"resources/images/weather-icons/{self.weather_data['icon']}.png"
                self.weather_image = load_image(icon_path, (24, 24))

            self.last_update = 0

    def update(self, delta_time):
        """Update weather display state"""
        # Update timers
        self.last_update += delta_time
        self.page_time += delta_time

        # Check if weather update is needed
        if self.last_update >= self.config['update_interval']:
            self._update_weather()

        # Cycle through pages
        if self.page_time >= self.page_duration:
            self.page_time = 0
            self.current_page = (self.current_page + 1) % 3  # 3 pages total

    def render(self, canvas):
        """Render the weather display"""
        # Clear canvas
        canvas.Clear()

        if not self.weather_data:
            # Display error message
            graphics.DrawText(canvas, self.font, 5, 16, 
                              self.colors['error'], "Weather")
            graphics.DrawText(canvas, self.font, 5, 30, 
                              self.colors['error'], "API Error")
            return

        # Show different pages of weather info
        if self.current_page == 0:
            # Page 1: City, temperature, and icon
            graphics.DrawText(canvas, self.font, 2, 12, 
                              self.colors['white'], self.weather_data['city'])

            temp = f"{self.weather_data['temp']}°"
            graphics.DrawText(canvas, self.font, 2, 30, 
                              self.colors['skyBlue'], temp)

            if self.weather_image:
                canvas.SetImage(self.weather_image, 40, 14)

        elif self.current_page == 1:
            # Page 2: Description, hi/low
            desc = self.weather_data['description'].capitalize()
            desc_len = len(desc)

            if desc_len <= 10:
                graphics.DrawText(canvas, self.font, 2, 12, 
                                 self.colors['white'], desc)
            else:
                # Split long description
                graphics.DrawText(canvas, self.font_small, 2, 8, 
                                 self.colors['white'], desc)

            hi_lo = f"Hi: {self.weather_data['temp_max']}° Lo: {self.weather_data['temp_min']}°"
            graphics.DrawText(canvas, self.font_small, 2, 25, 
                             self.colors['pink'], hi_lo)

            graphics.DrawText(canvas, self.font_small, 2, 32, 
                             self.colors['lightBlue'], f"Humidity: {self.weather_data['humidity']}%")

        elif self.current_page == 2:
            # Page 3: Wind and pressure
            graphics.DrawText(canvas, self.font_small, 2, 8, 
                             self.colors['yellow'], "Wind:")

            wind = f"{self.weather_data['wind_speed']} {self.config['units'] == 'imperial' and 'mph' or 'm/s'}"
            graphics.DrawText(canvas, self.font, 2, 18, 
                             self.colors['white'], wind)

            pressure = f"Press: {self.weather_data['pressure']} hPa"
            graphics.DrawText(canvas, self.font_small, 2, 30, 
                             self.colors['lime'], pressure)