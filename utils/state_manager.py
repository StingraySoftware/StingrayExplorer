"""
State Manager Module

This module provides centralized state management for the StingrayExplorer dashboard.
It replaces the global variables pattern with an encapsulated, observable state container.

The StateManager class manages:
- Event data (EventList objects)
- Light curves (Lightcurve objects)
- Time series data
- Memory usage tracking with dynamic limits based on system RAM
- Observer pattern for state change notifications

Example:
    >>> from utils.state_manager import state_manager
    >>> state_manager.add_event_data("my_event", event_list_obj)
    >>> event_list = state_manager.get_event_data("my_event")
    >>> state_manager.has_event_data("my_event")
    True
"""

import sys
import logging
import psutil
from typing import List, Tuple, Optional, Callable, Any, Dict
from collections import OrderedDict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StateManager:
    """
    Centralized state management for the StingrayExplorer dashboard.

    This class encapsulates all application state and provides a clean API
    for managing data with validation, memory tracking, and change notifications.

    The memory limit is dynamically calculated as 80% of available system RAM.

    Attributes:
        MAX_EVENT_LISTS (int): Maximum number of event lists to store
        MAX_LIGHT_CURVES (int): Maximum number of light curves to store
        MAX_TIMESERIES (int): Maximum number of time series to store
        MAX_MEMORY_MB (float): Maximum memory usage in megabytes (80% of system RAM)
        MEMORY_USAGE_PERCENT (float): Percentage of system RAM allowed (default: 80%)
    """

    # Configuration limits
    MAX_EVENT_LISTS = 50
    MAX_LIGHT_CURVES = 50
    MAX_TIMESERIES = 50
    MEMORY_USAGE_PERCENT = 0.80  # Use up to 80% of system RAM

    def __init__(self):
        """Initialize the StateManager with empty state collections."""
        # Use OrderedDict to maintain insertion order for LRU eviction
        self._event_data: OrderedDict[str, Any] = OrderedDict()
        self._light_curves: OrderedDict[str, Any] = OrderedDict()
        self._timeseries_data: OrderedDict[str, Any] = OrderedDict()

        # Observer pattern: list of callbacks to notify on state changes
        self._observers: List[Callable[[str, Any], None]] = []

        # Calculate dynamic memory limit based on system RAM
        self.MAX_MEMORY_MB = self._calculate_max_memory_limit()

        # Statistics
        self._stats = {
            'total_additions': 0,
            'total_removals': 0,
            'total_evictions': 0,
        }

        logger.info(
            f"StateManager initialized with dynamic memory limit: "
            f"{self.MAX_MEMORY_MB:.2f} MB ({self.MEMORY_USAGE_PERCENT*100:.0f}% of system RAM)"
        )

    def _calculate_max_memory_limit(self) -> float:
        """
        Calculate the maximum memory limit dynamically based on system RAM.

        Returns:
            float: Maximum memory in MB (80% of total system RAM)

        Example:
            System with 16 GB RAM -> 16384 * 0.80 = 13107.2 MB limit
        """
        try:
            # Get total system memory in bytes
            total_ram_bytes = psutil.virtual_memory().total

            # Convert to MB and apply percentage
            total_ram_mb = total_ram_bytes / (1024 * 1024)
            max_memory_mb = total_ram_mb * self.MEMORY_USAGE_PERCENT

            logger.info(
                f"System RAM: {total_ram_mb:.2f} MB, "
                f"Allocated limit: {max_memory_mb:.2f} MB ({self.MEMORY_USAGE_PERCENT*100:.0f}%)"
            )

            return max_memory_mb

        except Exception as e:
            # Fallback to 2GB if psutil fails
            logger.warning(f"Could not determine system RAM, using fallback 2GB limit: {e}")
            return 2000.0

    def set_memory_usage_percent(self, percent: float) -> None:
        """
        Set the percentage of system RAM that can be used.

        Args:
            percent (float): Percentage as decimal (e.g., 0.80 for 80%)

        Raises:
            ValueError: If percent is not between 0.1 and 1.0

        Example:
            >>> state_manager.set_memory_usage_percent(0.70)  # Use 70% of RAM
        """
        if not 0.1 <= percent <= 1.0:
            raise ValueError("Memory usage percent must be between 0.1 (10%) and 1.0 (100%)")

        self.MEMORY_USAGE_PERCENT = percent
        self.MAX_MEMORY_MB = self._calculate_max_memory_limit()

        logger.info(f"Memory limit updated to {self.MAX_MEMORY_MB:.2f} MB ({percent*100:.0f}%)")

    def get_system_memory_info(self) -> Dict[str, float]:
        """
        Get detailed system memory information.

        Returns:
            Dict with system memory stats in MB

        Example:
            >>> mem_info = state_manager.get_system_memory_info()
            >>> print(f"Available: {mem_info['available_mb']:.2f} MB")
        """
        try:
            mem = psutil.virtual_memory()
            return {
                'total_mb': mem.total / (1024 * 1024),
                'available_mb': mem.available / (1024 * 1024),
                'used_mb': mem.used / (1024 * 1024),
                'percent_used': mem.percent,
                'allocated_limit_mb': self.MAX_MEMORY_MB,
                'allocated_percent': self.MEMORY_USAGE_PERCENT * 100,
            }
        except Exception as e:
            logger.error(f"Error getting system memory info: {e}")
            return {}

    # =============================================================================
    # Event Data Management Methods
    # =============================================================================

    def add_event_data(self, name: str, event_list: Any) -> None:
        """
        Add an event list to the state.

        Args:
            name (str): Unique identifier for the event list
            event_list: EventList object from Stingray

        Raises:
            ValueError: If an event list with the same name already exists
            MemoryError: If adding would exceed memory limits

        Example:
            >>> state_manager.add_event_data("obs1", event_list_obj)
        """
        if not name or not name.strip():
            raise ValueError("Event data name cannot be empty")

        if self.has_event_data(name):
            raise ValueError(f"Event data with name '{name}' already exists")

        # Check memory limits before adding
        self._check_memory_limits()

        # Check count limits and evict if necessary
        if len(self._event_data) >= self.MAX_EVENT_LISTS:
            self._evict_oldest_event_data()

        # Add the event list
        self._event_data[name] = event_list
        self._stats['total_additions'] += 1

        logger.info(f"Added event data: '{name}' (total: {len(self._event_data)})")
        self._notify_observers('event_data_added', {'name': name, 'data': event_list})

    def get_event_data(self, name: Optional[str] = None) -> Any:
        """
        Get event data by name or all event data.

        Args:
            name (str, optional): Name of the event list to retrieve.
                                 If None, returns all event data as a list of tuples.

        Returns:
            If name is provided: EventList object or None if not found
            If name is None: List of (name, EventList) tuples

        Example:
            >>> event_list = state_manager.get_event_data("obs1")
            >>> all_data = state_manager.get_event_data()  # [(name1, data1), ...]
        """
        if name is None:
            # Return all event data as list of tuples for backward compatibility
            return list(self._event_data.items())

        return self._event_data.get(name)

    def get_event_data_names(self) -> List[str]:
        """
        Get list of all event data names.

        Returns:
            List[str]: List of event data names

        Example:
            >>> names = state_manager.get_event_data_names()
            >>> print(names)  # ['obs1', 'obs2', 'obs3']
        """
        return list(self._event_data.keys())

    def remove_event_data(self, name: str) -> bool:
        """
        Remove event data by name.

        Args:
            name (str): Name of the event list to remove

        Returns:
            bool: True if removed, False if not found

        Example:
            >>> state_manager.remove_event_data("obs1")
            True
        """
        if name in self._event_data:
            del self._event_data[name]
            self._stats['total_removals'] += 1
            logger.info(f"Removed event data: '{name}' (remaining: {len(self._event_data)})")
            self._notify_observers('event_data_removed', {'name': name})
            return True
        return False

    def has_event_data(self, name: str) -> bool:
        """
        Check if event data exists.

        Args:
            name (str): Name of the event list

        Returns:
            bool: True if exists, False otherwise

        Example:
            >>> if state_manager.has_event_data("obs1"):
            ...     print("Found!")
        """
        return name in self._event_data

    def clear_event_data(self) -> None:
        """
        Clear all event data.

        Example:
            >>> state_manager.clear_event_data()
        """
        count = len(self._event_data)
        self._event_data.clear()
        logger.info(f"Cleared all event data ({count} items)")
        self._notify_observers('event_data_cleared', {'count': count})

    def update_event_data(self, name: str, event_list: Any) -> bool:
        """
        Update existing event data.

        Args:
            name (str): Name of the event list to update
            event_list: New EventList object

        Returns:
            bool: True if updated, False if not found

        Example:
            >>> state_manager.update_event_data("obs1", modified_event_list)
        """
        if name in self._event_data:
            self._event_data[name] = event_list
            logger.info(f"Updated event data: '{name}'")
            self._notify_observers('event_data_updated', {'name': name, 'data': event_list})
            return True
        return False

    def _evict_oldest_event_data(self) -> None:
        """Evict the oldest event data using LRU strategy."""
        if self._event_data:
            oldest_name = next(iter(self._event_data))
            del self._event_data[oldest_name]
            self._stats['total_evictions'] += 1
            logger.warning(f"Evicted oldest event data: '{oldest_name}' (LRU policy)")
            self._notify_observers('event_data_evicted', {'name': oldest_name})

    # =============================================================================
    # Light Curve Management Methods
    # =============================================================================

    def add_light_curve(self, name: str, light_curve: Any) -> None:
        """
        Add a light curve to the state.

        Args:
            name (str): Unique identifier for the light curve
            light_curve: Lightcurve object from Stingray

        Raises:
            ValueError: If a light curve with the same name already exists
            MemoryError: If adding would exceed memory limits
        """
        if not name or not name.strip():
            raise ValueError("Light curve name cannot be empty")

        if self.has_light_curve(name):
            raise ValueError(f"Light curve with name '{name}' already exists")

        self._check_memory_limits()

        if len(self._light_curves) >= self.MAX_LIGHT_CURVES:
            self._evict_oldest_light_curve()

        self._light_curves[name] = light_curve
        self._stats['total_additions'] += 1

        logger.info(f"Added light curve: '{name}' (total: {len(self._light_curves)})")
        self._notify_observers('light_curve_added', {'name': name, 'data': light_curve})

    def get_light_curve(self, name: Optional[str] = None) -> Any:
        """
        Get light curve by name or all light curves.

        Args:
            name (str, optional): Name of the light curve to retrieve

        Returns:
            If name is provided: Lightcurve object or None if not found
            If name is None: List of (name, Lightcurve) tuples
        """
        if name is None:
            return list(self._light_curves.items())
        return self._light_curves.get(name)

    def get_light_curve_names(self) -> List[str]:
        """Get list of all light curve names."""
        return list(self._light_curves.keys())

    def remove_light_curve(self, name: str) -> bool:
        """Remove light curve by name."""
        if name in self._light_curves:
            del self._light_curves[name]
            self._stats['total_removals'] += 1
            logger.info(f"Removed light curve: '{name}' (remaining: {len(self._light_curves)})")
            self._notify_observers('light_curve_removed', {'name': name})
            return True
        return False

    def has_light_curve(self, name: str) -> bool:
        """Check if light curve exists."""
        return name in self._light_curves

    def clear_light_curves(self) -> None:
        """Clear all light curves."""
        count = len(self._light_curves)
        self._light_curves.clear()
        logger.info(f"Cleared all light curves ({count} items)")
        self._notify_observers('light_curves_cleared', {'count': count})

    def update_light_curve(self, name: str, light_curve: Any) -> bool:
        """Update existing light curve."""
        if name in self._light_curves:
            self._light_curves[name] = light_curve
            logger.info(f"Updated light curve: '{name}'")
            self._notify_observers('light_curve_updated', {'name': name, 'data': light_curve})
            return True
        return False

    def _evict_oldest_light_curve(self) -> None:
        """Evict the oldest light curve using LRU strategy."""
        if self._light_curves:
            oldest_name = next(iter(self._light_curves))
            del self._light_curves[oldest_name]
            self._stats['total_evictions'] += 1
            logger.warning(f"Evicted oldest light curve: '{oldest_name}' (LRU policy)")
            self._notify_observers('light_curve_evicted', {'name': oldest_name})

    # =============================================================================
    # Time Series Data Management Methods
    # =============================================================================

    def add_timeseries_data(self, name: str, timeseries: Any) -> None:
        """Add time series data to the state."""
        if not name or not name.strip():
            raise ValueError("Timeseries name cannot be empty")

        if self.has_timeseries_data(name):
            raise ValueError(f"Timeseries with name '{name}' already exists")

        self._check_memory_limits()

        if len(self._timeseries_data) >= self.MAX_TIMESERIES:
            self._evict_oldest_timeseries()

        self._timeseries_data[name] = timeseries
        self._stats['total_additions'] += 1

        logger.info(f"Added timeseries: '{name}' (total: {len(self._timeseries_data)})")
        self._notify_observers('timeseries_added', {'name': name, 'data': timeseries})

    def get_timeseries_data(self, name: Optional[str] = None) -> Any:
        """Get time series data by name or all time series."""
        if name is None:
            return list(self._timeseries_data.items())
        return self._timeseries_data.get(name)

    def get_timeseries_names(self) -> List[str]:
        """Get list of all time series names."""
        return list(self._timeseries_data.keys())

    def remove_timeseries_data(self, name: str) -> bool:
        """Remove time series data by name."""
        if name in self._timeseries_data:
            del self._timeseries_data[name]
            self._stats['total_removals'] += 1
            logger.info(f"Removed timeseries: '{name}' (remaining: {len(self._timeseries_data)})")
            self._notify_observers('timeseries_removed', {'name': name})
            return True
        return False

    def has_timeseries_data(self, name: str) -> bool:
        """Check if time series data exists."""
        return name in self._timeseries_data

    def clear_timeseries_data(self) -> None:
        """Clear all time series data."""
        count = len(self._timeseries_data)
        self._timeseries_data.clear()
        logger.info(f"Cleared all timeseries ({count} items)")
        self._notify_observers('timeseries_cleared', {'count': count})

    def update_timeseries_data(self, name: str, timeseries: Any) -> bool:
        """Update existing time series data."""
        if name in self._timeseries_data:
            self._timeseries_data[name] = timeseries
            logger.info(f"Updated timeseries: '{name}'")
            self._notify_observers('timeseries_updated', {'name': name, 'data': timeseries})
            return True
        return False

    def _evict_oldest_timeseries(self) -> None:
        """Evict the oldest time series using LRU strategy."""
        if self._timeseries_data:
            oldest_name = next(iter(self._timeseries_data))
            del self._timeseries_data[oldest_name]
            self._stats['total_evictions'] += 1
            logger.warning(f"Evicted oldest timeseries: '{oldest_name}' (LRU policy)")
            self._notify_observers('timeseries_evicted', {'name': oldest_name})

    # =============================================================================
    # Clear All Methods
    # =============================================================================

    def clear_all(self) -> None:
        """
        Clear all state data (event data, light curves, time series).

        Example:
            >>> state_manager.clear_all()
        """
        total_items = len(self._event_data) + len(self._light_curves) + len(self._timeseries_data)

        self._event_data.clear()
        self._light_curves.clear()
        self._timeseries_data.clear()

        logger.info(f"Cleared all state data ({total_items} total items)")
        self._notify_observers('state_cleared', {'total_items': total_items})

    # =============================================================================
    # Observer Pattern Methods
    # =============================================================================

    def register_observer(self, callback: Callable[[str, Any], None]) -> None:
        """
        Register an observer callback to be notified of state changes.

        Args:
            callback: Function that takes (event_type: str, data: Any) as arguments

        Example:
            >>> def on_state_change(event_type, data):
            ...     print(f"State changed: {event_type}")
            >>> state_manager.register_observer(on_state_change)
        """
        if callback not in self._observers:
            self._observers.append(callback)
            callback_name = getattr(callback, '__name__', repr(callback))
            logger.debug(f"Registered observer: {callback_name}")

    def unregister_observer(self, callback: Callable[[str, Any], None]) -> None:
        """
        Unregister an observer callback.

        Args:
            callback: The callback function to remove
        """
        if callback in self._observers:
            self._observers.remove(callback)
            callback_name = getattr(callback, '__name__', repr(callback))
            logger.debug(f"Unregistered observer: {callback_name}")

    def _notify_observers(self, event_type: str, data: Any = None) -> None:
        """
        Notify all observers of a state change.

        Args:
            event_type (str): Type of event (e.g., 'event_data_added')
            data (Any): Associated data for the event
        """
        for observer in self._observers:
            try:
                observer(event_type, data)
            except Exception as e:
                logger.error(f"Error in observer {observer.__name__}: {e}")

    # =============================================================================
    # Memory Management Methods
    # =============================================================================

    def _calculate_memory_usage(self) -> float:
        """
        Calculate total memory usage of stored data in MB.

        Returns:
            float: Total memory usage in megabytes
        """
        total_bytes = 0

        # Calculate event data memory
        for event_list in self._event_data.values():
            total_bytes += sys.getsizeof(event_list)

        # Calculate light curve memory
        for light_curve in self._light_curves.values():
            total_bytes += sys.getsizeof(light_curve)

        # Calculate timeseries memory
        for timeseries in self._timeseries_data.values():
            total_bytes += sys.getsizeof(timeseries)

        return total_bytes / (1024 * 1024)  # Convert to MB

    def _check_memory_limits(self) -> None:
        """
        Check if current memory usage exceeds limits.

        Raises:
            MemoryError: If memory usage exceeds MAX_MEMORY_MB
        """
        current_memory = self._calculate_memory_usage()
        if current_memory > self.MAX_MEMORY_MB:
            raise MemoryError(
                f"Memory limit exceeded: {current_memory:.2f} MB / {self.MAX_MEMORY_MB:.2f} MB"
            )

    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current memory usage statistics.

        Returns:
            Dict with memory usage information

        Example:
            >>> usage = state_manager.get_memory_usage()
            >>> print(f"Using {usage['current_mb']:.2f} MB")
        """
        current_mb = self._calculate_memory_usage()
        return {
            'current_mb': current_mb,
            'max_mb': self.MAX_MEMORY_MB,
            'usage_percent': (current_mb / self.MAX_MEMORY_MB) * 100 if self.MAX_MEMORY_MB > 0 else 0,
        }

    # =============================================================================
    # Statistics and Info Methods
    # =============================================================================

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about state manager usage.

        Returns:
            Dict with statistics including counts, memory usage, etc.

        Example:
            >>> stats = state_manager.get_stats()
            >>> print(f"Total additions: {stats['total_additions']}")
        """
        return {
            **self._stats,
            'event_data_count': len(self._event_data),
            'light_curve_count': len(self._light_curves),
            'timeseries_count': len(self._timeseries_data),
            'total_items': len(self._event_data) + len(self._light_curves) + len(self._timeseries_data),
            'memory_usage': self.get_memory_usage(),
            'system_memory': self.get_system_memory_info(),
        }

    def __repr__(self) -> str:
        """String representation of StateManager."""
        return (
            f"StateManager(event_data={len(self._event_data)}, "
            f"light_curves={len(self._light_curves)}, "
            f"timeseries={len(self._timeseries_data)}, "
            f"max_memory={self.MAX_MEMORY_MB:.2f}MB)"
        )


# =============================================================================
# Singleton Instance
# =============================================================================

# Create a singleton instance that can be imported throughout the application
state_manager = StateManager()

# Backward compatibility: Provide the same interface as globals.py
# This allows gradual migration from global lists to StateManager
loaded_event_data = state_manager
loaded_light_curve = state_manager
loaded_timeseries_data = state_manager
