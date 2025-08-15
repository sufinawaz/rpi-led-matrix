#!/usr/bin/env python
"""
Fixed stock plugin for 32x64 LED matrix display
"""

import time
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
    """Plugin for displaying stock ticker information with visual graph"""

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "stock"
        self.description = "Stock ticker display with visual graph"

        # Default configuration
        self.config.setdefault('symbols', ['AAPL', 'MSFT', 'AMZN'])
        self.config.setdefault('api_key', '')
        self.config.setdefault('update_interval', 900)  # 15 minutes by default
        self.config.setdefault('rotation_interval', 4)  # 4 seconds per stock

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
            'light_green': graphics.Color(180, 255, 180),
            'red': graphics.Color(255, 0, 0),
            'light_red': graphics.Color(255, 180, 180),
            'blue': graphics.Color(0, 191, 255),
            'orange': graphics.Color(255, 165, 0),
            'yellow': graphics.Color(255, 255, 0),
            'grey': graphics.Color(150, 150, 150),
            'dark_grey': graphics.Color(50, 50, 50),
            'error': graphics.Color(255, 0, 0)
        }

    def setup(self):
        """Set up the stock plugin"""
        # Load fonts
        try:
            self.font_small.LoadFont("resources/fonts/4x6.bdf")
            self.font.LoadFont("resources/fonts/7x13.bdf")  # Fall back to standard font

            try:
                self.font_large.LoadFont("resources/fonts/9x18.bdf")
            except (IOError, OSError, RuntimeError):
                logger.warning("9x18 font not available, using standard font instead")
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

            # Using the quote endpoint which is available in the free tier
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
                    logger.error(f"Response content: {response.text[:200]}")
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

                # Create data points for the graph
                num_points = 40  # More points for a smoother graph
                prices = []

                # Use open/high/low/close to create a coherent price series
                if open_price > 0 and high > 0 and low > 0 and current_price > 0:
                    # Generate a smooth price curve from open to close with reasonable variations
                    prices = [open_price]

                    # Divide the day into segments
                    for i in range(1, num_points-1):
                        # Linear interpolation with some variation
                        t = i / (num_points - 1)

                        # Base price (straight line from open to close)
                        base_price = open_price + (current_price - open_price) * t

                        # Add slight variation to make the line more interesting
                        # Early in the day, tend toward low; middle of the day, tend toward high
                        if t < 0.3:  # First third of the day
                            target = base_price + (low - base_price) * 0.3
                        elif t < 0.7:  # Middle of the day
                            target = base_price + (high - base_price) * 0.3
                        else:  # Last third of the day
                            # Move toward closing price
                            target = base_price

                        prices.append(target)

                    # Make sure the last price is the current price
                    prices.append(current_price)
                else:
                    # Fallback with placeholder data
                    prices = [previous_close] * 5 + [current_price] * 5

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

    def _draw_pixel_text(self, draw, text, x, y, color, scaled=False):
        """Draw text using LED-style pixel patterns"""
        # Get the clean text (remove any formatting)
        clean_text = text.replace('$', '')

        # Configuration
        dot_size = 2 if scaled else 1
        dot_gap = 1 * dot_size
        digit_width = 3 * dot_size
        digit_height = 5 * dot_size

        # Define 3x5 dot patterns for characters
        patterns = {
            '0': [(0,0), (1,0), (2,0), (0,1), (2,1), (0,2), (2,2), (0,3), (2,3), (0,4), (1,4), (2,4)],
            '1': [(1,0), (1,1), (1,2), (1,3), (1,4)],
            '2': [(0,0), (1,0), (2,0), (2,1), (0,2), (1,2), (2,2), (0,3), (0,4), (1,4), (2,4)],
            '3': [(0,0), (1,0), (2,0), (2,1), (0,2), (1,2), (2,2), (2,3), (0,4), (1,4), (2,4)],
            '4': [(0,0), (2,0), (0,1), (2,1), (0,2), (1,2), (2,2), (2,3), (2,4)],
            '5': [(0,0), (1,0), (2,0), (0,1), (0,2), (1,2), (2,2), (2,3), (0,4), (1,4), (2,4)],
            '6': [(0,0), (1,0), (2,0), (0,1), (0,2), (1,2), (2,2), (0,3), (2,3), (0,4), (1,4), (2,4)],
            '7': [(0,0), (1,0), (2,0), (2,1), (1,2), (1,3), (1,4)],
            '8': [(0,0), (1,0), (2,0), (0,1), (2,1), (0,2), (1,2), (2,2), (0,3), (2,3), (0,4), (1,4), (2,4)],
            '9': [(0,0), (1,0), (2,0), (0,1), (2,1), (0,2), (1,2), (2,2), (2,3), (0,4), (1,4), (2,4)],
            '.': [(1,4)],
            ',': [(1,3), (0,4)],
            '+': [(1,1), (0,2), (1,2), (2,2), (1,3)],
            '-': [(0,2), (1,2), (2,2)],
            '%': [(0,0), (2,0), (2,1), (1,2), (0,3), (0,4), (2,4)],
            ' ': []
        }

        # Add letter patterns for stock symbols
        patterns.update({
            'A': [(0,0), (1,0), (2,0), (0,1), (2,1), (0,2), (1,2), (2,2), (0,3), (2,3), (0,4), (2,4)],
            'B': [(0,0), (1,0), (0,1), (2,1), (0,2), (1,2), (0,3), (2,3), (0,4), (1,4)],
            'C': [(0,0), (1,0), (2,0), (0,1), (0,2), (0,3), (0,4), (1,4), (2,4)],
            'D': [(0,0), (1,0), (0,1), (2,1), (0,2), (2,2), (0,3), (2,3), (0,4), (1,4)],
            'E': [(0,0), (1,0), (2,0), (0,1), (0,2), (1,2), (0,3), (0,4), (1,4), (2,4)],
            'F': [(0,0), (1,0), (2,0), (0,1), (0,2), (1,2), (0,3), (0,4)],
            'G': [(0,0), (1,0), (2,0), (0,1), (0,2), (1,2), (2,2), (0,3), (2,3), (0,4), (1,4), (2,4)],
            'H': [(0,0), (2,0), (0,1), (2,1), (0,2), (1,2), (2,2), (0,3), (2,3), (0,4), (2,4)],
            'I': [(0,0), (1,0), (2,0), (1,1), (1,2), (1,3), (0,4), (1,4), (2,4)],
            'J': [(2,0), (2,1), (2,2), (0,3), (2,3), (0,4), (1,4), (2,4)],
            'K': [(0,0), (2,0), (0,1), (2,1), (0,2), (1,2), (0,3), (2,3), (0,4), (2,4)],
            'L': [(0,0), (0,1), (0,2), (0,3), (0,4), (1,4), (2,4)],
            'M': [(0,0), (2,0), (0,1), (1,1), (2,1), (0,2), (2,2), (0,3), (2,3), (0,4), (2,4)],
            'N': [(0,0), (2,0), (0,1), (1,1), (2,1), (0,2), (2,2), (0,3), (2,3), (0,4), (2,4)],
            'O': [(0,0), (1,0), (2,0), (0,1), (2,1), (0,2), (2,2), (0,3), (2,3), (0,4), (1,4), (2,4)],
            'P': [(0,0), (1,0), (2,0), (0,1), (2,1), (0,2), (1,2), (2,2), (0,3), (0,4)],
            'Q': [(0,0), (1,0), (2,0), (0,1), (2,1), (0,2), (2,2), (0,3), (1,3), (2,3), (1,4), (2,4)],
            'R': [(0,0), (1,0), (2,0), (0,1), (2,1), (0,2), (1,2), (0,3), (2,3), (0,4), (2,4)],
            'S': [(0,0), (1,0), (2,0), (0,1), (0,2), (1,2), (2,2), (2,3), (0,4), (1,4), (2,4)],
            'T': [(0,0), (1,0), (2,0), (1,1), (1,2), (1,3), (1,4)],
            'U': [(0,0), (2,0), (0,1), (2,1), (0,2), (2,2), (0,3), (2,3), (0,4), (1,4), (2,4)],
            'V': [(0,0), (2,0), (0,1), (2,1), (0,2), (2,2), (0,3), (2,3), (1,4)],
            'W': [(0,0), (2,0), (0,1), (2,1), (0,2), (2,2), (0,3), (1,3), (2,3), (0,4), (2,4)],
            'X': [(0,0), (2,0), (0,1), (2,1), (1,2), (0,3), (2,3), (0,4), (2,4)],
            'Y': [(0,0), (2,0), (0,1), (2,1), (1,2), (1,3), (1,4)],
            'Z': [(0,0), (1,0), (2,0), (2,1), (1,2), (0,3), (0,4), (1,4), (2,4)]
        })

        # Position tracking
        cursor_x = x

        # Draw each character
        for char in clean_text:
            char = char.upper()  # Convert to uppercase
            pattern = patterns.get(char, [])

            # Draw the dots for this character
            for dx, dy in pattern:
                px = cursor_x + dx * dot_size
                py = y + dy * dot_size

                # Draw a square for each dot
                if dot_size == 1:
                    # Single pixel
                    draw.point((px, py), fill=color)
                else:
                    # Larger dot
                    draw.rectangle(
                        [(px, py), (px + dot_size - 1, py + dot_size - 1)],
                        fill=color
                    )

            # Move cursor to next character position
            cursor_x += digit_width + dot_gap

        # Return the width of the text
        return cursor_x - x

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

            # Determine colors based on price change
            price_change = stock_data['change']
            positive_change = price_change >= 0

            # Set colors based on whether change is positive or negative
            primary_color = (0, 255, 0) if positive_change else (255, 0, 0)  # Green if up, red if down

            # Layout parameters
            # Left section: Symbol, price, percent
            # Right section: Graph
            left_section_width = 31  # Seems to match what's in your image
            right_section_width = width - left_section_width - 2

            # Fill left section with dark gray background
            for y in range(height):
                for x in range(left_section_width):
                    draw.point((x, y), fill=(5, 5, 5))  # Dark gray

            # Draw divider line (blue like in your image)
            divider_color = (20, 20, 20)  # Light blue
            for y in range(height):
                draw.point((left_section_width, y), fill=divider_color)

            # 1. Draw stock symbol in the top left
            # Scale up the text for better readability
            self._draw_pixel_text(draw, symbol, 0, 0, (255, 255, 255), scaled=True)

            # 2. Draw price with scaled-up text
            price = stock_data['current']
            price_text = f"{price:.1f}"
            if price < 10:
                price_text = f"{price:.2f}"
            elif price >= 100:
                price_text = f"{int(price)}"

            self._draw_pixel_text(draw, price_text, 0, 11, primary_color, scaled=True)

            # 3. Draw percent change
            percent_change = stock_data['percent_change']
            percent_text = f"{'+' if percent_change >= 0 else ''}{percent_change:.1f}%"
            self._draw_pixel_text(draw, percent_text, 0, 22, primary_color, scaled=False)

            # 4. Draw the graph on the right side
            graph_x_start = left_section_width + 1
            graph_width = right_section_width - 1

            # Get price data
            prices = stock_data['prices']
            if len(prices) > 1:
                # Find min/max for proper scaling
                min_price = min(prices)
                max_price = max(prices)

                # Add buffer to avoid graph touching the edges
                price_range = max_price - min_price
                if price_range < 0.01:
                    price_range = 0.01

                buffer = price_range * 0.1
                min_price -= buffer
                max_price += buffer
                price_range = max_price - min_price

                # Calculate points for the line graph with more granularity
                points = []
                num_points = min(len(prices), 40)  # Use more points for smoother curve

                for i in range(num_points):
                    # Get price at this position
                    idx = min(i * len(prices) // num_points, len(prices) - 1)
                    price = prices[idx]

                    # Calculate x position
                    x = graph_x_start + int(i * graph_width / (num_points - 1))

                    # Calculate y position (invert y axis)
                    normalized = (price - min_price) / price_range
                    y = height - int(normalized * height)

                    # Ensure y is within bounds
                    y = max(1, min(height - 1, y))

                    points.append((x, y))

                # Draw individual points first (for the traced line effect)
                for x, y in points:
                    draw.point((x, y), fill=primary_color)

                # Then draw line segments
                for i in range(len(points) - 1):
                    draw.line([points[i], points[i+1]], fill=primary_color, width=1)

            # Store the completed image
            self.stock_images[symbol] = image

        # Reset current stock index if needed
        if self.valid_symbols and self.current_stock_idx >= len(self.valid_symbols):
            self.current_stock_idx = 0

    def update(self, delta_time):
        """Update stock ticker display"""
        # Update timers
        self.last_update += delta_time
        self.last_rotation += delta_time

        # Update stock data based on interval
        if self.last_update >= self.config['update_interval']:
            self._fetch_stock_data()
            self.last_rotation = 0  # Reset rotation timer after refresh
            return

        # Rotate stocks every few seconds
        if self.last_rotation >= self.config['rotation_interval'] and len(self.valid_symbols) > 1:
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
                    graphics.DrawText(canvas, self.font, 2, 20, color, price_text)
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