#!/usr/bin/env python
import time
import requests
import logging
from datetime import datetime
from PIL import Image, ImageDraw
from rgbmatrix import graphics
import os
from .base_plugin import DisplayPlugin

# Set up logging
logger = logging.getLogger(__name__)

class WmataPlugin(DisplayPlugin):
    """Plugin for displaying WMATA (DC Metro) train arrival times

    Display is split into two halves (top and bottom) for two stations.
    Each half shows circle with metro line color, line code (e.g., OR),
    and scrolling station name with arrival times.
    """

    # Metro line colors (moved to class variable to reduce memory usage)
    LINE_COLORS = {
        'RD': [255, 0, 0],      # Red
        'BL': [0, 0, 255],      # Blue
        'OR': [255, 165, 0],    # Orange
        'SV': [192, 192, 192],  # Silver
        'GR': [0, 255, 0],      # Green
        'YL': [255, 255, 0]     # Yellow
    }

    # Simplified station names (cut down on memory usage)
    STATION_NAMES = {
        'A01': 'Metro Center', 'A02': 'Farragut North', 'A03': 'Dupont Circle',
        'A04': 'Woodley Park', 'A05': 'Cleveland Park', 'A06': 'Van Ness-UDC',
        'A07': 'Tenleytown-AU', 'A08': 'Friendship Heights', 'A09': 'Bethesda',
        'A10': 'Medical Center', 'A11': 'Grosvenor-Strathmore', 'A12': 'White Flint',
        'A13': 'Twinbrook', 'A14': 'Rockville', 'A15': 'Shady Grove',
        'B01': 'Gallery Place', 'B02': 'Judiciary Square', 'B03': 'Union Station',
        'B04': 'Rhode Island Ave', 'B05': 'Brookland-CUA', 'B06': 'Fort Totten',
        'B07': 'Takoma', 'B08': 'Silver Spring', 'B09': 'Forest Glen',
        'B10': 'Wheaton', 'B11': 'Glenmont', 'C01': 'Metro Center',
        'C02': 'McPherson Square', 'C03': 'Farragut West', 'C04': 'Foggy Bottom-GWU',
        'C05': 'Rosslyn', 'C06': 'Arlington Cemetery', 'C07': 'Pentagon',
        'C08': 'Pentagon City', 'C09': 'Crystal City', 'C10': 'Reagan Airport',
        'C11': 'Potomac Yard', 'C12': 'Braddock Road', 'C13': 'King St-Old Town',
        'C14': 'Eisenhower Avenue', 'C15': 'Huntington', 'D01': 'Federal Triangle',
        'D02': 'Smithsonian', 'D03': 'L\'Enfant Plaza', 'D04': 'Federal Center SW',
        'D05': 'Capitol South', 'D06': 'Eastern Market', 'D07': 'Potomac Ave',
        'D08': 'Stadium-Armory', 'D09': 'Minnesota Ave', 'D10': 'Deanwood',
        'D11': 'Cheverly', 'D12': 'Landover', 'D13': 'New Carrollton',
        'E01': 'Mt Vernon Square', 'E02': 'Shaw-Howard', 'E03': 'U Street',
        'E04': 'Columbia Heights', 'E05': 'Georgia Ave', 'E06': 'Fort Totten',
        'E07': 'West Hyattsville', 'E08': 'Prince George\'s', 'E09': 'College Park',
        'E10': 'Greenbelt', 'F01': 'Gallery Place', 'F02': 'Archives',
        'F03': 'L\'Enfant Plaza', 'F04': 'Waterfront', 'F05': 'Navy Yard',
        'F06': 'Anacostia', 'F07': 'Congress Heights', 'F08': 'Southern Avenue',
        'F09': 'Naylor Road', 'F10': 'Suitland', 'F11': 'Branch Ave',
        'G01': 'Benning Road', 'G02': 'Capitol Heights', 'G03': 'Addison Road',
        'G04': 'Morgan Boulevard', 'G05': 'Largo Town Center', 'J01': 'Court House',
        'J02': 'Clarendon', 'J03': 'Virginia Square', 'J04': 'Ballston',
        'K01': 'East Falls Church', 'K02': 'West Falls Church', 'K03': 'Dunn Loring',
        'K04': 'Vienna', 'K05': 'McLean', 'K06': 'Tysons', 'K07': 'Greensboro',
        'K08': 'Spring Hill', 'N01': 'Wiehle-Reston East', 'N02': 'Reston Town Center',
        'N03': 'Herndon', 'N04': 'Innovation Center', 'N06': 'Dulles Airport',
        'N08': 'Loudoun Gateway', 'N09': 'Ashburn', 'N10': 'Dulles Airport',
        'N12': 'Downtown Largo'
    }

    # Station to line mapping (merged red line stations for efficiency)
    STATION_LINES = {
        # Red Line stations (all A* and B* codes)
        **{code: 'RD' for code in ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08',
                                   'A09', 'A10', 'A11', 'A12', 'A13', 'A14', 'A15',
                                   'B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07',
                                   'B08', 'B09', 'B10', 'B11']},
        # Blue Line
        **{code: 'BL' for code in ['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08',
                                   'C09', 'C10', 'C11', 'C12', 'C13', 'C14', 'C15',
                                   'G01', 'G02', 'G03', 'G04', 'G05']},
        # Orange Line
        **{code: 'OR' for code in ['D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'D07', 'D08',
                                   'D09', 'D10', 'D11', 'D12', 'D13', 'J01', 'J02',
                                   'J03', 'J04', 'K01', 'K02', 'K03', 'K04']},
        # Silver Line
        **{code: 'SV' for code in ['K05', 'K06', 'K07', 'K08', 'N01', 'N02', 'N03', 'N04',
                                   'N06', 'N08', 'N09', 'N10']},
        # Green Line
        **{code: 'GR' for code in ['E01', 'E02', 'E03', 'E04', 'E05', 'E06', 'E07', 'E08',
                                   'E09', 'E10']},
        # Yellow Line
        **{code: 'YL' for code in ['F01', 'F02', 'F03', 'F04', 'F05', 'F06', 'F07', 'F08',
                                   'F09', 'F10', 'F11']}
    }

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "wmata"
        self.description = "DC Metro train arrival times"

        # Default configuration
        self.config.setdefault('api_key', '')
        self.config.setdefault('stations', ['K04', 'C01'])  # Vienna and Metro Center
        self.config.setdefault('update_interval', 50)  # 50 seconds between API calls
        self.config.setdefault('max_trains', 2)  # Show up to 2 trains per station
        self.config.setdefault('line_colors', self.LINE_COLORS.copy())

        # Internal state
        self.last_update = 0
        self.train_data = {}
        self.current_display = None
        self.scroll_position = 0
        self.scroll_timer = 0
        self.scroll_speed = 0.06  # Seconds between scroll updates

        # Text width and image storage
        self.station_name_width = {}  # Width of each station name in pixels
        self.should_scroll = {}  # Whether a station name needs scrolling
        self.scroll_amount = {}  # Total scroll amount needed for each station

        # Font loading
        self.font = graphics.Font()
        self.font_small = graphics.Font()
        self.font_tiny = graphics.Font()

        # Colors (reused for graphics)
        self.graphics_colors = self._init_graphics_colors()

        # API response cache
        self.api_cache = {}
        self.api_cache_time = {}

    def _init_graphics_colors(self):
        """Initialize commonly used graphics.Color objects"""
        return {
            'white': graphics.Color(255, 255, 255),
            'black': graphics.Color(0, 0, 0),
            'red': graphics.Color(255, 0, 0),
            'blue': graphics.Color(0, 0, 255),
            'green': graphics.Color(0, 255, 0),
            'orange': graphics.Color(255, 165, 0),
            'silver': graphics.Color(192, 192, 192),
            'yellow': graphics.Color(255, 255, 0),
            'gray': graphics.Color(128, 128, 128),
            'medium_gray': graphics.Color(100, 100, 100),
            'error': graphics.Color(255, 0, 0)
        }

    def setup(self):
        """Set up the WMATA plugin"""
        # Load fonts - try multiple locations for better compatibility
        self._load_fonts()

        # Check configuration
        logger.info(f"WMATA plugin configuration: {self.config}")

        # Validate and normalize station configuration
        self._validate_stations()

        # Initial data fetch
        self._fetch_train_data()

    def _load_fonts(self):
        """Load fonts from various possible locations"""
        font_paths = [
            # Try project fonts first
            ("resources/fonts/4x6.bdf", "resources/fonts/5x7.bdf", "resources/fonts/7x13.bdf"),
            # Then system fonts
            ("/usr/share/fonts/misc/4x6.bdf", "/usr/share/fonts/misc/5x7.bdf", "/usr/share/fonts/misc/7x13.bdf")
        ]

        for tiny_path, small_path, regular_path in font_paths:
            try:
                self.font_tiny.LoadFont(tiny_path)
                self.font_small.LoadFont(small_path)
                self.font.LoadFont(tiny_path)
                logger.info(f"Loaded fonts from {os.path.dirname(tiny_path)}")
                return
            except Exception as e:
                logger.debug(f"Could not load fonts from {os.path.dirname(tiny_path)}: {e}")
                continue

        logger.warning("Could not load fonts from any location")

    def _validate_stations(self):
        """Validate and normalize station configuration"""
        stations = self.config.get('stations', [])

        # Ensure we have exactly 2 stations
        if len(stations) > 2:
            self.config['stations'] = stations[:2]
            logger.info("Limited to 2 stations only")

        while len(self.config['stations']) < 2:
            self.config['stations'].append('C01')  # Add Metro Center as default
            logger.info("Added default station: Metro Center (C01)")

    def _fetch_train_data(self):
        """Fetch train arrival predictions from WMATA API"""
        api_key = self.config.get('api_key', '')
        if not api_key:
            logger.error("No API key configured for WMATA data")
            return

        # Get station codes to fetch (exactly 2)
        stations = self.config.get('stations', [])[:2]

        current_time = time.time()
        for station_code in stations:
            # Check cache first
            if (station_code in self.api_cache and
                current_time - self.api_cache_time.get(station_code, 0) < self.config['update_interval']):
                logger.info(f"Using cached data for station {station_code}")
                continue

            # WMATA API endpoint
            url = f"https://api.wmata.com/StationPrediction.svc/json/GetPrediction/{station_code}"
            headers = {'api_key': api_key}

            logger.info(f"Fetching train data for station {station_code}")

            try:
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code != 200:
                    logger.error(f"API error for {station_code}: HTTP {response.status_code}")
                    self.train_data[station_code] = {"error": f"HTTP {response.status_code}"}
                    continue

                # Process response
                data = response.json()

                # Cache the raw response
                self.api_cache[station_code] = data
                self.api_cache_time[station_code] = current_time

                # Process the trains data
                self._process_station_data(station_code, data)

            except Exception as e:
                logger.error(f"Error fetching data for station {station_code}: {e}")
                self.train_data[station_code] = {"error": str(e)}

        # Calculate text widths and prepare for scrolling
        self._prepare_display()

        # Reset update timer
        self.last_update = 0

    def _process_station_data(self, station_code, data):
        """Process raw API data for a station"""
        trains = data.get('Trains', [])

        if not trains:
            logger.warning(f"No trains found for station {station_code}")
            self.train_data[station_code] = {
                "name": self.STATION_NAMES.get(station_code, station_code),
                "trains": []
            }
            return

        # Process and sort train predictions
        processed_trains = []
        for train in trains:
            # Process minutes display
            min_val = train.get('Min', '')
            if min_val == 'BRD':
                minutes = 0
                min_display = "BRD"
            elif min_val == 'ARR':
                minutes = 0
                min_display = "ARR"
            elif min_val.isdigit():
                minutes = int(min_val)
                min_display = f"{minutes}m"
            else:
                # Skip trains with no arrival information
                continue

            processed_trains.append({
                'line': train.get('Line', ''),
                'minutes': minutes,
                'min_display': min_display,
                'cars': train.get('Car', '')
            })

        # Sort by minutes and limit to max_trains
        processed_trains.sort(key=lambda x: x['minutes'])
        max_trains = self.config.get('max_trains', 2)

        self.train_data[station_code] = {
            "name": self.STATION_NAMES.get(station_code, station_code),
            "trains": processed_trains[:max_trains]
        }

        logger.info(f"Processed {len(processed_trains)} trains for {station_code}")

    def _prepare_display(self):
        """Calculate text widths and prepare scrolling parameters"""
        self._calculate_name_widths()
        self._create_split_screen_display()
        self.scroll_position = 0  # Reset scrolling

    def _calculate_name_widths(self):
        """Calculate the pixel width of each station name and determine if scrolling is needed"""
        # Available width for name display (matrix width minus left section)
        left_width = 16  # 16px for line circle
        available_width = self.matrix.width - left_width
        char_width = 7  # Approximate pixels per character

        for station_code in self.config.get('stations', [])[:2]:
            # Get station name
            station_data = self.train_data.get(station_code, {})
            station_name = station_data.get("name", self.STATION_NAMES.get(station_code, station_code))

            # Calculate approximate width
            name_width = len(station_name) * char_width
            self.station_name_width[station_code] = name_width

            # Determine if scrolling is needed
            self.should_scroll[station_code] = name_width > available_width

            # Calculate total scroll amount if needed
            if self.should_scroll[station_code]:
                self.scroll_amount[station_code] = name_width + 10  # Add padding
            else:
                self.scroll_amount[station_code] = 0

    def _create_split_screen_display(self):
        """Create a display with split screen for two stations"""
        # Create a new image for the display
        width = self.matrix.width
        height = self.matrix.height
        display_image = Image.new('RGB', (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(display_image)

        # Draw each station in its half
        half_height = height // 2
        stations = self.config.get('stations', [])[:2]

        for i, station_code in enumerate(stations):
            y_offset = i * half_height
            self._draw_station_half(draw, display_image, width, half_height, y_offset, station_code)

        # Draw separator line
        for x in range(width):
            display_image.putpixel((x, half_height), (20, 20, 20))

        # Store the display
        self.current_display = display_image

    def _draw_station_half(self, draw, display_image, width, half_height, y_offset, station_code):
        """Draw a single station info in its half of the screen"""
        # Get station data
        station_data = self.train_data.get(station_code, {})
        station_name = station_data.get("name", self.STATION_NAMES.get(station_code, station_code))
        trains = station_data.get("trains", [])

        # Left section width for line circle
        left_width = 16

        # Determine line color
        primary_line = self.STATION_LINES.get(station_code, "RD")
        line_color = tuple(self.config.get('line_colors', {}).get(primary_line, [255, 255, 255]))

        # Draw colored circle with line code
        circle_x, circle_y = left_width // 2, y_offset + half_height // 2
        circle_radius = 7
        draw.ellipse(
            [(circle_x - circle_radius, circle_y - circle_radius),
             (circle_x + circle_radius, circle_y + circle_radius)],
            fill=line_color
        )

        # Draw line code inside circle
        draw.text((circle_x - 4, circle_y - 3), primary_line, fill=(0, 0, 0))

        # Create the text section image
        text_image = Image.new('RGB', (width - left_width, half_height), (0, 0, 0))
        text_draw = ImageDraw.Draw(text_image)

        # Draw station name (static or scrolling)
        self._draw_station_name(text_draw, station_code, station_name, width, left_width)

        # Draw train arrival times
        self._draw_train_times(text_draw, station_data, trains)

        # Create mask and paste the text image
        mask = Image.new('1', (width, half_height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rectangle([(left_width, 0), (width, half_height)], fill=1)

        display_image.paste(text_image, (left_width, y_offset), mask.crop((left_width, 0, width, half_height)))

    def _draw_station_name(self, text_draw, station_code, station_name, width, left_width):
        """Draw the station name (either static or scrolling)"""
        if not self.should_scroll.get(station_code, False):
            # Static display
            text_draw.text((2, -1), station_name, fill=(255, 255, 255))
        else:
            # Scrolling display
            scroll_x = width - left_width - self.scroll_position + 10

            # Reset when scrolled off screen
            if scroll_x < -self.station_name_width[station_code] - 40:
                scroll_x = width - left_width

            # Draw only when visible
            if scroll_x < width - left_width:
                text_draw.text((scroll_x, 0), station_name, fill=(255, 255, 255))

    def _draw_train_times(self, text_draw, station_data, trains):
        """Draw the train arrival times"""
        if not trains:
            # No trains or error
            if "error" in station_data:
                text_draw.text((2, 8), "API Error", fill=(255, 0, 0))
            else:
                text_draw.text((2, 8), "No trains", fill=(150, 150, 150))
            return

        # Format arrival times
        train_info = "-".join(train.get('min_display', '') for train in trains)

        # Determine color based on time
        minutes = trains[0].get('minutes', 999)
        if minutes == 0:
            info_color = (255, 165, 0)  # Orange for arriving/boarding
        elif minutes <= 5:
            info_color = (0, 255, 0)    # Green for soon
        else:
            info_color = (255, 255, 255)  # White for longer times

        # Draw train info
        text_draw.text((2, 7), train_info, fill=info_color)

    def update(self, delta_time):
        """Update WMATA display"""
        # Update API data when interval elapsed
        self.last_update += delta_time
        if self.last_update >= self.config['update_interval']:
            self._fetch_train_data()
            return

        # Handle scrolling if needed
        needs_scrolling = any(self.should_scroll.values())
        if not needs_scrolling:
            return

        # Update scroll position
        self.scroll_timer += delta_time
        if self.scroll_timer >= self.scroll_speed:
            self.scroll_timer = 0
            self.scroll_position += 1

            # Reset at the end of the longest scroll
            max_scroll = max(self.scroll_amount.values(), default=0)
            if self.scroll_position > max_scroll:
                self.scroll_position = 0

            # Update display with new scroll position
            self._create_split_screen_display()

    def render(self, canvas):
        """Render the WMATA display"""
        # Clear canvas
        canvas.Clear()

        # Check if we have a display image
        if self.current_display:
            canvas.SetImage(self.current_display)
            return

        # Show error/loading message if no display
        api_key = self.config.get('api_key', '')
        if not api_key:
            # No API key message
            graphics.DrawText(canvas, self.font, 2, 16,
                             self.graphics_colors['error'], "WMATA API")
            graphics.DrawText(canvas, self.font, 2, 25,
                             self.graphics_colors['error'], "Key Missing")
        else:
            # Loading message
            graphics.DrawText(canvas, self.font, 2, 16,
                             self.graphics_colors['white'], "Loading")
            graphics.DrawText(canvas, self.font, 2, 25,
                             self.graphics_colors['white'], "train data")

    def cleanup(self):
        """Clean up resources"""
        # Clear any cached data
        self.api_cache.clear()
        self.api_cache_time.clear()
        self.train_data.clear()
        self.current_display = None
        super().cleanup()