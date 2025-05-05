#!/usr/bin/env python
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
        self.config.setdefault('update_interval', 3600)  # 1 hour by default
        self.config.setdefault('time_period', 'day')
        self.config.setdefault('graph_colors', [
            [0, 255, 0],  # Green
            [0, 191, 255],  # Deep sky blue
            [255, 165, 0]  # Orange
        ])

        # Internal state
        self.last_update = 0
        self.stock_data = {}
        self.stock_error = {}
        self.combined_image = None

        # Font loading
        self.font = graphics.Font()
        self.font_small = graphics.Font()

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
        except Exception as e:
            logger.error(f"Error loading fonts: {e}")

        # Check configuration
        logger.info(f"Stock plugin configuration: {self.config}")

        # Check for API key
        if not self.config.get('api_key'):
            logger.warning("No Finnhub API key configured")
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

    def _get_time_period_params(self):
        """Get the time period parameters for Finnhub API"""
        now = int(time.time())

        if self.config['time_period'] == 'day':
            # One day of data - get 30-minute candles for the last 24 hours - available in free tier
            from_time = now - 24 * 60 * 60
            resolution = '30'  # Changed from 1 to 30 for free tier access
        elif self.config['time_period'] == 'week':
            # One week of data - get daily candles for the last week
            from_time = now - 7 * 24 * 60 * 60
            resolution = 'D'  # Changed from 60 to D for free tier access
        elif self.config['time_period'] == '3month':
            # Three months of data - get daily candles for the last 90 days
            from_time = now - 90 * 24 * 60 * 60
            resolution = 'D'
        else:
            # Default to daily data for one week
            from_time = now - 7 * 24 * 60 * 60
            resolution = 'D'

        return from_time, now, resolution

    def _fetch_stock_data(self):
        """Fetch stock data from Finnhub API"""
        api_key = self.config.get('api_key', '')
        if not api_key:
            logger.error("No API key configured for stock data")
            for symbol in self.config.get('symbols', []):
                if symbol and len(symbol.strip()) > 0:
                    self.stock_error[symbol] = "No API key configured"
            return

        logger.info(f"Using Finnhub API key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")

        # Get time period parameters
        from_time, to_time, resolution = self._get_time_period_params()
        logger.info(f"Using time period: {self.config['time_period']}, resolution: {resolution}")

        # Fetch data for each symbol
        for i, symbol in enumerate(self.config.get('symbols', [])):
            if not symbol or len(symbol.strip()) == 0:
                continue

            # Clean up the symbol - make sure it's properly formatted (uppercase and trim spaces)
            symbol = symbol.strip().upper()

            # Finnhub stock candles API URL
            url = f"https://finnhub.io/api/v1/stock/candle"
            params = {
                'symbol': symbol,
                'resolution': resolution,
                'from': from_time,
                'to': to_time,
                'token': api_key
            }

            logger.info(f"Fetching stock data for {symbol} with resolution {resolution}")

            try:
                # Add timeout and headers for better API behavior
                # headers = {
                #     'User-Agent': 'InfoCube Stock Display/1.0',
                #     'X-Finnhub-Token': api_key
                # }

                response = requests.get(url, params=params, timeout=10)

                # Log response status
                logger.info(f"API response status for {symbol}: {response.status_code}")

                if response.status_code != 200:
                    logger.error(f"API error for {symbol}: HTTP {response.status_code}")
                    self.stock_error[symbol] = f"API error: HTTP {response.status_code}"
                    continue

                data = response.json()

                # Check for error in response
                if data.get('s') == 'no_data':
                    logger.error(f"No data available for {symbol}")
                    self.stock_error[symbol] = "No data available"
                    continue

                if data.get('s') != 'ok':
                    logger.error(f"API Error for {symbol}: {data.get('error', 'Unknown error')}")
                    self.stock_error[symbol] = data.get('error', 'Unknown error')
                    continue

                # Extract close prices
                close_prices = data.get('c', [])

                if not close_prices:
                    logger.error(f"No price data found for {symbol}")
                    self.stock_error[symbol] = "No price data"
                    continue

                # Success - store data
                self.stock_data[symbol] = {
                    'prices': close_prices,
                    'change': close_prices[-1] - close_prices[0] if len(close_prices) > 1 else 0,
                    'current': close_prices[-1]
                }

                logger.info(f"Successfully loaded stock data for {symbol}: current price = {close_prices[-1]}, change = {close_prices[-1] - close_prices[0] if len(close_prices) > 1 else 0}")

                # Clear any previous error
                if symbol in self.stock_error:
                    del self.stock_error[symbol]

            except Exception as e:
                import traceback
                logger.error(f"Error fetching data for {symbol}: {e}")
                logger.error(traceback.format_exc())
                self.stock_error[symbol] = str(e)

        # Create the combined graph after fetching all stock data
        self._create_combined_graph()
        self.last_update = 0

    def _create_combined_graph(self):
        """Create a combined graph image with all stocks"""
        # Create a new image for the complete display
        width = self.matrix.width
        height = self.matrix.height
        image = Image.new('RGB', (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Define section sizes
        # Left side: 12 pixels for stock names and current prices
        # Right side: remaining width for graphs
        left_width = 14
        graph_width = width - left_width
        graph_height = height - 5  # Leave room for period display at top

        # Get all valid stock symbols with data
        valid_symbols = [symbol for symbol in self.config.get('symbols', []) if symbol in self.stock_data]

        if not valid_symbols:
            # No valid stock data available
            self.combined_image = image
            return

        # Find global min/max for all stocks to use consistent scale
        all_prices = []
        for symbol in valid_symbols:
            all_prices.extend(self.stock_data[symbol]['prices'])

        min_price = min(all_prices) if all_prices else 0
        max_price = max(all_prices) if all_prices else 100
        price_range = max_price - min_price

        # Ensure a minimum range to prevent division by zero
        if price_range < 0.01:
            price_range = 0.01

        logger.info(f"Combined graph price range: min={min_price}, max={max_price}, range={price_range}")

        # Draw time period indicator at top right
        period_text = {
            'day': '1D',
            'week': '1W', 
            '3month': '3M'
        }.get(self.config.get('time_period', 'day'), '1D')

        # Draw time period background (dark rectangle)
        draw.rectangle([(width - 10, 0), (width, 5)], fill=(20, 20, 20))

        # Display stock names on the left
        for i, symbol in enumerate(valid_symbols):
            if i >= 3:  # Maximum 3 stocks
                break

            y_pos = 7 + i * 8

            # Get color for this stock
            color_index = min(i, len(self.config.get('graph_colors', [])) - 1)
            graph_colors = self.config.get('graph_colors', [[0, 255, 0], [0, 191, 255], [255, 165, 0]])

            if color_index < len(graph_colors):
                color = tuple(graph_colors[color_index])
            else:
                color = (0, 255, 0)  # Default to green

            # Draw stock symbol
            draw.text((0, y_pos), symbol, fill=color)

            # Draw current price and change indicator below the symbol
            current = self.stock_data[symbol]['current']
            change = self.stock_data[symbol]['change']

            # Format price to fit in small space
            price_text = f"${current:.1f}"

            # Determine change color
            change_color = (0, 255, 0) if change >= 0 else (255, 0, 0)  # Green if positive, red if negative

            # Draw price
            draw.text((0, y_pos + 6), price_text, fill=color)

            # Draw small up/down indicator (using ASCII instead of Unicode)
            arrow = "+" if change >= 0 else "-"
            draw.text((left_width - 5, y_pos + 6), arrow, fill=change_color)

            # Draw graph line
            prices = self.stock_data[symbol]['prices']

            if prices and len(prices) > 1:
                points = []
                for j, price in enumerate(prices):
                    # Scale x position across the graph width
                    x = left_width + (j * graph_width / (len(prices) - 1))

                    # Scale y position to fit graph height (reverse Y axis)
                    y = 5 + (graph_height - ((price - min_price) / price_range * graph_height))

                    points.append((x, y))

                # Draw the line
                if len(points) > 1:
                    draw.line(points, fill=color, width=1)

        # Draw time period indicator (last to overlay)
        draw.text((width - 10, 0), period_text, fill=(150, 150, 150))

        # Store the final image
        self.combined_image = image

    def update(self, delta_time):
        """Update stock ticker display"""
        # Update timers
        self.last_update += delta_time

        # Update stock data based on interval
        if self.last_update >= self.config['update_interval']:
            self._fetch_stock_data()

    def render(self, canvas):
        """Render the stock ticker display"""
        # Clear canvas
        canvas.Clear()

        # Check if we have a combined image to display
        if self.combined_image:
            # Set the image on the canvas
            canvas.SetImage(self.combined_image)
            return

        # If no combined image (meaning no valid stock data), display error message
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
            return