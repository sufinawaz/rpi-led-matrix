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

# Setup basic logging
logging.basicConfig(
    level=logging.DEBUG,
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

# Image paths
IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")
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

#############################################
#              Utility Functions            #
#############################################
def get_date_time(h24format=False, minus_mins=0):
    tm = datetime.now() - timedelta(minutes=minus_mins)
    return tm.strftime('%a'), \
           tm.strftime('%d'), \
           tm.strftime('%b'), \
           tm.strftime('%H:%M') if h24format else tm.strftime('%I:%M%p')[:-1].lower()

def get_openweather_data():
    logger.info('Fetching OpenWeatherMap data')
    try:
        if not WEATHER_APP_ID:
            logger.warning("WEATHER_APP_ID environment variable not set")
            return None, None, None, None
            
        r = requests.get(
            f'https://openweathermap.org/data/2.5/weather?id=4791160&appid={WEATHER_APP_ID}&units=imperial',
            headers={'Accept': 'application/json'})
        
        # Check if the request was successful
        if r.status_code != 200:
            logger.error(f"Weather API returned status code {r.status_code}")
            return None, None, None, None
            
        j = r.json()
        current = f"{round(j['main']['temp'])}°"
        lowest = str(round(j['main']['temp_min']))
        highest = str(round(j['main']['temp_max']))
        icon = os.path.join(WEATHER_ICONS_DIR, f"{j['weather'][0]['icon']}.jpg")
        return current, lowest, highest, icon
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None, None, None, None

def get_prayer_times():
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
    day, dt, mo, clk = get_date_time(True, 10)
    for i in range(5):
        if times[i] > clk:
            return times[i], PRAYER_NAMES[i]
    return times[0], PRAYER_NAMES[0]

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
            sys.exit(0)

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
            'skyBlue': graphics.Color(0, 191, 255)
        }
        
        self.fontSmall = graphics.Font()
        self.font = graphics.Font()
        
        # Load fonts
        try:
            self.fontSmall.LoadFont(FONT_SMALL_PATH)
            self.font.LoadFont(FONT_MEDIUM_PATH)
        except Exception as e:
            logger.error(f"Failed to load fonts: {e}")
            logger.info(f"Looking for fonts in {FONT_DIR}")
            sys.exit(1)

    def run(self):
        # Default to clock display
        display_mode = "clock"
        canvas = self.matrix.CreateFrameCanvas()
        
        logger.info(f"Starting with display mode: {display_mode}")
        
        if display_mode == "clock":
            self.display_clock_weather(canvas)
        elif display_mode == "prayer":
            self.display_prayer_times(canvas)
        elif display_mode == "intro":
            self.display_wm_logo(canvas)
        else:
            self.display_hmarquee(canvas, "Welcome to InfoCube")

    def display_wm_logo(self, canvas):
        canvas.Clear()
        try:
            if os.path.exists(WOOD_MISTRY_LOGO):
                self.image = Image.open(WOOD_MISTRY_LOGO).convert('RGB')
                canvas.SetImage(self.image, 0, 0, False)
                canvas = self.matrix.SwapOnVSync(canvas)
                start_time = time.perf_counter()
                while True:
                    now = time.perf_counter()
                    time.sleep(1)
                    if (now - start_time) > 2:
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
            times = get_prayer_times()
            next_prayer_time, _ = get_next_prayer_time(times)
            canvas.Clear()
            
            if os.path.exists(MOSQUE_LOGO):
                self.image = Image.open(MOSQUE_LOGO).convert('RGB')
                canvas.SetImage(self.image, 44, 2, False)
            
            start_time = time.perf_counter()
            while True:
                now = time.perf_counter()
                if (now - start_time) > 60:
                    times = get_prayer_times()
                    next_prayer_time, _ = get_next_prayer_time(times)
                    start_time = now
                
                canvas.Clear()
                if hasattr(self, 'image') and self.image:
                    canvas.SetImage(self.image, 44, 2, False)
                
                for i in range(5):
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
            day, dt, mo, clk = get_date_time()
            times = get_prayer_times()
            next_prayer_time, prayer = get_next_prayer_time(times)
            
            # preload calendar and date while weather data loads
            graphics.DrawText(canvas, self.fontSmall, 3, 6, graphics.Color(173, 255, 47), day)
            graphics.DrawText(canvas, self.fontSmall, 20, 6, graphics.Color(173, 255, 47), dt)
            graphics.DrawText(canvas, self.fontSmall, 30, 6, graphics.Color(255, 255, 0), mo)
            # date
            graphics.DrawText(canvas, self.font, 3, 18, self.color['white'], clk)
            canvas = self.matrix.SwapOnVSync(canvas)
            
            # (slow) fetch weather data
            current, lowest, highest, icon = get_openweather_data()
            if icon and os.path.exists(icon):
                self.image = Image.open(icon).convert('RGB')
                self.image.thumbnail((24, 24), Image.ANTIALIAS)
            
            start_time = time.perf_counter()
            while True:
                now = time.perf_counter()
                if (now - start_time) > 600:  # Update every 10 minutes
                    times = get_prayer_times()
                    next_prayer_time, prayer = get_next_prayer_time(times)
                    c, l, h, i = get_openweather_data()
                    if c and l and h and i and os.path.exists(i):
                        current, lowest, highest, icon = c, l, h, i
                        self.image = Image.open(icon).convert('RGB')
                        self.image.thumbnail((24, 24), Image.ANTIALIAS)
                    start_time = now
                
                canvas.Clear()
                day, dt, mo, clk = get_date_time()
                
                # weather icon
                if hasattr(self, 'image') and self.image:
                    canvas.SetImage(self.image, 44, -4, False)
                
                # calendar
                graphics.DrawText(canvas, self.fontSmall, 3, 6, graphics.Color(173, 255, 47), day)
                graphics.DrawText(canvas, self.fontSmall, 20, 6, graphics.Color(173, 255, 47), dt)
                graphics.DrawText(canvas, self.fontSmall, 30, 6, graphics.Color(255, 255, 0), mo)
                
                # clock
                graphics.DrawText(canvas, self.font, 3, 18, self.color['white'], clk)
                
                # weather
                if current and highest and lowest:
                    graphics.DrawText(canvas, self.font, 42, 30, graphics.Color(135, 206, 235), current)
                    graphics.DrawText(canvas, self.fontSmall, 28, 25, graphics.Color(255, 114, 118), highest)
                    graphics.DrawText(canvas, self.fontSmall, 28, 31, graphics.Color(173, 216, 230), lowest)
                
                # prayer
                graphics.DrawText(canvas, self.fontSmall, 5, 25, graphics.Color(150, 150, 150), str(prayer))
                graphics.DrawText(canvas, self.fontSmall, 5, 31, graphics.Color(30, 144, 255), str(next_prayer_time))
                
                canvas = self.matrix.SwapOnVSync(canvas)
                time.sleep(0.1)  # Small sleep to prevent high CPU usage
        except KeyboardInterrupt:
            return
        except Exception as e:
            logger.error(f"Error in display_clock_weather: {e}")
            return

    def display_gif(self, canvas, message):
        try:
            if message in GIFS and os.path.exists(GIFS[message]):
                self.image = Image.open(GIFS[message])
                while True:
                    day, dt, mo, clk = get_date_time()
                    # preload calendar and date while weather data loads
                    clr = self.color['black'] if message in 'fireplace' else self.color['white']
                    for frame in range(self.image.n_frames):
                        canvas.Clear()
                        self.image.seek(frame)
                        canvas.SetImage(self.image.convert('RGB'), 0, 0, False)
                        graphics.DrawText(canvas, self.font, 3, 18, clr, clk)
                        canvas = self.matrix.SwapOnVSync(canvas)
                        time.sleep(0.1)
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
            while True:
                canvas.Clear()
                length = graphics.DrawText(canvas, self.font, pos, 20,
                                    self.color['white'], message)
                pos -= 1
                if pos + length < 0:
                    break
                time.sleep(0.02)
                canvas = self.matrix.SwapOnVSync(canvas)
        except Exception as e:
            logger.error(f"Error in display_hmarquee: {e}")
            return

#############################################
#              Main Function                #
#############################################
if __name__ == "__main__":
    try:
        # Create directories if they don't exist
        os.makedirs(IMAGES_DIR, exist_ok=True)
        os.makedirs(GIF_DIR, exist_ok=True)
        os.makedirs(WEATHER_ICONS_DIR, exist_ok=True)
        
        # Display clock by default
        info_cube = InfoCube()
        if not info_cube.process():
            info_cube.print_help()
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)
