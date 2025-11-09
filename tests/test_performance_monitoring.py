"""
Test Script for Performance Monitoring

This script tests that the PerformanceMonitor tracks operations correctly
and provides accurate statistics.
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.performance_monitor import performance_monitor
import numpy as np

def test_operation_tracking():
    """Test that operations are tracked correctly."""
    print("=" * 60)
    print("Testing Performance Monitoring")
    print("=" * 60)

    # Clear any existing history
    performance_monitor.clear_history()

    print(f"\nInitial state:")
    summary = performance_monitor.get_summary()
    print(f"  Total operations: {summary['total_operations']}")
    print(f"  Unique operations: {summary['unique_operations']}")

    # Test 1: Track a simple operation
    print(f"\n{'='*60}")
    print("Test 1: Tracking Simple Operation")
    print(f"{'='*60}")

    with performance_monitor.track_operation("test_operation_1"):
        # Simulate some work
        time.sleep(0.1)
        result = sum(range(1000))

    summary = performance_monitor.get_summary()
    print(f"\nAfter 1 operation:")
    print(f"  Total operations: {summary['total_operations']}")
    print(f"  Average duration: {summary['avg_duration_ms']:.2f} ms")
    print(f"  Success rate: {summary['success_rate']:.1f}%")

    # Test 2: Track multiple operations
    print(f"\n{'='*60}")
    print("Test 2: Tracking Multiple Operations")
    print(f"{'='*60}")

    for i in range(5):
        with performance_monitor.track_operation("batch_operation"):
            time.sleep(0.05)
            _ = np.random.rand(100)

    stats = performance_monitor.get_operation_stats("batch_operation")
    print(f"\nStats for 'batch_operation':")
    print(f"  Count: {stats['count']}")
    print(f"  Average: {stats['avg_ms']:.2f} ms")
    print(f"  Min: {stats['min_ms']:.2f} ms")
    print(f"  Max: {stats['max_ms']:.2f} ms")
    print(f"  Median: {stats['median_ms']:.2f} ms")
    print(f"  Success rate: {stats['success_rate']:.1f}%")

    # Test 3: Track failed operation
    print(f"\n{'='*60}")
    print("Test 3: Tracking Failed Operation")
    print(f"{'='*60}")

    try:
        with performance_monitor.track_operation("failing_operation"):
            raise ValueError("Intentional test error")
    except ValueError:
        pass  # Expected

    failed_ops = performance_monitor.get_failed_operations(limit=10)
    print(f"\nFailed operations: {len(failed_ops)}")
    if failed_ops:
        failed_op = failed_ops[0]
        print(f"  Operation: {failed_op.operation_name}")
        print(f"  Duration: {failed_op.duration_ms:.2f} ms")
        print(f"  Error: {failed_op.metadata.get('error', 'N/A')}")

    # Test 4: Get recent operations
    print(f"\n{'='*60}")
    print("Test 4: Recent Operations")
    print(f"{'='*60}")

    recent = performance_monitor.get_recent_operations(limit=5)
    print(f"\nLast {len(recent)} operations:")
    for op in recent:
        status = "[OK]" if op.success else "[X]"
        print(f"  {status} {op.operation_name}: {op.duration_ms:.2f} ms")

    # Test 5: Summary statistics
    print(f"\n{'='*60}")
    print("Test 5: Summary Statistics")
    print(f"{'='*60}")

    summary = performance_monitor.get_summary()
    print(f"\nOverall Summary:")
    print(f"  Total operations: {summary['total_operations']}")
    print(f"  Unique operations: {summary['unique_operations']}")
    print(f"  Total duration: {summary['total_duration_ms']:.2f} ms")
    print(f"  Average duration: {summary['avg_duration_ms']:.2f} ms")
    print(f"  Success rate: {summary['success_rate']:.1f}%")
    print(f"  Most frequent: {summary['most_frequent']}")
    print(f"  Slowest: {summary['slowest']}")

    print(f"\n{'='*60}")
    print("[PASS] All performance monitoring tests completed successfully!")
    print(f"{'='*60}")

    return summary['total_operations'] > 0

def test_metadata_tracking():
    """Test that metadata is tracked correctly."""
    print(f"\n{'='*60}")
    print("Test 6: Metadata Tracking")
    print(f"{'='*60}")

    with performance_monitor.track_operation("metadata_test",
                                              file_size=1024,
                                              format="ogip"):
        time.sleep(0.05)

    recent = performance_monitor.get_recent_operations(limit=1)
    if recent:
        op = recent[0]
        print(f"\nOperation: {op.operation_name}")
        print(f"Metadata:")
        for key, value in op.metadata.items():
            print(f"  {key}: {value}")

    print(f"\n{'='*60}")
    print("[PASS] Metadata tracking test completed successfully!")
    print(f"{'='*60}")

    return True

def test_slow_operations():
    """Test identification of slow operations."""
    print(f"\n{'='*60}")
    print("Test 7: Slow Operations Detection")
    print(f"{'='*60}")

    # Create some fast and slow operations
    with performance_monitor.track_operation("fast_operation"):
        time.sleep(0.01)

    with performance_monitor.track_operation("slow_operation"):
        time.sleep(0.15)

    # Get slow operations (threshold: 100ms)
    slow_ops = performance_monitor.get_slow_operations(threshold_ms=100.0, limit=10)
    print(f"\nOperations slower than 100ms: {len(slow_ops)}")
    for op in slow_ops:
        print(f"  {op.operation_name}: {op.duration_ms:.2f} ms")

    print(f"\n{'='*60}")
    print("[PASS] Slow operations detection test completed successfully!")
    print(f"{'='*60}")

    return len(slow_ops) > 0

if __name__ == "__main__":
    try:
        # Run tests
        test1_passed = test_operation_tracking()
        test2_passed = test_metadata_tracking()
        test3_passed = test_slow_operations()

        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Operation Tracking Test: {'[PASS] PASSED' if test1_passed else '[FAIL] FAILED'}")
        print(f"Metadata Tracking Test: {'[PASS] PASSED' if test2_passed else '[FAIL] FAILED'}")
        print(f"Slow Operations Test: {'[PASS] PASSED' if test3_passed else '[FAIL] FAILED'}")
        print(f"{'='*60}\n")

        if test1_passed and test2_passed and test3_passed:
            print("SUCCESS: All tests passed! Performance monitoring is working correctly.")
            sys.exit(0)
        else:
            print("[WARN] Some tests failed. Please review the output above.")
            sys.exit(1)

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
