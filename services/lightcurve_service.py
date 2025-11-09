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
