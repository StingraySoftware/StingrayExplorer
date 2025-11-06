"""
Global State Variables Module

DEPRECATED: This module is being migrated to use StateManager for better encapsulation.

The global lists below provide backward compatibility with existing code.
New code should import and use state_manager directly from utils.state_manager.

Migration guide:
    Old code:
        from utils.globals import loaded_event_data
        loaded_event_data.append((name, event_list))

    New code:
        from utils.state_manager import state_manager
        state_manager.add_event_data(name, event_list)
"""

# Import the state manager singleton
from utils.state_manager import state_manager

# Backward compatibility: Create wrapper classes that behave like lists
# but delegate to the state manager
class EventDataList:
    """Backward compatibility wrapper for event data access."""

    def append(self, item):
        """Add event data (name, event_list) tuple."""
        if isinstance(item, tuple) and len(item) == 2:
            name, event_list = item
            state_manager.add_event_data(name, event_list)
        else:
            raise ValueError("Expected tuple of (name, event_list)")

    def __getitem__(self, index):
        """Get event data by index."""
        all_data = state_manager.get_event_data()
        return all_data[index]

    def __len__(self):
        """Return number of event data items."""
        return len(state_manager.get_event_data())

    def __iter__(self):
        """Iterate over event data."""
        return iter(state_manager.get_event_data())

    def clear(self):
        """Clear all event data."""
        state_manager.clear_event_data()

    def __repr__(self):
        return f"EventDataList({len(self)} items)"


class LightCurveList:
    """Backward compatibility wrapper for light curve access."""

    def append(self, item):
        """Add light curve (name, light_curve) tuple."""
        if isinstance(item, tuple) and len(item) == 2:
            name, light_curve = item
            state_manager.add_light_curve(name, light_curve)
        else:
            raise ValueError("Expected tuple of (name, light_curve)")

    def __getitem__(self, index):
        """Get light curve by index."""
        all_data = state_manager.get_light_curve()
        return all_data[index]

    def __len__(self):
        """Return number of light curves."""
        return len(state_manager.get_light_curve())

    def __iter__(self):
        """Iterate over light curves."""
        return iter(state_manager.get_light_curve())

    def clear(self):
        """Clear all light curves."""
        state_manager.clear_light_curves()

    def __repr__(self):
        return f"LightCurveList({len(self)} items)"


class TimeseriesDataList:
    """Backward compatibility wrapper for timeseries data access."""

    def append(self, item):
        """Add timeseries (name, timeseries) tuple."""
        if isinstance(item, tuple) and len(item) == 2:
            name, timeseries = item
            state_manager.add_timeseries_data(name, timeseries)
        else:
            raise ValueError("Expected tuple of (name, timeseries)")

    def __getitem__(self, index):
        """Get timeseries by index."""
        all_data = state_manager.get_timeseries_data()
        return all_data[index]

    def __len__(self):
        """Return number of timeseries items."""
        return len(state_manager.get_timeseries_data())

    def __iter__(self):
        """Iterate over timeseries data."""
        return iter(state_manager.get_timeseries_data())

    def clear(self):
        """Clear all timeseries data."""
        state_manager.clear_timeseries_data()

    def __repr__(self):
        return f"TimeseriesDataList({len(self)} items)"


# Create instances that behave like the old global lists
loaded_event_data = EventDataList()
loaded_light_curve = LightCurveList()
loaded_timeseries_data = TimeseriesDataList()
