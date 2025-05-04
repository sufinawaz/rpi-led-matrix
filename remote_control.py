#!/usr/bin/env python
from flask import Flask, render_template, request, redirect, url_for
import subprocess
import os
import logging
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Use the correct project root directory
PROJECT_ROOT = "/home/pi/code/rpi-led-matrix"
GIF_DIR = os.path.join(PROJECT_ROOT, "resources", "images", "gifs")

# Track current state
current_mode = "clock"  # Default mode
current_gif = ""

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
        
        return ""
    except Exception as e:
        logger.error(f"Error getting API key: {e}")
        return ""

def scan_gifs():
    """Get list of available GIFs"""
    available_gifs = []
    if os.path.exists(GIF_DIR):
        for file in os.listdir(GIF_DIR):
            if file.endswith('.gif'):
                available_gifs.append(os.path.splitext(file)[0])
    logger.info(f"Found GIFs: {available_gifs}")
    return available_gifs

def change_display_mode(mode, gif_name=None):
    """Change the InfoCube display mode by restarting the service with new parameters"""
    global current_mode, current_gif
    
    # Get current environment variables from the service
    try:
        env_result = subprocess.run(
            ["sudo", "systemctl", "show", "infocube-display.service", "-p", "Environment"],
            capture_output=True,
            text=True,
            check=False
        )
        env_line = env_result.stdout.strip()
        
        # Extract the WEATHER_APP_ID if present
        weather_api_key = "YOUR_API_KEY_HERE"  # Default fallback
        if "WEATHER_APP_ID=" in env_line:
            env_parts = env_line.split("=", 1)[1].strip('"').split(" ")
            for part in env_parts:
                if part.startswith("WEATHER_APP_ID="):
                    weather_api_key = part.split("=", 1)[1]
                    break
    except Exception as e:
        logger.error(f"Error getting environment variables: {e}")
    
    # Build the ExecStart command
    exec_command = f"/usr/bin/python3 /home/pi/code/rpi-led-matrix/src/infocube.py --display-mode={mode}"
    if mode == "gif" and gif_name:
        exec_command += f" --gif-name={gif_name}"
        current_gif = gif_name
    
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
WorkingDirectory=/home/pi/code/rpi-led-matrix
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
        
        current_mode = mode
        logger.info(f"Display mode changed to: {mode}")
        return True
    except Exception as e:
        logger.error(f"Error changing display mode: {e}")
        return False

def get_current_status():
    """Get the current status of the InfoCube display service"""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "is-active", "infocube-display.service"],
            capture_output=True, 
            text=True, 
            check=False
        )
        status = result.stdout.strip()
        
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
            elif "--display-mode=gif" in cmd_line:
                current_mode = "gif"
                # Try to extract gif name
                if "--gif-name=" in cmd_line:
                    gif_part = cmd_line.split("--gif-name=")[1]
                    current_gif = gif_part.split(" ")[0]
            
            return True, status
        else:
            return False, status
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return False, "unknown"

@app.route('/')
def index():
    # Get the current status and mode
    is_running, service_status = get_current_status()
    available_gifs = scan_gifs()
    weather_api_key = get_weather_api_key()
    
    return render_template(
        'index.html', 
        current_mode=current_mode,
        current_gif=current_gif,
        available_gifs=available_gifs,
        is_running=is_running,
        service_status=service_status,
        weather_api_key=weather_api_key
    )

@app.route('/update_api_key', methods=['POST'])
def update_api_key():
    """Update the OpenWeatherMap API key"""
    api_key = request.form.get('weather_api_key', '')
    
    try:
        # Get current service file content
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
        
        # Reload and restart
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "restart", "infocube-display.service"], check=True)
        
        logger.info(f"Updated API key successfully")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error updating API key: {e}")
        return redirect(url_for('index'))

@app.route('/set_mode/<mode>')
def set_mode(mode):
    if mode in ['clock', 'prayer', 'intro']:
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
    except Exception as e:
        logger.error(f"Error restarting service: {e}")
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Start the web server
    app.run(host='0.0.0.0', port=8080, debug=True)
