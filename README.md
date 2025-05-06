# Raspberry Pi RGB LED Matrix InfoCube

This project provides a Python framework for controlling RGB LED matrices with a Raspberry Pi using the [rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) library.

## Features

- Simple interface for controlling RGB matrices
- Text rendering with multiple fonts
- Clock display with weather and prayer times
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

## Installation and System Setup

### 1. Clone the Repository

```bash
git clone https://github.com/sufinawaz/rpi-led-matrix.git
cd rgb-led-matrix-infocube
```

### 2. Run the Setup Script

The included `setup.py` script will handle most of the installation process automatically:

```bash
sudo python3 setup.py
```

The setup script performs the following actions:
- Creates the project directory structure
- Installs required system packages
- Clones and installs the rpi-rgb-led-matrix library
- Installs Python dependencies
- Creates a configuration file
- Creates a launcher script with proper permissions
- Sets up a global command (`infocube`)

### 3. System-Level Changes

#### Environment Variables

To use the weather display functionality, set up the OpenWeatherMap API key:

```bash
echo 'export WEATHER_APP_ID="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

#### Preserve Environment Variables for sudo

To ensure that environment variables are preserved when running with sudo:

```bash
sudo visudo
```

Add the following line:

```
Defaults env_keep += "WEATHER_APP_ID"
```

#### Permissions for GPIO Access

The RGB Matrix library requires root privileges to access GPIO. Running `setup.py` will handle this, but it's important to understand why `sudo` is needed.

#### Running as a Service

To run the InfoCube as a system service that starts on boot:

1. Create a systemd service file:

```bash
sudo nano /etc/systemd/system/infocube.service
```

2. Add the following content:

```
[Unit]
Description=RGB LED Matrix InfoCube
After=network.target

[Service]
Type=simple
User=root
Environment="WEATHER_APP_ID=your_api_key_here"
ExecStart=/usr/local/bin/infocube --display-mode=clock
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable infocube.service
sudo systemctl start infocube.service
```

## Configuration

### Config File

The main configuration file is located at `config.ini` in the project root. Edit this file to customize your setup:

```ini
[MATRIX]
rows = 32
cols = 64
chain_length = 1
brightness = 30
hardware_mapping = adafruit-hat
gpio_slowdown = 2

[API]
WEATHER_APP_ID = YOUR_API_KEY_HERE
```

## Running the Application

### Manual Execution

After running the setup script, you can start the application using:

```bash
sudo infocube
```

Or with specific options:

```bash
sudo infocube --display-mode=clock --gif-name=matrix
```

### Display Modes

The InfoCube supports various display modes:

- `--display-mode=clock`: Shows time, date, weather, and prayer times
- `--display-mode=prayer`: Shows prayer times
- `--display-mode=gif`: Displays an animated GIF (use with `--gif-name=name_of_gif`)
- `--display-mode=intro`: Shows the intro logo

## Debugging and Maintenance

### Viewing Logs

When running as a service, view logs with:

```bash
sudo journalctl -u infocube.service -f
```

For manual execution, logs are printed to the console.

### Common Debugging Commands

Check if the service is running:

```bash
sudo systemctl status infocube.service
```

Restart the service:

```bash
sudo systemctl restart infocube.service
```

Stop the service:

```bash
sudo systemctl stop infocube.service
```

Check for GPIO conflicts:

```bash
gpio readall
```

Test the matrix directly using the rpi-rgb-led-matrix examples:

```bash
cd rpi-rgb-led-matrix/examples-api-use
sudo ./demo -D 0 --led-rows=32 --led-cols=32 --led-gpio-mapping=adafruit-hat
```

### Troubleshooting GPIO Issues

1. Ensure correct permissions and access:

```bash
sudo usermod -a -G gpio,spi,i2c pi
```

2. Check for GPIO pin usage conflicts:

```bash
sudo cat /sys/kernel/debug/gpio
```

3. Test basic GPIO functionality:

```bash
sudo apt-get install -y wiringpi
gpio -g mode 17 out
gpio -g write 17 1
gpio -g write 17 0
```

### Hardware Diagnostics

Run this diagnostic script to verify hardware connections:

```bash
wget -O - https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/rgb-matrix.sh | bash
```

Select the "Quality test" option to verify your matrix connections.

### Upgrading and Maintenance

To update the application:

```bash
cd rgb-led-matrix-infocube
git pull
sudo python3 setup.py
sudo systemctl restart infocube.service
```

## Project Structure

- `src/`: Source code
  - `matrix_manager.py`: Core matrix control class
  - `text_renderer.py`: Text display utilities
  - `infocube.py`: Main application
- `resources/`: Font and image files
- `config.ini`: Configuration file
- `setup.py`: Installation script

## Advanced Configuration

### Hardware Mapping

If you're using a different GPIO mapping than the Adafruit HAT, update both:
1. The `hardware_mapping` setting in `config.ini`
2. The `--led-gpio-mapping` parameter in your service file

### Display Chain Configuration

For multiple panels chained together, update:
1. The `chain_length` and `parallel` settings in `config.ini`
2. Add corresponding command line arguments to your service file

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


# Remote Control for InfoCube

The InfoCube includes a modern web-based remote control interface, allowing you to manage your display from any device connected to the same network.

## Features

- Change between all display modes (clock, prayer times, intro, GIF)
- Modern, responsive mobile-friendly interface
- Upload new GIFs directly from your device
- Add GIFs from any URL on the internet
- Rename and delete GIFs
- Secure API key management
- Real-time display status monitoring
- Simple one-click activation of display modes

## Setup

The remote control is automatically set up during installation. No additional configuration is required.

### Access the Remote Control

1. Find your Raspberry Pi's IP address:
   ```bash
   hostname -I
   ```

2. Access the web interface from any device on the same network by navigating to:
   ```
   http://YOUR_PI_IP:8080
   ```

### Static IP Configuration (Recommended)

For easier access, configure your Raspberry Pi with a static IP:

1. Edit the dhcpcd.conf file:
   ```bash
   sudo nano /etc/dhcpcd.conf
   ```

2. Add these lines (adjust for your network):
   ```
   interface wlan0
   static ip_address=192.168.1.100/24
   static routers=192.168.1.1
   static domain_name_servers=192.168.1.1 8.8.8.8
   ```

3. Reboot the Pi:
   ```bash
   sudo reboot
   ```

## Using the Remote Control

### Display Modes

Click on any of the display mode buttons to immediately change the InfoCube's display:
- **Clock**: Shows time, date, weather, and next prayer time
- **Prayer**: Displays all prayer times
- **Intro**: Shows the intro logo

### GIF Management

The GIFs tab provides three options:
1. **Gallery**: View and activate existing GIFs
2. **Add from URL**: Download a GIF from any URL
3. **Upload**: Upload GIFs directly from your device

### Settings

- **API Key**: Securely manage your OpenWeatherMap API key
- **Restart**: Restart the InfoCube display if needed

## Services Management

The remote control uses two systemd services:

1. **infocube-display.service**: Controls the LED matrix display
2. **infocube-remote.service**: Provides the web interface

### Service Commands

Check status:
```bash
sudo systemctl status infocube-display.service
sudo systemctl status infocube-remote.service
```

Restart services:
```bash
sudo systemctl restart infocube-display.service
sudo systemctl restart infocube-remote.service
```

View logs:
```bash
sudo journalctl -u infocube-display.service -n 50
sudo journalctl -u infocube-remote.service -n 50
```

## Troubleshooting

If you encounter issues with the remote control:

1. **Web interface not accessible**:
   - Ensure the remote control service is running
   - Check your network connection
   - Verify you're using the correct IP address

2. **Changes not applying to the display**:
   - Check if the display service is running
   - Restart both services

3. **Cannot upload GIFs**:
   - Check if the 'resources/images/gifs' directory exists and has proper permissions
   - Ensure there's enough disk space

4. **Weather data not showing**:
   - Verify your API key is correctly set
   - Check internet connectivity

## Security Considerations

The remote control interface is designed for use on trusted local networks only. It does not include authentication, so anyone on your network can control the InfoCube.