"""
Lightcurve service for lightcurve operations.

Handles creation and manipulation of lightcurves.
"""

from copy import deepcopy
import hashlib
from typing import Any, Dict, List, Optional

import numpy as np
from stingray import Lightcurve
from stingray.gti import create_gti_mask, cross_two_gtis

from .analysis_helpers import event_gtis
from models.event_selection import EventSelection

from .base_service import BaseService
from .scientific_compatibility import (
    compatible_event_lightcurve,
    rebin_lightcurve_with_standard_errors,
)
from .spectrum_products import attach_spectrum_identity, input_snapshot

# Cap on points transferred for plotting. The full-resolution Lightcurve stays
# in StateManager; only the JSON payload is strided.
DEFAULT_MAX_PLOT_POINTS = 200_000


def _decimate_for_plot(time, counts, max_points):
    """Stride-decimate arrays for display. Returns (time, counts, stride).

    max_points: Cap on points in the JSON payload; None or 0 sends full resolution.
    """
    n = len(time)
    if not max_points or max_points < 0 or n <= max_points:
        return time, counts, 1
    stride = int(np.ceil(n / max_points))
    return time[::stride], counts[::stride], stride


def _validated_gtis(value: Any, label: str) -> np.ndarray:
    """Require explicit, finite, ordered observing intervals before binning."""
    try:
        intervals = np.asarray(value, dtype=np.longdouble)
    except (TypeError, ValueError) as exception:
        raise ValueError(
            f"{label} must have shape (N, 2) with numeric bounds"
        ) from exception
    if intervals.size == 0:
        raise ValueError(f"{label} must be a non-empty array of intervals")
    if intervals.ndim != 2 or intervals.shape[1] != 2:
        raise ValueError(f"{label} must have shape (N, 2)")
    if not np.isfinite(intervals).all():
        raise ValueError(f"{label} bounds must be finite")
    if np.any(intervals[:, 1] <= intervals[:, 0]):
        raise ValueError(f"{label} must have start < stop for every interval")
    if np.any(intervals[1:, 0] < intervals[:-1, 0]):
        raise ValueError(f"{label} must be ordered by start time")
    if np.any(intervals[1:, 0] < intervals[:-1, 1]):
        raise ValueError(f"{label} intervals must not overlap")
    return intervals


def _result_identity(
    lightcurve: Any, result_id: str, session_id: str
) -> dict[str, Any]:
    """Read a detached calculation record, preserving legacy handles honestly."""
    recorded = getattr(lightcurve, "result_identity", None)
    if recorded is not None:
        if not isinstance(recorded, dict) or recorded.get("result_id") != result_id:
            raise ValueError("The stored light curve has inconsistent result identity")
        return deepcopy(recorded)
    return {
        "schema": "stingray-explorer.lightcurve-result.v1",
        "result_id": result_id,
        "backend_session_id": session_id,
        "operation": "unrecorded_lightcurve",
        "inputs": [],
        "parameters": {},
        "warnings": [
            "The original creation parameters were not recorded for this light curve."
        ],
        "provenance": {},
    }


def _array_digest(values: np.ndarray) -> str:
    """Fingerprint actual float64 numeric inputs without retaining duplicate arrays."""
    canonical = np.ascontiguousarray(values, dtype="<f8")
    return hashlib.sha256(memoryview(canonical)).hexdigest()


class LightcurveService(BaseService):
    """
    Service for Lightcurve operations.

    Handles creation and manipulation of lightcurves without any UI dependencies.
    """

    def create_lightcurve_from_event_list(
        self,
        event_list_name: str,
        dt: float,
        output_name: str,
        gti: Optional[List[List[float]]] = None,
        max_points: Optional[int] = DEFAULT_MAX_PLOT_POINTS,
        selection: Optional[EventSelection] = None,
    ) -> Dict[str, Any]:
        """
        Create a Lightcurve from an EventList.

        Args:
            event_list_name: Name of the EventList in state
            dt: Time binning in seconds
            output_name: Name to save the lightcurve as
            gti: Optional ordered Good Time Intervals, intersected with the
                EventList's observing intervals. Only fully covered bins on
                the original light-curve grid are retained.
            max_points: Cap on points in the JSON payload; None or 0 sends full resolution.

        Returns:
            Result dictionary with lightcurve data
        """
        try:
            source = self.state.copy_event_data_with_identity(
                event_list_name, selection
            )
            if source is None:
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{event_list_name}' not found",
                    error=None,
                )

            event_list, dataset_id = source

            if not np.isfinite(dt) or dt <= 0:
                raise ValueError("dt must be finite and greater than zero")

            native_gtis = event_gtis(event_list)
            effective_gtis = native_gtis
            requested_gtis = None
            if gti is not None:
                requested_gtis = _validated_gtis(gti, "Requested GTIs")
                effective_gtis = cross_two_gtis(native_gtis, requested_gtis)
                if effective_gtis.size == 0:
                    raise ValueError(
                        "Requested GTIs have no overlap with the EventList GTIs"
                    )

            # Preserve the EventList's bin origin and instrument-compatible dt.
            # to_lc creates a detached Lightcurve, but does not remove gap bins
            # or carry all timing metadata from its input.
            lc = compatible_event_lightcurve(event_list, dt)
            if len(lc.time) == 0:
                raise ValueError(
                    "The GTI selection contains no complete light-curve bins"
                )
            lc.gti = effective_gtis.copy()
            # Stingray's default mask permits a 0.1%-of-dt boundary tolerance.
            # Permit only floating-point roundoff here: e.g. a nominal final
            # edge at 64 s can be slightly above 64 when dt=0.001 is represented
            # in binary. This does not admit observably partial boundary bins.
            rounding_scale = max(
                1.0,
                float(np.max(np.abs(lc.time))),
                float(np.max(np.abs(effective_gtis))),
            )
            rounding_epsilon = 4 * np.finfo(lc.time.dtype).eps * rounding_scale / lc.dt
            good_bins = create_gti_mask(
                lc.time, effective_gtis, dt=lc.dt, epsilon=rounding_epsilon
            )
            if not np.any(good_bins):
                raise ValueError(
                    "The GTI selection contains no complete light-curve bins"
                )
            kept_indices = np.flatnonzero(good_bins)
            # Consecutive original-grid bins form one observed interval. Keep
            # separate runs separate: joining filtered arrays would turn gaps
            # into exposure. Clip only machine-roundoff edge differences back
            # to the selected intervals.
            run_starts = np.r_[0, np.flatnonzero(np.diff(kept_indices) > 1) + 1]
            run_stops = np.r_[run_starts[1:] - 1, len(kept_indices) - 1]
            lc = lc.apply_mask(good_bins, inplace=True)
            kept_times = np.asarray(lc.time, dtype=np.longdouble)
            half_bin = np.longdouble(lc.dt) / 2
            bin_exposure = np.column_stack(
                (kept_times[run_starts] - half_bin, kept_times[run_stops] + half_bin)
            )
            lc.gti = cross_two_gtis(bin_exposure, effective_gtis)
            lc.tstart = lc.gti[0, 0]
            lc.tseg = lc.gti[-1, 1] - lc.gti[0, 0]
            # Record the unrounded selection separately from actual binned
            # exposure. Decimal strings preserve extended-precision bounds and
            # remain safe to serialize as ordinary application metadata.
            lc.gti_selection = {
                "input_event_list": event_list_name,
                "bin_policy": "retain_complete_original_grid_bins",
                "boundary_encoding": "decimal_seconds",
                "requested_gti": (
                    requested_gtis.astype(str).tolist()
                    if requested_gtis is not None
                    else None
                ),
                "intersected_gti": effective_gtis.astype(str).tolist(),
            }
            for attribute in (
                "timesys",
                "timeref",
                "ephem",
                "mission",
                "instr",
                "header",
            ):
                setattr(lc, attribute, deepcopy(getattr(event_list, attribute, None)))

            identity = attach_spectrum_identity(
                lc,
                operation="lightcurve_from_event_list",
                backend_session_id=self.state.session_id,
                inputs=[input_snapshot(event_list_name, event_list, dataset_id)],
                parameters={
                    "requested_dt": float(dt),
                    "dt": float(lc.dt),
                    "output_name": output_name,
                    "gti": requested_gtis.astype(float).tolist()
                    if requested_gtis is not None
                    else None,
                    "gti_selection": deepcopy(lc.gti_selection),
                },
                warnings=[],
                result_kind="lightcurve",
            )

            # Prepare response data
            plot_time, plot_counts, stride = _decimate_for_plot(
                lc.time, lc.counts, max_points
            )
            lc_data = {
                "name": output_name,
                "time": plot_time.astype(float).tolist(),
                "counts": plot_counts.astype(float).tolist(),
                "dt": float(lc.dt),
                "n_bins": len(lc.time),
                "plot_stride": stride,
                "time_range": [float(lc.time.min()), float(lc.time.max())],
                "count_rate_mean": float(np.mean(lc.counts / lc.dt)),
                **deepcopy(identity),
            }

            # Validate the complete result before publishing a stored product.
            # In particular, an empty selection must never leave a broken LC
            # behind when deriving time_range fails.
            if not self.state.add_lightcurve_data_if_absent(output_name, lc):
                raise ValueError(
                    f"Lightcurve '{output_name}' already exists; choose a new output name"
                )

            return self.create_result(
                success=True,
                data=lc_data,
                message=f"Lightcurve '{output_name}' created (dt={lc.dt}s, {len(lc.time)} bins)",
            )

        except Exception as e:
            return self.handle_error(
                e, "Creating lightcurve", event_list=event_list_name, dt=dt
            )

    def create_lightcurve_from_arrays(
        self,
        times: List[float],
        counts: List[float],
        dt: float,
        output_name: str,
    ) -> Dict[str, Any]:
        """
        Create a Lightcurve from time and count arrays.

        Args:
            times: Array of time values
            counts: Array of count values
            dt: Time binning in seconds
            output_name: Name to save the lightcurve as

        Returns:
            Result dictionary with lightcurve data
        """
        try:
            times_arr = np.asarray(times, dtype=float).copy()
            counts_arr = np.asarray(counts, dtype=float).copy()
            if not np.isfinite(dt) or dt <= 0:
                raise ValueError("dt must be finite and greater than zero")
            if (
                times_arr.ndim != 1
                or counts_arr.ndim != 1
                or times_arr.size == 0
                or times_arr.size != counts_arr.size
                or not np.isfinite(times_arr).all()
                or not np.isfinite(counts_arr).all()
            ):
                raise ValueError(
                    "Time and count arrays must be nonempty, finite and aligned"
                )

            lc = Lightcurve(times_arr, counts_arr, dt=dt, skip_checks=True)

            identity = attach_spectrum_identity(
                lc,
                operation="lightcurve_from_arrays",
                backend_session_id=self.state.session_id,
                inputs=[
                    {
                        "name": "input arrays",
                        "kind": "arrays",
                        "n_bins": len(times_arr),
                        "time_range": [
                            float(np.min(times_arr)),
                            float(np.max(times_arr)),
                        ],
                        "time_sha256": _array_digest(times_arr),
                        "counts_sha256": _array_digest(counts_arr),
                        "numeric_encoding": "little-endian float64",
                    }
                ],
                parameters={
                    "requested_dt": float(dt),
                    "dt": float(lc.dt),
                    "output_name": output_name,
                },
                warnings=[],
                result_kind="lightcurve",
                input_kind="arrays",
            )

            lc_data = {
                "name": output_name,
                "time": lc.time.astype(float).tolist(),
                "counts": lc.counts.astype(float).tolist(),
                "dt": float(lc.dt),
                "n_bins": len(lc.time),
                **deepcopy(identity),
            }

            if not self.state.add_lightcurve_data_if_absent(output_name, lc):
                raise ValueError(
                    f"Lightcurve '{output_name}' already exists; choose a new output name"
                )

            return self.create_result(
                success=True,
                data=lc_data,
                message=f"Lightcurve '{output_name}' created from arrays",
            )

        except Exception as e:
            return self.handle_error(e, "Creating lightcurve from arrays", dt=dt)

    def rebin_lightcurve(
        self,
        name: str,
        rebin_factor: float,
        output_name: str,
        max_points: Optional[int] = DEFAULT_MAX_PLOT_POINTS,
        expected_result_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Rebin a lightcurve.

        Args:
            name: Name of the lightcurve to rebin
            rebin_factor: Rebinning factor
            output_name: Name for the rebinned lightcurve
            max_points: Cap on points in the JSON payload; None or 0 sends full resolution.

        Returns:
            Result dictionary with rebinned lightcurve data
        """
        try:
            source = self.state.copy_lightcurve_data_with_identity(
                name, expected_result_id=expected_result_id
            )
            if source is None:
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Lightcurve '{name}' not found",
                    error=None,
                )

            lightcurve, parent_id = source
            if not np.isfinite(rebin_factor) or rebin_factor <= 0:
                raise ValueError("rebin_factor must be finite and greater than zero")
            parent_identity = _result_identity(
                lightcurve, parent_id, self.state.session_id
            )
            # stingray's first positional param is dt_new (absolute); we promise
            # factor semantics, so pass f= explicitly.
            rebinned_lc, uncertainty_workaround = rebin_lightcurve_with_standard_errors(
                lightcurve, rebin_factor
            )
            # Stingray constructs a fresh object but does not carry these
            # scientific metadata fields across, and its GTIs retain fractional
            # tail exposure even when rebinning discarded the last partial bin.
            for attribute in (
                "timesys",
                "timeref",
                "ephem",
                "mission",
                "instr",
                "header",
                "gti_selection",
            ):
                if hasattr(lightcurve, attribute):
                    setattr(
                        rebinned_lc, attribute, deepcopy(getattr(lightcurve, attribute))
                    )
            rebinned_times = np.asarray(rebinned_lc.time, dtype=np.longdouble)
            half_bin = np.longdouble(rebinned_lc.dt) / 2
            retained_exposure = []
            for start, stop in rebinned_lc.gti:
                inside = rebinned_times[
                    (rebinned_times >= start) & (rebinned_times < stop)
                ]
                if inside.size:
                    retained_exposure.append(
                        [
                            max(start, inside[0] - half_bin),
                            min(stop, inside[-1] + half_bin),
                        ]
                    )
            rebinned_lc.gti = np.asarray(retained_exposure, dtype=np.longdouble)
            rebinned_lc.tstart = rebinned_lc.gti[0, 0]
            rebinned_lc.tseg = rebinned_lc.gti[-1, 1] - rebinned_lc.gti[0, 0]

            identity = attach_spectrum_identity(
                rebinned_lc,
                operation="lightcurve_rebin",
                backend_session_id=self.state.session_id,
                inputs=deepcopy(parent_identity["inputs"]),
                parameters={
                    "name": name,
                    "rebin_factor": float(rebin_factor),
                    "legacy_uncertainty_workaround": uncertainty_workaround,
                    "dt": float(rebinned_lc.dt),
                    "output_name": output_name,
                },
                warnings=deepcopy(parent_identity.get("warnings", [])),
                parent=(parent_identity, name),
                result_kind="lightcurve",
                input_kind="lightcurve",
            )

            plot_time, plot_counts, stride = _decimate_for_plot(
                rebinned_lc.time, rebinned_lc.counts, max_points
            )
            lc_data = {
                "name": output_name,
                "time": plot_time.astype(float).tolist(),
                "counts": plot_counts.astype(float).tolist(),
                "dt": float(rebinned_lc.dt),
                "n_bins": len(rebinned_lc.time),
                "plot_stride": stride,
                "count_rate_mean": float(np.mean(rebinned_lc.counts / rebinned_lc.dt)),
                **deepcopy(identity),
            }

            if not self.state.add_lightcurve_data_if_absent(output_name, rebinned_lc):
                raise ValueError(
                    f"Lightcurve '{output_name}' already exists; choose a new output name"
                )

            return self.create_result(
                success=True,
                data=lc_data,
                message=f"Lightcurve rebinned (factor={rebin_factor})",
            )

        except Exception as e:
            return self.handle_error(
                e, "Rebinning lightcurve", name=name, rebin_factor=rebin_factor
            )

    def get_lightcurve_data(
        self, name: str, max_points: Optional[int] = DEFAULT_MAX_PLOT_POINTS
    ) -> Dict[str, Any]:
        """
        Get lightcurve data for plotting.

        Args:
            name: Name of the lightcurve
            max_points: Cap on points in the JSON payload; None or 0 sends full resolution.

        Returns:
            Result dictionary with lightcurve data
        """
        try:
            source = self.state.copy_lightcurve_data_with_identity(name)
            if source is None:
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Lightcurve '{name}' not found",
                    error=None,
                )

            lc, result_id = source
            identity = _result_identity(lc, result_id, self.state.session_id)

            plot_time, plot_counts, stride = _decimate_for_plot(
                lc.time, lc.counts, max_points
            )
            lc_data = {
                "name": name,
                "time": plot_time.astype(float).tolist(),
                "counts": plot_counts.astype(float).tolist(),
                "dt": float(lc.dt),
                "n_bins": len(lc.time),
                "plot_stride": stride,
                "time_range": [float(lc.time.min()), float(lc.time.max())],
                "count_rate_mean": float(np.mean(lc.counts / lc.dt)),
                "count_stats": {
                    "mean": float(np.mean(lc.counts)),
                    "std": float(np.std(lc.counts)),
                    "min": float(np.min(lc.counts)),
                    "max": float(np.max(lc.counts)),
                },
                **deepcopy(identity),
            }

            return self.create_result(
                success=True,
                data=lc_data,
                message=f"Lightcurve '{name}' data retrieved",
            )

        except Exception as e:
            return self.handle_error(e, "Getting lightcurve data", name=name)

    def list_lightcurves(self) -> Dict[str, Any]:
        """List all loaded lightcurves."""
        try:
            summaries = []
            for name in self.state.list_lightcurve_names():
                source = self.state.copy_lightcurve_data_with_identity(name)
                if source is None:
                    continue
                lc, result_id = source
                summaries.append(
                    {
                        "name": name,
                        "n_bins": len(lc.time),
                        "dt": float(lc.dt),
                        "time_range": [float(lc.time.min()), float(lc.time.max())],
                        **_result_identity(lc, result_id, self.state.session_id),
                    }
                )

            return self.create_result(
                success=True,
                data=summaries,
                message=f"Found {len(summaries)} lightcurve(s)",
            )

        except Exception as e:
            return self.handle_error(e, "Listing lightcurves")

    def delete_lightcurve(self, name: str) -> Dict[str, Any]:
        """Delete a lightcurve from state."""
        try:
            if not self.state.has_lightcurve_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Lightcurve '{name}' not found",
                    error=None,
                )

            self.state.remove_lightcurve_data(name)

            return self.create_result(
                success=True,
                data={"name": name},
                message=f"Lightcurve '{name}' deleted",
            )

        except Exception as e:
            return self.handle_error(e, "Deleting lightcurve", name=name)
