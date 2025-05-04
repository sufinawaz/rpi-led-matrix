#!/usr/bin/env python
import requests
import time
import logging
import os

logger = logging.getLogger(__name__)

class APIService:
    """Service for handling API requests with caching"""

    def __init__(self, config_manager):
        """Initialize the API service

        Args:
            config_manager: ConfigManager instance
        """
        self.config = config_manager
        self.cache = {}
        self.cache_expiry = {}

    def get(self, url, params=None, cache_key=None, cache_time=300):
        """Make a GET request with caching

        Args:
            url: URL to request
            params: Query parameters
            cache_key: Cache key, defaults to URL if None
            cache_time: Cache time in seconds

        Returns:
            Response data or None if request failed
        """
        if cache_key is None:
            cache_key = url

        # Check cache
        now = time.time()
        if cache_key in self.cache and self.cache_expiry.get(cache_key, 0) > now:
            logger.debug(f"Using cached response for {cache_key}")
            return self.cache[cache_key]

        # Make request
        try:
            logger.info(f"Making API request to {url}")
            response = requests.get(url, params=params)

            if response.status_code == 200:
                try:
                    data = response.json()

                    # Cache result
                    self.cache[cache_key] = data
                    self.cache_expiry[cache_key] = now + cache_time

                    return data
                except ValueError:
                    logger.error(f"Invalid JSON response from {url}")
                    return None
            else:
                logger.error(f"API request failed: {response.status_code} {response.text}")
                return None

        except Exception as e:
            logger.error(f"API request error: {e}")
            return None

    def clear_cache(self, cache_key=None):
        """Clear cache entries

        Args:
            cache_key: Key to clear, or None to clear all
        """
        if cache_key is None:
            self.cache = {}
            self.cache_expiry = {}
        elif cache_key in self.cache:
            del self.cache[cache_key]
            del self.cache_expiry[cache_key]

class WeatherService:
    """Service for weather data"""

    def __init__(self, api_service):
        """Initialize the weather service

        Args:
            api_service: APIService instance
        """
        self.api = api_service

    def get_current_weather(self, city_id, units="metric"):
        """Get current weather for city

        Args:
            city_id: OpenWeatherMap city ID
            units: Units system ('metric' or 'imperial')

        Returns:
            Weather data or None if request failed
        """
        api_key = self.api.config.get("api_keys", "openweathermap") if self.api.config else os.getenv('WEATHER_APP_ID', '')

        if not api_key:
            logger.warning("No OpenWeatherMap API key configured")
            return None

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "id": city_id,
            "appid": api_key,
            "units": units
        }

        return self.api.get(url, params, f"weather_{city_id}_{units}", 3600)

    def get_forecast(self, city_id, units="metric"):
        """Get weather forecast for city

        Args:
            city_id: OpenWeatherMap city ID
            units: Units system ('metric' or 'imperial')

        Returns:
            Forecast data or None if request failed
        """
        api_key = self.api.config.get("api_keys", "openweathermap") if self.api.config else os.getenv('WEATHER_APP_ID', '')

        if not api_key:
            logger.warning("No OpenWeatherMap API key configured")
            return None

        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "id": city_id,
            "appid": api_key,
            "units": units
        }

        return self.api.get(url, params, f"forecast_{city_id}_{units}", 3600)

class PrayerTimesService:
    """Service for prayer times data"""

    def __init__(self, api_service):
        """Initialize the prayer times service

        Args:
            api_service: APIService instance
        """
        self.api = api_service

    def get_prayer_times(self, latitude, longitude, method=1):
        """Get prayer times for location

        Args:
            latitude: Latitude
            longitude: Longitude
            method: Calculation method (1-7)

        Returns:
            Prayer times data or None if request failed
        """
        url = "http://api.aladhan.com/v1/timings"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "method": method
        }

        # Cache for 24 hours (86400 seconds)
        return self.api.get(url, params, f"prayer_{latitude}_{longitude}_{method}", 86400)