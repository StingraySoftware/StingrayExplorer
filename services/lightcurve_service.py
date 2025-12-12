"""
Lightcurve service for lightcurve operations.

This service handles all Lightcurve-related business logic including:
- Creating lightcurves from event lists
- Creating lightcurves from arrays
- Combining multiple event lists into lightcurves
- Applying GTI filtering
- Rebinning lightcurves
"""

from typing import Dict, Any, Optional, List
import numpy as np
from stingray import Lightcurve, EventList
from .base_service import BaseService
from utils.performance_monitor import performance_monitor


class LightcurveService(BaseService):
    """
    Service for Lightcurve operations.

    Handles creation and manipulation of lightcurves without any UI dependencies.
    All operations return standardized result dictionaries.
    """

    def create_lightcurve_from_event_list(
        self,
        event_list: EventList,
        dt: float,
        gti: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Create a Lightcurve from an EventList.

        Args:
            event_list: The EventList to convert
            dt: Time binning in seconds
            gti: Optional Good Time Intervals [[start1, end1], [start2, end2], ...]

        Returns:
            Result dictionary with the Lightcurve as data

        Example:
            >>> result = lightcurve_service.create_lightcurve_from_event_list(
            ...     event_list=event_list,
            ...     dt=1.0,
            ...     gti=[[0, 100], [200, 300]]
            ... )
            >>> if result["success"]:
            ...     lightcurve = result["data"]
        """
        with performance_monitor.track_operation("create_lightcurve_from_event_list", dt=dt):
            try:
                # Create lightcurve from event list
                lc = event_list.to_lc(dt=dt)

                # Apply GTIs if provided
                if gti is not None:
                    gti_array = np.array(gti)
                    lc = lc.apply_gtis(gti_array)

                return self.create_result(
                    success=True,
                    data=lc,
                    message=f"Lightcurve created successfully (dt={dt}s)"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Creating lightcurve from event list",
                    dt=dt,
                    gti=gti
                )

    def create_lightcurve_from_arrays(
        self,
        times: np.ndarray,
        counts: np.ndarray,
        dt: float
    ) -> Dict[str, Any]:
        """
        Create a Lightcurve from time and count arrays.

        Args:
            times: Array of time values
            counts: Array of count values
            dt: Time binning in seconds

        Returns:
            Result dictionary with the Lightcurve as data

        Example:
            >>> times = np.arange(0, 100, 1.0)
            >>> counts = np.random.poisson(10, 100)
            >>> result = lightcurve_service.create_lightcurve_from_arrays(
            ...     times=times,
            ...     counts=counts,
            ...     dt=1.0
            ... )
        """
        with performance_monitor.track_operation("create_lightcurve_from_arrays", dt=dt):
            try:
                lc = Lightcurve(times, counts, dt=dt, skip_checks=True)

                return self.create_result(
                    success=True,
                    data=lc,
                    message=f"Lightcurve created successfully from arrays (dt={dt}s)"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Creating lightcurve from arrays",
                    dt=dt,
                    array_length=len(times)
                )

    def combine_event_lists_to_lightcurve(
        self,
        event_list_names: List[str],
        dt: float,
        gti: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Combine multiple event lists into a single lightcurve.

        Args:
            event_list_names: List of event list names from state
            dt: Time binning in seconds
            gti: Optional Good Time Intervals

        Returns:
            Result dictionary with the combined Lightcurve as data

        Example:
            >>> result = lightcurve_service.combine_event_lists_to_lightcurve(
            ...     event_list_names=["obs1", "obs2", "obs3"],
            ...     dt=1.0
            ... )
        """
        try:
            # Validate all event lists exist
            for name in event_list_names:
                if not self.state.has_event_data(name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"Event list '{name}' not found in state",
                        error=None
                    )

            # Get all event lists
            event_lists = [self.state.get_event_data(name) for name in event_list_names]

            # Combine event lists (merge all events)
            all_times = np.concatenate([el.time for el in event_lists])
            all_times.sort()

            # Create a combined event list
            # Note: This is simplified - in production you'd want to merge GTIs properly
            combined_event_list = EventList(
                time=all_times,
                gti=event_lists[0].gti  # Use first event list's GTI as base
            )

            # Create lightcurve
            lc = combined_event_list.to_lc(dt=dt)

            # Apply GTIs if provided
            if gti is not None:
                gti_array = np.array(gti)
                lc = lc.apply_gtis(gti_array)

            return self.create_result(
                success=True,
                data=lc,
                message=f"Combined {len(event_list_names)} event lists into lightcurve (dt={dt}s)"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Combining event lists to lightcurve",
                event_list_names=event_list_names,
                dt=dt
            )

    def apply_gtis(
        self,
        lightcurve: Lightcurve,
        gti: List[List[float]]
    ) -> Dict[str, Any]:
        """
        Apply Good Time Intervals to a lightcurve.

        Args:
            lightcurve: The Lightcurve to filter
            gti: Good Time Intervals [[start1, end1], [start2, end2], ...]

        Returns:
            Result dictionary with the filtered Lightcurve as data

        Example:
            >>> result = lightcurve_service.apply_gtis(
            ...     lightcurve=lc,
            ...     gti=[[0, 100], [200, 300]]
            ... )
        """
        try:
            gti_array = np.array(gti)
            filtered_lc = lightcurve.apply_gtis(gti_array)

            return self.create_result(
                success=True,
                data=filtered_lc,
                message=f"GTIs applied successfully ({len(gti)} intervals)"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Applying GTIs to lightcurve",
                gti=gti
            )

    def rebin_lightcurve(
        self,
        lightcurve: Lightcurve,
        rebin_factor: float
    ) -> Dict[str, Any]:
        """
        Rebin a lightcurve.

        Args:
            lightcurve: The Lightcurve to rebin
            rebin_factor: Rebinning factor (new_dt = old_dt * rebin_factor)

        Returns:
            Result dictionary with the rebinned Lightcurve as data

        Example:
            >>> result = lightcurve_service.rebin_lightcurve(
            ...     lightcurve=lc,
            ...     rebin_factor=2.0
            ... )
        """
        with performance_monitor.track_operation("rebin_lightcurve", rebin_factor=rebin_factor):
            try:
                rebinned_lc = lightcurve.rebin(rebin_factor)

                return self.create_result(
                    success=True,
                    data=rebinned_lc,
                    message=f"Lightcurve rebinned successfully (factor={rebin_factor})"
                )

            except Exception as e:
                return self.handle_error(
                    e,
                    "Rebinning lightcurve",
                    rebin_factor=rebin_factor
                )

    def create_event_list_from_lightcurve(
        self,
        lightcurve: Lightcurve
    ) -> Dict[str, Any]:
        """
        Create an EventList from a Lightcurve.

        This is useful for simulating event lists from synthetic lightcurves
        or converting binned data back to event format.

        Args:
            lightcurve: The Lightcurve to convert to EventList

        Returns:
            Result dictionary with the EventList as data

        Example:
            >>> result = lightcurve_service.create_event_list_from_lightcurve(
            ...     lightcurve=lc
            ... )
            >>> if result["success"]:
            ...     event_list = result["data"]
        """
        try:
            event_list = EventList.from_lc(lightcurve)

            return self.create_result(
                success=True,
                data=event_list,
                message="EventList created successfully from lightcurve"
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Creating EventList from lightcurve",
                lightcurve_dt=lightcurve.dt if hasattr(lightcurve, 'dt') else None
            )

    def simulate_event_list_from_lightcurve(
        self,
        lightcurve: Lightcurve,
        method: str = 'probabilistic',
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Simulate EventList from Lightcurve using specified method.

        This method provides two approaches:
        1. Probabilistic (recommended): Uses inverse CDF sampling for
           statistically realistic event generation
        2. Deterministic (legacy): Uses from_lc() for exact count matching

        Args:
            lightcurve: Lightcurve object to simulate events from
            method: Simulation method - 'probabilistic' (recommended) or 'deterministic'
            seed: Random seed for reproducible probabilistic simulations

        Returns:
            Result dictionary with EventList and simulation metadata

        Example:
            >>> result = lightcurve_service.simulate_event_list_from_lightcurve(
            ...     lightcurve=lc,
            ...     method='probabilistic',
            ...     seed=42
            ... )
            >>> if result["success"]:
            ...     event_list = result["data"]
        """
        try:
            if method not in ['probabilistic', 'deterministic']:
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Invalid method: {method}. Use 'probabilistic' or 'deterministic'.",
                    error=f"Method must be 'probabilistic' or 'deterministic', got '{method}'"
                )

            if method == 'probabilistic':
                # Recommended method using inverse CDF sampling
                if seed is not None:
                    np.random.seed(seed)

                event_list = EventList()
                event_list.simulate_times(lightcurve)

                return self.create_result(
                    success=True,
                    data=event_list,
                    message=f"EventList simulated successfully using probabilistic method (seed={seed if seed is not None else 'random'})",
                    metadata={
                        'method': 'probabilistic',
                        'seed': seed,
                        'n_events': len(event_list.time),
                        'time_range': (float(event_list.time[0]), float(event_list.time[-1]))
                    }
                )

            else:  # deterministic
                # Legacy method for backwards compatibility
                event_list = EventList.from_lc(lightcurve)

                return self.create_result(
                    success=True,
                    data=event_list,
                    message="EventList created using deterministic method (from_lc)",
                    metadata={
                        'method': 'deterministic',
                        'n_events': len(event_list.time)
                    }
                )

        except Exception as e:
            return self.handle_error(
                e,
                "Simulating EventList from lightcurve",
                method=method,
                seed=seed,
                lightcurve_dt=lightcurve.dt if hasattr(lightcurve, 'dt') else None
            )

    def simulate_energies_for_event_list(
        self,
        event_list: EventList,
        spectrum: List[List[float]]
    ) -> Dict[str, Any]:
        """
        Simulate photon energies for an EventList based on a spectral distribution.

        Uses inverse CDF method to assign realistic energy values to events
        based on the provided spectrum. The spectrum is a two-dimensional array
        where the first dimension is energy bins (keV) and the second is counts
        in each bin (normalized before simulation).

        Args:
            event_list: EventList object to add energies to
            spectrum: 2D list [[energies], [counts]]
                     Example: [[1, 2, 3, 4, 5, 6], [1000, 2040, 1000, 3000, 4020, 2070]]

        Returns:
            Result dictionary with updated EventList and simulation metadata

        Example:
            >>> spectrum = [[1, 2, 3, 4, 5, 6], [1000, 2040, 1000, 3000, 4020, 2070]]
            >>> result = lightcurve_service.simulate_energies_for_event_list(
            ...     event_list=ev,
            ...     spectrum=spectrum
            ... )
            >>> if result["success"]:
            ...     ev_with_energies = result["data"]
        """
        try:
            # Validate spectrum format
            if not isinstance(spectrum, list) or len(spectrum) != 2:
                return self.create_result(
                    success=False,
                    data=None,
                    message="Spectrum must be a 2D list with [energies, counts]",
                    error=f"Invalid spectrum format: expected [[energies], [counts]], got {type(spectrum)}"
                )

            energies, counts = spectrum[0], spectrum[1]

            if len(energies) != len(counts):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Energy bins ({len(energies)}) and counts ({len(counts)}) must have same length",
                    error=f"Mismatch: {len(energies)} energies vs {len(counts)} counts"
                )

            if len(energies) < 2:
                return self.create_result(
                    success=False,
                    data=None,
                    message="Spectrum must have at least 2 energy bins",
                    error=f"Only {len(energies)} energy bins provided"
                )

            # Convert to numpy arrays
            energy_array = np.array(energies, dtype=float)
            count_array = np.array(counts, dtype=float)

            # Validate energy bins are sorted
            if not np.all(energy_array[:-1] <= energy_array[1:]):
                return self.create_result(
                    success=False,
                    data=None,
                    message="Energy bins must be in ascending order",
                    error=f"Energy bins not sorted: {energies}"
                )

            # Simulate energies using Stingray's method
            event_list.simulate_energies([energy_array.tolist(), count_array.tolist()])

            return self.create_result(
                success=True,
                data=event_list,
                message=f"Energies simulated successfully for {len(event_list.time)} events",
                metadata={
                    'n_energy_bins': len(energies),
                    'energy_range': (float(energies[0]), float(energies[-1])),
                    'mean_energy': float(np.mean(event_list.energy)) if hasattr(event_list, 'energy') and event_list.energy is not None else None,
                    'n_events': len(event_list.time)
                }
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Simulating energies for EventList",
                n_energy_bins=len(spectrum[0]) if spectrum and len(spectrum) > 0 else 0,
                n_events=len(event_list.time) if hasattr(event_list, 'time') else 0
            )
