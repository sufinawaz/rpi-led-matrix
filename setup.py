#!/usr/bin/env python
import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def print_header(message):
    """Print a formatted header message"""
    logger.info("\n" + "=" * 60)
    logger.info(f" {message}")
    logger.info("=" * 60)

def run_command(command, cwd=None, shell=False):
    """Run a shell command and log output"""
    logger.info(f"Running: {command}")
    if not shell and isinstance(command, str):
        command = command.split()
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            shell=shell
        )
        
        # Print output in real-time
        for line in iter(process.stdout.readline, ''):
            line = line.rstrip()
            if line:
                logger.info(f"  {line}")
                
        process.wait()
        return process.returncode
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return 1

def create_directory(directory):
    """Create a directory if it doesn't exist"""
    try:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        return False

def create_project_structure():
    """Create the project directory structure"""
    print_header("Setting up project structure")
    
    # Project root is where this script is located
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Define project directories
    directories = [
        os.path.join(project_root, "src"),  # Just one src directory
        os.path.join(project_root, "resources"),
        os.path.join(project_root, "resources/images"),
        os.path.join(project_root, "resources/images/gifs"),
        os.path.join(project_root, "resources/images/weather-icons"),
        os.path.join(project_root, "resources/fonts")
    ]
    
    # Create directories
    for directory in directories:
        create_directory(directory)
    
    return project_root

def install_system_packages():
    """Install required system packages"""
    print_header("Installing system packages")
    
    # Check if we're running on a Raspberry Pi
    is_raspberry_pi = False
    try:
        with open('/proc/cpuinfo', 'r') as f:
            if 'Raspberry Pi' in f.read():
                is_raspberry_pi = True
    except:
        pass
    
    if is_raspberry_pi:
        # Install required packages for Raspberry Pi
        packages = [
            "python3-dev",
            "python3-pillow",
            "python3-pip",
            "libgraphicsmagick++-dev",
            "libwebp-dev",
            "git"
        ]
        
        apt_command = ["apt-get", "update"]
        if run_command(["sudo"] + apt_command) != 0:
            logger.error("Failed to update package list")
            return False
        
        apt_command = ["apt-get", "install", "-y"] + packages
        if run_command(["sudo"] + apt_command) != 0:
            logger.error("Failed to install system packages")
            return False
    else:
        logger.warning("Not running on a Raspberry Pi - skipping system package installation")
        logger.warning("You may need to manually install required packages")
    
    return True

def install_rgb_matrix_library(project_root):
    """Clone and install the rpi-rgb-led-matrix library"""
    print_header("Installing RGB Matrix Library")
    
    # Check if we're running on Linux
    if not sys.platform.startswith('linux'):
        logger.warning("Not running on Linux - the RGB Matrix library can only be installed on Linux/Raspberry Pi")
        logger.warning("Skipping RGB Matrix library installation")
        return True
    
    rgb_matrix_dir = os.path.join(project_root, "rpi-rgb-led-matrix")
    
    # Clone the repository if it doesn't exist
    if not os.path.exists(rgb_matrix_dir):
        logger.info("Cloning rpi-rgb-led-matrix repository")
        git_command = ["git", "clone", "https://github.com/hzeller/rpi-rgb-led-matrix.git", rgb_matrix_dir]
        if run_command(git_command) != 0:
            logger.error("Failed to clone rpi-rgb-led-matrix repository")
            return False
    
    # Build the library
    logger.info("Building rpi-rgb-led-matrix library")
    if run_command("make", cwd=rgb_matrix_dir) != 0:
        logger.error("Failed to build rpi-rgb-led-matrix library")
        return False
    
    # Build and install Python bindings
    python_bindings_dir = os.path.join(rgb_matrix_dir, "bindings", "python")
    logger.info("Building Python bindings")
    if run_command("make", cwd=python_bindings_dir) != 0:
        logger.error("Failed to build Python bindings")
        return False
    
    logger.info("Installing Python bindings")
    install_command = ["sudo", "make", "install"]
    if run_command(install_command, cwd=python_bindings_dir) != 0:
        logger.error("Failed to install Python bindings")
        return False
    
    # Copy fonts to the project's resources/fonts directory
    fonts_source_dir = os.path.join(rgb_matrix_dir, "fonts")
    fonts_target_dir = os.path.join(project_root, "resources", "fonts")
    
    if os.path.exists(fonts_source_dir):
        logger.info("Copying fonts")
        for font_file in os.listdir(fonts_source_dir):
            if font_file.endswith('.bdf'):
                shutil.copy2(
                    os.path.join(fonts_source_dir, font_file),
                    os.path.join(fonts_target_dir, font_file)
                )
        
        # Specifically check for the required font files
        required_fonts = ["4x6.bdf", "7x13.bdf"]
        found_fonts = os.listdir(fonts_target_dir)
        
        for required_font in required_fonts:
            if required_font in found_fonts:
                logger.info(f"Found required font: {required_font}")
            else:
                logger.warning(f"Required font {required_font} not found!")
    
    return True

def install_python_dependencies():
    """Install required Python packages"""
    print_header("Installing Python dependencies")
    
    packages = ["requests", "pillow", "configparser"]
    pip_command = [sys.executable, "-m", "pip", "install"] + packages
    
    if run_command(pip_command) != 0:
        logger.error("Failed to install Python dependencies")
        return False
    
    return True

def create_config_file(project_root):
    """Create a config.ini file"""
    print_header("Creating configuration file")
    
    config_path = os.path.join(project_root, "config.ini")
    
    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            f.write("[MATRIX]\n")
            f.write("rows = 32\n")
            f.write("cols = 32\n")
            f.write("chain_length = 1\n")
            f.write("brightness = 70\n")
            f.write("hardware_mapping = adafruit-hat\n")
            f.write("gpio_slowdown = 2\n\n")
            
            f.write("[API]\n")
            f.write("# OpenWeatherMap API key\n")
            f.write("WEATHER_APP_ID = YOUR_API_KEY_HERE\n")
        
        logger.info(f"Created config file at {config_path}")
    else:
        logger.info(f"Config file already exists at {config_path}")
    
    return True

def create_launcher_script(project_root):
    """Create a launcher script to run infocube from anywhere"""
    print_header("Creating launcher script")
    
    launcher_path = os.path.join(project_root, "run_infocube")
    
    with open(launcher_path, 'w') as f:
        f.write("#!/bin/bash\n\n")
        f.write(f"PROJECT_ROOT=\"{project_root}\"\n")
        f.write("cd \"$PROJECT_ROOT\"\n\n")
        f.write("# Run infocube with default settings\n")
        f.write("sudo python3 \"$PROJECT_ROOT/src/infocube.py\" \"$@\"\n")
    
    # Make the launcher script executable
    os.chmod(launcher_path, 0o755)
    
    # Create global symlink (requires sudo)
    global_link = "/usr/local/bin/infocube"
    logger.info(f"Creating global symlink at {global_link}")
    
    if os.path.exists(global_link) or os.path.islink(global_link):
        run_command(["sudo", "rm", global_link])
    
    try:
        run_command(["sudo", "ln", "-s", launcher_path, global_link])
        logger.info(f"You can now run 'infocube' from anywhere!")
    except Exception as e:
        logger.error(f"Failed to create global symlink: {e}")
        logger.info(f"You can still run the script using {launcher_path}")
    
    return True

def move_infocube_to_src(project_root):
    """Move infocube.py from examples to src directory if it exists"""
    print_header("Moving infocube.py")
    
    examples_dir = os.path.join(project_root, "src", "examples")
    infocube_source = os.path.join(examples_dir, "infocube.py")
    infocube_dest = os.path.join(project_root, "src", "infocube.py")
    
    if os.path.isfile(infocube_source):
        try:
            shutil.copy2(infocube_source, infocube_dest)
            logger.info(f"Copied infocube.py from examples to src directory")
            # Make the file executable
            os.chmod(infocube_dest, 0o755)
            return True
        except Exception as e:
            logger.error(f"Failed to copy infocube.py: {e}")
            return False
    else:
        logger.info("infocube.py not found in examples directory. This is normal for a fresh installation.")
        return True

def setup():
    """Main setup function"""
    print_header("LED Matrix InfoCube Setup")
    
    # Create project structure
    project_root = create_project_structure()
    
    # Move infocube.py if it exists in examples
    move_infocube_to_src(project_root)
    
    # Install system packages
    if not install_system_packages():
        return False
    
    # Install RGB Matrix library
    if not install_rgb_matrix_library(project_root):
        return False
    
    # Install Python dependencies
    if not install_python_dependencies():
        return False
    
    # Create config file
    if not create_config_file(project_root):
        return False
    
    # Create launcher script
    if not create_launcher_script(project_root):
        return False
    
    print_header("Setup Complete")
    logger.info("The LED Matrix InfoCube has been set up successfully!")
    logger.info(f"Project directory: {project_root}")
    logger.info("\nTo run InfoCube with default settings:")
    logger.info("  sudo infocube")
    logger.info("\nOr with custom options:")
    logger.info("  sudo infocube --display-mode=clock --led-brightness=50")
    logger.info("\nPlease configure your OpenWeatherMap API key in config.ini")
    logger.info("or set the WEATHER_APP_ID environment variable before running.")
    
    return True

if __name__ == "__main__":
    try:
        if os.geteuid() == 0:  # Checking if running as root
            logger.warning("\nRunning the setup script as root is not recommended.")
            cont = input("Continue anyway? (y/n): ").lower()
            if cont != 'y':
                sys.exit(0)
        
        result = setup()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred during setup: {e}")
        sys.exit(1)