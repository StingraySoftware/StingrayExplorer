"""
Timing service for timing analysis operations.

Handles bispectrum, power colors, and other timing analysis.
"""

from typing import Any, Dict, Optional

import numpy as np
from stingray import Bispectrum, DynamicalPowerspectrum

from .base_service import BaseService


class TimingService(BaseService):
    """
    Service for timing analysis operations.

    Handles bispectrum, power colors, and higher-order timing analysis.
    """

    def create_bispectrum(
        self,
        event_list_name: str,
        dt: float,
        maxlag: int = 25,
        scale: str = "unbiased",
        window: str = "uniform",
        output_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a bispectrum from an EventList.

        The bispectrum is used to detect non-linear interactions and
        non-Gaussian features in the data.

        Args:
            event_list_name: Name of the EventList in state
            dt: Time binning in seconds
            maxlag: Maximum lag for bispectrum calculation
            scale: Scaling type ("biased" or "unbiased")
            window: Window function type
            output_name: Optional name to save the result

        Returns:
            Result dictionary with bispectrum data
        """
        try:
            if not self.state.has_event_data(event_list_name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{event_list_name}' not found",
                    error=None,
                )

            event_list = self.state.get_event_data(event_list_name)
            lc = event_list.to_lc(dt=dt)
            bs = Bispectrum(lc, maxlag=maxlag, scale=scale, window=window)

            if output_name:
                self.state.add_analysis_result(output_name, bs)

            bs_data = {
                "name": output_name,
                "freq": bs.freq.tolist(),
                "lags": bs.lags.tolist(),
                "bispec_mag": bs.bispec_mag.tolist(),
                "bispec_phase": bs.bispec_phase.tolist(),
                "cum3": bs.cum3.tolist(),
                "maxlag": maxlag,
                "scale": scale,
                "window": window,
            }

            return self.create_result(
                success=True,
                data=bs_data,
                message=f"Bispectrum created (maxlag={maxlag})",
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Creating bispectrum",
                event_list=event_list_name,
                dt=dt,
                maxlag=maxlag,
            )

    def calculate_power_colors(
        self,
        event_list_name: str,
        dt: float,
        segment_size: float,
        freq_ranges: Dict[str, tuple],
        output_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate power colors from frequency bands.

        Power colors are ratios of integrated power in different frequency bands,
        useful for source classification and state analysis.

        Args:
            event_list_name: Name of the EventList in state
            dt: Time binning in seconds
            segment_size: Segment size in seconds
            freq_ranges: Dictionary of frequency ranges
            output_name: Optional name to save the result

        Returns:
            Result dictionary with power colors
        """
        try:
            if not self.state.has_event_data(event_list_name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{event_list_name}' not found",
                    error=None,
                )

            event_list = self.state.get_event_data(event_list_name)
            lc = event_list.to_lc(dt=dt)
            dps = DynamicalPowerspectrum(lc, segment_size=segment_size, norm="leahy")

            # Calculate integrated power in each frequency band
            power_colors = {}
            for band_name, (f_min, f_max) in freq_ranges.items():
                mask = (dps.freq >= f_min) & (dps.freq < f_max)
                integrated_power = dps.dyn_ps[:, mask].mean(axis=1)
                power_colors[band_name] = integrated_power.tolist()

            result_data = {
                "name": output_name,
                "power_colors": power_colors,
                "time": dps.time.tolist(),
                "freq_ranges": freq_ranges,
            }

            if output_name:
                self.state.add_analysis_result(output_name, result_data)

            return self.create_result(
                success=True,
                data=result_data,
                message=f"Power colors calculated for {len(freq_ranges)} bands",
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Calculating power colors",
                event_list=event_list_name,
                dt=dt,
                segment_size=segment_size,
            )

    def calculate_time_lags(
        self,
        event_list_1_name: str,
        event_list_2_name: str,
        dt: float,
        segment_size: float,
        freq_range: Optional[tuple] = None,
        output_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate time lags between two event lists.

        Args:
            event_list_1_name: Name of first EventList
            event_list_2_name: Name of second EventList
            dt: Time binning in seconds
            segment_size: Segment size in seconds
            freq_range: Optional frequency range to calculate lags for
            output_name: Optional name to save the result

        Returns:
            Result dictionary with time lags
        """
        try:
            if not self.state.has_event_data(event_list_1_name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{event_list_1_name}' not found",
                    error=None,
                )

            if not self.state.has_event_data(event_list_2_name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{event_list_2_name}' not found",
                    error=None,
                )

            from stingray import AveragedCrossspectrum

            event_list_1 = self.state.get_event_data(event_list_1_name)
            event_list_2 = self.state.get_event_data(event_list_2_name)

            lc1 = event_list_1.to_lc(dt=dt)
            lc2 = event_list_2.to_lc(dt=dt)

            cs = AveragedCrossspectrum.from_lightcurve(
                lc1=lc1,
                lc2=lc2,
                segment_size=segment_size,
                norm="leahy",
            )

            # Calculate time lags
            freq = cs.freq
            time_lags = np.angle(cs.unnorm_power) / (2 * np.pi * freq)

            # Filter by frequency range if provided
            if freq_range:
                mask = (freq >= freq_range[0]) & (freq <= freq_range[1])
                freq = freq[mask]
                time_lags = time_lags[mask]

            result_data = {
                "name": output_name,
                "freq": freq.tolist(),
                "time_lags": time_lags.tolist(),
                "freq_range": freq_range,
            }

            if output_name:
                self.state.add_analysis_result(output_name, result_data)

            return self.create_result(
                success=True,
                data=result_data,
                message="Time lags calculated",
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Calculating time lags",
                event_list_1=event_list_1_name,
                event_list_2=event_list_2_name,
                dt=dt,
                segment_size=segment_size,
            )

    def calculate_coherence(
        self,
        event_list_1_name: str,
        event_list_2_name: str,
        dt: float,
        segment_size: float,
        output_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate coherence between two event lists.

        Args:
            event_list_1_name: Name of first EventList
            event_list_2_name: Name of second EventList
            dt: Time binning in seconds
            segment_size: Segment size in seconds
            output_name: Optional name to save the result

        Returns:
            Result dictionary with coherence data
        """
        try:
            if not self.state.has_event_data(event_list_1_name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{event_list_1_name}' not found",
                    error=None,
                )

            if not self.state.has_event_data(event_list_2_name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{event_list_2_name}' not found",
                    error=None,
                )

            from stingray import AveragedCrossspectrum

            event_list_1 = self.state.get_event_data(event_list_1_name)
            event_list_2 = self.state.get_event_data(event_list_2_name)

            lc1 = event_list_1.to_lc(dt=dt)
            lc2 = event_list_2.to_lc(dt=dt)

            cs = AveragedCrossspectrum.from_lightcurve(
                lc1=lc1,
                lc2=lc2,
                segment_size=segment_size,
                norm="leahy",
            )

            # Calculate coherence
            coherence = np.abs(cs.unnorm_power) ** 2

            result_data = {
                "name": output_name,
                "freq": cs.freq.tolist(),
                "coherence": coherence.tolist(),
            }

            if output_name:
                self.state.add_analysis_result(output_name, result_data)

            return self.create_result(
                success=True,
                data=result_data,
                message="Coherence calculated",
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Calculating coherence",
                event_list_1=event_list_1_name,
                event_list_2=event_list_2_name,
                dt=dt,
                segment_size=segment_size,
            )
