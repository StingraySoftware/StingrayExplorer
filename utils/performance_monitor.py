"""
Performance Monitoring Module

This module provides performance monitoring and timing instrumentation for
StingrayExplorer operations.

Features:
- Operation timing with context managers
- Performance metrics collection
- Operation history tracking
- Statistical analysis of operation performance
"""

import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
import statistics

logger = logging.getLogger(__name__)


@dataclass
class OperationMetric:
    """
    Represents a single operation metric.

    Attributes:
        operation_name: Name of the operation
        start_time: When the operation started
        end_time: When the operation ended
        duration_ms: Duration in milliseconds
        success: Whether the operation succeeded
        metadata: Additional metadata about the operation
    """
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """
    Performance monitoring system for tracking operation timings and metrics.

    This class provides tools for measuring, recording, and analyzing the
    performance of operations throughout the application.

    Example:
        >>> monitor = PerformanceMonitor()
        >>>
        >>> # Using context manager
        >>> with monitor.track_operation("load_event_list"):
        ...     event_list = EventList.read("file.evt")
        >>>
        >>> # Get statistics
        >>> stats = monitor.get_operation_stats("load_event_list")
        >>> print(f"Average: {stats['avg_ms']:.2f}ms")
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize the performance monitor.

        Args:
            max_history: Maximum number of metrics to keep in history
        """
        self.max_history = max_history
        self._metrics: List[OperationMetric] = []
        self._operation_counts: Dict[str, int] = {}
        logger.info(f"PerformanceMonitor initialized (max_history={max_history})")

    @contextmanager
    def track_operation(self, operation_name: str, **metadata):
        """
        Context manager for tracking operation performance.

        Args:
            operation_name: Name of the operation being tracked
            **metadata: Additional metadata to store with the metric

        Yields:
            None

        Example:
            >>> with monitor.track_operation("compute_power_spectrum", dt=0.1):
            ...     ps = AveragedPowerspectrum.from_lightcurve(lc, 100)
        """
        start_time = datetime.now()
        start_perf = time.perf_counter()
        success = True
        error = None

        try:
            yield
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = datetime.now()
            end_perf = time.perf_counter()
            duration_ms = (end_perf - start_perf) * 1000

            # Store error in metadata if operation failed
            if not success and error:
                metadata['error'] = error

            # Create and record metric
            metric = OperationMetric(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                success=success,
                metadata=metadata
            )

            self._record_metric(metric)

            # Log performance
            status = "SUCCESS" if success else "FAILED"
            logger.info(
                f"Operation '{operation_name}' {status} "
                f"(duration: {duration_ms:.2f}ms)"
            )

    def _record_metric(self, metric: OperationMetric) -> None:
        """Record a metric and maintain history limits."""
        self._metrics.append(metric)

        # Update operation count
        self._operation_counts[metric.operation_name] = (
            self._operation_counts.get(metric.operation_name, 0) + 1
        )

        # Enforce history limit (FIFO)
        if len(self._metrics) > self.max_history:
            oldest = self._metrics.pop(0)
            self._operation_counts[oldest.operation_name] -= 1

    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """
        Get statistical analysis for a specific operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Dict containing statistics:
            - count: Number of times operation was executed
            - avg_ms: Average duration in milliseconds
            - min_ms: Minimum duration
            - max_ms: Maximum duration
            - median_ms: Median duration
            - std_dev_ms: Standard deviation
            - success_rate: Percentage of successful operations

        Example:
            >>> stats = monitor.get_operation_stats("load_event_list")
            >>> print(f"Executed {stats['count']} times, avg {stats['avg_ms']:.2f}ms")
        """
        # Filter metrics for this operation
        op_metrics = [m for m in self._metrics if m.operation_name == operation_name]

        if not op_metrics:
            return {
                'count': 0,
                'avg_ms': 0.0,
                'min_ms': 0.0,
                'max_ms': 0.0,
                'median_ms': 0.0,
                'std_dev_ms': 0.0,
                'success_rate': 0.0
            }

        durations = [m.duration_ms for m in op_metrics]
        successes = sum(1 for m in op_metrics if m.success)

        return {
            'count': len(op_metrics),
            'avg_ms': statistics.mean(durations),
            'min_ms': min(durations),
            'max_ms': max(durations),
            'median_ms': statistics.median(durations),
            'std_dev_ms': statistics.stdev(durations) if len(durations) > 1 else 0.0,
            'success_rate': (successes / len(op_metrics)) * 100 if op_metrics else 0.0
        }

    def get_all_operation_names(self) -> List[str]:
        """
        Get list of all tracked operation names.

        Returns:
            List of operation names
        """
        return list(self._operation_counts.keys())

    def get_recent_operations(self, limit: int = 10) -> List[OperationMetric]:
        """
        Get most recent operations.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of recent OperationMetric objects
        """
        return self._metrics[-limit:] if self._metrics else []

    def get_slow_operations(self, threshold_ms: float = 1000.0, limit: int = 10) -> List[OperationMetric]:
        """
        Get operations that exceeded a duration threshold.

        Args:
            threshold_ms: Duration threshold in milliseconds
            limit: Maximum number of operations to return

        Returns:
            List of slow OperationMetric objects, sorted by duration (slowest first)
        """
        slow_ops = [m for m in self._metrics if m.duration_ms > threshold_ms]
        slow_ops.sort(key=lambda x: x.duration_ms, reverse=True)
        return slow_ops[:limit]

    def get_failed_operations(self, limit: int = 10) -> List[OperationMetric]:
        """
        Get operations that failed.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of failed OperationMetric objects (most recent first)
        """
        failed = [m for m in self._metrics if not m.success]
        return failed[-limit:] if failed else []

    def get_summary(self) -> Dict[str, Any]:
        """
        Get overall performance summary.

        Returns:
            Dict with summary statistics:
            - total_operations: Total number of tracked operations
            - unique_operations: Number of unique operation types
            - total_duration_ms: Total time spent in all operations
            - avg_duration_ms: Average operation duration
            - success_rate: Overall success rate
            - most_frequent: Most frequently called operation
            - slowest: Slowest operation type (by average)
        """
        if not self._metrics:
            return {
                'total_operations': 0,
                'unique_operations': 0,
                'total_duration_ms': 0.0,
                'avg_duration_ms': 0.0,
                'success_rate': 0.0,
                'most_frequent': None,
                'slowest': None
            }

        total_duration = sum(m.duration_ms for m in self._metrics)
        total_success = sum(1 for m in self._metrics if m.success)

        # Find most frequent operation
        most_frequent = max(self._operation_counts.items(), key=lambda x: x[1])[0] if self._operation_counts else None

        # Find slowest operation (by average)
        slowest = None
        slowest_avg = 0.0
        for op_name in self.get_all_operation_names():
            stats = self.get_operation_stats(op_name)
            if stats['avg_ms'] > slowest_avg:
                slowest_avg = stats['avg_ms']
                slowest = op_name

        return {
            'total_operations': len(self._metrics),
            'unique_operations': len(self._operation_counts),
            'total_duration_ms': total_duration,
            'avg_duration_ms': total_duration / len(self._metrics),
            'success_rate': (total_success / len(self._metrics)) * 100,
            'most_frequent': most_frequent,
            'slowest': slowest
        }

    def clear_history(self) -> None:
        """Clear all recorded metrics."""
        count = len(self._metrics)
        self._metrics.clear()
        self._operation_counts.clear()
        logger.info(f"Cleared performance history ({count} metrics)")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
