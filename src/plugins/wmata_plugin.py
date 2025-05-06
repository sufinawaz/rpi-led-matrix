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

    Configuration options:
        api_key (str): WMATA API key
        stations (list): List of station codes to display (up to 2)
        update_interval (int): How often to update train data in seconds
        line_colors (dict): RGB color tuples for each train line
        display_mode (str): Display mode - 'alternating' or 'combined'
        show_station_name (bool): Whether to display the station name
        max_trains (int): Maximum number of trains to display per station
    """

    def __init__(self, matrix, config=None):
        super().__init__(matrix, config)
        self.name = "wmata"
        self.description = "DC Metro train arrival times"

        # Default configuration
        self.config.setdefault('api_key', '')
        self.config.setdefault('stations', ['K04', 'C01'])  # Vienna (Orange) and Metro Center
        self.config.setdefault('update_interval', 30)  # 30 seconds
        self.config.setdefault('display_mode', 'alternating')  # 'alternating' or 'combined'
        self.config.setdefault('show_station_name', True)
        self.config.setdefault('max_trains', 3)  # Show up to 3 trains per station
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
        self.current_station_index = 0
        self.station_display_time = 0
        self.station_display_duration = 5  # Seconds to display each station
        self.current_display = None

        # Font loading
        self.font = graphics.Font()
        self.font_small = graphics.Font()

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
            'error': graphics.Color(255, 0, 0)
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

    def setup(self):
        """Set up the WMATA plugin"""
        # Load fonts
        try:
            self.font_small.LoadFont("resources/fonts/4x6.bdf")
            self.font.LoadFont("resources/fonts/7x13.bdf") 
        except Exception as e:
            logger.error(f"Error loading fonts: {e}")

        # Check configuration
        logger.info(f"WMATA plugin configuration: {self.config}")

        # Check for API key
        if not self.config.get('api_key'):
            logger.warning("No WMATA API key configured")

        # Limit to 2 stations only
        if len(self.config.get('stations', [])) > 2:
            self.config['stations'] = self.config['stations'][:2]
            logger.info("Limited to 2 stations only")

        # Initial data fetch
        self._fetch_train_data()

    def _fetch_train_data(self):
        """Fetch train arrival predictions from WMATA API"""
        api_key = self.config.get('api_key', '')
        if not api_key:
            logger.error("No API key configured for WMATA data")
            return

        # Get station codes to fetch (limited to 2)
        stations = self.config.get('stations', [])[:2]
        if not stations:
            logger.error("No stations configured")
            return

        for station_code in stations:
            # WMATA API endpoint for real-time train predictions
            url = f"https://api.wmata.com/StationPrediction.svc/json/GetPrediction/{station_code}"
            headers = {
                'api_key': api_key
            }

            logger.info(f"Fetching train data for station {station_code}")

            try:
                response = requests.get(url, headers=headers, timeout=10)

                # Log response status
                logger.info(f"API response status for {station_code}: {response.status_code}")

                if response.status_code != 200:
                    logger.error(f"API error for {station_code}: HTTP {response.status_code}")
                    continue

                data = response.json()
                trains = data.get('Trains', [])

                if not trains:
                    logger.warning(f"No trains found for station {station_code}")
                    self.train_data[station_code] = []
                    continue

                # Process and sort train predictions
                processed_trains = []
                for train in trains:
                    # Skip trains with no information or that aren't boarding
                    if train.get('Min', '') == 'BRD':
                        minutes = 0
                    elif train.get('Min', '') == 'ARR':
                        minutes = 0
                    elif train.get('Min', '').isdigit():
                        minutes = int(train.get('Min', ''))
                    else:
                        # Skip trains with no arrival information
                        continue

                    processed_trains.append({
                        'line': train.get('Line', ''),
                        'destination': train.get('Destination', ''),
                        'minutes': minutes,
                        'cars': train.get('Car', '')
                    })

                # Sort by minutes
                processed_trains.sort(key=lambda x: x['minutes'])

                # Store data - limit to max_trains per station
                max_trains = self.config.get('max_trains', 3)
                self.train_data[station_code] = processed_trains[:max_trains]
                logger.info(f"Successfully fetched {len(processed_trains)} trains for {station_code}")

            except Exception as e:
                logger.error(f"Error fetching data for station {station_code}: {e}")

        # Create display image
        self._create_display_image()
        self.last_update = 0

    def _create_display_image(self):
        """Create the display image for the current station"""
        # Get current station to display
        if self.config.get('display_mode') == 'alternating':
            stations = self.config.get('stations', [])
            if not stations:
                return

            station_code = stations[self.current_station_index % len(stations)]
            self._create_cube_style_display(station_code)
        else:
            # Combined mode - show all stations
            self._create_combined_cube_display()

    def _create_cube_style_display(self, station_code):
        """Create a Cube-style display for a single station"""
        # Create a new image for the display
        width = self.matrix.width
        height = self.matrix.height
        image = Image.new('RGB', (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Get station name
        station_name = self.station_names.get(station_code, station_code)

        # Get train data for this station
        trains = self.train_data.get(station_code, [])

        # Draw station name at top with black background
        draw.rectangle([(0, 0), (width, 9)], fill=(0, 0, 0))

        # Draw station name - make it more prominent
        if len(station_name) > 12 and width <= 32:
            station_name = station_name[:11] + '.'

        # Calculate position to center text
        name_width = len(station_name) * 4  # Approximate width for small font
        name_x = max(0, (width - name_width) // 2)

        # Draw station name in white text
        draw.text((name_x, 1), station_name.upper(), fill=(255, 255, 255))

        # Horizontal line separator
        draw.line([(0, 10), (width, 10)], fill=(40, 40, 40), width=1)

        if not trains:
            # No trains - display message centered
            message = "No trains"
            msg_width = len(message) * 6  # Approximate width
            msg_x = max(0, (width - msg_width) // 2)
            msg_y = max(0, (height - 7) // 2) 
            draw.text((msg_x, msg_y), message, fill=(255, 0, 0))
        else:
            # Display trains using Cube-style layout
            # Each train gets a row with colored circle for line, destination and minutes
            y_pos = 13  # Start below the header

            for i, train in enumerate(trains):
                if i >= self.config.get('max_trains', 3):
                    break  # Limit display to max_trains

                # Get line color
                line = train.get('line', '')
                line_rgb = self.config.get('line_colors', {}).get(line, [255, 255, 255])

                # Draw colored circle for train line - make it more prominent
                circle_x, circle_y = 4, y_pos + 4
                circle_radius = 4
                draw.ellipse(
                    [(circle_x - circle_radius, circle_y - circle_radius), 
                     (circle_x + circle_radius, circle_y + circle_radius)], 
                    fill=tuple(line_rgb)
                )

                # Draw destination - truncate if too long
                dest = train.get('destination', '')
                if len(dest) > 8 and width <= 32:
                    dest = dest[:7] + '.'

                # Draw destination in bright white
                draw.text((10, y_pos), dest, fill=(255, 255, 255))

                # Draw minutes
                minutes = train.get('minutes')
                if minutes == 0:
                    min_text = "ARR"
                else:
                    min_text = f"{minutes}m"

                # Right-align minutes text with large, bold visual style
                min_width = len(min_text) * 5  # Make it wider for prominence
                min_x = width - min_width - 2

                # Draw minutes in bright color based on wait time
                if minutes == 0:
                    min_color = (255, 165, 0)  # Orange for arriving
                elif minutes <= 5:
                    min_color = (0, 255, 0)  # Green for soon
                else:
                    min_color = (255, 255, 255)  # White for longer waits

                draw.text((min_x, y_pos), min_text, fill=min_color)

                # Move to next position - add more space between rows
                y_pos += 10

        # Store the display
        self.current_display = image

    def _create_combined_cube_display(self):
        """Create a Cube-style display showing trains from multiple stations"""
        # Create a new image for the display
        width = self.matrix.width
        height = self.matrix.height
        image = Image.new('RGB', (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Get all stations (limited to 2)
        stations = self.config.get('stations', [])[:2]
        if not stations:
            return

        # Draw header "METRO"
        header = "METRO"
        header_width = len(header) * 5  # Wider for emphasis
        header_x = max(0, (width - header_width) // 2)
        draw.text((header_x, 1), header, fill=(255, 255, 255))

        # Horizontal separator line
        draw.line([(0, 10), (width, 10)], fill=(40, 40, 40), width=1)

        # Start display below header
        y_pos = 13

        # Display one station at a time, Cube style
        for station_index, station_code in enumerate(stations):
            if station_index > 0:
                # Add separator between stations
                draw.line([(0, y_pos - 1), (width, y_pos - 1)], fill=(30, 30, 30), width=1)
                y_pos += 2

            # Get station name (abbreviated)
            station_name = self.station_names.get(station_code, station_code)
            if len(station_name) > 10:
                station_name = station_name[:9] + '.'

            # Draw station name in a lighter color to differentiate
            draw.text((2, y_pos), station_name, fill=(180, 180, 180))
            y_pos += 7

            # Get train data
            trains = self.train_data.get(station_code, [])

            if not trains:
                # No trains for this station
                draw.text((4, y_pos), "No trains", fill=(150, 150, 150))
                y_pos += 7
            else:
                # Show up to 2 trains per station in combined view
                for i, train in enumerate(trains[:2]):
                    # Get line color
                    line = train.get('line', '')
                    line_rgb = self.config.get('line_colors', {}).get(line, [255, 255, 255])

                    # Draw colored circle for train line
                    circle_x, circle_y = 4, y_pos + 3
                    circle_radius = 3
                    draw.ellipse(
                        [(circle_x - circle_radius, circle_y - circle_radius), 
                         (circle_x + circle_radius, circle_y + circle_radius)], 
                        fill=tuple(line_rgb)
                    )

                    # Draw minutes
                    minutes = train.get('minutes')
                    if minutes == 0:
                        min_text = "ARR"
                    else:
                        min_text = f"{minutes}m"

                    # Right-align minutes with color based on wait time
                    min_width = len(min_text) * 4
                    min_x = width - min_width - 2

                    if minutes == 0:
                        min_color = (255, 165, 0)  # Orange for arriving
                    elif minutes <= 5:
                        min_color = (0, 255, 0)  # Green for soon
                    else:
                        min_color = (255, 255, 255)  # White for longer waits

                    # For combined view, show destination more compactly
                    dest = train.get('destination', '')
                    if len(dest) > 6:
                        dest = dest[:5] + '.'

                    # Draw destination between line and minutes
                    draw.text((10, y_pos), dest, fill=(255, 255, 255))
                    draw.text((min_x, y_pos), min_text, fill=min_color)

                    y_pos += 7

            # Add space before next station
            y_pos += 1

        # Store the display
        self.current_display = image

    def update(self, delta_time):
        """Update WMATA display"""
        # Update timers
        self.last_update += delta_time
        self.station_display_time += delta_time

        # Update train data based on interval
        if self.last_update >= self.config['update_interval']:
            self._fetch_train_data()
            self.last_update = 0

        # Update station display in alternating mode
        if self.config.get('display_mode') == 'alternating':
            if self.station_display_time >= self.station_display_duration:
                self.station_display_time = 0
                self.current_station_index += 1
                self._create_display_image()

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