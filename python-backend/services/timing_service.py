"""
Timing service for timing analysis operations.

Handles bispectrum, power colors, and other timing analysis.
"""

from typing import Any, Dict, Optional

import numpy as np
from stingray import Bispectrum, DynamicalPowerspectrum
from stingray.gti import generate_indices_of_segment_boundaries_unbinned

from .base_service import BaseService
from .scientific_compatibility import compatible_event_lightcurve
from .scientific_compatibility import averaged_raw_coherence
from .analysis_helpers import (
    analysis_event_copy,
    collect_warnings,
    common_gtis,
    overlap_error as _overlap_error,
    pair_binning_error,
    segment_size_error as _segment_size_error,
)
from .power_color_helpers import (
    BAND_ORDER,
    integrate_power_colors,
    validate_power_color_inputs,
)
from .utility_helpers import operation_provenance


def _finite_list(arr) -> list:
    """Convert a float array to a list, replacing non-finite values with None."""
    values = np.asarray(arr, dtype=float)
    if np.isfinite(values).all():
        return values.tolist()
    return [float(v) if np.isfinite(v) else None for v in values]


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
            lc = compatible_event_lightcurve(event_list, dt)
            bs = Bispectrum(lc, maxlag=maxlag, scale=scale, window=window)

            if output_name:
                self.state.add_analysis_result(output_name, bs)

            bs_data = {
                "name": output_name,
                "freq": bs.freq.tolist(),
                "lags": bs.lags.tolist(),
                "bispec_mag": bs.bispec_mag.tolist(),
                "bispec_phase": bs.bispec_phase.tolist(),
                # cum3 omitted from the payload — large and unused by the UI;
                # recompute server-side if ever needed.
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
        """Per-segment, integrated fractional variances and Heil C/A, B/D colours.

        Common-mean normalization requires each segment's Poisson density to be
        2 * segment_rate / common_mean_rate**2. Instrumental dead time/background
        are not corrected here. Unlike the paper's averaged
        observation spectra, these are exploratory per-segment measurements.
        """
        scientific_warnings = []
        try:
            if not self.state.has_event_data(event_list_name):
                return self.create_result(
                    False, message=f"EventList '{event_list_name}' not found"
                )
            bands = validate_power_color_inputs(dt, segment_size, freq_ranges)
            event_list = analysis_event_copy(self.state.get_event_data(event_list_name))
            binning_error = pair_binning_error(event_list, event_list, dt)
            if binning_error:
                raise ValueError(binning_error)
            times = np.asarray(event_list.time)
            if times.ndim != 1 or times.size == 0 or not np.isfinite(times).all():
                raise ValueError(
                    "Event times must be a nonempty finite one-dimensional array"
                )
            segments = list(
                generate_indices_of_segment_boundaries_unbinned(
                    times, event_list.gti, segment_size
                )
            )
            segment_counts = np.asarray(
                [stop_index - start_index for _, _, start_index, stop_index in segments]
            )
            retained = segment_counts >= 2
            if not retained.any():
                raise ValueError(
                    "No complete segment contains at least two photons inside the GTIs"
                )
            segment_times = np.asarray(
                [(float(start) + float(stop)) / 2 for start, stop, _, _ in segments]
            )
            with collect_warnings(scientific_warnings):
                dps = DynamicalPowerspectrum(
                    event_list, segment_size=segment_size, norm="frac", sample_time=dt
                )
            actual_segment_size = 1 / float(dps.df)
            # Validate the actual FFT, including any Stingray rounding, before
            # integrating: never silently crop a requested frequency range.
            validate_power_color_inputs(dt, actual_segment_size, bands)
            if not np.isclose(actual_segment_size, segment_size, rtol=1e-10, atol=0):
                raise ValueError(
                    "Stingray changed the requested segment_size; choose an integer number of dt samples"
                )
            if not np.isfinite(dps.meanrate) or dps.meanrate <= 0:
                raise ValueError("A finite positive detected count rate is required")
            if dps.dyn_ps.shape[1] != int(retained.sum()):
                raise ValueError(
                    "Stingray periodogram columns do not match the retained GTI segments"
                )
            segment_rates = segment_counts / actual_segment_size
            if not np.isclose(
                segment_rates[retained].mean(), dps.meanrate, rtol=1e-10, atol=0
            ):
                raise ValueError(
                    "Stingray's common mean differs from the counted segment rates"
                )
            # avg_pds_from_iterable normalizes every sub-periodogram by one
            # common mean squared. A changing segment rate changes its Poisson
            # density even though the fractional normalization is fixed.
            poisson_power = 2 / float(dps.meanrate)
            segment_noise = 2 * segment_rates / float(dps.meanrate) ** 2
            powers = dps.dyn_ps
            if not retained.all():
                powers = np.full((len(dps.freq), len(segments)), np.nan)
                powers[:, retained] = dps.dyn_ps
                scientific_warnings.append(
                    f"{int((~retained).sum())} segments have fewer than two photons (including segments with no photons); their variances and colours are null at the original time positions."
                )
            integrated = integrate_power_colors(
                dps.freq, powers, float(dps.df), bands, segment_noise
            )
            invalid_count = integrated["valid_segments"].count(False)
            if invalid_count:
                scientific_warnings.append(
                    f"{invalid_count} of {len(segment_times)} segments lack a positive >=3 sigma variance detection in all four bands; their power colours are null."
                )
            if any(count < 30 for count in integrated["band_bin_counts"].values()):
                scientific_warnings.append(
                    "At least one band has fewer than 30 Fourier bins. Propagated Gaussian errors and the 3 sigma detection screen are approximate; use longer segments or averaged spectra for inference."
                )
            scientific_warnings.append(
                "Assumes ideal Poisson counting noise: each segment uses 2 * segment count rate / common mean count rate squared, without background or detector dead-time correction. Per-segment colours are exploratory; the Heil paper averages observation spectra and fits the white-noise level."
            )
            result_data = {
                "name": output_name,
                **integrated,
                "time": segment_times.tolist(),
                "freq_ranges": bands,
                "band_order": list(BAND_ORDER),
                "normalization": "frac",
                "variance_unit": "fractional rms squared",
                "poisson_power": poisson_power,
                "poisson_power_by_segment": segment_noise.tolist(),
                "segment_count_rates": segment_rates.tolist(),
                "common_mean_count_rate": float(dps.meanrate),
                "normalization_reference": "common mean detected count rate across segments with at least two photons",
                "dt": dt,
                "segment_size": actual_segment_size,
                "df": float(dps.df),
                "detection_sigma": 3,
                "warnings": scientific_warnings,
                "metadata": {
                    "units": {
                        "time": "s",
                        "power_colors": "(rms/mean)^2",
                        "band_variance_errors": "(rms/mean)^2",
                        "pc1": "1",
                        "pc1_err": "1",
                        "pc2": "1",
                        "pc2_err": "1",
                    },
                    "power_color_definition": {"pc1": "C/A", "pc2": "B/D"},
                    "uncertainty": "observed periodogram P/sqrt(m), m=1; integrated errors and covariance-aware ratio derivatives in quadrature",
                    "validity_policy": "all four band variances positive and >=3 sigma; null ratios preserve time alignment",
                    "measurement": "per-segment exploratory",
                    "poisson_model": "2 * segment_count_rate / common_mean_count_rate**2",
                    "normalization_reference": "common mean detected count rate across retained segments",
                },
                "provenance": operation_provenance(
                    "timing_power_colors",
                    input_source={"kind": "event_list", "name": event_list_name},
                    parameters={
                        "dt": dt,
                        "segment_size": actual_segment_size,
                        "freq_ranges": bands,
                        "output_name": output_name,
                    },
                    method="Fourier-bin overlap integration of common-mean fractional-rms density minus per-segment theoretical Poisson noise",
                    poisson_model="2 * segment_count_rate / common_mean_count_rate**2",
                    reference="https://arxiv.org/html/1405.2024v2",
                ),
            }
            if output_name:
                self.state.add_analysis_result(output_name, result_data)
            return self.create_result(
                True,
                data=result_data,
                message=f"Integrated power colours calculated for {len(segment_times)} segments",
                warnings=scientific_warnings,
            )
        except ValueError as error:
            return self.create_result(
                False, message=str(error), warnings=scientific_warnings
            )
        except Exception as error:
            result = self.handle_error(
                error,
                "Calculating power colors",
                event_list=event_list_name,
                dt=dt,
                segment_size=segment_size,
            )
            result["warnings"] = scientific_warnings
            return result

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
        scientific_warnings = []
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

            from stingray import AveragedCrossspectrum

            event_list_1 = self.state.get_event_data(event_list_1_name)
            event_list_2 = self.state.get_event_data(event_list_2_name)

            overlap_error = _overlap_error(
                event_list_1, event_list_2, segment_size=segment_size
            )
            if overlap_error:
                return self.create_result(
                    success=False, data=None, message=overlap_error, error=None
                )

            binning_error = pair_binning_error(event_list_1, event_list_2, dt)
            if binning_error:
                return self.create_result(False, message=binning_error)
            event_list_1 = analysis_event_copy(event_list_1)
            event_list_2 = analysis_event_copy(event_list_2)
            with collect_warnings(scientific_warnings):
                cs = AveragedCrossspectrum.from_events(
                    event_list_1,
                    event_list_2,
                    dt=dt,
                    segment_size=segment_size,
                    norm="leahy",
                    silent=True,
                    gti=common_gtis(event_list_1, event_list_2),
                )

            # Stingray's time_lag() returns (lag, lag_err) for averaged spectra.
            with collect_warnings(scientific_warnings):
                lag_result = cs.time_lag()
            if isinstance(lag_result, tuple):
                time_lags, time_lags_err = lag_result
            else:
                time_lags, time_lags_err = lag_result, None

            freq = np.asarray(cs.freq, dtype=float)
            time_lags = np.real(np.asarray(time_lags))
            if time_lags_err is not None:
                time_lags_err = np.real(np.asarray(time_lags_err))

            if time_lags.shape != freq.shape:
                raise ValueError(
                    f"Unexpected time_lag() result shape {time_lags.shape}"
                )

            if freq_range:
                mask = (freq >= freq_range[0]) & (freq <= freq_range[1])
                freq = freq[mask]
                time_lags = time_lags[mask]
                if time_lags_err is not None:
                    time_lags_err = time_lags_err[mask]

            lag_units = {"freq": "Hz", "time_lags": "s"}
            if time_lags_err is not None:
                lag_units["time_lags_err"] = "s"
            result_data = {
                "name": output_name,
                "dt": float(cs.dt),
                "segment_size": float(cs.segment_size),
                "requested_segment_size": segment_size,
                "warnings": scientific_warnings,
                "freq": freq.tolist(),
                "time_lags": _finite_list(time_lags),
                "time_lags_err": (
                    _finite_list(time_lags_err) if time_lags_err is not None else None
                ),
                "freq_range": freq_range,
                "metadata": {
                    "units": lag_units,
                    "non_column_fields": ["freq_range"],
                },
                "provenance": operation_provenance(
                    "timing_time_lags",
                    input_source={
                        "kind": "event_list_pair",
                        "names": [event_list_1_name, event_list_2_name],
                    },
                    parameters={
                        "dt": float(cs.dt),
                        "segment_size": float(cs.segment_size),
                        "requested_segment_size": segment_size,
                        "freq_range": freq_range,
                        "output_name": output_name,
                    },
                ),
            }

            if output_name:
                self.state.add_analysis_result(output_name, result_data)

            return self.create_result(
                success=True,
                data=result_data,
                message="Time lags calculated",
                warnings=scientific_warnings,
            )

        except Exception as e:
            result = self.handle_error(
                e,
                "Calculating time lags",
                event_list_1=event_list_1_name,
                event_list_2=event_list_2_name,
                dt=dt,
                segment_size=segment_size,
            )
            result["warnings"] = scientific_warnings
            return result

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
        scientific_warnings = []
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

            from stingray import AveragedCrossspectrum

            event_list_1 = self.state.get_event_data(event_list_1_name)
            event_list_2 = self.state.get_event_data(event_list_2_name)

            overlap_error = _overlap_error(
                event_list_1, event_list_2, segment_size=segment_size
            )
            if overlap_error:
                return self.create_result(
                    success=False, data=None, message=overlap_error, error=None
                )

            binning_error = pair_binning_error(event_list_1, event_list_2, dt)
            if binning_error:
                return self.create_result(False, message=binning_error)
            event_list_1 = analysis_event_copy(event_list_1)
            event_list_2 = analysis_event_copy(event_list_2)
            with collect_warnings(scientific_warnings):
                cs = AveragedCrossspectrum.from_events(
                    event_list_1,
                    event_list_2,
                    dt=dt,
                    segment_size=segment_size,
                    norm="leahy",
                    silent=True,
                    gti=common_gtis(event_list_1, event_list_2),
                )

            # Stingray's coherence() returns (coherence, uncertainty) for
            # averaged cross spectra (Vaughan & Nowak 1997).
            with collect_warnings(scientific_warnings):
                coh_result = averaged_raw_coherence(cs)
            if isinstance(coh_result, tuple):
                coherence_vals, coherence_err = coh_result
            else:
                coherence_vals, coherence_err = coh_result, None

            coherence_vals = np.real(np.asarray(coherence_vals))
            if coherence_vals.shape != np.asarray(cs.freq).shape:
                raise ValueError(
                    f"Unexpected coherence() result shape {coherence_vals.shape}"
                )

            # Keep the estimator unclipped, but invalid/negative uncertainty
            # estimates are not meaningful error-bar magnitudes.
            if coherence_err is not None:
                coherence_err = np.asarray(coherence_err, dtype=float)
                bad_error = ~np.isfinite(coherence_err) | (coherence_err < 0)
                if bad_error.any():
                    scientific_warnings.append(
                        "Some coherence uncertainties are undefined; affected error bars are null. Coherence estimates are not clipped."
                    )
                    coherence_err = np.where(bad_error, np.nan, coherence_err)
            coherence_units = {"freq": "Hz", "coherence": "1"}
            if coherence_err is not None:
                coherence_units["coherence_err"] = "1"
            result_data = {
                "name": output_name,
                "dt": float(cs.dt),
                "segment_size": float(cs.segment_size),
                "requested_segment_size": segment_size,
                "warnings": scientific_warnings,
                "freq": cs.freq.tolist(),
                "coherence": _finite_list(coherence_vals),
                "coherence_err": (
                    _finite_list(coherence_err) if coherence_err is not None else None
                ),
                "n_segments": int(cs.m) if hasattr(cs, "m") else None,
                "metadata": {"units": coherence_units},
                "provenance": operation_provenance(
                    "timing_coherence",
                    input_source={
                        "kind": "event_list_pair",
                        "names": [event_list_1_name, event_list_2_name],
                    },
                    parameters={
                        "dt": float(cs.dt),
                        "segment_size": float(cs.segment_size),
                        "requested_segment_size": segment_size,
                        "coherence_estimator": "raw_noise_bias_corrected_with_n_averaged",
                        "output_name": output_name,
                    },
                ),
            }

            if output_name:
                self.state.add_analysis_result(output_name, result_data)

            return self.create_result(
                success=True,
                data=result_data,
                message="Coherence calculated",
                warnings=scientific_warnings,
            )

        except Exception as e:
            result = self.handle_error(
                e,
                "Calculating coherence",
                event_list_1=event_list_1_name,
                event_list_2=event_list_2_name,
                dt=dt,
                segment_size=segment_size,
            )
            result["warnings"] = scientific_warnings
            return result
