#!/usr/bin/env python
import time
from datetime import datetime
from PIL import Image, ImageDraw
import logging
import sys
import os
import argparse
import requests
from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions

# Configure logging - simplified
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

#############################################
#          Configuration Settings           #
#############################################
# Get the WEATHER_APP_ID from environment variable
WEATHER_APP_ID = os.getenv('WEATHER_APP_ID', '')

# Set up paths
SCRIPT_PATH = os.path.abspath(__file__)
SRC_DIR = os.path.dirname(SCRIPT_PATH)
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# Resource directories
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "resources")
IMAGES_DIR = os.path.join(RESOURCES_DIR, "images")
GIF_DIR = os.path.join(IMAGES_DIR, "gifs")
WEATHER_ICONS_DIR = os.path.join(IMAGES_DIR, "weather-icons")
FONT_DIR = os.path.join(RESOURCES_DIR, "fonts")

# Font paths
FONT_SMALL_PATH = os.path.join(FONT_DIR, "4x6.bdf")
FONT_MEDIUM_PATH = os.path.join(FONT_DIR, "7x13.bdf")

# Image paths
WOOD_MISTRY_LOGO = os.path.join(IMAGES_DIR, "wm.jpg")
MOSQUE_LOGO = os.path.join(IMAGES_DIR, "mosque.jpg")

# Prayer names
PRAYER_NAMES = ('Fajr', 'Zuhr', 'Asr', 'Magh', 'Isha')

# Default images for when files aren't found
DEFAULT_WEATHER_ICON = Image.new('RGB', (24, 24), color=(0, 0, 0))
DEFAULT_DRAW = ImageDraw.Draw(DEFAULT_WEATHER_ICON)
DEFAULT_DRAW.ellipse((4, 4, 20, 20), fill=(255, 255, 0))  # Simple sun icon

# Update intervals (in seconds)
WEATHER_UPDATE_INTERVAL = 3600  # 1 hour

def check_directories():
    """Check that required directories exist"""
    dirs = [RESOURCES_DIR, IMAGES_DIR, GIF_DIR, WEATHER_ICONS_DIR, FONT_DIR]
    for directory in dirs:
        if os.path.exists(directory):
            logger.info(f"Using directory: {directory}")
        else:
            logger.warning(f"Directory does not exist: {directory}")

def get_date_time(h24format=False):
    """Get formatted date and time"""
    tm = datetime.now()
    day = tm.strftime('%a')
    date = tm.strftime('%d')
    month = tm.strftime('%b')
    time_str = tm.strftime('%H:%M') if h24format else tm.strftime('%I:%M%p')[:-1].lower()
    return day, date, month, time_str

def get_weather_icon_path(icon_code):
    """Get the path to a weather icon file"""
    icon_path = os.path.join(WEATHER_ICONS_DIR, f"{icon_code}.png")
    if os.path.exists(icon_path):
        return icon_path
    else:
        # Return a default icon path if the specific one doesn't exist
        default_icon = os.path.join(WEATHER_ICONS_DIR, "01d.png")  # Clear day as default
        return default_icon if os.path.exists(default_icon) else None

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
        
        if r.status_code != 200:
            logger.error(f"Weather API returned status code {r.status_code}")
            return None, None, None, None
            
        j = r.json()
        current = f"{round(j['main']['temp'])}°"
        lowest = str(round(j['main']['temp_min']))
        highest = str(round(j['main']['temp_max']))
        
        # Get the icon path
        icon_code = j['weather'][0]['icon']
        icon_path = get_weather_icon_path(icon_code)
        
        return current, lowest, highest, icon_path
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None, None, None, None

def get_prayer_times():
    """Fetch prayer times"""
    logger.info('Fetching prayer times from API')
    try:
        r = requests.get('http://api.aladhan.com/v1/timings?latitude=38.903481&longitude=-77.262817&method=1&school=1',
                         headers={'Accept': 'application/json'})
        
        if r.status_code != 200:
            logger.error(f"Prayer times API returned status code {r.status_code}")
            return None
            
        j = r.json()
        timings = j['data']['timings']
        fajr, dhuhr, asr, maghrib, isha = timings['Fajr'], timings['Dhuhr'], timings['Asr'], timings['Maghrib'], timings['Isha']
        
        logger.info(f"Received prayer times: Fajr={fajr}, Dhuhr={dhuhr}, Asr={asr}, Maghrib={maghrib}, Isha={isha}")
        return fajr, dhuhr, asr, maghrib, isha
    except Exception as e:
        logger.error(f"Error fetching prayer times: {e}")
        return None

def get_next_prayer_time(times):
    """
    Get the next prayer time based on current time
    Returns (time, name) tuple or (None, None) if times is None
    """
    if not times:
        return None, None
        
    _, _, _, current_time = get_date_time(True)
    
    for i in range(5):
        if times[i] > current_time:
            logger.info(f"Next prayer is {PRAYER_NAMES[i]} at {times[i]}")
            return times[i], PRAYER_NAMES[i]
    
    # If all prayer times have passed for today, return the first prayer for tomorrow
    logger.info(f"All prayer times for today have passed. Next prayer is {PRAYER_NAMES[0]} at {times[0]} tomorrow")
    return times[0], PRAYER_NAMES[0]

def load_image(image_path, size=None):
    """Load an image with error handling and optional resizing"""
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return None

    try:
        # Open with transparency preserved, then explicitly convert to RGB with background 
        if image_path.lower().endswith(('.png', '.gif')):
            # For image formats that might have transparency
            image = Image.open(image_path).convert('RGBA')
            
            # Create a white background image
            background = Image.new('RGBA', image.size, (0, 0, 0, 255))
            
            # Paste the image on the background, using alpha as mask
            image = Image.alpha_composite(background, image).convert('RGB')
        else:
            # For image formats without transparency (like JPG)
            image = Image.open(image_path).convert('RGB')
        
        if size:
            # Use LANCZOS for best quality resizing
            image.thumbnail(size, Image.LANCZOS)
            
        return image
    except Exception as e:
        logger.error(f"Error loading image {image_path}: {e}")
        return None

#############################################
#              InfoCube Class               #
#############################################
class InfoCube:
    image = None
    
    def __init__(self, display_mode="clock", gif_name="matrix"):
        self.display_mode = display_mode
        self.gif_name = gif_name
        
        # Setup matrix with fixed parameters for 32x64 display
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.brightness = 40
        options.hardware_mapping = 'adafruit-hat'
        options.gpio_slowdown = 2
        options.led_rgb_sequence = 'RBG'
        options.drop_privileges = False  # --led-no-drop-privs always enabled
        
        self.matrix = RGBMatrix(options=options)
        
        # Define colors
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
            'pink': graphics.Color(255, 114, 118),
            'error': graphics.Color(255, 0, 0)
        }
        
        # Load fonts - assuming they exist in resources/fonts
        logger.info(f"Loading fonts from {FONT_DIR}")
        self.fontSmall = graphics.Font()
        self.font = graphics.Font()
        try:
            self.fontSmall.LoadFont(FONT_SMALL_PATH)
            self.font.LoadFont(FONT_MEDIUM_PATH)
        except Exception as e:
            logger.error(f"Error loading fonts: {e}")
    
    def run(self):
        """Run the InfoCube with the selected display mode"""
        canvas = self.matrix.CreateFrameCanvas()
        
        try:
            logger.info(f"Starting with display mode: {self.display_mode}")
            
            if self.display_mode == "clock":
                self.display_clock_weather(canvas)
            elif self.display_mode == "prayer":
                self.display_prayer_times(canvas)
            elif self.display_mode == "gif":
                self.display_gif(canvas, self.gif_name)
            elif self.display_mode == "intro":
                self.display_wm_logo(canvas)
            else:
                self.display_hmarquee(canvas, f"Welcome to InfoCube - {self.display_mode} mode")
        except KeyboardInterrupt:
            logger.info("Exiting...")
            canvas.Clear()
            self.matrix.SwapOnVSync(canvas)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
    
    def display_wm_logo(self, canvas):
        """Display the Wood Mistry logo"""
        canvas.Clear()
        image = load_image(WOOD_MISTRY_LOGO)
        if image:
            canvas.SetImage(image, 0, 0, False)
            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(5)  # Show for 5 seconds
        else:
            self.display_hmarquee(canvas, "InfoCube")
    
    def display_prayer_times(self, canvas):
        """Display prayer times"""
        # Get initial prayer times
        times = get_prayer_times()
        next_prayer_time, next_prayer_name = get_next_prayer_time(times)
        
        # Load mosque logo if available
        mosque_image = load_image(MOSQUE_LOGO)
        if mosque_image:
            self.image = mosque_image
        
        last_update_time = time.perf_counter()
        force_update = False
        
        while True:
            now = time.perf_counter()
            _, _, _, current_time = get_date_time(True)  # Get current time in HH:MM format
            
            # Check if we need to refresh prayer times based on next prayer time
            if next_prayer_time and current_time >= next_prayer_time:
                logger.info("Prayer time reached, updating to get next prayer")
                force_update = True
            
            # Update prayer times every 4 hours to ensure data is fresh
            # or if the next prayer time has passed or API previously failed
            if now - last_update_time > 14400 or force_update:
                logger.info("Fetching fresh prayer times data")
                times = get_prayer_times()
                if times:
                    next_prayer_time, next_prayer_name = get_next_prayer_time(times)
                last_update_time = now
                force_update = False
            
            # If API failed, retry every minute
            if not times and now - last_update_time > 60:
                logger.info("Previous API call failed, retrying")
                times = get_prayer_times()
                if times:
                    next_prayer_time, next_prayer_name = get_next_prayer_time(times)
                last_update_time = now
            
            canvas.Clear()
            
            # Display mosque image if available
            if self.image:
                canvas.SetImage(self.image, 44, 2, False)
            
            if times:
                # Display prayer times
                for i in range(5):
                    # Highlight the next prayer
                    timecolor = self.color['orange'] if times[i] == next_prayer_time else self.color['white']
                    graphics.DrawText(canvas, self.fontSmall, 5, (i+1)*6, self.color['skyBlue'], str(PRAYER_NAMES[i]))
                    graphics.DrawText(canvas, self.fontSmall, 23, (i+1)*6, timecolor, str(times[i]))
            else:
                # Display error message if API failed
                graphics.DrawText(canvas, self.fontSmall, 5, 15, self.color['error'], "Prayer API Error")
                graphics.DrawText(canvas, self.fontSmall, 5, 25, self.color['white'], "Retrying...")
            
            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(0.1)
    
    def display_clock_weather(self, canvas):
        """Display clock and weather information"""
        # Get initial data
        times = get_prayer_times()
        next_prayer_time, prayer = get_next_prayer_time(times)
        
        # Fetch weather data
        current, lowest, highest, icon_path = get_openweather_data()
        if icon_path and os.path.exists(icon_path):
            weather_image = load_image(icon_path, (24, 24))
            if weather_image:
                self.image = weather_image
        else:
            # Use default weather icon
            self.image = DEFAULT_WEATHER_ICON
        
        last_weather_update = time.perf_counter()
        last_prayer_update = time.perf_counter()
        force_prayer_update = False
        
        while True:
            now = time.perf_counter()
            _, _, _, current_time = get_date_time(True)  # Get current time in HH:MM format
            
            # Update weather data every 1 hour
            if now - last_weather_update > WEATHER_UPDATE_INTERVAL:
                logger.info("Updating weather data (hourly update)")
                c, l, h, i = get_openweather_data()
                if c and l and h and i:
                    current, lowest, highest, icon_path = c, l, h, i
                    weather_image = load_image(icon_path, (24, 24))
                    if weather_image:
                        self.image = weather_image
                last_weather_update = now
            
            # Check if we need to refresh prayer times based on time passing
            if next_prayer_time and current_time >= next_prayer_time:
                logger.info("Prayer time reached, updating to get next prayer")
                force_prayer_update = True
            
            # Update prayer times every 4 hours to ensure data is fresh
            if now - last_prayer_update > 14400 or force_prayer_update:
                logger.info("Updating prayer times")
                times = get_prayer_times()
                if times:
                    next_prayer_time, prayer = get_next_prayer_time(times)
                last_prayer_update = now
                force_prayer_update = False
            
            # Clear canvas for new frame
            canvas.Clear()
            
            # Get current time
            day, date, month, clock = get_date_time()
            
            # Display weather icon if available
            if self.image:
                canvas.SetImage(self.image, 44, -4, False)
            
            # Display calendar
            graphics.DrawText(canvas, self.fontSmall, 3, 6, self.color['lime'], day)
            graphics.DrawText(canvas, self.fontSmall, 20, 6, self.color['lime'], date)
            graphics.DrawText(canvas, self.fontSmall, 30, 6, self.color['yellow'], month)
            
            # Display clock
            graphics.DrawText(canvas, self.font, 3, 18, self.color['white'], clock)
            
            # Display weather information if available
            if current and highest and lowest:
                graphics.DrawText(canvas, self.font, 42, 30, self.color['skyBlue'], current)
                graphics.DrawText(canvas, self.fontSmall, 28, 25, self.color['pink'], highest)
                graphics.DrawText(canvas, self.fontSmall, 28, 31, self.color['lightBlue'], lowest)
            else:
                # Display error message if weather API failed
                graphics.DrawText(canvas, self.fontSmall, 42, 30, self.color['error'], "W-ERR")
            
            # Display prayer information if available
            if prayer and next_prayer_time:
                graphics.DrawText(canvas, self.fontSmall, 5, 25, self.color['grey'], str(prayer))
                graphics.DrawText(canvas, self.fontSmall, 5, 31, self.color['darkBlue'], str(next_prayer_time))
            else:
                # Display error message if prayer API failed
                graphics.DrawText(canvas, self.fontSmall, 5, 25, self.color['error'], "P-ERR")
            
            # Update display
            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(0.1)
    
    def display_gif(self, canvas, gif_name):
        """Display an animated GIF"""
        gif_path = os.path.join(GIF_DIR, f"{gif_name}.gif")
        
        if not os.path.exists(gif_path):
            logger.error(f"GIF file not found: {gif_path}")
            self.display_hmarquee(canvas, f"GIF {gif_name} not found")
            return
        
        # Load the GIF
        self.image = Image.open(gif_path)
        frame_count = getattr(self.image, "n_frames", 0)
        
        if frame_count == 0:
            logger.error(f"Not a valid animated GIF: {gif_path}")
            self.display_hmarquee(canvas, f"Invalid GIF: {gif_name}")
            return
        
        logger.info(f"Playing GIF {gif_name} with {frame_count} frames")
        
        while True:
            # Get current time for clock display
            _, _, _, clock = get_date_time()
            
            # Display each frame of the GIF
            for frame in range(frame_count):
                canvas.Clear()
                
                self.image.seek(frame)
                frame_image = self.image.convert('RGB')
                canvas.SetImage(frame_image, 0, 0, False)
                
                # Display time centered on the GIF
                text_width = len(clock) * 8  # Approximate width per character
                x_pos = (canvas.width - text_width) // 2
                y_pos = canvas.height // 2  # Center vertically
                
                graphics.DrawText(canvas, self.font, x_pos, y_pos, self.color['white'], clock)
                
                canvas = self.matrix.SwapOnVSync(canvas)
                time.sleep(0.1)
    
    def display_hmarquee(self, canvas, message):
        """Display scrolling text"""
        pos = canvas.width
        length = 0
        
        # Continuously scroll the text
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

#############################################
#              Main Function                #
#############################################
if __name__ == "__main__":
    # Parse command line arguments - simplified to just the essentials
    parser = argparse.ArgumentParser(description="RGB LED Matrix Display for Raspberry Pi")
    parser.add_argument("--display-mode", help="Display mode: clock, prayer, gif, intro", default="clock")
    parser.add_argument("--gif-name", help="GIF to display (if display-mode is 'gif')", default="matrix")
    args = parser.parse_args()
    
    # Check directories
    check_directories()
    
    # Verify we're running as root (required for GPIO access)
    if os.geteuid() != 0:
        logger.error("This program must be run as root (sudo) for GPIO access")
        sys.exit(1)
    
    try:
        # Start InfoCube
        logger.info(f"Starting InfoCube with mode: {args.display_mode}")
        info_cube = InfoCube(display_mode=args.display_mode, gif_name=args.gif_name)
        info_cube.run()
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)