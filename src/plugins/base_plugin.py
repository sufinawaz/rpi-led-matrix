#!/usr/bin/env python
from abc import ABC, abstractmethod

class DisplayPlugin(ABC):
    """Base class for all display plugins

    Each plugin provides a specific display mode for the InfoCube.
    Plugins should implement the required methods to handle setup,
    update, rendering, and cleanup.
    """

    def __init__(self, matrix, config=None):
        """Initialize the plugin

        Args:
            matrix: The MatrixManager instance
            config: Optional configuration dictionary
        """
        self.matrix = matrix
        self.config = config or {}
        self.name = "base"
        self.description = "Base display plugin"
        self.running = False

    def setup(self):
        """Initialize the plugin

        Called when the plugin is first loaded or activated.
        Initialize resources, load fonts, etc.
        """
        pass

    @abstractmethod
    def update(self, delta_time):
        """Update plugin state

        Args:
            delta_time: Time elapsed since last update in seconds
        """
        pass

    @abstractmethod
    def render(self, canvas):
        """Render to the matrix

        Args:
            canvas: RGB Matrix canvas to render to
        """
        pass

    def cleanup(self):
        """Clean up resources

        Called when switching away from this plugin or shutting down.
        """
        pass

    def start(self):
        """Start the plugin"""
        self.running = True

    def stop(self):
        """Stop the plugin"""
        self.running = False