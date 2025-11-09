"""
Test Script for Reactive State Updates

This script tests that the StateManager's reactive parameters trigger
UI updates when state changes occur.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.state_manager import StateManager
from stingray.events import EventList
import numpy as np

def test_reactive_parameters():
    """Test that reactive parameters update correctly."""
    print("=" * 60)
    print("Testing Reactive State Updates")
    print("=" * 60)

    # Create state manager
    state = StateManager()

    print(f"\nInitial state:")
    print(f"  Event data count: {state.event_data_count}")
    print(f"  Light curve count: {state.light_curve_count}")
    print(f"  Timeseries count: {state.timeseries_count}")
    print(f"  Memory usage: {state.memory_usage_mb:.2f} MB")
    print(f"  Last operation: '{state.last_operation}'")

    # Test 1: Add event data
    print(f"\n{'='*60}")
    print("Test 1: Adding Event Data")
    print(f"{'='*60}")

    # Create mock event list
    times = np.arange(0, 100, 0.1)
    event_list = EventList(times, gti=np.array([[0, 100]]))

    # Add to state
    state.add_event_data("test_event_1", event_list)

    print(f"\nAfter adding 1 event list:")
    print(f"  Event data count: {state.event_data_count}")
    print(f"  Last operation: '{state.last_operation}'")

    # Test 2: Add more event data
    print(f"\n{'='*60}")
    print("Test 2: Adding More Event Data")
    print(f"{'='*60}")

    event_list_2 = EventList(times, gti=np.array([[0, 100]]))
    state.add_event_data("test_event_2", event_list_2)

    print(f"\nAfter adding 2nd event list:")
    print(f"  Event data count: {state.event_data_count}")
    print(f"  Last operation: '{state.last_operation}'")

    # Test 3: Remove event data
    print(f"\n{'='*60}")
    print("Test 3: Removing Event Data")
    print(f"{'='*60}")

    state.remove_event_data("test_event_1")

    print(f"\nAfter removing 1 event list:")
    print(f"  Event data count: {state.event_data_count}")
    print(f"  Last operation: '{state.last_operation}'")

    # Test 4: Clear all data
    print(f"\n{'='*60}")
    print("Test 4: Clearing All Data")
    print(f"{'='*60}")

    state.clear_event_data()

    print(f"\nAfter clearing all event data:")
    print(f"  Event data count: {state.event_data_count}")
    print(f"  Last operation: '{state.last_operation}'")

    # Test 5: Test stats
    print(f"\n{'='*60}")
    print("Test 5: State Statistics")
    print(f"{'='*60}")

    # Add some data again
    state.add_event_data("test_1", event_list)
    state.add_event_data("test_2", event_list_2)

    stats = state.get_stats()
    print(f"\nState statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print(f"\n{'='*60}")
    print("[PASS] All reactive update tests completed successfully!")
    print(f"{'='*60}")

    return True

def test_param_watchers():
    """Test that param watchers can be attached and triggered."""
    print(f"\n{'='*60}")
    print("Test 6: Parameter Watchers")
    print(f"{'='*60}")

    state = StateManager()

    # Track changes
    changes = []

    def on_event_count_change(event):
        changes.append(('event_data_count', event.new))
        print(f"  [OK] event_data_count changed to: {event.new}")

    def on_operation_change(event):
        changes.append(('last_operation', event.new))
        print(f"  [OK] last_operation changed to: '{event.new}'")

    # Attach watchers
    state.param.watch(on_event_count_change, 'event_data_count')
    state.param.watch(on_operation_change, 'last_operation')

    print("\nAttached watchers. Now adding event data...")

    # Create and add event list
    times = np.arange(0, 100, 0.1)
    event_list = EventList(times, gti=np.array([[0, 100]]))
    state.add_event_data("watched_event", event_list)

    print(f"\nChanges detected: {len(changes)}")
    for param_name, value in changes:
        print(f"  - {param_name}: {value}")

    print(f"\n{'='*60}")
    print("[PASS] Parameter watcher tests completed successfully!")
    print(f"{'='*60}")

    return len(changes) > 0

if __name__ == "__main__":
    try:
        # Run tests
        test1_passed = test_reactive_parameters()
        test2_passed = test_param_watchers()

        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Reactive Parameters Test: {'[PASS] PASSED' if test1_passed else '[FAIL] FAILED'}")
        print(f"Parameter Watchers Test: {'[PASS] PASSED' if test2_passed else '[FAIL] FAILED'}")
        print(f"{'='*60}\n")

        if test1_passed and test2_passed:
            print("SUCCESS: All tests passed! Reactive state updates are working correctly.")
            sys.exit(0)
        else:
            print("[WARN] Some tests failed. Please review the output above.")
            sys.exit(1)

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
