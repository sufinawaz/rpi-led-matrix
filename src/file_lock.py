#!/usr/bin/env python3
"""
File locking utilities to prevent race conditions in file operations.
"""
import fcntl
import os
import time
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@contextmanager
def file_lock(file_path, mode='r', timeout=10, lock_type=fcntl.LOCK_EX):
    """
    Context manager for file locking to prevent race conditions.

    Args:
        file_path: Path to the file to lock
        mode: File open mode ('r', 'w', 'a', etc.)
        timeout: Maximum time to wait for lock (seconds)
        lock_type: Type of lock (fcntl.LOCK_EX for exclusive, fcntl.LOCK_SH for shared)

    Yields:
        File object with lock acquired

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
        OSError: If file operations fail
    """
    lock_file_path = f"{file_path}.lock"

    try:
        # Create lock file
        lock_fd = os.open(lock_file_path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o644)

        # Try to acquire lock with timeout
        start_time = time.time()
        while True:
            try:
                fcntl.flock(lock_fd, lock_type | fcntl.LOCK_NB)
                break
            except (OSError, IOError):
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Could not acquire lock for {file_path} within {timeout} seconds")
                time.sleep(0.1)

        # Open the actual file
        with open(file_path, mode) as f:
            logger.debug(f"Acquired lock for {file_path}")
            yield f

    finally:
        # Release lock and clean up
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
            if os.path.exists(lock_file_path):
                os.unlink(lock_file_path)
            logger.debug(f"Released lock for {file_path}")
        except (OSError, IOError) as e:
            logger.warning(f"Error releasing lock for {file_path}: {e}")

class FileLockError(Exception):
    """Exception raised when file locking operations fail."""
    pass

def safe_write_file(file_path, content, encoding='utf-8', timeout=10):
    """
    Safely write content to a file with locking and atomic operations.

    Args:
        file_path: Path to file to write
        content: Content to write (string or bytes)
        encoding: Text encoding (ignored if content is bytes)
        timeout: Lock timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    import tempfile
    import shutil

    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Create temporary file in same directory for atomic write
        file_dir = os.path.dirname(file_path)
        mode = 'wb' if isinstance(content, bytes) else 'w'

        with tempfile.NamedTemporaryFile(
            mode=mode,
            dir=file_dir,
            delete=False,
            suffix='.tmp',
            encoding=encoding if isinstance(content, str) else None
        ) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_filename = temp_file.name

        # Use file lock during the atomic move
        lock_file_path = f"{file_path}.lock"
        try:
            lock_fd = os.open(lock_file_path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o644)

            # Acquire lock
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except (OSError, IOError):
                    if time.time() - start_time > timeout:
                        raise TimeoutError(f"Could not acquire lock for {file_path}")
                    time.sleep(0.1)

            # Atomic move while holding lock
            shutil.move(temp_filename, file_path)
            logger.debug(f"Successfully wrote {file_path}")
            return True

        finally:
            # Release lock
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
                if os.path.exists(lock_file_path):
                    os.unlink(lock_file_path)
            except (OSError, IOError):
                pass

    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        # Clean up temp file if it exists
        try:
            if 'temp_filename' in locals() and os.path.exists(temp_filename):
                os.unlink(temp_filename)
        except OSError:
            pass
        return False

def safe_read_file(file_path, encoding='utf-8', timeout=10):
    """
    Safely read content from a file with locking.

    Args:
        file_path: Path to file to read
        encoding: Text encoding
        timeout: Lock timeout in seconds

    Returns:
        File content as string, or None if error
    """
    try:
        with file_lock(file_path, 'r', timeout=timeout, lock_type=fcntl.LOCK_SH):
            # Shared lock for reading
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
    except (FileNotFoundError, TimeoutError, OSError) as e:
        logger.warning(f"Error reading file {file_path}: {e}")
        return None