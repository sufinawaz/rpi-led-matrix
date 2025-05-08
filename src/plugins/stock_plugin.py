#!/usr/bin/env python
"""
Enhanced stock plugin with rotating single-stock display and improved visuals
"""

import time
from datetime import datetime, timedelta
import os
import json
import requests
import logging
from PIL import Image, ImageDraw
from rgbmatrix import graphics

from .base_plugin import DisplayPlugin

# Set up logging
logger = logging.getLogger(__name__)

class StockPlugin(DisplayPlugin):
    """Plugin for displaying stock ticker information

    Configuration options:
        symbols (list): List of stock symbols to display
        api_key (str): API key for Finnhub
        update_interval (int): How often to update stock data in seconds
        rotation_interval (int): How long to display each stock in seconds
        time_period (str): Time period to display ('day', 'week', '3month')
        graph_colors (list): RGB color tuples for each stock graph
    """

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "stock"
        self.description = "Stock ticker display"

        # Default configuration
        self.config.setdefault('symbols', ['AAPL', 'MSFT', 'AMZN'])
        self.config.setdefault('api_key', '')
        self.config.setdefault('update_interval', 900)  # 15 minutes by default
        self.config.setdefault('rotation_interval', 2)  # 2 seconds per stock
        self.config.setdefault('time_period', 'day')
        self.config.setdefault('graph_colors', [
            [0, 255, 0],  # Green
            [0, 191, 255],  # Deep sky blue
            [255, 165, 0]  # Orange
        ])

        # Internal state
        self.last_update = 0
        self.last_rotation = 0
        self.stock_data = {}
        self.stock_error = {}
        self.stock_images = {}
        self.current_stock_idx = 0
        self.valid_symbols = []

        # Font loading
        self.font = graphics.Font()
        self.font_small = graphics.Font()
        self.font_large = graphics.Font()

        # Colors
        self.colors = {
            'white': graphics.Color(255, 255, 255),
            'green': graphics.Color(0, 255, 0),
            'red': graphics.Color(255, 0, 0),
            'blue': graphics.Color(0, 191, 255),
            'orange': graphics.Color(255, 165, 0),
            'yellow': graphics.Color(255, 255, 0),
            'grey': graphics.Color(150, 150, 150),
            'error': graphics.Color(255, 0, 0)
        }

    def setup(self):
        """Set up the stock plugin"""
        # Load fonts
        try:
            self.font_small.LoadFont("resources/fonts/4x6.bdf")
            self.font.LoadFont("resources/fonts/7x13.bdf")
            # Try to load a larger font for the stock symbol and price
            try:
                self.font_large.LoadFont("resources/fonts/9x18.bdf")
            except:
                logger.warning("9x18 font not available, using 7x13 instead")
                self.font_large = self.font
        except Exception as e:
            logger.error(f"Error loading fonts: {e}")

        # Check configuration
        logger.info(f"Stock plugin configuration: {self.config}")

        # Check for API key
        if not self.config.get('api_key'):
            logger.warning("No Finnhub API key configured in plugin settings")
            # Try to get API key from config file
            try:
                config_path = os.path.join(os.path.dirname(__file__), '../../config.json')
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config_data = json.load(f)
                        api_key = config_data.get('api_keys', {}).get('finnhub', '')
                        if api_key:
                            logger.info("Found Finnhub API key in config.json")
                            self.config['api_key'] = api_key
                        else:
                            logger.warning("No Finnhub API key found in config.json")
            except Exception as e:
                logger.error(f"Error reading config.json: {e}")

        # Initial data fetch
        self._fetch_stock_data()

    def _get_api_key(self):
        """Get the API key, checking multiple possible locations"""
        # First, check the plugin config
        api_key = self.config.get('api_key', '')
        if api_key:
            return api_key

        # If not found, try the main config file
        try:
            config_path = os.path.join(os.path.dirname(__file__), '../../config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    api_key = config_data.get('api_keys', {}).get('finnhub', '')
                    if api_key:
                        # Save it to the plugin config for future use
                        self.config['api_key'] = api_key
                        return api_key
        except Exception as e:
            logger.error(f"Error reading config.json for API key: {e}")

        return ''

    def _get_time_period_params(self):
        """Get the time period parameters for Finnhub API"""
        now = int(time.time())

        if self.config['time_period'] == 'day':
            # One day of data
            from_time = now - 7 * 24 * 60 * 60
            resolution = 'D'
        elif self.config['time_period'] == 'week':
            # One week of data
            from_time = now - 7 * 24 * 60 * 60
            resolution = 'D'
        elif self.config['time_period'] == '3month':
            # Three months of data
            from_time = now - 90 * 24 * 60 * 60
            resolution = 'D'
        else:
            # Default to daily data for one week
            from_time = now - 7 * 24 * 60 * 60
            resolution = 'D'

        return from_time, now, resolution

    def _fetch_stock_data(self):
        """Fetch stock data from Finnhub API using the quote endpoint for free tier"""
        api_key = self._get_api_key()
        if not api_key:
            logger.error("No API key configured for stock data")
            for symbol in self.config.get('symbols', []):
                if symbol and len(symbol.strip()) > 0:
                    self.stock_error[symbol] = "No API key configured"
            return

        logger.info(f"Using Finnhub API key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")

        # Reset valid symbols list
        self.valid_symbols = []

        # Fetch data for each symbol
        for i, symbol in enumerate(self.config.get('symbols', [])):
            if not symbol or len(symbol.strip()) == 0:
                continue

            # Clean up the symbol - make sure it's properly formatted (uppercase and trim spaces)
            symbol = symbol.strip().upper()

            # FIXED: Using the quote endpoint which is available in the free tier
            url = "https://finnhub.io/api/v1/quote"
            params = {
                'symbol': symbol,
                'token': api_key
            }

            logger.info(f"Fetching stock data for {symbol} using quote endpoint")

            try:
                # Add timeout and headers for better API behavior
                headers = {
                    'User-Agent': 'InfoCube Stock Display/1.0'
                }

                response = requests.get(
                    url, 
                    params=params, 
                    headers=headers,
                    timeout=10
                )

                # Log response status
                logger.info(f"API response status for {symbol}: {response.status_code}")

                # Log response details if error occurs
                if response.status_code != 200:
                    logger.error(f"API error for {symbol}: HTTP {response.status_code}")
                    logger.error(f"Response content: {response.text[:200]}")  # Log first 200 chars
                    self.stock_error[symbol] = f"API error: HTTP {response.status_code}"
                    continue

                data = response.json()

                # Extract needed data from quote endpoint
                current_price = data.get('c', 0)
                previous_close = data.get('pc', 0)
                high = data.get('h', current_price)
                low = data.get('l', current_price)
                open_price = data.get('o', previous_close)

                # Calculate change
                price_change = current_price - previous_close
                percent_change = (price_change / previous_close * 100) if previous_close > 0 else 0

                # Create more data points for a smoother graph
                # We'll create a simple approximation by interpolating between open and close
                num_points = 10
                prices = []

                # Start with previous close
                prices.append(previous_close)

                # Interpolate between open and current price
                for j in range(1, num_points-1):
                    t = j / (num_points-1)
                    # Add some variation to make the graph look more interesting
                    # by using high and low as control points
                    if j < num_points/2:
                        # First half: interpolate between open and high/low
                        prices.append(open_price + (high - open_price) * t * 2)
                    else:
                        # Second half: interpolate between high/low and close
                        prices.append(high + (current_price - high) * (t*2-1))

                # End with current price
                prices.append(current_price)

                if current_price == 0:
                    logger.error(f"No price data found for {symbol}")
                    self.stock_error[symbol] = "No price data"
                    continue

                # Success - store data
                self.stock_data[symbol] = {
                    'prices': prices,
                    'change': price_change,
                    'percent_change': percent_change,
                    'current': current_price,
                    'high': high,
                    'low': low,
                    'open': open_price,
                    'previous_close': previous_close
                }

                # Add to valid symbols list
                self.valid_symbols.append(symbol)

                logger.info(f"Successfully loaded stock data for {symbol}: current price = {current_price}, previous close = {previous_close}, change = {price_change}")

                # Clear any previous error
                if symbol in self.stock_error:
                    del self.stock_error[symbol]

                # Add a small delay between requests to avoid rate limiting
                time.sleep(0.5)

            except Exception as e:
                import traceback
                logger.error(f"Error fetching data for {symbol}: {e}")
                logger.error(traceback.format_exc())
                self.stock_error[symbol] = str(e)

        # Create individual stock images after fetching all stock data
        self._create_stock_images()
        self.last_update = 0

    def _create_stock_images(self):
        """Create individual image for each stock"""
        width = self.matrix.width
        height = self.matrix.height

        # Clear the current stock images dict
        self.stock_images = {}

        # Create an image for each valid stock
        for symbol in self.valid_symbols:
            # Create a new image
            image = Image.new('RGB', (width, height), (0, 0, 0))
            draw = ImageDraw.Draw(image)

            stock_data = self.stock_data[symbol]

            # Get color based on whether the stock is up or down
            change = stock_data['change']
            color = (0, 255, 0) if change >= 0 else (255, 0, 0)  # Green if positive, red if negative

            # Draw stock symbol in upper left (large font)
            draw.text((2, 0), symbol, fill=(255, 255, 255), font=None)  # None font will be handled by PIL

            # Format price and change
            current_price = stock_data['current']
            price_text = f"${current_price:.2f}"

            # Draw price in upper right
            price_width = len(price_text) * 9  # Approximate width with large font
            draw.text((width - price_width - 2, 0), price_text, fill=color, font=None)

            # Draw percent change below the price
            percent_change = stock_data['percent_change']
            change_text = f"{'+' if percent_change >= 0 else ''}{percent_change:.2f}%"
            change_width = len(change_text) * 5  # Approximate width with small font
            draw.text((width - change_width - 2, 12), change_text, fill=color, font=None)

            # Draw graph taking up the lower part of the screen
            graph_y_start = 18  # Start below the text
            graph_height = height - graph_y_start

            prices = stock_data['prices']

            if prices and len(prices) > 1:
                # Find min and max for scaling
                min_price = min(prices)
                max_price = max(prices)
                price_range = max_price - min_price

                # Ensure a minimum range to prevent division by zero
                if price_range < 0.01:
                    price_range = 0.01

                # Draw the graph line
                points = []
                for j, price in enumerate(prices):
                    # Scale x position across the width
                    x = int(j * width / (len(prices) - 1))

                    # Scale y position to fit graph height (reverse Y axis)
                    y = graph_y_start + int(graph_height - ((price - min_price) / price_range * graph_height))

                    points.append((x, y))

                # Draw the line with appropriate color
                draw.line(points, fill=color, width=2)

                # Draw price markers
                for k in range(1, 10, 2):
                    mark_price = min_price + (k / 10) * price_range
                    mark_y = graph_y_start + int(graph_height - ((mark_price - min_price) / price_range * graph_height))
                    draw.line([(0, mark_y), (width, mark_y)], fill=(20, 20, 30), width=1)

            # Store the image
            self.stock_images[symbol] = image

        # Reset current stock index if needed
        if self.valid_symbols and self.current_stock_idx >= len(self.valid_symbols):
            self.current_stock_idx = 0

    def update(self, delta_time):
        """Update stock ticker display"""
        # Update timers
        self.last_update += delta_time
        self.last_rotation += delta_time

        # Update stock data based on interval (15 minutes)
        if self.last_update >= self.config['update_interval']:
            self._fetch_stock_data()
            self.last_rotation = 0  # Reset rotation timer after refresh
            return

        # Rotate stocks every X seconds (default 2 seconds)
        if self.last_rotation >= self.config['rotation_interval'] and self.valid_symbols:
            self.last_rotation = 0
            self.current_stock_idx = (self.current_stock_idx + 1) % len(self.valid_symbols)

    def render(self, canvas):
        """Render the stock ticker display"""
        # Clear canvas
        canvas.Clear()

        # If we have valid stocks, show the current one
        if self.valid_symbols:
            current_symbol = self.valid_symbols[self.current_stock_idx]

            if current_symbol in self.stock_images:
                # Display the pre-rendered image for this stock
                canvas.SetImage(self.stock_images[current_symbol])
                return
            else:
                # Fallback if image not found - should not happen
                graphics.DrawText(canvas, self.font, 2, 10, 
                                self.colors['white'], current_symbol)

                stock_data = self.stock_data.get(current_symbol, {})
                if 'current' in stock_data:
                    price_text = f"${stock_data['current']:.2f}"
                    color = self.colors['green'] if stock_data.get('change', 0) >= 0 else self.colors['red']
                    graphics.DrawText(canvas, self.font, 2, 24, color, price_text)
                return

        # No valid stocks - show error message
        valid_symbols = self.config.get('symbols', [])
        valid_symbols = [s for s in valid_symbols if s and len(s.strip()) > 0]

        if not valid_symbols:
            # No stock symbols configured
            graphics.DrawText(canvas, self.font, 2, 16, 
                             self.colors['error'], "No stocks")
            graphics.DrawText(canvas, self.font_small, 2, 25, 
                             self.colors['white'], "Add in settings")
            return

        # Check for errors
        has_errors = any(symbol in self.stock_error for symbol in valid_symbols)

        if has_errors:
            # Display error message
            graphics.DrawText(canvas, self.font, 2, 12, 
                             self.colors['error'], "Stock API")
            graphics.DrawText(canvas, self.font, 2, 25, 
                             self.colors['error'], "Error")

            # Display the specific error for debugging
            first_error = next((self.stock_error[symbol] for symbol in valid_symbols if symbol in self.stock_error), "Unknown")
            if len(first_error) > 20:
                first_error = first_error[:17] + "..."
            graphics.DrawText(canvas, self.font_small, 2, 31, 
                            self.colors['white'], first_error)
            return