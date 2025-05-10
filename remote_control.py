#!/usr/bin/env python
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import subprocess
import os
import logging
import time
import requests
import uuid
from werkzeug.utils import secure_filename
import shutil
import re
import json
from api_client import APIClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Replace the API client instantiation after the app creation
app = Flask(__name__)
app.secret_key = os.urandom(24)
# Create API client instance
api_client = APIClient(host='localhost', port=8081)

# Use the correct project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ''))
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")
GIF_DIR = os.path.join(PROJECT_ROOT, "resources", "images", "gifs")

# Make sure the directories exist
os.makedirs(GIF_DIR, exist_ok=True)

def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    return {}

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def get_plugin_config(plugin_name):
    """Get configuration for a specific plugin"""
    config = load_config()
    return config.get("plugins", {}).get("settings", {}).get(plugin_name, {})

def update_plugin_config(plugin_name, plugin_config):
    """Update configuration for a specific plugin"""
    config = load_config()

    if "plugins" not in config:
        config["plugins"] = {}
    if "settings" not in config["plugins"]:
        config["plugins"]["settings"] = {}

    config["plugins"]["settings"][plugin_name] = plugin_config

    return save_config(config)

def scan_gifs():
    """Get list of available GIFs"""
    available_gifs = []
    if os.path.exists(GIF_DIR):
        for file in os.listdir(GIF_DIR):
            if file.endswith('.gif'):
                available_gifs.append(os.path.splitext(file)[0])
    logger.info(f"Found GIFs: {available_gifs}")
    return sorted(available_gifs)

# Replace the change_display_mode function with this version:
def change_display_mode(mode, gif_name=None):
    """Change the InfoCube display mode by communicating with the running application"""
    # First, try to use the API client
    if mode == "gif" and gif_name:
        success = api_client.set_gif(gif_name)

        # Update gif plugin configuration in config file too
        if success:
            gif_config = get_plugin_config("gif")
            gif_config["current_gif"] = gif_name
            update_plugin_config("gif", gif_config)
            return True
    else:
        success = api_client.set_mode(mode)
        if success:
            return True

    # If API client fails (service not running with API), fall back to the old method
    logger.warning("API client failed to change mode, falling back to service restart method")

    # Build the ExecStart command
    exec_command = f"/usr/bin/python3 {PROJECT_ROOT}/src/infocube.py --display-mode={mode}"
    if mode == "gif" and gif_name:
        exec_command += f" --gif-name={gif_name}"

        # Update gif plugin configuration
        gif_config = get_plugin_config("gif")
        gif_config["current_gif"] = gif_name
        update_plugin_config("gif", gif_config)

    # Get current environment variables from the service
    weather_api_key = get_weather_api_key()

    # Modify the service file
    try:
        logger.info(f"Updating service to mode: {mode}")

        # Create a new temporary service file
        with open('/tmp/infocube-display.service', 'w') as f:
            f.write(f"""[Unit]
Description=InfoCube LED Matrix Display
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={PROJECT_ROOT}
ExecStart={exec_command}
Environment="WEATHER_APP_ID={weather_api_key}"
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
""")

        # Replace the existing service file
        subprocess.run(["sudo", "cp", "/tmp/infocube-display.service", "/etc/systemd/system/infocube-display.service"], check=True)

        # Reload systemd and restart the service
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "restart", "infocube-display.service"], check=True)

        logger.info(f"Display mode changed to: {mode}")
        return True
    except Exception as e:
        logger.error(f"Error changing display mode: {e}")
        return False

# Replace the get_current_status function with this version:
def get_current_status():
    """Get the current status of the InfoCube display service"""
    # First, try to use the API client
    status_data = api_client.get_status()
    if status_data:
        # API is available
        current_mode = status_data.get('current_plugin', 'unknown')
        current_gif = status_data.get('current_gif', '')

        # Check if service is running
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "is-active", "infocube-display.service"],
                capture_output=True, 
                text=True, 
                check=False
            )
            service_status = result.stdout.strip()
            is_running = service_status == "active"
        except:
            service_status = "unknown"
            is_running = status_data.get('running', False)

        return is_running, service_status, current_mode, current_gif

    # If API client fails (service not running with API), fall back to the old method
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "is-active", "infocube-display.service"],
            capture_output=True, 
            text=True, 
            check=False
        )
        status = result.stdout.strip()

        # Default values
        current_mode = "unknown"
        current_gif = ""

        # If service is running, get the command to see the current mode
        if status == "active":
            cmd_result = subprocess.run(
                ["sudo", "systemctl", "show", "infocube-display.service", "-p", "ExecStart"],
                capture_output=True,
                text=True,
                check=False
            )
            cmd_line = cmd_result.stdout.strip()

            # Extract mode from command line
            if "--display-mode=clock" in cmd_line:
                current_mode = "clock"
            elif "--display-mode=prayer" in cmd_line:
                current_mode = "prayer"
            elif "--display-mode=intro" in cmd_line:
                current_mode = "intro"
            elif "--display-mode=moon" in cmd_line:
                current_mode = "moon"
            elif "--display-mode=stock" in cmd_line:
                current_mode = "stock"
            elif "--display-mode=weather" in cmd_line:
                current_mode = "weather"
            elif "--display-mode=wmata" in cmd_line:
                current_mode = "wmata"
            elif "--display-mode=gif" in cmd_line:
                current_mode = "gif"
                # Try to extract gif name
                if "--gif-name=" in cmd_line:
                    gif_part = cmd_line.split("--gif-name=")[1]
                    current_gif = gif_part.split(" ")[0]

            return True, status, current_mode, current_gif
        else:
            return False, status, current_mode, current_gif
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return False, "unknown", "unknown", ""

def get_weather_api_key():
    """Get the current API key from the service"""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "show", "infocube-display.service", "-p", "Environment"],
            capture_output=True,
            text=True,
            check=False
        )
        env_line = result.stdout.strip()

        # Extract the WEATHER_APP_ID if present
        if "WEATHER_APP_ID=" in env_line:
            env_parts = env_line.split("=", 1)[1].strip('"').split(" ")
            for part in env_parts:
                if part.startswith("WEATHER_APP_ID="):
                    return part.split("=", 1)[1]

        # Check config file if not found in service
        config = load_config()
        return config.get("api_keys", {}).get("openweathermap", "")
    except Exception as e:
        logger.error(f"Error getting API key: {e}")
        return ""

def get_masked_api_key():
    """Get the masked API key for display"""
    api_key = get_weather_api_key()
    if api_key and len(api_key) > 4:
        # Show only the last 4 characters
        return "•" * (len(api_key) - 4) + api_key[-4:]
    return ""

def get_plugins():
    """Get list of installed plugins"""
    config = load_config()
    enabled_plugins = config.get("plugins", {}).get("enabled", [])

    # Get the current active plugin
    _, _, current_mode, _ = get_current_status()

    plugins = []
    for plugin in enabled_plugins:
        plugin_info = {
            "name": plugin,
            "active": (plugin == current_mode),
            "description": get_plugin_description(plugin),
            "config": get_plugin_config(plugin)
        }
        plugins.append(plugin_info)

    return plugins

def get_plugin_description(plugin_name):
    """Get description for a plugin"""
    descriptions = {
        "clock": "Clock with date, weather, and prayer times",
        "prayer": "Prayer times display",
        "gif": "Animated GIF display",
        "intro": "Introduction screen",
        "moon": "Moon phase display",
        "weather": "Detailed weather information",
        "stock": "Stock ticker display",
        "wmata": "DC Metro train arrival times"
    }
    return descriptions.get(plugin_name, "")

# New functions for start/stop service

def start_service():
    """Start the InfoCube display service"""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "is-active", "infocube-display.service"],
            capture_output=True, 
            text=True, 
            check=False
        )
        status = result.stdout.strip()

        if status == "active":
            logger.info("Service already running")
            return True, "Service is already running"

        # Start the service
        start_result = subprocess.run(
            ["sudo", "systemctl", "start", "infocube-display.service"],
            capture_output=True,
            text=True,
            check=False
        )

        if start_result.returncode == 0:
            logger.info("Service started successfully")
            return True, "Service started successfully"
        else:
            logger.error(f"Error starting service: {start_result.stderr}")
            return False, f"Error starting service: {start_result.stderr}"
    except Exception as e:
        logger.error(f"Error starting service: {e}")
        return False, f"Error starting service: {e}"

def stop_service():
    """Stop the InfoCube display service"""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "is-active", "infocube-display.service"],
            capture_output=True, 
            text=True, 
            check=False
        )
        status = result.stdout.strip()

        if status != "active":
            logger.info("Service is not running")
            return True, "Service is already stopped"

        # Stop the service
        stop_result = subprocess.run(
            ["sudo", "systemctl", "stop", "infocube-display.service"],
            capture_output=True,
            text=True,
            check=False
        )

        if stop_result.returncode == 0:
            logger.info("Service stopped successfully")
            return True, "Service stopped successfully"
        else:
            logger.error(f"Error stopping service: {stop_result.stderr}")
            return False, f"Error stopping service: {stop_result.stderr}"
    except Exception as e:
        logger.error(f"Error stopping service: {e}")
        return False, f"Error stopping service: {e}"

@app.route('/')
def index():
    # Get the current status, mode, and plugins
    is_running, service_status, current_mode, current_gif = get_current_status()
    available_gifs = scan_gifs()
    masked_api_key = get_masked_api_key()
    plugins = get_plugins()

    # Get brightness from config.ini
    import configparser

    # Initialize config data structure
    config = {}
    config['matrix'] = {}
    config['matrix']['brightness'] = 50  # Default brightness

    # Path to the config.ini file in the project root
    config_path = os.path.join(PROJECT_ROOT, "config.ini")

    # Load the config file if it exists
    if os.path.exists(config_path):
        try:
            parser = configparser.ConfigParser()
            parser.read(config_path)

            # Read brightness from MATRIX section if it exists
            if 'MATRIX' in parser and 'brightness' in parser['MATRIX']:
                try:
                    brightness = int(parser['MATRIX']['brightness'])
                    # Ensure valid range
                    brightness = max(1, min(100, brightness))
                    config['matrix']['brightness'] = brightness
                    logger.info(f"Read brightness value from config.ini: {brightness}")
                except ValueError:
                    # If the value isn't a valid integer
                    logger.warning("Invalid brightness value in config.ini")
        except Exception as e:
            logger.error(f"Error reading config.ini: {e}")
    else:
        logger.info("config.ini not found, using default brightness")

    return render_template(
        'index.html', 
        current_mode=current_mode,
        current_gif=current_gif,
        available_gifs=available_gifs,
        is_running=is_running,
        service_status=service_status,
        masked_api_key=masked_api_key,
        plugins=plugins,
        config=config  # Pass the config with brightness value
    )

@app.route('/set_mode/<mode>')
def set_mode(mode):
    logger.info(f"Setting mode to: {mode}")

    # Special handling for gif mode - select a default gif if needed
    if mode == 'gif':
        # Get the current gif configuration
        gif_config = get_plugin_config('gif')
        current_gif = gif_config.get('current_gif', '')

        # Get list of available gifs
        available_gifs = scan_gifs()

        # If no current gif or the current one doesn't exist, select the first available
        if not current_gif or (available_gifs and current_gif not in available_gifs):
            if available_gifs:
                current_gif = available_gifs[0]
                gif_config['current_gif'] = current_gif
                update_plugin_config('gif', gif_config)

        # If we have a valid gif, use it
        if current_gif:
            change_display_mode('gif', current_gif)
            flash(f"Switched to animation mode: {current_gif}", "success")
        else:
            # No gifs available
            flash("No animations available. Please add some GIFs first.", "error")
            return redirect(url_for('index'))
    else:
        # Normal mode switching
        change_display_mode(mode)

    return redirect(url_for('index'))

@app.route('/set_gif', methods=['POST'])
def set_gif():
    gif_name = request.form.get('gif_name')
    if gif_name:
        change_display_mode('gif', gif_name)
    return redirect(url_for('index'))

@app.route('/restart_service')
def restart_service():
    try:
        subprocess.run(["sudo", "systemctl", "restart", "infocube-display.service"], check=True)
        logger.info("Service restarted successfully")
        flash("InfoCube restarted successfully", "success")
    except Exception as e:
        logger.error(f"Error restarting service: {e}")
        flash(f"Error restarting service: {e}", "error")
    return redirect(url_for('index'))

# New routes for start/stop service
@app.route('/start_service')
def start_service_route():
    success, message = start_service()
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
    return redirect(url_for('index'))

@app.route('/stop_service')
def stop_service_route():
    success, message = stop_service()
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
    return redirect(url_for('index'))

@app.route('/update_api_key', methods=['POST'])
def update_api_key():
    """Update the OpenWeatherMap API key"""
    api_key = request.form.get('weather_api_key', '')

    try:
        # Update in environment variable
        with open('/etc/systemd/system/infocube-display.service', 'r') as f:
            service_content = f.read()

        # Update Environment line
        if 'Environment=' in service_content:
            lines = service_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('Environment='):
                    lines[i] = f'Environment="WEATHER_APP_ID={api_key}"'
                    break

            updated_content = '\n'.join(lines)
        else:
            # If no Environment line found, add it after ExecStart
            lines = service_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('ExecStart='):
                    lines.insert(i+1, f'Environment="WEATHER_APP_ID={api_key}"')
                    break

            updated_content = '\n'.join(lines)

        # Write updated content
        with open('/tmp/infocube-display.service', 'w') as f:
            f.write(updated_content)

        # Replace the existing service file
        subprocess.run(["sudo", "cp", "/tmp/infocube-display.service", "/etc/systemd/system/infocube-display.service"], check=True)

        # Update config file too
        config = load_config()
        if "api_keys" not in config:
            config["api_keys"] = {}
        config["api_keys"]["openweathermap"] = api_key
        save_config(config)

        # Reload and restart
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "restart", "infocube-display.service"], check=True)

        logger.info(f"Updated API key successfully")
        flash("API key updated successfully", "success")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error updating API key: {e}")
        flash(f"Error updating API key: {e}", "error")
        return redirect(url_for('index'))

@app.route('/update_brightness', methods=['POST'])
def update_brightness():
    """Update the LED matrix brightness in real-time"""
    try:
        brightness = int(request.form.get('brightness', 50))

        # Ensure brightness is within valid range
        brightness = max(1, min(100, brightness))

        # Store whether we succeeded with direct update
        direct_update_success = False

        # Step 1: Update brightness in config.ini file for persistence
        import configparser

        # Path to the config.ini file in the project root
        config_path = os.path.join(PROJECT_ROOT, "config.ini")

        # Create or load the config file
        config = configparser.ConfigParser()
        if os.path.exists(config_path):
            config.read(config_path)

        # Make sure MATRIX section exists
        if 'MATRIX' not in config:
            config['MATRIX'] = {}

        # Update the brightness value
        config['MATRIX']['brightness'] = str(brightness)

        # Save the changes
        with open(config_path, 'w') as f:
            config.write(f)

        logger.info(f"Updated brightness to {brightness}% in config.ini")

        # Step 2: Try to update brightness directly using API client
        try:
            response = api_client.set_brightness(brightness)
            if response and isinstance(response, dict):
                # Check if update was applied immediately
                if response.get('applied') == 'immediate':
                    direct_update_success = True
                    logger.info("Brightness updated immediately via API")
                else:
                    logger.info("API reports brightness will apply on restart")
            elif response:
                # Boolean response (legacy)
                direct_update_success = True
                logger.info("Brightness updated via API (legacy response)")
        except Exception as e:
            logger.info(f"Could not update brightness via API: {e}")

        # Step 3: If API direct update succeeded, we're done!
        if direct_update_success:
            flash(f"Brightness updated to {brightness}%", "success")
            return redirect(url_for('index'))

        # Step 4: If direct update failed, try restart as last resort
        logger.info("Direct brightness update not available, restarting service")
        subprocess.run(["sudo", "systemctl", "restart", "infocube-display.service"], check=True)

        flash(f"Brightness updated to {brightness}% (required restart)", "success")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error updating brightness: {e}")
        flash(f"Error updating brightness: {e}", "error")
        return redirect(url_for('index'))


@app.route('/plugin_config/<plugin_name>', methods=['GET', 'POST'])
def plugin_config(plugin_name):
    """Get or update plugin configuration"""
    # Special handling for stock plugin with Finnhub API
    if plugin_name == 'wmata':
        if request.method == 'POST':
            # Get basic settings
            api_key = request.form.get('api_key', '')
            display_mode = request.form.get('display_mode', 'alternating')
            update_interval = int(request.form.get('update_interval', 30))
            show_station_name = 'show_station_name' in request.form

            # Ensure minimum update interval
            update_interval = max(30, update_interval)

            # Process station codes
            station_codes = []
            for i in range(4):  # Up to 4 stations
                station_code = request.form.get(f'station_{i}', '').strip()
                if station_code:
                    station_codes.append(station_code)

            # Must have at least one station
            if not station_codes:
                flash("Please select at least one Metro station.", "error")
                plugin_config = get_plugin_config(plugin_name)
                return render_template(
                    'wmata_config.html',
                    plugin_name=plugin_name,
                    plugin_config=plugin_config,
                    description=get_plugin_description(plugin_name)
                )

            # Get line colors from existing config to preserve them
            existing_config = get_plugin_config(plugin_name)
            line_colors = existing_config.get('line_colors', {
                "RD": [255, 0, 0],      # Red
                "BL": [0, 0, 255],      # Blue
                "OR": [255, 165, 0],    # Orange
                "SV": [192, 192, 192],  # Silver
                "GR": [0, 255, 0],      # Green
                "YL": [255, 255, 0]     # Yellow
            })

            # Create config
            plugin_config = {
                'api_key': api_key,
                'display_mode': display_mode,
                'update_interval': update_interval,
                'show_station_name': show_station_name,
                'stations': station_codes,
                'line_colors': line_colors
            }

            # Update the API key in the overall config too if provided
            if api_key:
                config = load_config()
                if "api_keys" not in config:
                    config["api_keys"] = {}
                config["api_keys"]["wmata"] = api_key
                save_config(config)

            # Update configuration
            update_plugin_config(plugin_name, plugin_config)

            # Restart service to apply changes
            subprocess.run(["sudo", "systemctl", "restart", "infocube-display.service"], check=True)

            flash(f"Configuration for {plugin_name} updated successfully", "success")
            return redirect(url_for('index'))

        # GET request - show config page
        plugin_config = get_plugin_config(plugin_name)
        return render_template(
            'wmata_config.html',
            plugin_name=plugin_name,
            plugin_config=plugin_config,
            description=get_plugin_description(plugin_name)
        )

    if plugin_name == 'stock':
        if request.method == 'POST':
            # Get basic settings
            api_key = request.form.get('api_key', '')
            time_period = request.form.get('time_period', 'day')
            update_interval = int(request.form.get('update_interval', 3600))

            # Ensure minimum update interval
            update_interval = max(60, update_interval)

            # Process stock symbols
            symbols = []
            for i in range(3):  # Up to 3 stocks
                symbol = request.form.get(f'symbols_{i}', '').strip().upper()
                if symbol:
                    symbols.append(symbol)

            # Process graph colors
            graph_colors = []
            for i in range(3):  # Up to 3 colors
                r = int(request.form.get(f'graph_color_r_{i}', 0))
                g = int(request.form.get(f'graph_color_g_{i}', 255))
                b = int(request.form.get(f'graph_color_b_{i}', 0))
                graph_colors.append([r, g, b])

            # Create config
            plugin_config = {
                'api_key': api_key,
                'time_period': time_period,
                'update_interval': update_interval,
                'symbols': symbols,
                'graph_colors': graph_colors
            }

            # Update the API key in the overall config too if provided
            if api_key:
                config = load_config()
                if "api_keys" not in config:
                    config["api_keys"] = {}
                config["api_keys"]["finnhub"] = api_key
                save_config(config)

            # Update configuration
            update_plugin_config(plugin_name, plugin_config)

            # Restart service to apply changes
            subprocess.run(["sudo", "systemctl", "restart", "infocube-display.service"], check=True)

            flash(f"Configuration for {plugin_name} updated successfully", "success")
            return redirect(url_for('index'))

        # GET request - show config page
        template_name = 'stock_config.html'
        plugin_config = get_plugin_config(plugin_name)
        return render_template(
            template_name,
            plugin_name=plugin_name,
            plugin_config=plugin_config,
            description=get_plugin_description(plugin_name)
        )

    # Standard plugin config handling
    if request.method == 'POST':
        # Update configuration
        plugin_config = request.form.to_dict()

        # Convert boolean and numeric values
        for key, value in plugin_config.items():
            if value.lower() in ['true', 'yes', 'on', '1']:
                plugin_config[key] = True
            elif value.lower() in ['false', 'no', 'off', '0']:
                plugin_config[key] = False
            elif value.isdigit():
                plugin_config[key] = int(value)
            elif value.replace('.', '', 1).isdigit() and value.count('.') <= 1:
                plugin_config[key] = float(value)

        # Update configuration
        update_plugin_config(plugin_name, plugin_config)

        # Restart service to apply changes
        subprocess.run(["sudo", "systemctl", "restart", "infocube-display.service"], check=True)

        flash(f"Configuration for {plugin_name} updated successfully", "success")
        return redirect(url_for('index'))
    else:
        # Get configuration
        plugin_config = get_plugin_config(plugin_name)
        return render_template(
            'plugin_config.html',
            plugin_name=plugin_name,
            plugin_config=plugin_config,
            description=get_plugin_description(plugin_name)
        )

@app.route('/add_gif', methods=['POST'])
def add_gif():
    """Add a new GIF from URL"""
    gif_url = request.form.get('gif_url', '')
    custom_name = request.form.get('gif_name', '')

    if not gif_url:
        flash("Please provide a GIF URL", "error")
        return redirect(url_for('index'))

    try:
        # Request the GIF
        response = requests.get(gif_url, stream=True)
        if response.status_code != 200:
            flash(f"Failed to download GIF: HTTP {response.status_code}", "error")
            return redirect(url_for('index'))

        # Check if it's actually a GIF
        content_type = response.headers.get('Content-Type', '')
        if 'image/gif' not in content_type:
            flash(f"URL does not point to a GIF image (Content-Type: {content_type})", "error")
            return redirect(url_for('index'))

        # Generate a filename
        if custom_name:
            # Clean up the custom name
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', custom_name.lower().replace(' ', '_'))
            if not safe_name:
                safe_name = f"gif_{uuid.uuid4().hex[:8]}"
        else:
            # Extract filename from URL or generate random
            url_filename = os.path.basename(gif_url.split('?')[0])
            if url_filename.endswith('.gif'):
                safe_name = secure_filename(os.path.splitext(url_filename)[0])
            else:
                safe_name = f"gif_{uuid.uuid4().hex[:8]}"

        # Make sure we don't overwrite existing files
        target_path = os.path.join(GIF_DIR, f"{safe_name}.gif")
        counter = 1
        while os.path.exists(target_path):
            target_path = os.path.join(GIF_DIR, f"{safe_name}_{counter}.gif")
            counter += 1

        # Save the file
        with open(target_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)

        logger.info(f"Downloaded GIF to {target_path}")

        # Get the final gif name
        gif_name = os.path.splitext(os.path.basename(target_path))[0]
        flash(f"GIF '{gif_name}' added successfully", "success")

        # Auto-select the new GIF
        change_display_mode('gif', gif_name)

        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error downloading GIF: {e}")
        flash(f"Error adding GIF: {e}", "error")
        return redirect(url_for('index'))

@app.route('/upload_gif', methods=['POST'])
def upload_gif():
    """Upload a GIF file"""
    if 'gif_file' not in request.files:
        flash("No file selected", "error")
        return redirect(url_for('index'))

    gif_file = request.files['gif_file']
    custom_name = request.form.get('gif_upload_name', '')

    if gif_file.filename == '':
        flash("No file selected", "error")
        return redirect(url_for('index'))

    if not gif_file.filename.lower().endswith('.gif'):
        flash("Only GIF files are allowed", "error")
        return redirect(url_for('index'))

    try:
        # Generate a filename
        if custom_name:
            # Clean up the custom name
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', custom_name.lower().replace(' ', '_'))
            if not safe_name:
                safe_name = f"gif_{uuid.uuid4().hex[:8]}"
        else:
            # Use original filename or generate random
            safe_name = secure_filename(os.path.splitext(gif_file.filename)[0])
            if not safe_name:
                safe_name = f"gif_{uuid.uuid4().hex[:8]}"

        # Make sure we don't overwrite existing files
        target_path = os.path.join(GIF_DIR, f"{safe_name}.gif")
        counter = 1
        while os.path.exists(target_path):
            target_path = os.path.join(GIF_DIR, f"{safe_name}_{counter}.gif")
            counter += 1

        # Save the file
        gif_file.save(target_path)

        gif_name = os.path.splitext(os.path.basename(target_path))[0]
        logger.info(f"Uploaded GIF to {target_path}")
        flash(f"GIF '{gif_name}' uploaded successfully", "success")

        # Auto-select the new GIF
        change_display_mode('gif', gif_name)

    except Exception as e:
        logger.error(f"Error uploading GIF: {e}")
        flash(f"Error uploading GIF: {e}", "error")

    return redirect(url_for('index'))

@app.route('/delete_gif/<gif_name>')
def delete_gif(gif_name):
    """Delete a GIF file"""
    try:
        gif_path = os.path.join(GIF_DIR, f"{gif_name}.gif")
        if os.path.exists(gif_path):
            os.remove(gif_path)
            logger.info(f"Deleted GIF: {gif_path}")

            # If we're currently displaying this GIF, switch to clock mode
            _, _, current_mode, current_gif = get_current_status()
            if current_mode == 'gif' and current_gif == gif_name:
                change_display_mode('clock')
                flash(f"GIF '{gif_name}' deleted and display mode changed to clock", "success")
            else:
                flash(f"GIF '{gif_name}' deleted", "success")
        else:
            flash(f"GIF '{gif_name}' not found", "error")
    except Exception as e:
        logger.error(f"Error deleting GIF: {e}")
        flash(f"Error deleting GIF: {e}", "error")

    return redirect(url_for('index'))

@app.route('/api/plugins')
def api_list_plugins():
    """API endpoint to list plugins"""
    plugins = get_plugins()
    return jsonify(plugins)

@app.route('/api/status')
def api_status():
    """API endpoint to get system status"""
    is_running, service_status, current_mode, current_gif = get_current_status()

    status = {
        "running": is_running,
        "service_status": service_status,
        "current_mode": current_mode,
        "current_gif": current_gif if current_mode == "gif" else None
    }

    return jsonify(status)

@app.route('/api/gifs')
def api_list_gifs():
    """API endpoint to list available GIFs"""
    gifs = scan_gifs()
    return jsonify(gifs)

if __name__ == '__main__':
    # Start the web server
    app.run(host='0.0.0.0', port=8080, debug=True)