"""
Lazy Loading Module for Large FITS Files

This module provides memory-efficient loading of large X-ray observation files
using Stingray's FITSTimeseriesReader for streaming data access.

Based on Stingray's official performance tutorial:
https://docs.stingray.science/en/stable/notebooks/Performance/Dealing%20with%20large%20data%20files.html

Features:
- Lazy loading of FITS files without loading entire dataset into memory
- Memory usage estimation and safety checks
- Streaming segment access for chunked processing
- Metadata extraction without full data load
"""

import os
import logging
from typing import Dict, List, Optional, Any, Iterator, Tuple
import numpy as np
import psutil

from stingray.io import FITSTimeseriesReader
from stingray.gti import time_intervals_from_gtis
from stingray.utils import histogram
from stingray import EventList

logger = logging.getLogger(__name__)


class LazyEventLoader:
    """
    Memory-efficient wrapper for loading large FITS event files.

    This class uses Stingray's FITSTimeseriesReader to enable lazy loading,
    where data remains in the FITS file until accessed. This allows analysis
    of files larger than available RAM.

    Example:
        >>> loader = LazyEventLoader("large_observation.evt")
        >>> metadata = loader.get_metadata()
        >>> print(f"File has {metadata['n_events_estimate']} events")
        >>>
        >>> if loader.can_load_safely():
        ...     # Safe to load into memory
        ...     events = loader.load_full()
        ... else:
        ...     # Use streaming instead
        ...     for segment in loader.stream_segments(segment_size=100):
        ...         process_segment(segment)
    """

    def __init__(self, file_path: str):
        """
        Initialize lazy loader for a FITS file.

        Args:
            file_path: Path to the FITS event file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid FITS event file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        self.file_path = file_path
        self.file_size = os.path.getsize(file_path)

        try:
            # Initialize reader (doesn't load data, just opens file)
            self.reader = FITSTimeseriesReader(file_path, data_kind="times")
        except Exception as e:
            raise ValueError(f"Failed to open FITS file: {e}") from e

        logger.info(
            f"LazyEventLoader initialized for {file_path} "
            f"({self.format_file_size(self.file_size)})"
        )

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get file metadata without loading event data.

        This is a fast operation that only reads the FITS headers,
        not the event data itself.

        Returns:
            Dict containing:
                - gti: Good time intervals
                - mjdref: Reference MJD
                - n_events_estimate: Rough estimate of number of events
                - time_range: (min_time, max_time) from GTIs
                - file_size_mb: File size in megabytes
                - file_size_gb: File size in gigabytes
                - duration_s: Total observation duration in seconds
        """
        gti = self.reader.gti

        # Estimate number of events from file size
        # Typical FITS event: ~12 bytes compressed in file
        n_events_estimate = self.file_size / 12

        # Calculate observation duration from GTIs
        duration_s = float(np.sum(gti[:, 1] - gti[:, 0]))

        metadata = {
            'gti': gti,
            'mjdref': getattr(self.reader, 'mjdref', 0.0),
            'n_events_estimate': int(n_events_estimate),
            'time_range': (float(gti.min()), float(gti.max())),
            'file_size_mb': self.file_size / (1024**2),
            'file_size_gb': self.file_size / (1024**3),
            'duration_s': duration_s,
            'estimated_count_rate': n_events_estimate / duration_s if duration_s > 0 else 0
        }

        logger.debug(f"Metadata extracted: {metadata}")
        return metadata

    def estimate_memory_usage(self, format_type: str = 'fits') -> int:
        """
        Estimate memory needed to load entire file into EventList.

        Based on Stingray's official benchmarks:
        - FITS event file: ~3x file size (2.6x measured + safety margin)
        - HDF5: ~2x file size (more efficient format)
        - Pickle: ~1.5x file size (most efficient)

        Reference: Stingray Performance Tutorial
        https://docs.stingray.science/en/stable/notebooks/Performance/Dealing%20with%20large%20data%20files.html
        Real test: 2GB FITS file → 5.2GB peak memory = 2.6x multiplier

        Args:
            format_type: File format type (fits, evt, ogip, hea)

        Returns:
            Estimated peak memory usage in bytes
        """
        # Memory multipliers based on file type
        # Values based on Stingray's official performance benchmarks
        multipliers = {
            'fits': 3,
            'evt': 3,
            'ogip': 3,
            'hea': 3,
            'hdf5': 2,
            'pickle': 1.5,
        }

        multiplier = multipliers.get(format_type, 3)  # Conservative default
        estimated_bytes = self.file_size * multiplier

        logger.debug(
            f"Estimated memory: {self.format_file_size(estimated_bytes)} "
            f"(multiplier: {multiplier}x)"
        )

        return estimated_bytes

    def can_load_safely(
        self,
        safety_margin: float = 0.5,
        format_type: str = 'fits'
    ) -> bool:
        """
        Check if file can be safely loaded into memory.

        Args:
            safety_margin: Fraction of available RAM to use (0.0-1.0)
                          Default 0.5 means use at most 50% of available RAM
            format_type: File format for memory estimation

        Returns:
            True if file can be loaded without risk of memory exhaustion
        """
        available_ram = psutil.virtual_memory().available
        needed_ram = self.estimate_memory_usage(format_type)
        safe_limit = available_ram * safety_margin

        can_load = needed_ram < safe_limit

        logger.info(
            f"Memory check: Need {self.format_file_size(needed_ram)}, "
            f"Safe limit {self.format_file_size(safe_limit)} "
            f"({safety_margin*100:.0f}% of {self.format_file_size(available_ram)} available) "
            f"-> {'SAFE' if can_load else 'RISKY'}"
        )

        return can_load

    def get_system_memory_info(self) -> Dict[str, Any]:
        """
        Get current system memory information.

        Returns:
            Dict with memory stats:
                - total_mb: Total system RAM
                - available_mb: Available RAM
                - used_mb: Used RAM
                - percent: Memory usage percentage
                - process_mb: Current process memory usage
        """
        vm = psutil.virtual_memory()
        process = psutil.Process()

        return {
            'total_mb': vm.total / (1024**2),
            'available_mb': vm.available / (1024**2),
            'used_mb': vm.used / (1024**2),
            'percent': vm.percent,
            'process_mb': process.memory_info().rss / (1024**2)
        }

    def load_full(
        self,
        rmf_file: Optional[str] = None,
        additional_columns: Optional[List[str]] = None
    ) -> EventList:
        """
        Load entire file into EventList.

        WARNING: Only use this if can_load_safely() returns True!
        For large files, use stream_segments() instead.

        Args:
            rmf_file: Optional path to RMF file for energy calibration
            additional_columns: Additional FITS columns to load

        Returns:
            Complete EventList object

        Raises:
            MemoryError: If system runs out of memory during load
        """
        logger.info(f"Loading full EventList from {self.file_path}")

        try:
            # Use EventList.read for full load (works with FITSTimeseriesReader internally)
            events = EventList.read(
                self.file_path,
                fmt='ogip',
                rmf_file=rmf_file,
                additional_columns=additional_columns
            )

            logger.info(
                f"Loaded {len(events.time)} events "
                f"(memory: {self.get_system_memory_info()['process_mb']:.1f} MB)"
            )

            return events

        except MemoryError as e:
            logger.error(f"Out of memory loading {self.file_path}")
            raise MemoryError(
                f"Insufficient memory to load file. "
                f"File size: {self.format_file_size(self.file_size)}. "
                f"Try using stream_segments() instead."
            ) from e

    def stream_segments(
        self,
        segment_size: float
    ) -> Iterator[np.ndarray]:
        """
        Stream event time segments without loading full file.

        This is the recommended approach for large files. Events are
        read in chunks based on good time intervals.

        Args:
            segment_size: Size of each segment in seconds

        Yields:
            numpy arrays of event times for each segment

        Example:
            >>> loader = LazyEventLoader("large.evt")
            >>> for times in loader.stream_segments(segment_size=100):
            ...     # Process 100-second chunks
            ...     lc = histogram(times, bins=1000, range=[times[0], times[-1]])
            ...     analyze(lc)
        """
        logger.info(
            f"Streaming segments from {self.file_path} "
            f"(segment_size={segment_size}s)"
        )

        # Get segment boundaries from GTIs
        start, stop = time_intervals_from_gtis(self.reader.gti, segment_size)
        intervals = [[s, e] for s, e in zip(start, stop)]

        logger.debug(f"Created {len(intervals)} segments")

        # Stream times for each interval
        times_iter = self.reader.filter_at_time_intervals(
            intervals,
            check_gtis=True
        )

        segment_count = 0
        for time_segment in times_iter:
            segment_count += 1
            logger.debug(
                f"Yielding segment {segment_count}/{len(intervals)} "
                f"({len(time_segment)} events)"
            )
            yield time_segment

        logger.info(f"Streamed {segment_count} segments")

    def create_lightcurve_streaming(
        self,
        segment_size: float,
        dt: float
    ) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """
        Create light curve by streaming data in segments.

        This avoids loading the entire EventList into memory.

        Args:
            segment_size: Segment size in seconds
            dt: Light curve bin time

        Yields:
            Tuples of (times, counts) for each light curve segment

        Example:
            >>> loader = LazyEventLoader("large.evt")
            >>> all_times = []
            >>> all_counts = []
            >>> for times, counts in loader.create_lightcurve_streaming(100, 0.1):
            ...     all_times.extend(times)
            ...     all_counts.extend(counts)
        """
        logger.info(
            f"Creating lightcurve via streaming "
            f"(segment_size={segment_size}s, dt={dt}s)"
        )

        start, stop = time_intervals_from_gtis(self.reader.gti, segment_size)
        intervals = [[s, e] for s, e in zip(start, stop)]
        times_iter = self.reader.filter_at_time_intervals(intervals, check_gtis=True)

        for time_segment, (s, e) in zip(times_iter, intervals):
            # Create light curve for this segment
            n_bins = int(np.rint((e - s) / dt))

            # Use Stingray's optimized histogram (returns only counts)
            counts = histogram(
                time_segment,
                bins=n_bins,
                range=[s, e]
            )

            # Calculate bin edges manually (Stingray's approach)
            bin_edges = np.linspace(s, e, n_bins + 1)

            # Bin centers
            times = (bin_edges[:-1] + bin_edges[1:]) / 2

            yield times, counts

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format bytes to human-readable string.

        Args:
            size_bytes: Size in bytes

        Returns:
            Human-readable string (e.g., "1.5 GB", "234.5 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"LazyEventLoader('{self.file_path}', "
            f"size={self.format_file_size(self.file_size)})"
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup if needed."""
        # FITSTimeseriesReader handles its own cleanup
        pass


def assess_loading_risk(
    file_size: int,
    file_format: str = 'fits',
    available_memory: Optional[int] = None
) -> str:
    """
    Assess risk level of loading a file into memory.

    Args:
        file_size: Size of file in bytes
        file_format: File format type
        available_memory: Available RAM in bytes (auto-detected if None)

    Returns:
        Risk level: 'safe', 'caution', 'risky', or 'critical'
    """
    if available_memory is None:
        available_memory = psutil.virtual_memory().available

    # Estimate memory needed
    # Based on Stingray's official performance benchmarks
    multipliers = {
        'fits': 3, 'evt': 3, 'ogip': 3, 'hea': 3,
        'hdf5': 2, 'pickle': 1.5,
    }
    multiplier = multipliers.get(file_format, 3)
    needed_memory = file_size * multiplier

    # Calculate ratio
    ratio = needed_memory / available_memory

    if ratio < 0.3:
        return 'safe'       # <30% of RAM
    elif ratio < 0.6:
        return 'caution'    # 30-60% of RAM
    elif ratio < 0.9:
        return 'risky'      # 60-90% of RAM
    else:
        return 'critical'   # >90% of RAM
