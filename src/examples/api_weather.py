#!/usr/bin/env python
import sys
import os
import time
import requests
import json
from PIL import Image, ImageDraw, ImageFont

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.matrix_manager import MatrixManager
from src.text_renderer import TextRenderer
from src.animations.scroll_text import ScrollText

# OpenWeatherMap API key - replace with your own
API_KEY = "YOUR_API_KEY_HERE"
CITY = "YOUR_CITY_HERE"

def get_weather():
    """Fetch weather data from OpenWeatherMap API"""
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"

    try:
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            # Extract relevant information
            weather = {
                'temp': data['main']['temp'],
                'description': data['weather'][0]['description'],
                'humidity': data['main']['humidity'],
                'wind_speed': data['wind']['speed'],
                'city': data['name']
            }
            return weather
        else:
            print(f"Error fetching weather: {data.get('message', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def main():
    # Initialize the matrix
    matrix = MatrixManager(
        rows=32,
        cols=32,
        chain_length=1,
        brightness=50,
        hardware_mapping="adafruit-hat"
    )

    # Create a text renderer
    text = TextRenderer(matrix)

    try:
        while True:
            # Fetch weather data
            weather = get_weather()

            if weather:
                # Display city name
                text.draw_centered_text(
                    f"{weather['city']}",
                    color=(64, 224, 208)  # Turquoise
                )
                time.sleep(2)

                # Display temperature
                text.draw_centered_text(
                    f"{weather['temp']:.1f}°C",
                    color=(255, 255, 0)  # Yellow
                )
                time.sleep(2)

                # Scroll weather description
                scroll = ScrollText(
                    matrix,
                    text=f"{weather['description']} - Humidity: {weather['humidity']}% - Wind: {weather['wind_speed']} m/s",
                    color=(135, 206, 235),  # Sky blue
                    scroll_speed=15
                )

                # Run for 20 seconds then update weather
                scroll.start(run_time=20)
            else:
                # Display error message
                text.draw_centered_text(
                    "API Error",
                    color=(255, 0, 0)  # Red
                )
                time.sleep(5)

    except KeyboardInterrupt:
        # Clear the display when done
        matrix.clear()
        matrix.swap()
        sys.exit(0)

if __name__ == "__main__":
    main()