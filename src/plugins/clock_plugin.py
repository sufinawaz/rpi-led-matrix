#!/usr/bin/env python
from datetime import datetime
from PIL import Image, ImageDraw
from rgbmatrix import graphics

from .base_plugin import DisplayPlugin
from ui.text import TextComponent
from ui.layout import GridLayout
from api_service import WeatherService, PrayerTimesService

class ClockPlugin(DisplayPlugin):
    """Plugin for displaying clock, date, weather, and prayer time

    Configuration options:
        show_seconds (bool): Whether to show seconds in the clock
        format_24h (bool): Use 24-hour format if True, 12-hour if False
        update_interval (int): How often to update weather in seconds
        city_id (int): OpenWeatherMap city ID
        units (str): 'metric' or 'imperial'
    """

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "clock"
        self.description = "Clock with date, weather, and prayer time"

        # Default configuration
        self.config.setdefault('show_seconds', False)
        self.config.setdefault('format_24h', True)
        self.config.setdefault('update_interval', 3600)
        self.config.setdefault('city_id', 4791160)
        self.config.setdefault('units', 'imperial')

        # Internal state
        self.last_weather_update = 0
        self.last_prayer_update = 0
        self.weather_data = None
        self.prayer_data = None
        self.weather_image = None

        # Font loading
        self.font = graphics.Font()
        self.font_small = graphics.Font()

        # Colors
        self.colors = {
            'white': graphics.Color(255, 255, 255),
            'orange': graphics.Color(255, 165, 0),
            'black': graphics.Color(0, 0, 0),
            'skyBlue': graphics.Color(0, 191, 255),
            'red': graphics.Color(255, 0, 0),
            'green': graphics.Color(0, 255, 0),
            'yellow': graphics.Color(255, 255, 0),
            'lime': graphics.Color(173, 255, 47),
            'lightBlue': graphics.Color(173, 216, 230),
            'darkBlue': graphics.Color(30, 144, 255),
            'grey': graphics.Color(150, 150, 150),
            'pink': graphics.Color(255, 114, 118),
            'error': graphics.Color(255, 0, 0)
        }

        # UI layout
        self.layout = GridLayout(0, 0, matrix.width, matrix.height, rows=4, cols=2)

        # API services
        self.weather_service = None
        self.prayer_service = None

    def setup(self):
        """Set up the clock plugin"""
        # Load fonts
        try:
            self.font_small.LoadFont("resources/fonts/4x6.bdf")
            self.font.LoadFont("resources/fonts/7x13.bdf") 
        except Exception as e:
            print(f"Error loading fonts: {e}")

        # Initialize services if not already
        if self.weather_service is None:
            from api_service import APIService
            api_service = APIService(None)  # We'll need to pass config
            self.weather_service = WeatherService(api_service)
            self.prayer_service = PrayerTimesService(api_service)

        # Initial data fetch
        self._update_weather()
        self._update_prayer_times()

    def _update_weather(self):
        """Update weather data from API"""
        if self.weather_service:
            data = self.weather_service.get_current_weather(
                self.config['city_id'],
                self.config['units']
            )

            if data:
                self.weather_data = {
                    'temp': str(round(data['main']['temp'])) + '°',
                    'temp_min': str(round(data['main']['temp_min'])),
                    'temp_max': str(round(data['main']['temp_max'])),
                    'description': data['weather'][0]['description'],
                    'icon': data['weather'][0]['icon']
                }

                # Load weather icon
                from ui.image import load_image
                icon_path = f"resources/images/weather-icons/{self.weather_data['icon']}.png"
                self.weather_image = load_image(icon_path, (24, 24))

            self.last_weather_update = 0

    def _update_prayer_times(self):
        """Update prayer times from API"""
        if self.prayer_service:
            data = self.prayer_service.get_prayer_times(38.903481, -77.262817)

            if data:
                timings = data['data']['timings']
                self.prayer_data = {
                    'fajr': timings['Fajr'],
                    'dhuhr': timings['Dhuhr'],
                    'asr': timings['Asr'],
                    'maghrib': timings['Maghrib'],
                    'isha': timings['Isha']
                }

                # Calculate next prayer
                self.next_prayer = self._get_next_prayer()

            self.last_prayer_update = 0

    def _get_next_prayer(self):
        """Get the next prayer time"""
        if not self.prayer_data:
            return None

        # Get current time in HH:MM format
        current_time = datetime.now().strftime('%H:%M')

        # Check each prayer time
        prayer_order = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']
        prayer_names = {'fajr': 'Fajr', 'dhuhr': 'Zuhr', 'asr': 'Asr', 
                        'maghrib': 'Magh', 'isha': 'Isha'}

        for prayer in prayer_order:
            if self.prayer_data[prayer] > current_time:
                return {
                    'name': prayer_names[prayer],
                    'time': self.prayer_data[prayer]
                }

        # If all prayers have passed, return the first prayer for tomorrow
        return {
            'name': prayer_names['fajr'],
            'time': self.prayer_data['fajr']
        }

    def update(self, delta_time):
        """Update clock state"""
        # Update timers
        self.last_weather_update += delta_time
        self.last_prayer_update += delta_time

        # Check if weather update is needed
        if self.last_weather_update >= self.config['update_interval']:
            self._update_weather()

        # Check if prayer update is needed (every 4 hours)
        if self.last_prayer_update >= 14400:
            self._update_prayer_times()

        # Check if next prayer time has passed
        current_time = datetime.now().strftime('%H:%M')
        if self.next_prayer and current_time >= self.next_prayer['time']:
            self._update_prayer_times()

    def render(self, canvas):
        """Render the clock display"""
        # Clear canvas
        canvas.Clear()

        # Get current time and date
        now = datetime.now()
        day = now.strftime('%a')
        date = now.strftime('%d')
        month = now.strftime('%b')

        if self.config['format_24h']:
            time_format = '%H:%M'
            if self.config['show_seconds']:
                time_format += ':%S'
        else:
            time_format = '%I:%M'
            if self.config['show_seconds']:
                time_format += ':%S'
            time_format += '%p'

        time_str = now.strftime(time_format)

        # Draw calendar (day, date, month)
        graphics.DrawText(canvas, self.font_small, 3, 6, 
                          self.colors['lime'], day)
        graphics.DrawText(canvas, self.font_small, 20, 6, 
                          self.colors['lime'], date)
        graphics.DrawText(canvas, self.font_small, 30, 6, 
                          self.colors['yellow'], month)

        # Draw time
        graphics.DrawText(canvas, self.font, 3, 18, 
                          self.colors['white'], time_str)

        # Draw weather info if available
        if self.weather_data:
            # Display temperature
            graphics.DrawText(canvas, self.font, 42, 30, 
                              self.colors['skyBlue'], self.weather_data['temp'])

            # Display high/low
            graphics.DrawText(canvas, self.font_small, 28, 25, 
                              self.colors['pink'], self.weather_data['temp_max'])
            graphics.DrawText(canvas, self.font_small, 28, 31, 
                              self.colors['lightBlue'], self.weather_data['temp_min'])

            # Display weather icon
            if self.weather_image:
                canvas.SetImage(self.weather_image, 44, -4)
        else:
            # Display error message if weather API failed
            graphics.DrawText(canvas, self.font_small, 42, 30, 
                              self.colors['error'], "W-ERR")

        # Draw prayer info if available
        if self.next_prayer:
            graphics.DrawText(canvas, self.font_small, 5, 25, 
                              self.colors['grey'], self.next_prayer['name'])
            graphics.DrawText(canvas, self.font_small, 5, 31, 
                              self.colors['darkBlue'], self.next_prayer['time'])
        else:
            # Display error message if prayer API failed
            graphics.DrawText(canvas, self.font_small, 5, 25, 
                              self.colors['error'], "P-ERR")