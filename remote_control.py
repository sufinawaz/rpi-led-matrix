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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For flash messages

# Use the correct project root directory
PROJECT_ROOT = "/home/pi/code/rpi-led-matrix"
GIF_DIR = os.path.join(PROJECT_ROOT, "resources", "images", "gifs")

# Track current state
current_mode = "clock"  # Default mode
current_gif = ""

# Make sure the directories exist
os.makedirs(GIF_DIR, exist_ok=True)

def scan_gifs():
    """Get list of available GIFs"""
    available_gifs = []
    if os.path.exists(GIF_DIR):
        for file in os.listdir(GIF_DIR):
            if file.endswith('.gif'):
                available_gifs.append(os.path.splitext(file)[0])
    logger.info(f"Found GIFs: {available_gifs}")
    return sorted(available_gifs)

def change_display_mode(mode, gif_name=None):
    """Change the InfoCube display mode by restarting the service with new parameters"""
    global current_mode, current_gif

    # Get current environment variables from the service
    weather_api_key = get_weather_api_key()

    # Build the ExecStart command
    exec_command = f"/usr/bin/python3 {PROJECT_ROOT}/src/infocube.py --display-mode={mode}"
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

def get_masked_api_key():
    """Get the masked API key for display"""
    api_key = get_weather_api_key()
    if api_key and len(api_key) > 4:
        # Show only the last 4 characters
        return "•" * (len(api_key) - 4) + api_key[-4:]
    return ""

def download_gif(url, custom_name=None):
    """Download a GIF from a URL and save it"""
    try:
        # Request the GIF
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            return False, f"Failed to download GIF: HTTP {response.status_code}"

        # Check if it's actually a GIF
        content_type = response.headers.get('Content-Type', '')
        if 'image/gif' not in content_type:
            return False, f"URL does not point to a GIF image (Content-Type: {content_type})"

        # Generate a filename
        if custom_name:
            # Clean up the custom name
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', custom_name.lower().replace(' ', '_'))
            if not safe_name:
                safe_name = f"gif_{uuid.uuid4().hex[:8]}"
        else:
            # Extract filename from URL or generate random
            url_filename = os.path.basename(url.split('?')[0])
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
        return True, os.path.splitext(os.path.basename(target_path))[0]

    except Exception as e:
        logger.error(f"Error downloading GIF: {e}")
        return False, str(e)

@app.route('/')
def index():
    # Get the current status and mode
    is_running, service_status = get_current_status()
    available_gifs = scan_gifs()
    masked_api_key = get_masked_api_key()

    return render_template(
        'index.html', 
        current_mode=current_mode,
        current_gif=current_gif,
        available_gifs=available_gifs,
        is_running=is_running,
        service_status=service_status,
        masked_api_key=masked_api_key
    )

@app.route('/set_mode/<mode>')
def set_mode(mode):
    if mode in ['clock', 'prayer', 'intro', 'moon']:
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
        flash("API key updated successfully", "success")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error updating API key: {e}")
        flash(f"Error updating API key: {e}", "error")
        return redirect(url_for('index'))

@app.route('/add_gif', methods=['POST'])
def add_gif():
    """Add a new GIF from URL"""
    gif_url = request.form.get('gif_url', '')
    custom_name = request.form.get('gif_name', '')

    if not gif_url:
        flash("Please provide a GIF URL", "error")
        return redirect(url_for('index'))

    success, result = download_gif(gif_url, custom_name)

    if success:
        flash(f"GIF '{result}' added successfully", "success")
        # Auto-select the new GIF
        change_display_mode('gif', result)
    else:
        flash(f"Error adding GIF: {result}", "error")

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

if __name__ == '__main__':
    # Start the web server
    app.run(host='0.0.0.0', port=8080, debug=True)