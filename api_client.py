#!/usr/bin/env python
import socket
import json
import logging

logger = logging.getLogger(__name__)

class APIClient:
    """Client for communicating with the InfoCube API server"""

    def __init__(self, host='localhost', port=8081, timeout=5.0):
        """Initialize the API client

        Args:
            host: Host address of the API server
            port: Port number of the API server
            timeout: Socket timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout

    def _send_request(self, request):
        """Send a request to the API server

        Args:
            request: JSON-serializable request object

        Returns:
            Response from the server or None if error
        """
        try:
            # Create socket
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(self.timeout)

            # Connect to server
            client_socket.connect((self.host, self.port))

            # Send request
            client_socket.sendall(json.dumps(request).encode('utf-8'))

            # Receive response
            response_data = client_socket.recv(1024).decode('utf-8')

            # Parse and return response
            if response_data:
                return json.loads(response_data)
            else:
                logger.error("Empty response from server")
                return None

        except socket.timeout:
            logger.error(f"Connection timeout to {self.host}:{self.port}")
            return None
        except ConnectionRefusedError:
            logger.error(f"Connection refused to {self.host}:{self.port}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error communicating with API server: {e}")
            return None
        finally:
            if 'client_socket' in locals():
                client_socket.close()

    def set_mode(self, plugin_name):
        """Set the display mode/plugin

        Args:
            plugin_name: Name of the plugin to switch to

        Returns:
            True if successful, False otherwise
        """
        request = {
            'command': 'set_mode',
            'plugin': plugin_name
        }

        response = self._send_request(request)
        if response and response.get('status') == 'success':
            logger.info(f"Successfully switched to {plugin_name}")
            return True
        else:
            error_msg = response.get('message', 'Unknown error') if response else 'No response'
            logger.error(f"Failed to switch mode: {error_msg}")
            return False

    def set_gif(self, gif_name):
        """Set the GIF to display

        Args:
            gif_name: Name of the GIF to display

        Returns:
            True if successful, False otherwise
        """
        request = {
            'command': 'set_gif',
            'gif_name': gif_name
        }

        response = self._send_request(request)
        if response and response.get('status') == 'success':
            logger.info(f"Successfully switched to GIF: {gif_name}")
            return True
        else:
            error_msg = response.get('message', 'Unknown error') if response else 'No response'
            logger.error(f"Failed to set GIF: {error_msg}")
            return False

    def get_status(self):
        """Get the current status of the InfoCube

        Returns:
            Status dictionary or None if error
        """
        request = {
            'command': 'get_status'
        }

        response = self._send_request(request)
        if response and response.get('status') == 'success':
            return response.get('data', {})
        else:
            logger.error("Failed to get status")
            return None

    def set_brightness(self, brightness):
        """Set the LED matrix brightness

        Args:
            brightness: Brightness level (1-100)

        Returns:
            True if successful, False otherwise
        """
        request = {
            'command': 'set_brightness',
            'brightness': brightness
        }

        response = self._send_request(request)
        if response and response.get('status') == 'success':
            logger.info(f"Successfully set brightness to {brightness}%")
            return True
        else:
            error_msg = response.get('message', 'Unknown error') if response else 'No response'
            logger.error(f"Failed to set brightness: {error_msg}")
            return False