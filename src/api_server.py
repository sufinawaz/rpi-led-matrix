#!/usr/bin/env python
import threading
import socket
import json
import logging

logger = logging.getLogger(__name__)

class APIServer:
    """Simple socket-based API server to allow remote control of the InfoCube"""

    def __init__(self, display_manager, host='0.0.0.0', port=8081):
        """Initialize the API server

        Args:
            display_manager: Reference to the DisplayManager instance
            host: Host to bind to
            port: Port to listen on
        """
        self.display_manager = display_manager
        self.host = host
        self.port = port
        self.running = False
        self.server_thread = None
        self.server_socket = None

    def start(self):
        """Start the API server in a background thread"""
        if self.running:
            return

        self.running = True
        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.daemon = True  # Daemon thread will exit when main thread exits
        self.server_thread.start()
        logger.info(f"API server started on {self.host}:{self.port}")

    def stop(self):
        """Stop the API server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self.server_thread:
            self.server_thread.join(timeout=1.0)
        logger.info("API server stopped")

    def _run_server(self):
        """Run the server loop"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.settimeout(1.0)  # Timeout to allow checking running flag
            self.server_socket.listen(5)

            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:  # Only log if not intentionally stopping
                        logger.error(f"Error accepting connection: {e}")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def _handle_client(self, client_socket, address):
        """Handle a client connection

        Args:
            client_socket: Connected client socket
            address: Client address
        """
        try:
            client_socket.settimeout(5.0)  # 5 second timeout for requests
            data = client_socket.recv(1024).decode('utf-8')

            if not data:
                return

            logger.info(f"Received request from {address}: {data}")

            try:
                request = json.loads(data)
                response = self._process_request(request)
            except json.JSONDecodeError:
                response = {"status": "error", "message": "Invalid JSON"}

            client_socket.sendall(json.dumps(response).encode('utf-8'))
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()

    def _process_request(self, request):
        """Process an API request

        Args:
            request: JSON request object

        Returns:
            JSON response object
        """
        command = request.get('command', '')

        if command == 'set_mode':
            plugin_name = request.get('plugin', '')
            if not plugin_name:
                return {"status": "error", "message": "No plugin specified"}

            success = self.display_manager.set_plugin(plugin_name)
            return {
                "status": "success" if success else "error",
                "message": f"Switched to {plugin_name}" if success else f"Failed to switch to {plugin_name}"
            }

        elif command == 'set_gif':
            plugin_name = 'gif'
            gif_name = request.get('gif_name', '')
            if not gif_name:
                return {"status": "error", "message": "No GIF specified"}

            # Update GIF plugin configuration
            gif_plugin = self.display_manager.plugins.get('gif')
            if gif_plugin:
                # Update the current GIF setting
                previous_gif = gif_plugin.config.get('current_gif', '')
                gif_plugin.config['current_gif'] = gif_name

                # If already in GIF mode and the GIF plugin has the reload method, use it
                if (self.display_manager.current_plugin and 
                    self.display_manager.current_plugin.name == 'gif' and
                    hasattr(gif_plugin, 'reload_if_changed')):

                    # Force reload the GIF
                    reloaded = gif_plugin.reload_if_changed()
                    if reloaded:
                        return {
                            "status": "success",
                            "message": f"Changed GIF to: {gif_name}"
                        }

                # Otherwise, switch to GIF plugin (which will load the new GIF)
                success = self.display_manager.set_plugin(plugin_name)
                return {
                    "status": "success" if success else "error",
                    "message": f"Switched to GIF: {gif_name}" if success else f"Failed to switch to GIF: {gif_name}"
                }
            else:
                return {"status": "error", "message": "GIF plugin not available"}

        elif command == 'get_status':
            current_plugin = None
            if self.display_manager.current_plugin:
                current_plugin = self.display_manager.current_plugin.name

            gif_name = ""
            if current_plugin == 'gif':
                gif_plugin = self.display_manager.plugins.get('gif')
                if gif_plugin:
                    gif_name = gif_plugin.config.get('current_gif', '')

            return {
                "status": "success",
                "data": {
                    "current_plugin": current_plugin,
                    "running": True,
                    "current_gif": gif_name if current_plugin == 'gif' else ""
                }
            }

        elif command == 'set_brightness':
            brightness = request.get('brightness', 50)
            if not isinstance(brightness, int) or brightness < 1 or brightness > 100:
                return {"status": "error", "message": "Invalid brightness value"}

            # Update the configuration
            config = self.display_manager.config

            if "matrix" not in config.config:
                config.config["matrix"] = {}

            config.config["matrix"]["brightness"] = brightness
            config.save_config()

            # Try to update the actual brightness if possible
            try:
                # Option 1: If matrix has a brightness attribute
                if hasattr(self.display_manager.matrix, 'brightness'):
                    self.display_manager.matrix.brightness = brightness
                # Option 2: If matrix has a setBrightness method
                elif hasattr(self.display_manager.matrix, 'setBrightness'):
                    self.display_manager.matrix.setBrightness(brightness)
                # Option 3: If matrix options has a brightness attribute
                elif hasattr(self.display_manager.matrix, 'options') and hasattr(self.display_manager.matrix.options, 'brightness'):
                    self.display_manager.matrix.options.brightness = brightness
                    # Reinitialize matrix if needed

                return {
                    "status": "success",
                    "message": f"Brightness set to {brightness}%"
                }
            except Exception as e:
                logger.error(f"Failed to update brightness directly: {e}")
                return {
                    "status": "success",
                    "message": f"Brightness set to {brightness}% (will apply on restart)"
                }

        else:
            return {"status": "error", "message": f"Unknown command: {command}"}