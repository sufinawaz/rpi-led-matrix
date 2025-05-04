#!/usr/bin/env python
from abc import ABC, abstractmethod

class UIComponent(ABC):
    """Base class for UI components

    A UI component is a visual element that can be rendered on the matrix.
    Components can be positioned and sized, and can respond to updates.
    """

    def __init__(self, x=0, y=0, width=0, height=0):
        """Initialize the component

        Args:
            x: X position
            y: Y position
            width: Width
            height: Height
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.visible = True
        self.parent = None

    def get_absolute_position(self):
        """Get absolute position of the component

        Returns:
            (x, y) tuple of absolute position
        """
        x, y = self.x, self.y

        # Apply parent offsets
        parent = self.parent
        while parent:
            x += parent.x
            y += parent.y
            parent = parent.parent

        return (x, y)

    def update(self, delta_time):
        """Update component state

        Args:
            delta_time: Time elapsed since last update in seconds
        """
        pass

    @abstractmethod
    def render(self, canvas):
        """Render component to canvas

        Args:
            canvas: RGB Matrix canvas to render to
        """
        pass