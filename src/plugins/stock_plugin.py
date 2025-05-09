#!/usr/bin/env python
"""
Redesigned stock plugin for 32x64 LED matrix display
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
    """Plugin for displaying stock ticker information with visual graph
    
    Shows stock symbol, current price, change percentage, and a graph
    with gradient fill in a clean, easy-to-read layout.
    """

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
            self.font.LoadFont("resources/fonts/6x10.bdf")  # Try to load medium font first
            if not self.font.height():  # If medium font loading failed
                self.font.LoadFont("resources/fonts/7x13.bdf")  # Fall back to standard font
            
            try:
                self.font_large.LoadFont("resources/fonts/9x18.bdf")
            except:
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

                # Create data points for the graph - generate a reasonable price sequence
                # We want to simulate a day's worth of trading data
                num_points = 24  # One point per hour
                prices = []

                # Use open/high/low/close to create a coherent price series
                if open_price > 0 and high > 0 and low > 0 and current_price > 0:
                    # Start with open price
                    prices.append(open_price)
                    
                    # Add some intermediate points with randomization based on high/low
                    mid_point = num_points // 2
                    
                    for j in range(1, num_points):
                        if j < mid_point:
                            # First half: move toward high or low
                            if j % 2 == 0:
                                # Move toward high
                                t = j / mid_point  # 0 to 1
                                price = open_price + (high - open_price) * t * 0.8
                            else:
                                # Move toward low
                                t = j / mid_point  # 0 to 1
                                price = open_price + (low - open_price) * t * 0.8
                        else:
                            # Second half: move toward close
                            t = (j - mid_point) / (num_points - mid_point)  # 0 to 1
                            
                            # Target is previous price point + slope toward close
                            prev_price = prices[-1]
                            target = prev_price + (current_price - prev_price) * t
                            
                            # Add small random fluctuation
                            price = target
                        
                        prices.append(price)
                    
                    # End with current price
                    if prices[-1] != current_price:
                        prices.append(current_price)
                else:
                    # Fallback with just placeholder data
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

    def _create_dot_number(self, draw, number, x, y, color, size=1):
        """
        Draw a number using dot matrix style similar to LED display
        
        Args:
            draw: PIL ImageDraw object
            number: Number to draw (can be a string or number)
            x: X position
            y: Y position
            color: RGB color tuple
            size: Size multiplier for dots
        """
        # Convert to string
        number = str(number)
        
        # Patterns for digits 0-9 and decimal point in 3x5 dot matrix
        patterns = {
            '0': [(0,0), (1,0), (2,0), (0,1), (2,1), (0,2), (2,2), (0,3), (2,3), (0,4), (1,4), (2,4)],
            '1': [(1,0), (0,1), (1,1), (1,2), (1,3), (0,4), (1,4), (2,4)],
            '2': [(0,0), (1,0), (2,0), (2,1), (0,2), (1,2), (2,2), (0,3), (0,4), (1,4), (2,4)],
            '3': [(0,0), (1,0), (2,0), (2,1), (0,2), (1,2), (2,2), (2,3), (0,4), (1,4), (2,4)],
            '4': [(0,0), (2,0), (0,1), (2,1), (0,2), (1,2), (2,2), (2,3), (2,4)],
            '5': [(0,0), (1,0), (2,0), (0,1), (0,2), (1,2), (2,2), (2,3), (0,4), (1,4), (2,4)],
            '6': [(0,0), (1,0), (2,0), (0,1), (0,2), (1,2), (2,2), (0,3), (2,3), (0,4), (1,4), (2,4)],
            '7': [(0,0), (1,0), (2,0), (2,1), (1,2), (1,3), (1,4)],
            '8': [(0,0), (1,0), (2,0), (0,1), (2,1), (0,2), (1,2), (2,2), (0,3), (2,3), (0,4), (1,4), (2,4)],
            '9': [(0,0), (1,0), (2,0), (0,1), (2,1), (0,2), (1,2), (2,2), (2,3), (0,4), (1,4), (2,4)],
            '.': [(1,4)],
            '+': [(1,1), (0,2), (1,2), (2,2), (1,3)],
            '-': [(0,2), (1,2), (2,2)],
            '%': [(0,0), (2,0), (2,1), (1,2), (0,3), (0,4), (2,4)],
            ' ': []
        }
        
        # Spacing between characters (in addition to character width)
        char_spacing = 1
        
        # Draw each character
        pos_x = x
        for char in number:
            # Get pattern for this character
            char_pattern = patterns.get(char, patterns[' '])
            
            # Draw the pattern
            for dx, dy in char_pattern:
                # Calculate the actual pixel position
                pixel_x = pos_x + dx * size
                pixel_y = y + dy * size
                
                # Draw a dot of the specified size
                if size == 1:
                    draw.point((pixel_x, pixel_y), fill=color)
                else:
                    draw.rectangle(
                        [(pixel_x, pixel_y), (pixel_x + size - 1, pixel_y + size - 1)],
                        fill=color
                    )
            
            # Move to the next character position (3 + spacing dots wide)
            pos_x += (3 + char_spacing) * size
        
        # Return the width of the drawn text
        return pos_x - x - char_spacing * size  # Subtract the trailing space

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
            percent_change = stock_data['percent_change']
            positive_change = price_change >= 0
            
            # Set colors based on whether change is positive or negative
            primary_color = (0, 255, 0) if positive_change else (255, 0, 0)  # Green if up, red if down
            light_color = (100, 255, 100) if positive_change else (255, 100, 100)  # Lighter version for gradient
            
            # Layout parameters
            # Left section (20-22 columns): Symbol, price, percent
            # Right section (42-44 columns): Graph
            
            info_section_width = 22
            graph_section_width = width - info_section_width
            
            # Draw a subtle vertical divider
            draw.line([(info_section_width, 0), (info_section_width, height)], fill=(20, 20, 20), width=1)
            
            # 1. DRAW STOCK SYMBOL at the top of the info section
            # Use regular text drawing for the symbol (big clear text)
            symbol_pos_y = 2
            symbol_text = symbol
            # Use a 2x2 dot matrix for larger symbols
            self._create_dot_number(draw, symbol_text, 2, symbol_pos_y, (255, 255, 255), size=2)
            
            # 2. DRAW CURRENT PRICE below the symbol
            price_pos_y = 12
            current_price = stock_data['current']
            
            # Format price with appropriate precision
            if current_price < 10:
                price_text = f"{current_price:.2f}"
            elif current_price < 100:
                price_text = f"{current_price:.1f}"
            else:
                price_text = f"{int(current_price)}"
                
            # Draw price with 2x2 dot matrix for better visibility
            self._create_dot_number(draw, price_text, 2, price_pos_y, primary_color, size=2)
            
            # 3. DRAW PERCENTAGE CHANGE at the bottom of info section
            percent_pos_y = 22
            percent_str = f"{'+' if percent_change >= 0 else ''}{percent_change:.1f}%"
            
            # Draw percentage with 1x1 dot matrix (smaller)
            self._create_dot_number(draw, percent_str, 2, percent_pos_y, primary_color, size=1)
            
            # 4. DRAW THE GRAPH in the right section
            graph_x_start = info_section_width + 1
            graph_y_start = 0
            graph_width = graph_section_width - 1
            graph_height = height
            
            # Get price data for graphing
            prices = stock_data['prices']
            
            if len(prices) > 1:
                # Find min/max for scaling
                min_price = min(prices)
                max_price = max(prices)
                price_range = max_price - min_price
                
                # Ensure minimum range
                if price_range < 0.01:
                    price_range = 0.01
                
                # Add buffer to avoid edges
                buffer = price_range * 0.05
                min_price = min_price - buffer
                max_price = max_price + buffer
                price_range = max_price - min_price
                
                # Create points for the line
                points = []
                for i, price in enumerate(prices):
                    # Scale x across graph width
                    x = graph_x_start + int(i * graph_width / (len(prices) - 1))
                    
                    # Scale y (inverted, since y increases downward)
                    y = graph_y_start + int(graph_height - ((price - min_price) / price_range * graph_height))
                    
                    # Ensure within bounds
                    y = max(graph_y_start, min(graph_y_start + graph_height - 1, y))
                    
                    points.append((x, y))
                
                # Create polygon for fill
                fill_points = list(points)
                # Add bottom corners to complete
                fill_points.append((graph_x_start + graph_width, graph_y_start + graph_height))
                fill_points.append((graph_x_start, graph_y_start + graph_height))
                
                # Draw a gradient-like fill under the graph line
                # Simple approach: Draw 10 polygons with decreasing height and opacity
                for i in range(10):
                    level = i / 10.0  # 0.0 to 0.9
                    
                    # Calculate y position for this level (0=bottom, 1=top)
                    level_y = graph_y_start + graph_height - level * graph_height
                    
                    # Create polygon points for this level
                    level_points = []
                    
                    # Only include points above this level
                    for x, y in points:
                        if y <= level_y:
                            level_points.append((x, y))
                        else:
                            level_points.append((x, level_y))
                    
                    # Complete the polygon if we have any points
                    if level_points:
                        level_points.append((graph_x_start + graph_width, level_y))
                        level_points.append((graph_x_start, level_y))
                        
                        # Calculate alpha based on level (higher = more transparent)
                        alpha = int(50 * (1.0 - level))
                        r, g, b = primary_color
                        
                        # Draw this band - note we're creating an RGBA tuple
                        fill_color = (r, g, b, alpha)
                        draw.polygon(level_points, fill=fill_color)
                
                # Draw main graph line with increased width
                for i in range(len(points) - 1):
                    draw.line([points[i], points[i+1]], fill=primary_color, width=2)
            
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