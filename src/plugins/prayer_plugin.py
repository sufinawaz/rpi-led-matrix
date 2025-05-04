#!/usr/bin/env python
from datetime import datetime
from PIL import Image
import os
from rgbmatrix import graphics

from .base_plugin import DisplayPlugin
from api_service import PrayerTimesService
from ui.image import load_image

class PrayerPlugin(DisplayPlugin):
    """Plugin for displaying prayer times

    Configuration options:
        latitude (float): Latitude for prayer times calculation
        longitude (float): Longitude for prayer times calculation
        method (int): Calculation method (1-7)
        show_mosque_image (bool): Whether to display mosque icon
        mosque_image_path (str): Path to mosque image
    """

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "prayer"
        self.description = "Prayer times display"

        # Default configuration
        self.config.setdefault('latitude', 38.903481)
        self.config.setdefault('longitude', -77.262817)
        self.config.setdefault('method', 1)
        self.config.setdefault('show_mosque_image', True)
        self.config.setdefault('mosque_image_path', 'resources/images/mosque.jpg')

        # Prayer names
        self.prayer_names = ['Fajr', 'Zuhr', 'Asr', 'Magh', 'Isha']

        # Internal state
        self.last_update = 0
        self.update_interval = 14400  # 4 hours
        self.prayer_times = None
        self.next_prayer = None
        self.mosque_image = None
        self.force_update = False

        # Font loading
        self.font = graphics.Font()
        self.font_small = graphics.Font()

        # Colors
        self.colors = {
            'white': graphics.Color(255, 255, 255),
            'skyBlue': graphics.Color(0, 191, 255),
            'orange': graphics.Color(255, 165, 0),
            'error': graphics.Color(255, 0, 0)
        }

        # API service
        self.prayer_service = None

    def setup(self):
        """Set up the prayer plugin"""
        # Load fonts
        try:
            self.font_small.LoadFont("resources/fonts/4x6.bdf")
            self.font.LoadFont("resources/fonts/7x13.bdf") 
        except Exception as e:
            print(f"Error loading fonts: {e}")

        # Load mosque image if enabled
        if self.config['show_mosque_image']:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
            mosque_path = os.path.join(project_root, self.config['mosque_image_path'])
            self.mosque_image = load_image(mosque_path)

        # Initialize service if not already
        if self.prayer_service is None:
            from api_service import APIService
            api_service = APIService(None)  # We'll need to pass config
            self.prayer_service = PrayerTimesService(api_service)

        # Initial data fetch
        self._update_prayer_times()

    def _update_prayer_times(self):
        """Update prayer times from API"""
        if self.prayer_service:
            data = self.prayer_service.get_prayer_times(
                self.config['latitude'],
                self.config['longitude'],
                self.config['method']
            )

            if data:
                timings = data['data']['timings']
                self.prayer_times = [
                    timings['Fajr'],
                    timings['Dhuhr'],
                    timings['Asr'],
                    timings['Maghrib'],
                    timings['Isha']
                ]

                # Calculate next prayer
                self._calculate_next_prayer()

            self.last_update = 0
            self.force_update = False

    def _calculate_next_prayer(self):
        """Calculate the next prayer time"""
        if not self.prayer_times:
            self.next_prayer = None
            return

        # Get current time in HH:MM format
        current_time = datetime.now().strftime('%H:%M')

        # Find the next prayer time
        for i, prayer_time in enumerate(self.prayer_times):
            if prayer_time > current_time:
                self.next_prayer = {
                    'index': i,
                    'name': self.prayer_names[i],
                    'time': prayer_time
                }
                return

        # If all prayers have passed, the next prayer is Fajr tomorrow
        self.next_prayer = {
            'index': 0,
            'name': self.prayer_names[0],
            'time': self.prayer_times[0]
        }

    def update(self, delta_time):
        """Update prayer times display"""
        # Update timers
        self.last_update += delta_time

        # Get current time
        current_time = datetime.now().strftime('%H:%M')

        # Check if next prayer time has passed
        if self.next_prayer and current_time >= self.next_prayer['time']:
            self.force_update = True

        # Update if forced or interval elapsed
        if self.force_update or self.last_update >= self.update_interval:
            self._update_prayer_times()

    def render(self, canvas):
        """Render the prayer times display"""
        # Clear canvas
        canvas.Clear()

        # Display mosque image if available
        if self.mosque_image and self.config['show_mosque_image']:
            canvas.SetImage(self.mosque_image, 44, 2)

        if self.prayer_times:
            # Display prayer times
            for i in range(5):
                # Highlight the next prayer
                time_color = self.colors['orange'] if self.next_prayer and i == self.next_prayer['index'] else self.colors['white']

                graphics.DrawText(canvas, self.font_small, 5, (i+1)*6, 
                                 self.colors['skyBlue'], self.prayer_names[i])

                graphics.DrawText(canvas, self.font_small, 23, (i+1)*6, 
                                 time_color, self.prayer_times[i])
        else:
            # Display error message if API failed
            graphics.DrawText(canvas, self.font_small, 5, 15, 
                             self.colors['error'], "Prayer API Error")
            graphics.DrawText(canvas, self.font_small, 5, 25, 
                             self.colors['white'], "Retrying...")