# Raspberry Pi RGB LED Matrix Control

This project provides a Python framework for controlling RGB LED matrices with a Raspberry Pi using the excellent [rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) library.

## Features

- Simple interface for controlling RGB matrices
- Text rendering with multiple fonts
- Scrolling text animation
- Clock display
- Image and GIF display
- API integration (Weather and Prayer Times)
- Animation framework for creating custom animations

## Hardware Requirements

- Raspberry Pi (Zero 2W or newer recommended)
- Adafruit RGB Matrix HAT or compatible hardware
- RGB LED Matrix panel (32x32, 64x32, 64x64, etc.)
- 5V power supply with sufficient current for your matrix
- Micro SD card with Raspberry Pi OS

## Software Requirements

- Raspberry Pi OS (Buster or newer)
- Python 3.6+
- Required system packages and Python libraries (see Installation)

## Installation

### 1. System Packages

First, install the required system packages:

```bash
sudo apt-get update
sudo apt-get install -y python3-dev python3-pillow python3-pip libgraphicsmagick++-dev libwebp-dev git
```

### 2. Install the RGB Matrix Library

Clone and install the rgb-matrix library:

```bash
# Clone the library
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix

# Install
make
cd bindings/python
make build
sudo make install
```

### 3. Python Dependencies

Install required Python dependencies:

```bash
sudo pip3 install requests configparser
```

### 4. System Configuration

#### Preserve Environment Variables for sudo

To ensure that environment variables like WEATHER_APP_ID are preserved when running with sudo:

```bash
sudo visudo
```

Add the following line to the sudoers file:

```
Defaults env_keep += "WEATHER_APP_ID"
```

Save and exit the editor.

#### Set up API Keys

For the weather display to work, you'll need an OpenWeatherMap API key:

1. Register at [OpenWeatherMap](https://openweathermap.org/api) to get an API key
2. Add your API key to your environment by adding this line to your `~/.bashrc` file:

```bash
export WEATHER_APP_ID="your_api_key_here"
```

Then reload your .bashrc file:

```bash
source ~/.bashrc
```

Alternatively, you can create a config.ini file in the same directory as the script:

```ini
[API]
WEATHER_APP_ID = your_api_key_here
```

#### Directory Structure

Create the necessary directories for images and other resources:

```bash
# Create the base directory structure
mkdir -p ~/led/images/gifs
mkdir -p ~/led/images/weather-icons
```

### 5. Running the InfoCube

The standard command to run the InfoCube is:

```bash
sudo python3 infocube.py
```

You can use these default settings for a 32x64 matrix with an Adafruit HAT:

```bash
sudo python3 infocube.py --led-rows=32 --led-cols=64 --led-gpio-mapping=adafruit-hat --led-rgb-sequence=rbg --led-brightness=40 --led-no-drop-privs --led-slowdown-gpio=2 --led-pwm-bits=8 --led-scan-mode=0
```

#### Display Modes

The InfoCube supports various display modes:

- `--display-mode=clock`: Shows time, date, weather, and prayer times
- `--display-mode=prayer`: Shows prayer times
- `--display-mode=gif`: Displays an animated GIF
- `--display-mode=intro`: Shows the intro logo

For GIF mode, specify a GIF name:

```bash
sudo python3 infocube.py --display-mode=gif --gif-name=matrix
```

## Troubleshooting

### Common Issues

#### Permission Denied

If you see permission errors:

```
Error accessing GPIO
```

Make sure you are running the script with sudo or that the `--led-no-drop-privs` option is used.

#### Missing Fonts

If you see errors about missing fonts:

```
Error loading font
```

The fonts should be available in the rpi-rgb-led-matrix/fonts directory. Update your FONT_DIR path if necessary.

#### Weather API Issues

If weather information isn't displaying:

1. Check that your WEATHER_APP_ID environment variable is set
2. Ensure your internet connection is working
3. Verify your API key is valid

## Advanced Configuration

For more advanced matrix configurations, refer to the [rpi-rgb-led-matrix documentation](https://github.com/hzeller/rpi-rgb-led-matrix#changing-parameters-via-command-line-flags).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.


## Remote Control

The InfoCube can be controlled remotely from your phone or any other device connected to the same WiFi network.

### Features
- View current display mode and status
- Switch between clock, prayer times, and intro modes
- Select and display GIFs
- Restart the InfoCube display

### Setup
1. The remote control is automatically installed and configured during setup
2. Access the remote control interface by navigating to:


### How It Works
- The system runs two services:
- `infocube-display.service`: Controls the LED matrix display
- `infocube-remote.service`: Provides the web interface
- Changes made through the web interface update the display service
- The display automatically starts in clock mode on boot

### Troubleshooting
If you encounter issues with the remote control:
1. Check if both services are running:
sudo systemctl status infocube-display.service
sudo systemctl status infocube-remote.service
2. Restart services if needed:
sudo systemctl restart infocube-display.service
sudo systemctl restart infocube-remote.service
3. View logs for more information:
sudo journalctl -u infocube-display.service -n 50
sudo journalctl -u infocube-remote.service -n 50
