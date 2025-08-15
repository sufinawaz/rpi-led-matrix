#!/usr/bin/env python3
"""
Central path configuration module to avoid hardcoded paths throughout the codebase.
"""
import os
import tempfile

# System paths
SYSTEM_PATHS = {
    'python_executable': '/usr/bin/python3',
    'systemd_system_dir': '/etc/systemd/system',
    'proc_cpuinfo': '/proc/cpuinfo',
    'usr_local_bin': '/usr/local/bin',
    'tmp_dir': tempfile.gettempdir(),
}

# Font paths (in order of preference)
FONT_SEARCH_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Monaco.ttf",  # macOS fallback
]

# System font directories
SYSTEM_FONT_DIRS = [
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "/System/Library/Fonts",  # macOS
    "/Library/Fonts",  # macOS
]

def get_system_path(path_key, fallback=None):
    """
    Get a system path with optional fallback.

    Args:
        path_key: Key from SYSTEM_PATHS
        fallback: Fallback value if path doesn't exist

    Returns:
        Path string or fallback
    """
    path = SYSTEM_PATHS.get(path_key, fallback)
    return path if path else fallback

def find_font_file(font_name=None, size=8):
    """
    Find the best available font file.

    Args:
        font_name: Specific font name to search for
        size: Font size (for PIL fonts)

    Returns:
        Path to font file or None if not found
    """
    from PIL import ImageFont

    # If specific font requested, try it first
    if font_name:
        try:
            font = ImageFont.truetype(font_name, size)
            return font_name
        except (IOError, OSError):
            pass

    # Try each font path in order
    for font_path in FONT_SEARCH_PATHS:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, size)
                return font_path
            except (IOError, OSError):
                continue

    # If no TrueType fonts found, return None (will use default)
    return None

def get_temp_file_path(filename):
    """
    Get a temporary file path.

    Args:
        filename: Name of the temporary file

    Returns:
        Full path to temporary file
    """
    return os.path.join(get_system_path('tmp_dir', '/tmp'), filename)

def validate_system_paths():
    """
    Validate that critical system paths exist.

    Returns:
        dict: Status of each path
    """
    status = {}

    for key, path in SYSTEM_PATHS.items():
        if key == 'tmp_dir':
            # Temp dir should always be available
            status[key] = {'exists': True, 'path': path}
        else:
            exists = os.path.exists(path)
            status[key] = {'exists': exists, 'path': path}

    return status