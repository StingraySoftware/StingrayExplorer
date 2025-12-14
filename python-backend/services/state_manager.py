"""
State management for Stingray Explorer backend.

Manages loaded data including EventLists, Lightcurves, and analysis results.
"""

from typing import Any, Dict, List, Optional, Tuple
import threading


class StateManager:
    """
    Thread-safe state manager for Stingray Explorer.

    Manages the application state including loaded event lists,
    lightcurves, and analysis results.
    """

    def __init__(self):
        """Initialize the state manager."""
        self._event_data: Dict[str, Any] = {}
        self._lightcurve_data: Dict[str, Any] = {}
        self._spectrum_data: Dict[str, Any] = {}
        self._analysis_results: Dict[str, Any] = {}
        self._lock = threading.RLock()

    # Event data methods
    def add_event_data(self, name: str, event_list: Any) -> None:
        """
        Add an event list to state.

        Args:
            name: Unique name for the event list
            event_list: Stingray EventList object
        """
        with self._lock:
            self._event_data[name] = event_list

    def get_event_data(self, name: Optional[str] = None) -> Any:
        """
        Get event list(s) from state.

        Args:
            name: Name of specific event list, or None for all

        Returns:
            Single EventList if name provided, otherwise list of (name, event_list) tuples
        """
        with self._lock:
            if name is not None:
                return self._event_data.get(name)
            return list(self._event_data.items())

    def has_event_data(self, name: str) -> bool:
        """Check if an event list with given name exists."""
        with self._lock:
            return name in self._event_data

    def remove_event_data(self, name: str) -> bool:
        """
        Remove an event list from state.

        Args:
            name: Name of the event list to remove

        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if name in self._event_data:
                del self._event_data[name]
                return True
            return False

    def list_event_names(self) -> List[str]:
        """Get list of all event list names."""
        with self._lock:
            return list(self._event_data.keys())

    # Lightcurve data methods
    def add_lightcurve_data(self, name: str, lightcurve: Any) -> None:
        """
        Add a lightcurve to state.

        Args:
            name: Unique name for the lightcurve
            lightcurve: Stingray Lightcurve object
        """
        with self._lock:
            self._lightcurve_data[name] = lightcurve

    def get_lightcurve_data(self, name: Optional[str] = None) -> Any:
        """
        Get lightcurve(s) from state.

        Args:
            name: Name of specific lightcurve, or None for all

        Returns:
            Single Lightcurve if name provided, otherwise list of (name, lightcurve) tuples
        """
        with self._lock:
            if name is not None:
                return self._lightcurve_data.get(name)
            return list(self._lightcurve_data.items())

    def has_lightcurve_data(self, name: str) -> bool:
        """Check if a lightcurve with given name exists."""
        with self._lock:
            return name in self._lightcurve_data

    def remove_lightcurve_data(self, name: str) -> bool:
        """Remove a lightcurve from state."""
        with self._lock:
            if name in self._lightcurve_data:
                del self._lightcurve_data[name]
                return True
            return False

    def list_lightcurve_names(self) -> List[str]:
        """Get list of all lightcurve names."""
        with self._lock:
            return list(self._lightcurve_data.keys())

    # Spectrum data methods
    def add_spectrum_data(self, name: str, spectrum: Any) -> None:
        """Add a spectrum to state."""
        with self._lock:
            self._spectrum_data[name] = spectrum

    def get_spectrum_data(self, name: Optional[str] = None) -> Any:
        """Get spectrum(s) from state."""
        with self._lock:
            if name is not None:
                return self._spectrum_data.get(name)
            return list(self._spectrum_data.items())

    def has_spectrum_data(self, name: str) -> bool:
        """Check if a spectrum with given name exists."""
        with self._lock:
            return name in self._spectrum_data

    def remove_spectrum_data(self, name: str) -> bool:
        """Remove a spectrum from state."""
        with self._lock:
            if name in self._spectrum_data:
                del self._spectrum_data[name]
                return True
            return False

    def list_spectrum_names(self) -> List[str]:
        """Get list of all spectrum names."""
        with self._lock:
            return list(self._spectrum_data.keys())

    # Analysis results methods
    def add_analysis_result(self, name: str, result: Any) -> None:
        """Add an analysis result to state."""
        with self._lock:
            self._analysis_results[name] = result

    def get_analysis_result(self, name: Optional[str] = None) -> Any:
        """Get analysis result(s) from state."""
        with self._lock:
            if name is not None:
                return self._analysis_results.get(name)
            return list(self._analysis_results.items())

    def remove_analysis_result(self, name: str) -> bool:
        """Remove an analysis result from state."""
        with self._lock:
            if name in self._analysis_results:
                del self._analysis_results[name]
                return True
            return False

    # Utility methods
    def clear_all(self) -> None:
        """Clear all state data."""
        with self._lock:
            self._event_data.clear()
            self._lightcurve_data.clear()
            self._spectrum_data.clear()
            self._analysis_results.clear()

    def get_summary(self) -> Dict[str, int]:
        """Get a summary of stored data counts."""
        with self._lock:
            return {
                "event_lists": len(self._event_data),
                "lightcurves": len(self._lightcurve_data),
                "spectra": len(self._spectrum_data),
                "analysis_results": len(self._analysis_results),
            }
