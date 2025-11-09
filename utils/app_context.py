"""
Application Context Module

This module provides a centralized context object for the StingrayExplorer dashboard
that encapsulates all UI containers and state management.

The AppContext class solves the "container passing anti-pattern" by providing a
single object that contains references to all UI containers and the state manager,
eliminating the need to pass 7-9 container parameters to every function.

Benefits:
- Reduces function signatures from 9 parameters to 1
- Centralizes UI container management
- Makes code more maintainable and testable
- Easier to add new containers without updating all function signatures
- Provides a clean API for container updates

Example:
    >>> from utils.app_context import AppContext
    >>> context = AppContext()
    >>> context.update_container('output_box', create_output("Loading..."))
    >>> data = context.state.get_event_data()
"""

import panel as pn
from typing import Dict, Any, Optional
from utils.state_manager import state_manager
from services import ServiceRegistry


class AppContext:
    """
    Application context that encapsulates all UI containers, state management, and services.

    This class provides a centralized way to access and update UI containers,
    application state, and business logic services throughout the dashboard.

    Attributes:
        state (StateManager): The application state manager
        services (ServiceRegistry): Registry of all business logic services
        containers (Dict[str, pn.viewable.Viewable]): Dictionary of UI containers

    Example:
        >>> context = AppContext()
        >>> context.update_container('header', create_home_header())
        >>> result = context.services.data.load_event_list(...)
        >>> header = context.get_container('header')
    """

    def __init__(self):
        """Initialize the AppContext with state manager, services, and empty containers."""
        # Reference to the global state manager
        self.state = state_manager

        # Initialize service registry with state manager
        # Services provide all business logic operations
        self.services = ServiceRegistry(state_manager)

        # Dictionary of all UI containers
        # Keys are container names, values are Panel viewable objects
        self.containers: Dict[str, Any] = {}

        # Container metadata for debugging and validation
        self._container_metadata: Dict[str, Dict[str, Any]] = {}

    def register_container(self, name: str, container: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a UI container with the context.

        Args:
            name (str): Unique identifier for the container
            container: Panel viewable object (Column, Row, FlexBox, etc.)
            metadata (Dict, optional): Additional metadata about the container

        Raises:
            ValueError: If container name is empty or already exists

        Example:
            >>> context.register_container('header', pn.Column())
            >>> context.register_container('main_area', pn.Column(), {'purpose': 'main workspace'})
        """
        if not name or not name.strip():
            raise ValueError("Container name cannot be empty")

        if name in self.containers:
            raise ValueError(f"Container '{name}' is already registered")

        self.containers[name] = container

        # Store metadata
        if metadata is None:
            metadata = {}
        metadata['registered_at'] = pn.state.as_cached('current_time', lambda: str(pn.pane.Markdown('')))
        self._container_metadata[name] = metadata

    def get_container(self, name: str) -> Optional[Any]:
        """
        Get a container by name.

        Args:
            name (str): Name of the container to retrieve

        Returns:
            Panel viewable object or None if not found

        Example:
            >>> header = context.get_container('header')
            >>> if header is not None:
            ...     header.objects = [new_content]
        """
        return self.containers.get(name)

    def update_container(self, name: str, content: Any) -> bool:
        """
        Update the content of a container.

        This is the preferred method for updating containers as it uses
        Panel's official API (container.objects = [content]) instead of
        the slice assignment pattern (container[:] = [content]).

        Args:
            name (str): Name of the container to update
            content: New content to set (can be single item or list)

        Returns:
            bool: True if updated successfully, False if container not found

        Example:
            >>> context.update_container('output_box', create_output("Success!"))
            >>> context.update_container('plots', [plot1, plot2])
        """
        container = self.containers.get(name)

        if container is None:
            return False

        # Ensure content is a list
        if not isinstance(content, list):
            content = [content]

        # Use Panel's official API for updating container content
        container.objects = content

        return True

    def append_to_container(self, name: str, content: Any) -> bool:
        """
        Append content to a container without replacing existing content.

        Args:
            name (str): Name of the container
            content: Content to append

        Returns:
            bool: True if appended successfully, False if container not found

        Example:
            >>> context.append_to_container('plots', new_plot)
        """
        container = self.containers.get(name)

        if container is None:
            return False

        container.append(content)
        return True

    def clear_container(self, name: str) -> bool:
        """
        Clear all content from a container.

        Args:
            name (str): Name of the container to clear

        Returns:
            bool: True if cleared successfully, False if container not found

        Example:
            >>> context.clear_container('output_box')
        """
        container = self.containers.get(name)

        if container is None:
            return False

        container.clear()
        return True

    def has_container(self, name: str) -> bool:
        """
        Check if a container exists.

        Args:
            name (str): Name of the container

        Returns:
            bool: True if container exists, False otherwise

        Example:
            >>> if context.has_container('header'):
            ...     print("Header container exists")
        """
        return name in self.containers

    def get_container_names(self) -> list:
        """
        Get list of all registered container names.

        Returns:
            List[str]: List of container names

        Example:
            >>> names = context.get_container_names()
            >>> print(names)  # ['header', 'main_area', 'output_box', ...]
        """
        return list(self.containers.keys())

    def get_container_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a container.

        Args:
            name (str): Name of the container

        Returns:
            Dict with metadata or None if not found

        Example:
            >>> metadata = context.get_container_metadata('header')
        """
        return self._container_metadata.get(name)

    def unregister_container(self, name: str) -> bool:
        """
        Unregister a container from the context.

        Args:
            name (str): Name of the container to unregister

        Returns:
            bool: True if unregistered, False if not found

        Example:
            >>> context.unregister_container('old_container')
        """
        if name in self.containers:
            del self.containers[name]
            if name in self._container_metadata:
                del self._container_metadata[name]
            return True
        return False

    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the application context.

        Returns:
            Dict with context information including container count, state stats, services, etc.

        Example:
            >>> info = context.get_info()
            >>> print(f"Total containers: {info['container_count']}")
        """
        return {
            'container_count': len(self.containers),
            'container_names': self.get_container_names(),
            'state_stats': self.state.get_stats(),
            'services': {
                'data': 'DataService',
                'lightcurve': 'LightcurveService',
                'spectrum': 'SpectrumService',
                'timing': 'TimingService',
                'export': 'ExportService',
            }
        }

    def __repr__(self) -> str:
        """String representation of AppContext."""
        return (
            f"AppContext(containers={len(self.containers)}, "
            f"state={repr(self.state)})"
        )


# =============================================================================
# Singleton Instance (Optional)
# =============================================================================

# You can create a singleton instance if needed, but for testing purposes
# it's often better to create instances explicitly in the main application
# app_context = AppContext()
