"""
Timing service for timing analysis operations.

This service handles timing-related business logic including:
- Bispectrum creation and analysis
- Power colors calculation
- Higher-order timing analysis
"""

from typing import Dict, Any
from stingray import EventList, Bispectrum
from .base_service import BaseService
from utils.performance_monitor import performance_monitor


class TimingService(BaseService):
    """
    Service for timing analysis operations.

    Handles bispectrum and higher-order timing analysis without any UI dependencies.
    All operations return standardized result dictionaries.
    """

    def create_bispectrum(
        self,
        event_list: EventList,
        dt: float,
        maxlag: int = 25,
        scale: str = "unbiased",
        window: str = "uniform"
    ) -> Dict[str, Any]:
        """
        Create a bispectrum from an EventList.

        The bispectrum is used to detect non-linear interactions and non-Gaussian
        features in the data.

        Args:
            event_list: The EventList to analyze
            dt: Time binning in seconds
            maxlag: Maximum lag for bispectrum calculation
            scale: Scaling type ("biased" or "unbiased")
            window: Window function type ("uniform", "parzen", "hamming", etc.)

        Returns:
            Result dictionary with the Bispectrum as data

        Example:
            >>> result = timing_service.create_bispectrum(
            ...     event_list=event_list,
            ...     dt=1.0,
            ...     maxlag=25,
            ...     scale="unbiased",
            ...     window="uniform"
            ... )
        """
        with performance_monitor.track_operation("create_bispectrum", dt=dt, maxlag=maxlag, scale=scale):
            try:
                lc = event_list.to_lc(dt=dt)
                bs = Bispectrum(lc, maxlag=maxlag, scale=scale, window=window)

                return self.create_result(
                    success=True,
                    data=bs,
                    message=f"Bispectrum created successfully (maxlag={maxlag}, scale={scale}, window={window})"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Creating bispectrum",
                    dt=dt,
                    maxlag=maxlag,
                    scale=scale,
                    window=window
                )

    def calculate_power_colors(
        self,
        event_list: EventList,
        dt: float,
        segment_size: float,
        freq_ranges: Dict[str, tuple]
    ) -> Dict[str, Any]:
        """
        Calculate power colors from frequency bands.

        Power colors are ratios of integrated power in different frequency bands,
        useful for source classification and state analysis.

        Args:
            event_list: The EventList to analyze
            dt: Time binning in seconds
            segment_size: Segment size in seconds
            freq_ranges: Dictionary of frequency ranges, e.g.,
                        {"low": (0.1, 1), "mid": (1, 10), "high": (10, 100)}

        Returns:
            Result dictionary with power colors as data

        Example:
            >>> result = timing_service.calculate_power_colors(
            ...     event_list=event_list,
            ...     dt=0.1,
            ...     segment_size=100,
            ...     freq_ranges={"low": (0.1, 1), "high": (10, 100)}
            ... )
        """
        with performance_monitor.track_operation("calculate_power_colors", dt=dt, segment_size=segment_size):
            try:
                # This is a simplified implementation
                # In production, you'd want more sophisticated power color calculation
                from stingray import DynamicalPowerspectrum

                lc = event_list.to_lc(dt=dt)
                dps = DynamicalPowerspectrum(lc, segment_size=segment_size, norm="leahy")

                # Calculate integrated power in each frequency band
                power_colors = {}
                for band_name, (f_min, f_max) in freq_ranges.items():
                    mask = (dps.freq >= f_min) & (dps.freq < f_max)
                    integrated_power = dps.dyn_ps[:, mask].mean(axis=1)
                    power_colors[band_name] = integrated_power

                return self.create_result(
                    success=True,
                    data=power_colors,
                    message=f"Power colors calculated for {len(freq_ranges)} frequency bands"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Calculating power colors",
                    dt=dt,
                    segment_size=segment_size,
                    freq_ranges=freq_ranges
                )
