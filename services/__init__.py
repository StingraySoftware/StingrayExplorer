"""
Service layer for StingrayExplorer.

This package contains all business logic services, separated from UI concerns.
Services handle data operations, astronomical computations, and file I/O.

Architecture:
- BaseService: Base class for all services
- ServiceRegistry: Central registry for accessing all services
- Individual services: Domain-specific business logic

Usage:
    from services import ServiceRegistry
    from utils.state_manager import StateManager

    state = StateManager()
    services = ServiceRegistry(state)

    # Access services
    result = services.data.load_event_list(...)
    result = services.spectrum.create_power_spectrum(...)
"""

from utils.state_manager import StateManager
from .base_service import BaseService


class ServiceRegistry:
    """
    Central registry for all services in the application.

    Provides a single access point for all business logic services.
    Each service is initialized with the StateManager and can be accessed
    as an attribute of this registry.

    Attributes:
        data: DataService for EventList operations
        lightcurve: LightcurveService for lightcurve operations
        spectrum: SpectrumService for spectral analysis
        timing: TimingService for timing analysis
        export: ExportService for data export operations

    Example:
        >>> from services import ServiceRegistry
        >>> from utils.state_manager import StateManager
        >>>
        >>> state = StateManager()
        >>> services = ServiceRegistry(state)
        >>>
        >>> # Load an event list
        >>> result = services.data.load_event_list(
        ...     file_path="/path/to/file.evt",
        ...     name="obs1",
        ...     fmt="ogip"
        ... )
        >>>
        >>> if result["success"]:
        ...     print(result["message"])
        ...     event_list = result["data"]
    """

    def __init__(self, state_manager: StateManager):
        """
        Initialize all services with the state manager.

        Args:
            state_manager: The application state manager instance
        """
        self.state_manager = state_manager

        # Import services here to avoid circular imports
        from .data_service import DataService
        from .lightcurve_service import LightcurveService
        from .spectrum_service import SpectrumService
        from .timing_service import TimingService
        from .export_service import ExportService

        # Initialize all services
        self.data = DataService(state_manager)
        self.lightcurve = LightcurveService(state_manager)
        self.spectrum = SpectrumService(state_manager)
        self.timing = TimingService(state_manager)
        self.export = ExportService(state_manager)


# Export public API
__all__ = [
    'BaseService',
    'ServiceRegistry',
]
