#!/usr/bin/env python
from .component import UIComponent

class Layout(UIComponent):
    """Base class for layouts

    A layout is a container for organizing UI components.
    """

    def __init__(self, x=0, y=0, width=32, height=32):
        """Initialize the layout

        Args:
            x: X position
            y: Y position
            width: Width
            height: Height
        """
        super().__init__(x, y, width, height)
        self.components = []

    def add(self, component):
        """Add a component to the layout

        Args:
            component: UIComponent to add

        Returns:
            The added component for chaining
        """
        self.components.append(component)
        component.parent = self
        return component

    def remove(self, component):
        """Remove a component from the layout

        Args:
            component: UIComponent to remove

        Returns:
            True if component was removed, False otherwise
        """
        if component in self.components:
            self.components.remove(component)
            component.parent = None
            return True
        return False

    def update(self, delta_time):
        """Update all components

        Args:
            delta_time: Time elapsed since last update in seconds
        """
        for component in self.components:
            component.update(delta_time)

    def render(self, canvas):
        """Render all components

        Args:
            canvas: RGB Matrix canvas to render to
        """
        if not self.visible:
            return

        for component in self.components:
            component.render(canvas)

class GridLayout(Layout):
    """Grid-based layout

    A grid layout organizes components in rows and columns.
    """

    def __init__(self, x=0, y=0, width=32, height=32, rows=1, cols=1):
        """Initialize the grid layout

        Args:
            x: X position
            y: Y position
            width: Width
            height: Height
            rows: Number of rows
            cols: Number of columns
        """
        super().__init__(x, y, width, height)
        self.rows = rows
        self.cols = cols
        self.cells = {}

    def add_at(self, component, row, col, row_span=1, col_span=1):
        """Add a component at a specific grid position

        Args:
            component: UIComponent to add
            row: Row index (0-based)
            col: Column index (0-based)
            row_span: Number of rows to span
            col_span: Number of columns to span

        Returns:
            The added component for chaining
        """
        # Add to components list
        self.components.append(component)
        component.parent = self

        # Store grid cell info
        self.cells[(row, col)] = {
            'component': component,
            'row_span': row_span,
            'col_span': col_span
        }

        # Calculate position
        cell_width = self.width / self.cols
        cell_height = self.height / self.rows

        component.x = col * cell_width
        component.y = row * cell_height

        # Set component size if not already set
        if component.width == 0:
            component.width = cell_width * col_span
        if component.height == 0:
            component.height = cell_height * row_span

        return component