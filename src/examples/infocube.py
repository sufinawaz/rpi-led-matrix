#!/usr/bin/env python
from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions
import time
from datetime import datetime, timedelta
import threading
from PIL import Image
import logging
import sys
import os
import argparse
import requests
import shutil

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

#############################################
#          Configuration Settings           #
#############################################
WEATHER_APP_ID = os.getenv('WEATHER_APP_ID', '')

# Default paths - update these to match your setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MATRIX_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))

# Use /tmp directory for images to avoid permission issues
IMAGES_DIR = os.path.join("/tmp", "infocube_images")
GIF_DIR = os.path.join(IMAGES_DIR, "gifs")
WEATHER_ICONS_DIR = os.path.join(IMAGES_DIR, "weather-icons")

# Font paths
FONT_DIR = os.path.join(MATRIX_DIR, "fonts")
FONT_SMALL_PATH = os.path.join(FONT_DIR, "4x6.bdf")
FONT_MEDIUM_PATH = os.path.join(FONT_DIR, "7x13.bdf")

# Image paths
WOOD_MISTRY_LOGO = os.path.join(IMAGES_DIR, "wm.jpg")
MOSQUE_LOGO = os.path.join(IMAGES_DIR, "mosque.jpg")

# GIF paths
GIFS = {
    'fireplace': os.path.join(GIF_DIR, "fireplace.gif"),
    'matrix': os.path.join(GIF_DIR, "matrix.gif"),
    'nebula': os.path.join(GIF_DIR, "nebula.gif"),
    'hyperloop': os.path.join(GIF_DIR, "hyperloop.gif"),
    'spacetravel': os.path.join(GIF_DIR, "spacetravel.gif"),
    'retro': os.path.join(GIF_DIR, "retro.gif")
}

# Prayer names
PRAYER_NAMES = ('Fajr', 'Zuhr', 'Asr', 'Magh', 'Isha')

# Weather icons mapping (OpenWeatherMap code to icon filename)
WEATHER_ICONS = {
    '01d': 'clear-day.png',
    '01n': 'clear-night.png',
    '02d': 'partly-cloudy-day.png',
    '02n': 'partly-cloudy-night.png',
    '03d': 'cloudy.png',
    '03n': 'cloudy.png',
    '04d': 'cloudy.png',
    '04n': 'cloudy.png',
    '09d': 'rain.png',
    '09n': 'rain.png',
    '10d': 'rain.png',
    '10n': 'rain.png',
    '11d': 'thunderstorm.png',
    '11n': 'thunderstorm.png',
    '13d': 'snow.png',
    '13n': 'snow.png',
    '50d': 'fog.png',
    '50n': 'fog.png'
}

# Fallback icon if OpenWeatherMap icon code is not recognized
DEFAULT_WEATHER_ICON = 'cloudy.png'

#############################################
#              Utility Functions            #
#############################################
def get_date_time(h24format=False, minus_mins=0):
    tm = datetime.now() - timedelta(minutes=minus_mins)
    return tm.strftime('%a'), \
           tm.strftime('%d'), \
           tm.strftime('%b'), \
           tm.strftime('%H:%M') if h24format else tm.strftime('%I:%M%p')[:-1].lower()

def ensure_directory_exists(directory):
    """Make sure the directory exists, create it if it doesn't"""
    if not os.path.exists(directory):
        try:
            # Create directory with explicit permissions
            os.makedirs(directory, mode=0o777, exist_ok=True)
            logger.info(f"Created directory: {directory}")
            # Ensure permissions after creation
            os.chmod(directory, 0o777)
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")
            return False
    return True

def download_weather_icon(icon_code):
    """Download a weather icon from OpenWeatherMap if it doesn't exist locally"""
    # Make sure weather icons directory exists
    if not ensure_directory_exists(WEATHER_ICONS_DIR):
        return None
    
    # Define the icon path
    icon_path = os.path.join(WEATHER_ICONS_DIR, f"{icon_code}.png")
    
    # If the icon already exists, return the path
    if os.path.exists(icon_path):
        return icon_path
    else:
        logging.info(f"Icon Path: {icon_path}")
    # If the icon doesn't exist, download it from OpenWeatherMap
    try:
        # Construct the OpenWeatherMap icon URL
        icon_url = f"http://openweathermap.org/img/wn/{icon_code}.png"
        logger.info(f"Downloading weather icon: {icon_url}")
        
        # Download the icon
        response = requests.get(icon_url, stream=True)
        if response.status_code == 200:
            with open(icon_path, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            logger.info(f"Downloaded weather icon to {icon_path}")
            return icon_path
        else:
            logger.warning(f"Failed to download weather icon, status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error downloading weather icon: {e}")
        return None

def get_openweather_data():
    """Fetch weather data from OpenWeatherMap API"""
    logger.info('Fetching OpenWeatherMap data')
    try:
        if not WEATHER_APP_ID:
            logger.warning("WEATHER_APP_ID environment variable not set")
            return None, None, None, None
            
        r = requests.get(
            f'https://api.openweathermap.org/data/2.5/weather?id=4791160&APPID={WEATHER_APP_ID}&units=imperial',
            headers={'Accept': 'application/json'})
        
        # Check if the request was successful
        if r.status_code != 200:
            logger.error(f"Weather API returned status code {r.status_code}")
            return None, None, None, None
            
        j = r.json()
        current = f"{round(j['main']['temp'])}°"
        lowest = str(round(j['main']['temp_min']))
        highest = str(round(j['main']['temp_max']))
        
        # Handle the icon
        icon_code = j['weather'][0]['icon']
        logger.error(f"Icon Path: {WEATHER_ICONS_DIR} {icon_code}")
        
        # First ensure the directory exists to avoid permission errors
        if not os.path.exists(WEATHER_ICONS_DIR):
            try:
                os.makedirs(WEATHER_ICONS_DIR, mode=0o777, exist_ok=True)
                os.chmod(WEATHER_ICONS_DIR, 0o777)
                logger.info(f"Created weather icons directory: {WEATHER_ICONS_DIR}")
            except Exception as e:
                logger.error(f"Failed to create weather icons directory: {e}")
                # Use a fallback path in /tmp
                fallback_dir = "/tmp/weather-icons"
                os.makedirs(fallback_dir, mode=0o777, exist_ok=True)
                logger.info(f"Using fallback path: {fallback_dir}")
                icon_path = os.path.join(fallback_dir, f"{icon_code}.png")
                return current, lowest, highest, icon_path
        
        icon_path = download_weather_icon(icon_code)
        
        if icon_path and os.path.exists(icon_path):
            logger.info(f"Using weather icon: {icon_path}")
        else:
            logger.warning("Weather icon not found, will use default")
            # Try to find any weather icon as a fallback
            try:
                if os.path.exists(WEATHER_ICONS_DIR):
                    for filename in os.listdir(WEATHER_ICONS_DIR):
                        if filename.endswith('.png') or filename.endswith('.jpg'):
                            icon_path = os.path.join(WEATHER_ICONS_DIR, filename)
                            break
            except Exception as e:
                logger.error(f"Error finding fallback icon: {e}")
                icon_path = None
        
        return current, lowest, highest, icon_path
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None, None, None, None

def get_prayer_times():
    """Fetch prayer times"""
    logger.info('Fetching prayer times')
    try:
        r = requests.get('http://api.aladhan.com/v1/timings?latitude=38.903481&longitude=-77.262817&method=1&school=1',
                         headers={'Accept': 'application/json'})
        j = r.json()
        timings = j['data']['timings']
        fajr, dhuhr, asr, maghrib, isha = timings['Fajr'], timings['Dhuhr'], timings['Asr'], timings['Maghrib'], timings['Isha']
        return fajr, dhuhr, asr, maghrib, isha
    except Exception as e:
        logger.error(f"Error fetching prayer times: {e}")
        return "05:00", "12:00", "15:00", "18:00", "20:00"  # Default values if API fails

def get_next_prayer_time(times):
    """Get the next prayer time based on current time"""
    day, dt, mo, clk = get_date_time(True, 10)
    for i in range(5):
        if times[i] > clk:
            return times[i], PRAYER_NAMES[i]
    return times[0], PRAYER_NAMES[0]

def load_image(image_path, size=None):
    """Load an image with error handling and resizing"""
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return None

    try:
        image = Image.open(image_path).convert('RGB')
        if size:
            # Use LANCZOS resampling for high-quality downsampling (replaces deprecated ANTIALIAS)
            image_resize_method = Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS
            image.thumbnail(size, image_resize_method)
        return image
    except Exception as e:
        logger.error(f"Error loading image {image_path}: {e}")
        return None

#############################################
#              SampleBase Class             #
#############################################
class SampleBase(object):
    def __init__(self, *args, **kwargs):
        self.parser = argparse.ArgumentParser()

        self.parser.add_argument("-r", "--led-rows", action="store", help="Display rows. 16 for 16x32, 32 for 32x32. Default: 32", default=32, type=int)
        self.parser.add_argument("--led-cols", action="store", help="Panel columns. Typically 32 or 64. (Default: 32)", default=32, type=int)
        self.parser.add_argument("-c", "--led-chain", action="store", help="Daisy-chained boards. Default: 1.", default=1, type=int)
        self.parser.add_argument("-P", "--led-parallel", action="store", help="For Plus-models or RPi2: parallel chains. 1..3. Default: 1", default=1, type=int)
        self.parser.add_argument("-p", "--led-pwm-bits", action="store", help="Bits used for PWM. Something between 1..11. Default: 11", default=11, type=int)
        self.parser.add_argument("-b", "--led-brightness", action="store", help="Sets brightness level. Default: 15. Range: 1..100", default=15, type=int)
        self.parser.add_argument("-m", "--led-gpio-mapping", help="Hardware Mapping: regular, adafruit-hat, adafruit-hat-pwm" , choices=['regular', 'regular-pi1', 'adafruit-hat', 'adafruit-hat-pwm'], default='adafruit-hat', type=str)
        self.parser.add_argument("--led-scan-mode", action="store", help="Progressive or interlaced scan. 0 Progressive, 1 Interlaced (default)", default=1, choices=range(2), type=int)
        self.parser.add_argument("--led-pwm-lsb-nanoseconds", action="store", help="Base time-unit for the on-time in the lowest significant bit in nanoseconds. Default: 130", default=130, type=int)
        self.parser.add_argument("--led-show-refresh", action="store_true", help="Shows the current refresh rate of the LED panel")
        self.parser.add_argument("--led-slowdown-gpio", action="store", help="Slow down writing to GPIO. Range: 0..4. Default: 1", default=1, type=int)
        self.parser.add_argument("--led-no-hardware-pulse", action="store", help="Don't use hardware pin-pulse generation")
        self.parser.add_argument("--led-rgb-sequence", action="store", help="Switch if your matrix has led colors swapped. Default: RGB", default="RGB", type=str)
        self.parser.add_argument("--led-pixel-mapper", action="store", help="Apply pixel mappers. e.g \"Rotate:90\"", default="", type=str)
        self.parser.add_argument("--led-row-addr-type", action="store", help="0 = default; 1=AB-addressed panels; 2=row direct; 3=ABC-addressed panels; 4 = ABC Shift + DE direct", default=0, type=int, choices=[0,1,2,3,4])
        self.parser.add_argument("--led-multiplexing", action="store", help="Multiplexing type: 0=direct; 1=strip; 2=checker; 3=spiral; 4=ZStripe; 5=ZnMirrorZStripe; 6=coreman; 7=Kaler2Scan; 8=ZStripeUneven... (Default: 0)", default=0, type=int)
        self.parser.add_argument("--led-panel-type", action="store", help="Needed to initialize special panels. Supported: 'FM6126A'", default="", type=str)
        self.parser.add_argument("--led-no-drop-privs", dest="drop_privileges", help="Don't drop privileges from 'root' after initializing the hardware.", action='store_false')
        self.parser.add_argument("--display-mode", action="store", help="Display mode: clock, prayer, gif, intro", default="clock", type=str)
        self.parser.add_argument("--gif-name", action="store", help="GIF to display (if display-mode is 'gif')", default="matrix", type=str)
        self.parser.set_defaults(drop_privileges=True)

    def usleep(self, value):
        time.sleep(value / 1000000.0)

    def run(self):
        print("Running")

    def process(self):
        self.args = self.parser.parse_args()

        options = RGBMatrixOptions()

        if self.args.led_gpio_mapping != None:
          options.hardware_mapping = self.args.led_gpio_mapping
        options.rows = self.args.led_rows
        options.cols = self.args.led_cols
        options.chain_length = self.args.led_chain
        options.parallel = self.args.led_parallel
        options.row_address_type = self.args.led_row_addr_type
        options.multiplexing = self.args.led_multiplexing
        options.pwm_bits = self.args.led_pwm_bits
        options.brightness = self.args.led_brightness
        options.pwm_lsb_nanoseconds = self.args.led_pwm_lsb_nanoseconds
        options.led_rgb_sequence = self.args.led_rgb_sequence
        options.pixel_mapper_config = self.args.led_pixel_mapper
        options.panel_type = self.args.led_panel_type

        if self.args.led_show_refresh:
          options.show_refresh_rate = 1

        if self.args.led_slowdown_gpio != None:
            options.gpio_slowdown = self.args.led_slowdown_gpio
        if self.args.led_no_hardware_pulse:
          options.disable_hardware_pulsing = True
        if not self.args.drop_privileges:
          options.drop_privileges=False

        self.matrix = RGBMatrix(options = options)

        try:
            # Start loop
            logger.info("Press CTRL-C to stop")
            self.run()
        except KeyboardInterrupt:
            logger.info("Exiting\n")
            # Clear the display when done
            canvas = self.matrix.CreateFrameCanvas()
            canvas.Clear()
            self.matrix.SwapOnVSync(canvas)
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            sys.exit(1)

        return True

#############################################
#              InfoCube Class               #
#############################################
class InfoCube(SampleBase):
    image = None
    
    def __init__(self, *args, **kwargs):
        super(InfoCube, self).__init__(*args, **kwargs)
        self.color = {
            'white': graphics.Color(255, 255, 255),
            'orange': graphics.Color(255, 165, 0),
            'black': graphics.Color(0, 0, 0),
            'skyBlue': graphics.Color(0, 191, 255),
            'red': graphics.Color(255, 0, 0),
            'green': graphics.Color(0, 255, 0),
            'yellow': graphics.Color(255, 255, 0),
            'lime': graphics.Color(173, 255, 47),
            'lightBlue': graphics.Color(173, 216, 230),
            'darkBlue': graphics.Color(30, 144, 255),
            'grey': graphics.Color(150, 150, 150),
            'pink': graphics.Color(255, 114, 118)
        }
        
        self.fontSmall = graphics.Font()
        self.font = graphics.Font()
        
        # Create required directories
        ensure_directory_exists(IMAGES_DIR)
        ensure_directory_exists(GIF_DIR)
        ensure_directory_exists(WEATHER_ICONS_DIR)
        
        # Load fonts
        try:
            if os.path.exists(FONT_SMALL_PATH):
                self.fontSmall.LoadFont(FONT_SMALL_PATH)
            else:
                logger.error(f"Small font not found at {FONT_SMALL_PATH}")
                # Try to find any fonts
                for font_dir in [FONT_DIR, "/usr/share/fonts", "/usr/local/share/fonts"]:
                    if os.path.exists(font_dir):
                        for file in os.listdir(font_dir):
                            if file.endswith('.bdf'):
                                self.fontSmall.LoadFont(os.path.join(font_dir, file))
                                logger.info(f"Using fallback small font: {file}")
                                break
            
            if os.path.exists(FONT_MEDIUM_PATH):
                self.font.LoadFont(FONT_MEDIUM_PATH)
            else:
                logger.error(f"Medium font not found at {FONT_MEDIUM_PATH}")
                # Use the same font as small if available
                if hasattr(self, 'fontSmall') and self.fontSmall:
                    self.font = self.fontSmall
        except Exception as e:
            logger.error(f"Failed to load fonts: {e}")
            logger.info(f"Looking for fonts in {FONT_DIR}")

    def run(self):
        # Get the display mode from command line
        display_mode = self.args.display_mode
        canvas = self.matrix.CreateFrameCanvas()
        
        logger.info(f"Starting with display mode: {display_mode}")
        
        # Run the appropriate display function based on mode
        if display_mode == "clock":
            self.display_clock_weather(canvas)
        elif display_mode == "prayer":
            self.display_prayer_times(canvas)
        elif display_mode == "gif":
            self.display_gif(canvas, self.args.gif_name)
        elif display_mode == "intro":
            self.display_wm_logo(canvas)
        else:
            self.display_hmarquee(canvas, f"Welcome to InfoCube - {display_mode} mode")

    def display_wm_logo(self, canvas):
        canvas.Clear()
        try:
            # Load the logo image
            image = load_image(WOOD_MISTRY_LOGO)
            if image:
                canvas.SetImage(image, 0, 0, False)
                canvas = self.matrix.SwapOnVSync(canvas)
                start_time = time.perf_counter()
                while True:
                    now = time.perf_counter()
                    time.sleep(1)
                    if (now - start_time) > 5:  # Show for 5 seconds
                        logger.info(f"Returning out of display_wm_logo")
                        return
            else:
                logger.error(f"Logo file not found at {WOOD_MISTRY_LOGO}")
                self.display_hmarquee(canvas, "InfoCube")
        except Exception as e:
            logger.error(f"Error displaying logo: {e}")
            return

    def display_prayer_times(self, canvas):
        try:
            # Get initial prayer times
            times = get_prayer_times()
            next_prayer_time, _ = get_next_prayer_time(times)
            canvas.Clear()
            
            # Load mosque logo if available
            mosque_image = load_image(MOSQUE_LOGO)
            if mosque_image:
                canvas.SetImage(mosque_image, 44, 2, False)
                self.image = mosque_image  # Store for reuse
            
            start_time = time.perf_counter()
            while True:
                now = time.perf_counter()
                if (now - start_time) > 60:  # Update every minute
                    times = get_prayer_times()
                    next_prayer_time, _ = get_next_prayer_time(times)
                    start_time = now
                
                canvas.Clear()
                # Display mosque image if available
                if self.image:
                    canvas.SetImage(self.image, 44, 2, False)
                
                # Display prayer times
                for i in range(5):
                    # Highlight the next prayer
                    timecolor = self.color['orange'] if times[i] == next_prayer_time else self.color['white']
                    graphics.DrawText(canvas, self.fontSmall, 5, (i+1)*6, self.color['skyBlue'], str(PRAYER_NAMES[i]))
                    graphics.DrawText(canvas, self.fontSmall, 23, (i+1)*6, timecolor, str(times[i]))
                
                canvas = self.matrix.SwapOnVSync(canvas)
                time.sleep(0.1)  # Small sleep to prevent high CPU usage
        except KeyboardInterrupt:
            return
        except Exception as e:
            logger.error(f"Error in display_prayer_times: {e}")
            return

    def display_clock_weather(self, canvas):
        try:
            # Get initial data
            day, dt, mo, clk = get_date_time()
            times = get_prayer_times()
            next_prayer_time, prayer = get_next_prayer_time(times)
            
            # Display calendar and date while weather data loads
            graphics.DrawText(canvas, self.fontSmall, 3, 6, self.color['lime'], day)
            graphics.DrawText(canvas, self.fontSmall, 20, 6, self.color['lime'], dt)
            graphics.DrawText(canvas, self.fontSmall, 30, 6, self.color['yellow'], mo)
            # Display time
            graphics.DrawText(canvas, self.font, 3, 18, self.color['white'], clk)
            canvas = self.matrix.SwapOnVSync(canvas)
            
            # Create a default weather icon if needed
            default_icon = None
            
            # Fetch weather data
            current, lowest, highest, icon_path = get_openweather_data()
            if icon_path and os.path.exists(icon_path):
                weather_image = load_image(icon_path, (24, 24))
                if weather_image:
                    self.image = weather_image
            elif not hasattr(self, 'image') or self.image is None:
                # If no weather icon is available, create a simple icon
                logger.info("Creating a default weather icon")
                try:
                    from PIL import ImageDraw
                    # Create a blank icon
                    default_icon = Image.new('RGB', (24, 24), color=(0, 0, 0))
                    draw = ImageDraw.Draw(default_icon)
                    # Draw a simple sun
                    draw.ellipse((4, 4, 20, 20), fill=(255, 255, 0))
                    self.image = default_icon
                except Exception as e:
                    logger.error(f"Failed to create default icon: {e}")
            
            start_time = time.perf_counter()
            while True:
                now = time.perf_counter()
                if (now - start_time) > 600:  # Update every 10 minutes
                    # Refresh all data
                    times = get_prayer_times()
                    next_prayer_time, prayer = get_next_prayer_time(times)
                    c, l, h, i = get_openweather_data()
                    if c and l and h and i and os.path.exists(i):
                        current, lowest, highest, icon_path = c, l, h, i
                        weather_image = load_image(icon_path, (24, 24))
                        if weather_image:
                            self.image = weather_image
                    start_time = now
                
                # Clear canvas for new frame
                canvas.Clear()
                
                # Get current time
                day, dt, mo, clk = get_date_time()
                
                # Display weather icon if available
                if hasattr(self, 'image') and self.image:
                    canvas.SetImage(self.image, 44, -4, False)
                
                # Display calendar
                graphics.DrawText(canvas, self.fontSmall, 3, 6, self.color['lime'], day)
                graphics.DrawText(canvas, self.fontSmall, 20, 6, self.color['lime'], dt)
                graphics.DrawText(canvas, self.fontSmall, 30, 6, self.color['yellow'], mo)
                
                # Display clock
                graphics.DrawText(canvas, self.font, 3, 18, self.color['white'], clk)
                
                # Display weather information if available
                if current and highest and lowest:
                    graphics.DrawText(canvas, self.font, 42, 30, self.color['skyBlue'], current)
                    graphics.DrawText(canvas, self.fontSmall, 28, 25, self.color['pink'], highest)
                    graphics.DrawText(canvas, self.fontSmall, 28, 31, self.color['lightBlue'], lowest)
                
                # Display prayer information
                graphics.DrawText(canvas, self.fontSmall, 5, 25, self.color['grey'], str(prayer))
                graphics.DrawText(canvas, self.fontSmall, 5, 31, self.color['darkBlue'], str(next_prayer_time))
                
                # Update display
                canvas = self.matrix.SwapOnVSync(canvas)
                time.sleep(0.1)  # Small sleep to prevent high CPU usage
        except KeyboardInterrupt:
            return
        except Exception as e:
            logger.error(f"Error in display_clock_weather: {e}")
            return

    def display_gif(self, canvas, message):
        try:
            # Check if the specified GIF exists
            if message in GIFS and os.path.exists(GIFS[message]):
                # Load the GIF
                self.image = Image.open(GIFS[message])
                frame_count = getattr(self.image, "n_frames", 0)
                
                if frame_count == 0:
                    logger.error(f"Not a valid animated GIF: {GIFS[message]}")
                    self.display_hmarquee(canvas, f"Invalid GIF: {message}")
                    return
                
                logger.info(f"Playing GIF {message} with {frame_count} frames")
                
                while True:
                    # Get current time for clock display
                    day, dt, mo, clk = get_date_time()
                    
                    # Choose text color based on GIF
                    clr = self.color['black'] if message == 'fireplace' else self.color['white']
                    
                    # Display each frame of the GIF
                    for frame in range(frame_count):
                        canvas.Clear()
                        try:
                            self.image.seek(frame)
                            frame_image = self.image.convert('RGB')
                            canvas.SetImage(frame_image, 0, 0, False)
                            
                            # Display time on top of GIF
                            graphics.DrawText(canvas, self.font, 3, 18, clr, clk)
                            
                            canvas = self.matrix.SwapOnVSync(canvas)
                            
                            # Control frame rate (adjust as needed for smooth playback)
                            time.sleep(0.1)
                        except Exception as e:
                            logger.error(f"Error displaying frame {frame}: {e}")
                            continue
            else:
                logger.error(f"GIF file not found at {GIFS.get(message, 'unknown')}")
                self.display_hmarquee(canvas, f"GIF {message} not found")
        except KeyboardInterrupt:
            canvas.Clear()
            return
        except Exception as e:
            logger.error(f"Error in display_gif: {e}")
            return

    def display_hmarquee(self, canvas, message):
        try:
            pos = canvas.width
            length = 0
            
            # Continuously scroll the text until it's off-screen
            while True:
                canvas.Clear()
                length = graphics.DrawText(canvas, self.font, pos, 20,
                                   self.color['white'], message)
                pos -= 1
                
                # If the text has completely scrolled off the left side, restart
                if pos + length < 0:
                    pos = canvas.width
                
                time.sleep(0.02)
                canvas = self.matrix.SwapOnVSync(canvas)
        except KeyboardInterrupt:
            return
        except Exception as e:
            logger.error(f"Error in display_hmarquee: {e}")
            return

#############################################
#              Main Function                #
#############################################
if __name__ == "__main__":
    try:
        # Create required directories
        ensure_directory_exists(IMAGES_DIR)
        ensure_directory_exists(GIF_DIR)
        ensure_directory_exists(WEATHER_ICONS_DIR)
        
        # Start InfoCube
        info_cube = InfoCube()
        if not info_cube.process():
            info_cube.print_help()
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)