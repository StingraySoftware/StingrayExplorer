"""
Spectrum service for spectral analysis operations.

Handles power spectrum, cross spectrum, and dynamical power spectrum operations.
"""

from typing import Any, Dict, Optional
from copy import deepcopy

import numpy as np
from stingray import (
    AveragedCrossspectrum,
    AveragedPowerspectrum,
    Crossspectrum,
    DynamicalPowerspectrum,
    Powerspectrum,
)

from models.event_selection import EventSelection

from .base_service import BaseService
from .event_selection import EventSelectionError, band_overlap_warning
from .scientific_compatibility import compatible_event_lightcurve
from .analysis_helpers import (
    analysis_event_copy,
    collect_warnings,
    common_gtis,
    overlap_error as _overlap_error,
    pair_binning_error,
    segment_size_error as _segment_size_error,
)
from .spectrum_products import (
    _decimal,
    _public_lineage,
    attach_spectrum_identity,
    input_snapshot,
    spectrum_identity,
    spectrum_projection,
)
from .utility_helpers import validate_derived_name


def _power_to_lists(power) -> tuple:
    """Split a (possibly complex) power array into JSON-safe magnitude and phase lists.

    Returns (power_list, phase_list_or_None). Non-finite values become None so
    strict JSON (and JS JSON.parse) never sees NaN/Infinity.
    """
    arr = np.asarray(power)
    if np.iscomplexobj(arr):
        mag = np.abs(arr)
        phase = np.angle(arr)
        return _finite_list(mag), _finite_list(phase)
    return _finite_list(arr), None


def _finite_list(arr) -> list:
    """Convert a float array to a list, replacing non-finite values with None."""
    values = np.asarray(arr, dtype=float)
    if np.isfinite(values).all():
        return values.tolist()
    return [float(v) if np.isfinite(v) else None for v in values]


class SpectrumService(BaseService):
    """
    Service for spectral analysis operations.

    Handles power spectrum, cross spectrum, and dynamical power spectrum.
    """

    def _source(self, name, selection=None):
        captured = self.state.copy_event_data_with_identity(name, selection)
        if captured is None:
            raise ValueError(f"EventList '{name}' not found")
        event_list, dataset_id = captured
        snapshot = input_snapshot(name, event_list, dataset_id)
        return event_list, snapshot

    def _lightcurve_source(self, name, dt, selection):
        """A stored light curve as a spectral source, with its own lineage."""
        if selection is not None and not selection.is_empty():
            raise EventSelectionError(
                "Photon selections apply to event lists; a light curve has no "
                "photons to select. Remove the selection or choose an event list."
            )
        captured = self.state.copy_lightcurve_data_with_identity(name)
        if captured is None:
            raise ValueError(f"Light curve '{name}' not found")
        lightcurve, result_id = captured
        if dt is not None and not np.isclose(dt, lightcurve.dt, rtol=1e-9, atol=0):
            raise ValueError(
                f"Light curve '{name}' has {lightcurve.dt} s bins; leave dt empty "
                "to use them, or rebin the light curve first"
            )
        identity = getattr(lightcurve, "result_identity", None) or {}
        times = np.asarray(lightcurve.time)
        source = {
            "name": name,
            "kind": "lightcurve",
            "result_id": result_id,
            "dt": float(lightcurve.dt),
            "n_bins": int(times.size),
            "time_range": [_decimal(np.min(times)), _decimal(np.max(times))],
            "mjdref": _decimal(getattr(lightcurve, "mjdref", None)),
            "lineage": _public_lineage(
                {key: identity.get(key) for key in ("operation", "inputs", "parameters")}
            ),
        }
        return lightcurve, source

    def _complete(
        self, spectrum, name, operation, inputs, parameters, warnings, *, parent=None
    ):
        """Freeze inputs/settings, validate the projection, then publish atomically."""
        if name is not None:
            problem = validate_derived_name(name)
            if problem:
                raise ValueError(problem)
        parameters = deepcopy(parameters)
        if "dt" in parameters:
            parameters["requested_dt"] = parameters["dt"]
        actual_dt = (
            getattr(spectrum, "sample_time", None)
            if hasattr(spectrum, "dyn_ps")
            else getattr(spectrum, "dt", None)
        )
        if actual_dt is not None:
            parameters["dt"] = float(actual_dt)
        if "segment_size" in parameters:
            parameters["requested_segment_size"] = parameters["segment_size"]
        actual_segment = getattr(spectrum, "segment_size", None)
        if actual_segment is not None:
            parameters["segment_size"] = float(actual_segment)
        parameters["norm"] = getattr(spectrum, "norm", parameters.get("norm"))
        averaging = getattr(spectrum, "m", None)
        if (
            operation.startswith("averaged_")
            and averaging is not None
            and np.ndim(averaging) == 0
        ):
            parameters["n_segments"] = int(averaging)
        elif parent is not None:
            original = parent[0]["provenance"].get("original_parameters", {})
            if "n_segments" in original:
                parameters["n_segments"] = original["n_segments"]
        if getattr(spectrum, "gti", None) is not None:
            parameters["analysis_gti"] = (
                np.asarray(spectrum.gti, dtype=np.longdouble).astype(str).tolist()
            )
        identity = attach_spectrum_identity(
            spectrum,
            operation=operation,
            backend_session_id=self.state.session_id,
            inputs=inputs,
            parameters=parameters,
            warnings=warnings,
            parent=parent,
        )
        if getattr(spectrum, "dyn_ps", None) is not None:
            data = {
                "freq": np.asarray(spectrum.freq, dtype=float).tolist(),
                "time": np.asarray(spectrum.time, dtype=float).tolist(),
                "dyn_ps": [_finite_list(row) for row in spectrum.dyn_ps],
                "shape": list(spectrum.dyn_ps.shape),
                "metadata": {"units": {"freq": "Hz", "time": "s"}},
                **identity,
            }
        else:
            data = spectrum_projection(spectrum)
        data["name"] = name
        data["norm"] = getattr(spectrum, "norm", None)
        for field in ("dt", "segment_size", "requested_segment_size"):
            if field in parameters:
                data[field] = parameters[field]
        if "n_segments" in parameters:
            data["n_segments"] = parameters["n_segments"]
        if averaging is not None:
            data["n_averaged"] = np.asarray(averaging).tolist()
        if name is not None and not self.state.add_spectrum_data_if_absent(
            name, spectrum
        ):
            raise ValueError(
                f"Spectrum '{name}' already exists; choose a unique output name"
            )
        return data

    def create_power_spectrum(
        self,
        event_list_name: Optional[str] = None,
        dt: Optional[float] = None,
        norm: str = "leahy",
        output_name: Optional[str] = None,
        selection: Optional[EventSelection] = None,
        lightcurve_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a power spectrum from an EventList.

        Args:
            event_list_name: Name of the EventList in state
            dt: Time binning in seconds
            norm: Normalization type ("leahy", "frac", "abs", "none")
            output_name: Optional name to save the spectrum

        Returns:
            Result dictionary with power spectrum data
        """
        try:
            if (event_list_name is None) == (lightcurve_name is None):
                raise ValueError("Choose exactly one source: an event list or a light curve")
            if lightcurve_name is not None:
                lc, source = self._lightcurve_source(lightcurve_name, dt, selection)
            else:
                if not self.state.has_event_data(event_list_name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"EventList '{event_list_name}' not found",
                        error=None,
                    )
                event_list, source = self._source(event_list_name, selection)
                lc = None
            warnings = []
            with collect_warnings(warnings):
                if lc is None:
                    lc = compatible_event_lightcurve(event_list, dt)
                ps = Powerspectrum(lc, norm=norm)
            ps_data = self._complete(
                ps,
                output_name,
                "power_spectrum",
                [source],
                {"dt": dt, "norm": norm, "output_name": output_name},
                warnings,
            )
            ps_data["freq_range"] = [float(ps.freq[0]), float(ps.freq[-1])]

            return self.create_result(
                success=True,
                data=ps_data,
                message=f"Power spectrum created (dt={ps.dt}s, norm={norm})",
                warnings=warnings,
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Creating power spectrum",
                event_list=event_list_name,
                dt=dt,
                norm=norm,
            )

    def create_averaged_power_spectrum(
        self,
        event_list_name: Optional[str] = None,
        dt: Optional[float] = None,
        segment_size: Optional[float] = None,
        norm: str = "leahy",
        output_name: Optional[str] = None,
        selection: Optional[EventSelection] = None,
        lightcurve_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an averaged power spectrum from an EventList.

        Args:
            event_list_name: Name of the EventList in state
            dt: Time binning in seconds
            segment_size: Segment size in seconds for averaging
            norm: Normalization type
            output_name: Optional name to save the spectrum

        Returns:
            Result dictionary with averaged power spectrum data
        """
        try:
            if (event_list_name is None) == (lightcurve_name is None):
                raise ValueError("Choose exactly one source: an event list or a light curve")
            if lightcurve_name is not None:
                lc, source = self._lightcurve_source(lightcurve_name, dt, selection)
                effective_dt = float(lc.dt)
            else:
                if not self.state.has_event_data(event_list_name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"EventList '{event_list_name}' not found",
                        error=None,
                    )
                lc = None
                effective_dt = dt

            seg_error = _segment_size_error(segment_size, effective_dt)
            if seg_error:
                return self.create_result(
                    success=False, data=None, message=seg_error, error=None
                )

            if lc is None:
                event_list, source = self._source(event_list_name, selection)
            warnings = []
            with collect_warnings(warnings):
                if lc is None:
                    lc = compatible_event_lightcurve(event_list, dt)
                ps = AveragedPowerspectrum.from_lightcurve(lc, segment_size, norm=norm)
            ps_data = self._complete(
                ps,
                output_name,
                "averaged_power_spectrum",
                [source],
                {
                    "dt": dt,
                    "segment_size": segment_size,
                    "norm": norm,
                    "output_name": output_name,
                },
                warnings,
            )

            return self.create_result(
                success=True,
                data=ps_data,
                message=f"Averaged power spectrum created (segment={segment_size}s)",
                warnings=warnings,
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Creating averaged power spectrum",
                event_list=event_list_name,
                dt=dt,
                segment_size=segment_size,
                norm=norm,
            )

    def create_cross_spectrum(
        self,
        event_list_1_name: str,
        event_list_2_name: str,
        dt: float,
        norm: str = "leahy",
        output_name: Optional[str] = None,
        selection_1: Optional[EventSelection] = None,
        selection_2: Optional[EventSelection] = None,
    ) -> Dict[str, Any]:
        """
        Create a cross spectrum from two EventLists.

        Args:
            event_list_1_name: Name of first EventList
            event_list_2_name: Name of second EventList
            dt: Time binning in seconds
            norm: Normalization type
            output_name: Optional name to save the spectrum

        Returns:
            Result dictionary with cross spectrum data
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

            event_list_1, source_1 = self._source(event_list_1_name, selection_1)
            event_list_2, source_2 = self._source(event_list_2_name, selection_2)

            overlap_error = _overlap_error(event_list_1, event_list_2)
            if overlap_error:
                return self.create_result(
                    success=False, data=None, message=overlap_error, error=None
                )
            binning_error = pair_binning_error(event_list_1, event_list_2, dt)
            if binning_error:
                return self.create_result(
                    success=False, data=None, message=binning_error, error=None
                )

            warnings = []
            band_warning = band_overlap_warning(
                self.state.get_event_data(event_list_1_name),
                event_list_1_name,
                selection_1,
                event_list_2_name,
                selection_2,
            )
            if band_warning:
                warnings.append(band_warning)
            with collect_warnings(warnings):
                cs = Crossspectrum.from_events(
                    events1=analysis_event_copy(event_list_1),
                    events2=analysis_event_copy(event_list_2),
                    dt=dt,
                    norm=norm,
                    gti=common_gtis(event_list_1, event_list_2),
                )
            cs_data = self._complete(
                cs,
                output_name,
                "cross_spectrum",
                [source_1, source_2],
                {"dt": dt, "norm": norm, "output_name": output_name},
                warnings,
            )

            return self.create_result(
                success=True,
                data=cs_data,
                message=f"Cross spectrum created (dt={dt}s)",
                warnings=warnings,
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Creating cross spectrum",
                event_list_1=event_list_1_name,
                event_list_2=event_list_2_name,
                dt=dt,
                norm=norm,
            )

    def create_averaged_cross_spectrum(
        self,
        event_list_1_name: str,
        event_list_2_name: str,
        dt: float,
        segment_size: float,
        norm: str = "leahy",
        output_name: Optional[str] = None,
        selection_1: Optional[EventSelection] = None,
        selection_2: Optional[EventSelection] = None,
    ) -> Dict[str, Any]:
        """
        Create an averaged cross spectrum from two EventLists.

        Args:
            event_list_1_name: Name of first EventList
            event_list_2_name: Name of second EventList
            dt: Time binning in seconds
            segment_size: Segment size in seconds
            norm: Normalization type
            output_name: Optional name to save the spectrum

        Returns:
            Result dictionary with averaged cross spectrum data
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

            seg_error = _segment_size_error(segment_size, dt)
            if seg_error:
                return self.create_result(
                    success=False, data=None, message=seg_error, error=None
                )

            event_list_1, source_1 = self._source(event_list_1_name, selection_1)
            event_list_2, source_2 = self._source(event_list_2_name, selection_2)

            overlap_error = _overlap_error(
                event_list_1, event_list_2, segment_size=segment_size
            )
            if overlap_error:
                return self.create_result(
                    success=False, data=None, message=overlap_error, error=None
                )
            binning_error = pair_binning_error(event_list_1, event_list_2, dt)
            if binning_error:
                return self.create_result(
                    success=False, data=None, message=binning_error, error=None
                )

            # Bin both event lists on the common exposure grid. Converting them
            # separately to light curves anchors their grids at different GTI
            # starts and can manufacture a phase/lag for identical photons.
            warnings = []
            band_warning = band_overlap_warning(
                self.state.get_event_data(event_list_1_name),
                event_list_1_name,
                selection_1,
                event_list_2_name,
                selection_2,
            )
            if band_warning:
                warnings.append(band_warning)
            with collect_warnings(warnings):
                cs = AveragedCrossspectrum.from_events(
                    events1=analysis_event_copy(event_list_1),
                    events2=analysis_event_copy(event_list_2),
                    dt=dt,
                    segment_size=segment_size,
                    norm=norm,
                    gti=common_gtis(event_list_1, event_list_2),
                )
            cs_data = self._complete(
                cs,
                output_name,
                "averaged_cross_spectrum",
                [source_1, source_2],
                {
                    "dt": dt,
                    "segment_size": segment_size,
                    "norm": norm,
                    "output_name": output_name,
                },
                warnings,
            )

            return self.create_result(
                success=True,
                data=cs_data,
                message=f"Averaged cross spectrum created (segment={segment_size}s)",
                warnings=warnings,
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Creating averaged cross spectrum",
                event_list_1=event_list_1_name,
                event_list_2=event_list_2_name,
                dt=dt,
                segment_size=segment_size,
                norm=norm,
            )

    def submit_dynamical_power_spectrum_job(
        self,
        job_manager,
        event_list_name: str,
        dt: float,
        segment_size: float,
        norm: str = "leahy",
        output_name: Optional[str] = None,
        selection: Optional[EventSelection] = None,
    ) -> Dict[str, Any]:
        """Run create_dynamical_power_spectrum in a cancellable worker process."""
        try:
            if output_name is not None:
                problem = validate_derived_name(output_name)
                if problem:
                    raise ValueError(problem)
                if self.state.get_spectrum_data(output_name) is not None:
                    raise ValueError(
                        f"Spectrum '{output_name}' already exists; choose a new name"
                    )
            captured = self.state.copy_event_data_with_identity(event_list_name)
            if captured is None:
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{event_list_name}' not found",
                    error=None,
                )
            events, dataset_id = captured
            state = self.state

            def publish(worker_result):
                response = worker_result["response"]
                if not response.get("success"):
                    raise ValueError(response.get("message") or "The analysis failed")
                stored = worker_result["stored"]
                if stored is not None and not state.add_spectrum_data_if_absent(
                    output_name, stored
                ):
                    raise ValueError(
                        f"Spectrum '{output_name}' already exists; choose a new name"
                    )
                data = response["data"]
                summary = {
                    "name": output_name or "",
                    "kind": "dynamical_power_spectrum",
                    "result_id": data.get("result_id") or "",
                }
                return summary, response

            job = job_manager.submit_analysis_job(
                target="services.analysis_jobs:dynamical_power_spectrum",
                payload={
                    "events": events,
                    "event_list_name": event_list_name,
                    "dataset_id": dataset_id,
                    "session_id": self.state.session_id,
                    "selection": selection.model_dump(exclude_none=True)
                    if selection is not None
                    else None,
                    "params": {
                        "dt": dt,
                        "segment_size": segment_size,
                        "norm": norm,
                        "output_name": output_name,
                    },
                },
                display_name="Dynamical power spectrum",
                publish=publish,
            )
            return self.create_result(
                success=True,
                data={"job_id": job.id},
                message="Dynamical power spectrum started as a background job",
            )
        except Exception as e:
            return self.handle_error(
                e, "Starting a dynamical power spectrum job", event_list=event_list_name
            )

    def create_dynamical_power_spectrum(
        self,
        event_list_name: str,
        dt: float,
        segment_size: float,
        norm: str = "leahy",
        output_name: Optional[str] = None,
        selection: Optional[EventSelection] = None,
    ) -> Dict[str, Any]:
        """
        Create a dynamical power spectrum from an EventList.

        Args:
            event_list_name: Name of the EventList in state
            dt: Time binning in seconds
            segment_size: Segment size in seconds
            norm: Normalization type
            output_name: Optional name to save the spectrum

        Returns:
            Result dictionary with dynamical power spectrum data
        """
        try:
            if not self.state.has_event_data(event_list_name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{event_list_name}' not found",
                    error=None,
                )

            seg_error = _segment_size_error(segment_size, dt)
            if seg_error:
                return self.create_result(
                    success=False, data=None, message=seg_error, error=None
                )

            event_list, source = self._source(event_list_name, selection)
            warnings = []
            with collect_warnings(warnings):
                lc = compatible_event_lightcurve(event_list, dt)
                dps = DynamicalPowerspectrum(lc, segment_size=segment_size, norm=norm)
            dps_data = self._complete(
                dps,
                output_name,
                "dynamical_power_spectrum",
                [source],
                {
                    "dt": dt,
                    "segment_size": segment_size,
                    "norm": norm,
                    "output_name": output_name,
                },
                warnings,
            )

            return self.create_result(
                success=True,
                data=dps_data,
                message=f"Dynamical power spectrum created (segment={segment_size}s)",
                warnings=warnings,
            )

        except Exception as e:
            return self.handle_error(
                e,
                "Creating dynamical power spectrum",
                event_list=event_list_name,
                dt=dt,
                segment_size=segment_size,
                norm=norm,
            )

    def rebin_spectrum(
        self,
        name: str,
        rebin_factor: float,
        log: bool = False,
        output_name: Optional[str] = None,
        expected_result_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Rebin a spectrum.

        Args:
            name: Name of the spectrum to rebin
            rebin_factor: Rebinning factor
            log: If True, use logarithmic rebinning
            output_name: Optional name for rebinned spectrum

        Returns:
            Result dictionary with rebinned spectrum data
        """
        try:
            if not self.state.has_spectrum_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Spectrum '{name}' not found",
                    error=None,
                )

            spectrum = self.state.copy_spectrum_for_analysis(
                name, expected_result_id=expected_result_id
            )
            if spectrum is None:
                raise ValueError(f"Spectrum '{name}' not found")
            parent_identity = spectrum_identity(spectrum)

            warnings = []
            with collect_warnings(warnings):
                if log:
                    rebinned = spectrum.rebin_log(rebin_factor)
                else:
                    # stingray rebin()'s positional arg is df (Hz), not a factor; use f=
                    rebinned = spectrum.rebin(f=rebin_factor)
            data = self._complete(
                rebinned,
                output_name,
                "rebin_spectrum",
                parent_identity["inputs"],
                {
                    "rebin_factor": rebin_factor,
                    "log": log,
                    "output_name": output_name,
                    "norm": spectrum.norm,
                },
                warnings,
                parent=(parent_identity, name),
            )

            return self.create_result(
                success=True,
                data=data,
                message=f"Spectrum rebinned ({'log' if log else 'linear'}, factor={rebin_factor})",
                warnings=warnings,
            )

        except Exception as e:
            return self.handle_error(
                e, "Rebinning spectrum", name=name, rebin_factor=rebin_factor, log=log
            )

    def list_spectra(self) -> Dict[str, Any]:
        """List all loaded spectra."""
        try:
            spec_data = self.state.get_spectrum_data()

            summaries = []
            for name, spec in spec_data:
                spec_type = type(spec).__name__
                summaries.append(
                    {
                        "name": name,
                        "type": spec_type,
                        "n_freq": len(spec.freq) if hasattr(spec, "freq") else None,
                        "result_id": getattr(spec, "result_identity", {}).get(
                            "result_id"
                        ),
                        "backend_session_id": getattr(spec, "result_identity", {}).get(
                            "backend_session_id"
                        ),
                    }
                )

            return self.create_result(
                success=True,
                data=summaries,
                message=f"Found {len(summaries)} spectrum/spectra",
            )

        except Exception as e:
            return self.handle_error(e, "Listing spectra")

    def delete_spectrum(self, name: str) -> Dict[str, Any]:
        """Delete a spectrum from state."""
        try:
            if not self.state.has_spectrum_data(name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"Spectrum '{name}' not found",
                    error=None,
                )

            self.state.remove_spectrum_data(name)

            return self.create_result(
                success=True,
                data={"name": name},
                message=f"Spectrum '{name}' deleted",
            )

        except Exception as e:
            return self.handle_error(e, "Deleting spectrum", name=name)
