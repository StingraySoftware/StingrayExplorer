"""
Unit tests for the StateManager class.

This test suite covers:
- Event data management (add, get, remove, update, clear)
- Light curve management
- Time series management
- Memory limits and LRU eviction
- Observer pattern
- Error handling and validation
"""

import pytest
from unittest.mock import MagicMock, patch
from utils.state_manager import StateManager


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def state_manager():
    """Create a fresh StateManager instance for each test."""
    return StateManager()


@pytest.fixture
def mock_event_list():
    """Create a mock EventList object."""
    mock = MagicMock()
    mock.__sizeof__ = MagicMock(return_value=1024 * 1024)  # 1 MB
    return mock


@pytest.fixture
def mock_light_curve():
    """Create a mock Lightcurve object."""
    mock = MagicMock()
    mock.__sizeof__ = MagicMock(return_value=512 * 1024)  # 512 KB
    return mock


@pytest.fixture
def mock_timeseries():
    """Create a mock timeseries object."""
    mock = MagicMock()
    mock.__sizeof__ = MagicMock(return_value=256 * 1024)  # 256 KB
    return mock


# =============================================================================
# Event Data Management Tests
# =============================================================================

class TestEventDataManagement:
    """Tests for event data management methods."""

    def test_add_event_data_success(self, state_manager, mock_event_list):
        """Test successfully adding event data."""
        state_manager.add_event_data("test_event", mock_event_list)

        assert state_manager.has_event_data("test_event")
        assert state_manager.get_event_data("test_event") == mock_event_list
        assert len(state_manager.get_event_data()) == 1

    def test_add_event_data_duplicate_name_raises_error(self, state_manager, mock_event_list):
        """Test that adding duplicate name raises ValueError."""
        state_manager.add_event_data("test_event", mock_event_list)

        with pytest.raises(ValueError, match="already exists"):
            state_manager.add_event_data("test_event", mock_event_list)

    def test_add_event_data_empty_name_raises_error(self, state_manager, mock_event_list):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            state_manager.add_event_data("", mock_event_list)

        with pytest.raises(ValueError, match="cannot be empty"):
            state_manager.add_event_data("   ", mock_event_list)

    def test_get_event_data_by_name(self, state_manager, mock_event_list):
        """Test retrieving event data by name."""
        state_manager.add_event_data("test_event", mock_event_list)

        result = state_manager.get_event_data("test_event")
        assert result == mock_event_list

    def test_get_event_data_nonexistent_returns_none(self, state_manager):
        """Test that getting nonexistent data returns None."""
        result = state_manager.get_event_data("nonexistent")
        assert result is None

    def test_get_all_event_data(self, state_manager, mock_event_list):
        """Test retrieving all event data."""
        mock_event_list2 = MagicMock()
        mock_event_list2.__sizeof__ = MagicMock(return_value=1024 * 1024)

        state_manager.add_event_data("event1", mock_event_list)
        state_manager.add_event_data("event2", mock_event_list2)

        all_data = state_manager.get_event_data()
        assert len(all_data) == 2
        assert all_data[0] == ("event1", mock_event_list)
        assert all_data[1] == ("event2", mock_event_list2)

    def test_get_event_data_names(self, state_manager, mock_event_list):
        """Test retrieving all event data names."""
        state_manager.add_event_data("event1", mock_event_list)
        state_manager.add_event_data("event2", mock_event_list)

        names = state_manager.get_event_data_names()
        assert names == ["event1", "event2"]

    def test_remove_event_data_success(self, state_manager, mock_event_list):
        """Test successfully removing event data."""
        state_manager.add_event_data("test_event", mock_event_list)

        result = state_manager.remove_event_data("test_event")
        assert result is True
        assert not state_manager.has_event_data("test_event")

    def test_remove_event_data_nonexistent_returns_false(self, state_manager):
        """Test that removing nonexistent data returns False."""
        result = state_manager.remove_event_data("nonexistent")
        assert result is False

    def test_update_event_data_success(self, state_manager, mock_event_list):
        """Test successfully updating event data."""
        state_manager.add_event_data("test_event", mock_event_list)

        new_mock = MagicMock()
        new_mock.__sizeof__ = MagicMock(return_value=1024 * 1024)

        result = state_manager.update_event_data("test_event", new_mock)
        assert result is True
        assert state_manager.get_event_data("test_event") == new_mock

    def test_update_event_data_nonexistent_returns_false(self, state_manager, mock_event_list):
        """Test that updating nonexistent data returns False."""
        result = state_manager.update_event_data("nonexistent", mock_event_list)
        assert result is False

    def test_clear_event_data(self, state_manager, mock_event_list):
        """Test clearing all event data."""
        state_manager.add_event_data("event1", mock_event_list)
        state_manager.add_event_data("event2", mock_event_list)

        state_manager.clear_event_data()
        assert len(state_manager.get_event_data()) == 0

    def test_has_event_data(self, state_manager, mock_event_list):
        """Test checking if event data exists."""
        assert not state_manager.has_event_data("test_event")

        state_manager.add_event_data("test_event", mock_event_list)
        assert state_manager.has_event_data("test_event")


# =============================================================================
# Light Curve Management Tests
# =============================================================================

class TestLightCurveManagement:
    """Tests for light curve management methods."""

    def test_add_light_curve_success(self, state_manager, mock_light_curve):
        """Test successfully adding light curve."""
        state_manager.add_light_curve("test_lc", mock_light_curve)

        assert state_manager.has_light_curve("test_lc")
        assert state_manager.get_light_curve("test_lc") == mock_light_curve

    def test_add_light_curve_duplicate_raises_error(self, state_manager, mock_light_curve):
        """Test that adding duplicate name raises ValueError."""
        state_manager.add_light_curve("test_lc", mock_light_curve)

        with pytest.raises(ValueError, match="already exists"):
            state_manager.add_light_curve("test_lc", mock_light_curve)

    def test_get_all_light_curves(self, state_manager, mock_light_curve):
        """Test retrieving all light curves."""
        state_manager.add_light_curve("lc1", mock_light_curve)
        state_manager.add_light_curve("lc2", mock_light_curve)

        all_lcs = state_manager.get_light_curve()
        assert len(all_lcs) == 2

    def test_get_light_curve_names(self, state_manager, mock_light_curve):
        """Test retrieving all light curve names."""
        state_manager.add_light_curve("lc1", mock_light_curve)
        state_manager.add_light_curve("lc2", mock_light_curve)

        names = state_manager.get_light_curve_names()
        assert names == ["lc1", "lc2"]

    def test_remove_light_curve(self, state_manager, mock_light_curve):
        """Test removing light curve."""
        state_manager.add_light_curve("test_lc", mock_light_curve)

        result = state_manager.remove_light_curve("test_lc")
        assert result is True
        assert not state_manager.has_light_curve("test_lc")

    def test_update_light_curve(self, state_manager, mock_light_curve):
        """Test updating light curve."""
        state_manager.add_light_curve("test_lc", mock_light_curve)

        new_mock = MagicMock()
        new_mock.__sizeof__ = MagicMock(return_value=512 * 1024)

        result = state_manager.update_light_curve("test_lc", new_mock)
        assert result is True
        assert state_manager.get_light_curve("test_lc") == new_mock

    def test_clear_light_curves(self, state_manager, mock_light_curve):
        """Test clearing all light curves."""
        state_manager.add_light_curve("lc1", mock_light_curve)
        state_manager.add_light_curve("lc2", mock_light_curve)

        state_manager.clear_light_curves()
        assert len(state_manager.get_light_curve()) == 0


# =============================================================================
# Time Series Management Tests
# =============================================================================

class TestTimeSeriesManagement:
    """Tests for time series management methods."""

    def test_add_timeseries_success(self, state_manager, mock_timeseries):
        """Test successfully adding timeseries."""
        state_manager.add_timeseries_data("test_ts", mock_timeseries)

        assert state_manager.has_timeseries_data("test_ts")
        assert state_manager.get_timeseries_data("test_ts") == mock_timeseries

    def test_add_timeseries_duplicate_raises_error(self, state_manager, mock_timeseries):
        """Test that adding duplicate name raises ValueError."""
        state_manager.add_timeseries_data("test_ts", mock_timeseries)

        with pytest.raises(ValueError, match="already exists"):
            state_manager.add_timeseries_data("test_ts", mock_timeseries)

    def test_remove_timeseries(self, state_manager, mock_timeseries):
        """Test removing timeseries."""
        state_manager.add_timeseries_data("test_ts", mock_timeseries)

        result = state_manager.remove_timeseries_data("test_ts")
        assert result is True
        assert not state_manager.has_timeseries_data("test_ts")


# =============================================================================
# Memory Management Tests
# =============================================================================

class TestMemoryManagement:
    """Tests for memory management features."""

    def test_max_event_lists_eviction(self, state_manager, mock_event_list):
        """Test that oldest event is evicted when MAX_EVENT_LISTS is reached."""
        state_manager.MAX_EVENT_LISTS = 3

        state_manager.add_event_data("event1", mock_event_list)
        state_manager.add_event_data("event2", mock_event_list)
        state_manager.add_event_data("event3", mock_event_list)

        # Adding 4th should evict event1
        state_manager.add_event_data("event4", mock_event_list)

        assert not state_manager.has_event_data("event1")
        assert state_manager.has_event_data("event2")
        assert state_manager.has_event_data("event3")
        assert state_manager.has_event_data("event4")
        assert len(state_manager.get_event_data()) == 3

    def test_memory_usage_calculation(self, state_manager, mock_event_list):
        """Test memory usage calculation."""
        state_manager.add_event_data("event1", mock_event_list)

        usage = state_manager.get_memory_usage()
        assert usage['current_mb'] > 0
        assert usage['max_mb'] > 0
        assert 0 <= usage['usage_percent'] <= 100

    @patch('psutil.virtual_memory')
    def test_dynamic_memory_limit(self, mock_vm):
        """Test that memory limit is dynamically calculated from system RAM."""
        # Mock system with 16 GB RAM
        mock_vm.return_value.total = 16 * 1024 * 1024 * 1024  # 16 GB in bytes

        sm = StateManager()

        # Should be 80% of 16 GB = 12.8 GB = 13107.2 MB
        expected_limit = (16 * 1024 * 0.80)
        assert abs(sm.MAX_MEMORY_MB - expected_limit) < 1  # Allow small rounding error

    def test_set_memory_usage_percent(self, state_manager):
        """Test changing memory usage percentage."""
        original_limit = state_manager.MAX_MEMORY_MB

        state_manager.set_memory_usage_percent(0.50)  # 50%

        # New limit should be approximately half of 80% limit
        assert state_manager.MAX_MEMORY_MB < original_limit

    def test_set_memory_usage_percent_invalid_raises_error(self, state_manager):
        """Test that invalid percentage raises ValueError."""
        with pytest.raises(ValueError, match="between 0.1"):
            state_manager.set_memory_usage_percent(0.05)  # Too low

        with pytest.raises(ValueError, match="between 0.1"):
            state_manager.set_memory_usage_percent(1.5)  # Too high

    def test_get_system_memory_info(self, state_manager):
        """Test getting system memory information."""
        info = state_manager.get_system_memory_info()

        assert 'total_mb' in info
        assert 'available_mb' in info
        assert 'allocated_limit_mb' in info
        assert info['total_mb'] > 0


# =============================================================================
# Observer Pattern Tests
# =============================================================================

class TestObserverPattern:
    """Tests for observer pattern implementation."""

    def test_register_observer(self, state_manager):
        """Test registering an observer."""
        callback = MagicMock()

        state_manager.register_observer(callback)
        assert callback in state_manager._observers

    def test_observer_notified_on_add(self, state_manager, mock_event_list):
        """Test that observers are notified when data is added."""
        callback = MagicMock()
        state_manager.register_observer(callback)

        state_manager.add_event_data("test_event", mock_event_list)

        callback.assert_called_once()
        call_args = callback.call_args[0]
        assert call_args[0] == 'event_data_added'
        assert call_args[1]['name'] == 'test_event'

    def test_observer_notified_on_remove(self, state_manager, mock_event_list):
        """Test that observers are notified when data is removed."""
        callback = MagicMock()
        state_manager.add_event_data("test_event", mock_event_list)

        state_manager.register_observer(callback)
        state_manager.remove_event_data("test_event")

        callback.assert_called_once()
        call_args = callback.call_args[0]
        assert call_args[0] == 'event_data_removed'

    def test_observer_notified_on_clear(self, state_manager, mock_event_list):
        """Test that observers are notified when data is cleared."""
        callback = MagicMock()
        state_manager.add_event_data("test_event", mock_event_list)

        state_manager.register_observer(callback)
        state_manager.clear_event_data()

        callback.assert_called_once()
        call_args = callback.call_args[0]
        assert call_args[0] == 'event_data_cleared'

    def test_unregister_observer(self, state_manager, mock_event_list):
        """Test unregistering an observer."""
        callback = MagicMock()
        state_manager.register_observer(callback)
        state_manager.unregister_observer(callback)

        assert callback not in state_manager._observers

        # Should not be called after unregistering
        state_manager.add_event_data("test_event", mock_event_list)
        callback.assert_not_called()

    def test_observer_error_doesnt_break_state(self, state_manager, mock_event_list):
        """Test that errors in observers don't break state management."""
        def bad_callback(event_type, data):
            raise Exception("Observer error!")

        state_manager.register_observer(bad_callback)

        # Should not raise exception
        state_manager.add_event_data("test_event", mock_event_list)

        # Data should still be added
        assert state_manager.has_event_data("test_event")


# =============================================================================
# Clear All Tests
# =============================================================================

class TestClearAll:
    """Tests for clearing all state."""

    def test_clear_all(self, state_manager, mock_event_list, mock_light_curve, mock_timeseries):
        """Test clearing all state data."""
        state_manager.add_event_data("event1", mock_event_list)
        state_manager.add_light_curve("lc1", mock_light_curve)
        state_manager.add_timeseries_data("ts1", mock_timeseries)

        state_manager.clear_all()

        assert len(state_manager.get_event_data()) == 0
        assert len(state_manager.get_light_curve()) == 0
        assert len(state_manager.get_timeseries_data()) == 0


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatistics:
    """Tests for statistics and info methods."""

    def test_get_stats(self, state_manager, mock_event_list):
        """Test getting statistics."""
        state_manager.add_event_data("event1", mock_event_list)

        stats = state_manager.get_stats()

        assert stats['total_additions'] >= 1
        assert stats['event_data_count'] == 1
        assert stats['total_items'] == 1
        assert 'memory_usage' in stats
        assert 'system_memory' in stats

    def test_repr(self, state_manager, mock_event_list):
        """Test string representation."""
        state_manager.add_event_data("event1", mock_event_list)

        repr_str = repr(state_manager)
        assert "StateManager" in repr_str
        assert "event_data=1" in repr_str


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for combined operations."""

    def test_mixed_data_types(self, state_manager, mock_event_list, mock_light_curve, mock_timeseries):
        """Test managing multiple data types simultaneously."""
        state_manager.add_event_data("event1", mock_event_list)
        state_manager.add_light_curve("lc1", mock_light_curve)
        state_manager.add_timeseries_data("ts1", mock_timeseries)

        assert state_manager.has_event_data("event1")
        assert state_manager.has_light_curve("lc1")
        assert state_manager.has_timeseries_data("ts1")

        stats = state_manager.get_stats()
        assert stats['total_items'] == 3

    def test_eviction_statistics(self, state_manager, mock_event_list):
        """Test that eviction updates statistics."""
        state_manager.MAX_EVENT_LISTS = 2

        state_manager.add_event_data("event1", mock_event_list)
        state_manager.add_event_data("event2", mock_event_list)
        state_manager.add_event_data("event3", mock_event_list)  # Should trigger eviction

        stats = state_manager.get_stats()
        assert stats['total_evictions'] == 1
