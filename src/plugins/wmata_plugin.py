#!/usr/bin/env python
import time
import json
import requests
import logging
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from rgbmatrix import graphics

from .base_plugin import DisplayPlugin

# Set up logging
logger = logging.getLogger(__name__)

class WmataPlugin(DisplayPlugin):
    """Plugin for displaying WMATA (DC Metro) train arrival times

    Display is split into two halves (top and bottom) for two stations.
    Each half shows circle with metro line color, line code (e.g., OR),
    and scrolling station name with arrival times.
    """

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "wmata"
        self.description = "DC Metro train arrival times"

        # Default configuration
        self.config.setdefault('api_key', '')
        self.config.setdefault('stations', ['K04', 'C01'])  # Vienna and Metro Center
        self.config.setdefault('update_interval', 50)  # 50 seconds between API calls
        self.config.setdefault('max_trains', 2)  # Show up to 2 trains per station
        self.config.setdefault('line_colors', {
            'RD': [255, 0, 0],      # Red
            'BL': [0, 0, 255],      # Blue
            'OR': [255, 165, 0],    # Orange
            'SV': [192, 192, 192],  # Silver
            'GR': [0, 255, 0],      # Green
            'YL': [255, 255, 0]     # Yellow
        })

        # Internal state
        self.last_update = 0
        self.train_data = {}
        self.current_display = None
        self.scroll_position = 0
        self.scroll_timer = 0
        self.scroll_speed = 0.03  # 3x faster (0.1 / 3 = 0.03 seconds per pixel)

        # Text width and image storage
        self.station_name_width = {}  # Width of each station name in pixels
        self.should_scroll = {}  # Whether a station name needs scrolling
        self.scroll_amount = {}  # Total scroll amount needed for each station

        # Font loading
        self.font = graphics.Font()
        self.font_small = graphics.Font()
        self.font_tiny = graphics.Font()

        # Colors
        self.colors = {
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

        # Short line code mapping
        self.line_codes = {
            'RD': 'RD',
            'BL': 'BL',
            'OR': 'OR',
            'SV': 'SV',
            'GR': 'GR',
            'YL': 'YL',
        }

        # Station name mapping
        self.station_names = {
            'A01': 'Metro Center',
            'A02': 'Farragut North',
            'A03': 'Dupont Circle',
            'A04': 'Woodley Park',
            'A05': 'Cleveland Park',
            'A06': 'Van Ness-UDC',
            'A07': 'Tenleytown-AU',
            'A08': 'Friendship Heights',
            'A09': 'Bethesda',
            'A10': 'Medical Center',
            'A11': 'Grosvenor-Strathmore',
            'A12': 'White Flint',
            'A13': 'Twinbrook',
            'A14': 'Rockville',
            'A15': 'Shady Grove',
            'B01': 'Gallery Place',
            'B02': 'Judiciary Square',
            'B03': 'Union Station',
            'B04': 'Rhode Island Ave',
            'B05': 'Brookland-CUA',
            'B06': 'Fort Totten',
            'B07': 'Takoma',
            'B08': 'Silver Spring',
            'B09': 'Forest Glen',
            'B10': 'Wheaton',
            'B11': 'Glenmont',
            'C01': 'Metro Center',
            'C02': 'McPherson Square',
            'C03': 'Farragut West',
            'C04': 'Foggy Bottom-GWU',
            'C05': 'Rosslyn',
            'C06': 'Arlington Cemetery',
            'C07': 'Pentagon',
            'C08': 'Pentagon City',
            'C09': 'Crystal City',
            'C10': 'Reagan Airport',
            'C11': 'Potomac Yard',
            'C12': 'Braddock Road',
            'C13': 'King St-Old Town',
            'C14': 'Eisenhower Avenue',
            'C15': 'Huntington',
            'D01': 'Federal Triangle',
            'D02': 'Smithsonian',
            'D03': 'L\'Enfant Plaza',
            'D04': 'Federal Center SW',
            'D05': 'Capitol South',
            'D06': 'Eastern Market',
            'D07': 'Potomac Ave',
            'D08': 'Stadium-Armory',
            'D09': 'Minnesota Ave',
            'D10': 'Deanwood',
            'D11': 'Cheverly',
            'D12': 'Landover',
            'D13': 'New Carrollton',
            'E01': 'Mt Vernon Square',
            'E02': 'Shaw-Howard',
            'E03': 'U Street',
            'E04': 'Columbia Heights',
            'E05': 'Georgia Ave',
            'E06': 'Fort Totten',
            'E07': 'West Hyattsville',
            'E08': 'Prince George\'s',
            'E09': 'College Park',
            'E10': 'Greenbelt',
            'F01': 'Gallery Place',
            'F02': 'Archives',
            'F03': 'L\'Enfant Plaza',
            'F04': 'Waterfront',
            'F05': 'Navy Yard',
            'F06': 'Anacostia',
            'F07': 'Congress Heights',
            'F08': 'Southern Avenue',
            'F09': 'Naylor Road',
            'F10': 'Suitland',
            'F11': 'Branch Ave',
            'G01': 'Benning Road',
            'G02': 'Capitol Heights',
            'G03': 'Addison Road',
            'G04': 'Morgan Boulevard',
            'G05': 'Largo Town Center',
            'J01': 'Court House',
            'J02': 'Clarendon',
            'J03': 'Virginia Square',
            'J04': 'Ballston',
            'K01': 'East Falls Church',
            'K02': 'West Falls Church',
            'K03': 'Dunn Loring',
            'K04': 'Vienna',
            'K05': 'McLean',
            'K06': 'Tysons',
            'K07': 'Greensboro',
            'K08': 'Spring Hill',
            'N01': 'Wiehle-Reston East',
            'N02': 'Reston Town Center',
            'N03': 'Herndon',
            'N04': 'Innovation Center',
            'N06': 'Dulles Airport',
            'N08': 'Loudoun Gateway',
            'N09': 'Ashburn',
            'N10': 'Dulles Airport',
            'N12': 'Downtown Largo'
        }

        # Station to line mapping (manually defined)
        self.station_lines = {
            # Red Line
            'A01': 'RD', 'A02': 'RD', 'A03': 'RD', 'A04': 'RD', 'A05': 'RD',
            'A06': 'RD', 'A07': 'RD', 'A08': 'RD', 'A09': 'RD', 'A10': 'RD',
            'A11': 'RD', 'A12': 'RD', 'A13': 'RD', 'A14': 'RD', 'A15': 'RD',
            'B01': 'RD', 'B02': 'RD', 'B03': 'RD', 'B04': 'RD', 'B05': 'RD',
            'B06': 'RD', 'B07': 'RD', 'B08': 'RD', 'B09': 'RD', 'B10': 'RD', 'B11': 'RD',

            # Blue Line
            'C01': 'BL', 'C02': 'BL', 'C03': 'BL', 'C04': 'BL', 'C05': 'BL',
            'C06': 'BL', 'C07': 'BL', 'C08': 'BL', 'C09': 'BL', 'C10': 'BL',
            'C11': 'BL', 'C12': 'BL', 'C13': 'BL', 'C14': 'BL', 'C15': 'BL',

            # Orange Line
            'D01': 'OR', 'D02': 'OR', 'D03': 'OR', 'D04': 'OR', 'D05': 'OR',
            'D06': 'OR', 'D07': 'OR', 'D08': 'OR', 'D09': 'OR', 'D10': 'OR',
            'D11': 'OR', 'D12': 'OR', 'D13': 'OR', 
            'K01': 'OR', 'K02': 'OR', 'K03': 'OR', 'K04': 'OR',

            # Silver Line
            'K05': 'SV', 'K06': 'SV', 'K07': 'SV', 'K08': 'SV',
            'N01': 'SV', 'N02': 'SV', 'N03': 'SV', 'N04': 'SV',
            'N06': 'SV', 'N08': 'SV', 'N09': 'SV', 'N10': 'SV',

            # Green Line
            'E01': 'GR', 'E02': 'GR', 'E03': 'GR', 'E04': 'GR', 'E05': 'GR',
            'E06': 'GR', 'E07': 'GR', 'E08': 'GR', 'E09': 'GR', 'E10': 'GR',

            # Yellow Line
            'F01': 'YL', 'F02': 'YL', 'F03': 'YL', 'F04': 'YL', 'F05': 'YL',
            'F06': 'YL', 'F07': 'YL', 'F08': 'YL', 'F09': 'YL', 'F10': 'YL', 'F11': 'YL',

            # Stations that serve multiple lines - we'll set default colors for these
            'J01': 'OR', 'J02': 'OR', 'J03': 'OR', 'J04': 'OR',  # These stations serve Orange and Silver but showing as Orange
            'G01': 'BL', 'G02': 'BL', 'G03': 'BL', 'G04': 'BL', 'G05': 'BL'  # Silver/Blue line stations showing as Blue
        }

    def setup(self):
        """Set up the WMATA plugin"""
        # Load fonts - fixed to avoid height attribute errors
        try:
            self.font_tiny.LoadFont("resources/fonts/4x6.bdf")
            self.font_small.LoadFont("resources/fonts/5x7.bdf") 
            self.font.LoadFont("resources/fonts/7x13.bdf")
        except Exception as e:
            logger.error(f"Error loading fonts: {e}")
            # Try system fonts
            try:
                self.font_tiny.LoadFont("/usr/share/fonts/misc/4x6.bdf")
                self.font_small.LoadFont("/usr/share/fonts/misc/5x7.bdf")
                self.font.LoadFont("/usr/share/fonts/misc/7x13.bdf")
            except Exception as e:
                logger.error(f"Error loading system fonts: {e}")

        # Check configuration
        logger.info(f"WMATA plugin configuration: {self.config}")

        # Check for API key
        if not self.config.get('api_key'):
            logger.warning("No WMATA API key configured")

        # Limit to 2 stations only
        if len(self.config.get('stations', [])) > 2:
            self.config['stations'] = self.config['stations'][:2]
            logger.info("Limited to 2 stations only")

        # Ensure we have exactly 2 stations
        while len(self.config.get('stations', [])) < 2:
            self.config['stations'].append('C01')  # Add Metro Center as default

        # Initial data fetch
        self._fetch_train_data()

    def _fetch_train_data(self):
        """Fetch train arrival predictions from WMATA API"""
        api_key = self.config.get('api_key', '')
        if not api_key:
            logger.error("No API key configured for WMATA data")
            return

        # Get station codes to fetch (exactly 2)
        stations = self.config.get('stations', [])
        if len(stations) != 2:
            logger.warning(f"Expected exactly 2 stations, got {len(stations)}")
            # Ensure we have exactly 2 stations
            while len(stations) < 2:
                stations.append('C01')  # Add Metro Center as default
            stations = stations[:2]  # Limit to 2

        for station_code in stations:
            # WMATA API endpoint for real-time train predictions
            url = f"https://api.wmata.com/StationPrediction.svc/json/GetPrediction/{station_code}"
            headers = {
                'api_key': api_key
            }

            logger.info(f"Fetching train data for station {station_code}")

            try:
                response = requests.get(url, headers=headers, timeout=10)
                logger.info(f"API response status for {station_code}: {response.status_code}")

                if response.status_code != 200:
                    logger.error(f"API error for {station_code}: HTTP {response.status_code}")
                    self.train_data[station_code] = {"error": f"HTTP {response.status_code}"}
                    continue

                data = response.json()
                trains = data.get('Trains', [])

                if not trains:
                    logger.warning(f"No trains found for station {station_code}")
                    self.train_data[station_code] = {"trains": []}
                    continue

                # Process and sort train predictions
                processed_trains = []
                for train in trains:
                    # Get train information
                    line = train.get('Line', '')

                    # Skip destination as requested

                    # Process minutes
                    if train.get('Min', '') == 'BRD':
                        minutes = 0
                        min_display = "BRD"
                    elif train.get('Min', '') == 'ARR':
                        minutes = 0
                        min_display = "ARR"
                    elif train.get('Min', '').isdigit():
                        minutes = int(train.get('Min', ''))
                        min_display = f"{minutes}m"
                    else:
                        # Skip trains with no arrival information
                        continue

                    processed_trains.append({
                        'line': line,
                        'minutes': minutes,
                        'min_display': min_display,
                        'cars': train.get('Car', '')
                    })

                # Sort by minutes
                processed_trains.sort(key=lambda x: x['minutes'])

                # Store data - limit to max_trains per station
                max_trains = self.config.get('max_trains', 2)
                self.train_data[station_code] = {
                    "name": self.station_names.get(station_code, station_code),
                    "trains": processed_trains[:max_trains]
                }

                logger.info(f"Got {len(processed_trains)} trains for {station_code}")

            except Exception as e:
                logger.error(f"Error fetching data for station {station_code}: {e}")
                self.train_data[station_code] = {"error": str(e)}

        # Calculate text widths for each station name
        self._calculate_name_widths()

        # Reset scrolling when new data arrives
        self.scroll_position = 0

        # Create the initial display
        self._create_split_screen_display()

        # Reset update timer
        self.last_update = 0

    def _calculate_name_widths(self):
        """Calculate the pixel width of each station name and determine if scrolling is needed"""
        # Get station codes
        stations = self.config.get('stations', [])[:2]

        # Available width for name display (matrix width minus left section)
        available_width = self.matrix.width - 16  # 16px for line circle

        for station_code in stations:
            # Get station name
            station_data = self.train_data.get(station_code, {})
            station_name = station_data.get("name", self.station_names.get(station_code, station_code))

            # Calculate approximate width based on character count and font
            # The clock font is approximately 6-7 pixels per character
            char_width = 7  # Pixels per character for the clock font
            name_width = len(station_name) * char_width

            # Store the calculated width
            self.station_name_width[station_code] = name_width

            # Determine if scrolling is needed (name longer than 7 characters / 48 pixels)
            self.should_scroll[station_code] = name_width > available_width

            # Calculate total scroll amount if scrolling is needed
            if self.should_scroll[station_code]:
                # Need to scroll the full width plus some padding
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

        # Get station codes
        stations = self.config.get('stations', [])[:2]

        # Draw each station in its half (top and bottom)
        for i, station_code in enumerate(stations):
            half_height = height // 2
            y_offset = i * half_height  # 0 for top half, half_height for bottom half

            # Draw station info in this half
            self._draw_station_half(draw, display_image, width, half_height, y_offset, station_code)

        # Draw a medium gray line in the middle to separate the two stations
        separator_y = height // 2
        for x in range(width):
            display_image.putpixel((x, separator_y), (100, 100, 100))  # Medium gray color

        # Store the complete display
        self.current_display = display_image

    def _draw_station_half(self, draw, display_image, width, half_height, y_offset, station_code):
        """Draw a single station info in its half of the screen"""
        # Get station data
        station_data = self.train_data.get(station_code, {})
        station_name = station_data.get("name", self.station_names.get(station_code, station_code))
        trains = station_data.get("trains", [])

        # Left section: 16x16 pixels for line circle and code
        left_width = 16

        # Determine line color for the station
        primary_line = self.station_lines.get(station_code, "RD")  # Default to Red if unknown
        line_color = tuple(self.config.get('line_colors', {}).get(primary_line, [255, 255, 255]))
        line_code = self.line_codes.get(primary_line, primary_line)

        # Draw colored circle with line code
        circle_x, circle_y = left_width // 2, y_offset + half_height // 2
        circle_radius = 7
        draw.ellipse(
            [(circle_x - circle_radius, circle_y - circle_radius),
             (circle_x + circle_radius, circle_y + circle_radius)],
            fill=line_color
        )

        # Draw line code inside circle
        code_x = circle_x - len(line_code) * 2  # Center text in circle
        code_y = circle_y - 3  # Vertical center
        draw.text((code_x, code_y), line_code, fill=(0, 0, 0))  # Black text

        # Create a PIL ImageDraw for the text section
        text_image = Image.new('RGB', (width - left_width, half_height), (0, 0, 0))
        text_draw = ImageDraw.Draw(text_image)

        # Draw station name - either static or scrolling
        if not self.should_scroll.get(station_code, False):
            # Static display (name fits without scrolling)
            text_draw.text((2, 0), station_name, fill=(255, 255, 255))
        else:
            # Scrolling display for long names
            # Calculate position based on scroll_position
            # We want the text to start fully off-screen to the right and scroll left
            scroll_x = width - left_width - self.scroll_position
            if scroll_x < -self.station_name_width[station_code]:
                # Reset when the name has scrolled completely off the left
                scroll_x = width - left_width

            # We only draw the station name when it's at least partially visible
            if scroll_x < width - left_width:
                text_draw.text((scroll_x, 0), station_name, fill=(255, 255, 255))

        # Draw arrival times (always static, never scrolling)
        if not trains:
            if "error" in station_data:
                text_draw.text((2, 8), "API Error", fill=(255, 0, 0))
            else:
                text_draw.text((2, 8), "No trains", fill=(150, 150, 150))
        else:
            # Format train arrival times - just times, no destinations
            train_info = ""
            for i, train in enumerate(trains):
                if i > 0:
                    train_info += " - "  # Use dash separator

                min_display = train.get('min_display', '')
                train_info += min_display

            # Determine color based on time
            minutes = trains[0].get('minutes', 999)
            if minutes == 0:
                info_color = (255, 165, 0)  # Orange for arriving/boarding
            elif minutes <= 5:
                info_color = (0, 255, 0)  # Green for soon
            else:
                info_color = (255, 255, 255)  # White for longer times

            # Draw train info with temperature font
            text_draw.text((2, 8), train_info, fill=info_color)

        # Create a mask for the right section to prevent overlap with circle
        mask = Image.new('1', (width, half_height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rectangle([(left_width, 0), (width, half_height)], fill=1)

        # Paste the text image onto the main display
        display_image.paste(text_image, (left_width, y_offset), mask.crop((left_width, 0, width, half_height)))

    def update(self, delta_time):
        """Update WMATA display"""
        # Update timers
        self.last_update += delta_time

        # Update train data based on interval
        if self.last_update >= self.config['update_interval']:
            self._fetch_train_data()
            return

        # Check if any station needs scrolling
        needs_scrolling = any(self.should_scroll.values())
        if not needs_scrolling:
            # No scrolling needed, skip the rest
            return

        # Handle scrolling
        self.scroll_timer += delta_time
        if self.scroll_timer >= self.scroll_speed:
            self.scroll_timer = 0

            # Increment scroll position
            self.scroll_position += 1

            # Find max scroll amount needed
            max_scroll = max(self.scroll_amount.values())

            # Reset at the end of the longest scroll
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
            # Set the image on the canvas
            canvas.SetImage(self.current_display)
            return

        # If no display image, show loading/error message
        api_key = self.config.get('api_key', '')
        if not api_key:
            # No API key - display error
            graphics.DrawText(canvas, self.font, 2, 16, 
                             self.colors['error'], "WMATA API")
            graphics.DrawText(canvas, self.font, 2, 25, 
                             self.colors['error'], "Key Missing")
        else:
            # Loading data
            graphics.DrawText(canvas, self.font, 2, 16, 
                             self.colors['white'], "Loading")
            graphics.DrawText(canvas, self.font, 2, 25, 
                             self.colors['white'], "train data")