"""Stable application contracts for changed public Stingray interfaces."""

import inspect
from functools import lru_cache
import warnings
import numpy as np
from stingray.fourier import poisson_level
from stingray.io import FITSTimeseriesReader


def event_read_options(fmt, **options):
    if fmt in {"ogip", "hea", "fits"}:
        # New EventList.read forwards kwargs to this reader; these options are
        # not reader arguments. Retain every option the reader does accept.
        parameters = inspect.signature(FITSTimeseriesReader).parameters
        for key in ("high_precision", "skip_checks"):
            if key not in parameters:
                options.pop(key, None)
    return options


def averaged_raw_coherence(spectrum):
    """Use the number of averaged spectra, never the number of time bins.

    Older AveragedCrossspectrum.coherence passed n instead of m into the
    finite-average bias correction. Evaluate the documented finite-average expression directly.
    Preserve the application's VN97 uncertainty convention and null invalid
    uncertainties in the calling service, rather than silently clipping them.
    """
    if np.any(np.asarray(spectrum.m) < 50):
        warnings.warn(
            "Number of segments used in averaging is significantly low; Gaussian coherence uncertainty estimates may be unreliable."
        )
    cross = np.asarray(spectrum.unnorm_power)
    first, second = spectrum.pds1.unnorm_power, spectrum.pds2.unnorm_power
    first_noise = poisson_level(norm="none", n_ph=spectrum.nphots1)
    second_noise = poisson_level(norm="none", n_ph=spectrum.nphots2)
    averages = np.asarray(spectrum.m)
    bias = (first * second - (first - first_noise) * (second - second_noise)) / averages
    bias = np.where(averages > 500, 0.0, bias)
    raw = np.abs(cross) ** 2
    numerator = np.where(raw - bias < 0, raw, raw - bias)
    coherence = numerator / (first * second)
    with np.errstate(invalid="ignore", divide="ignore"):
        error = (
            np.sqrt(2.0) * coherence * (1 - coherence) / np.sqrt(coherence * spectrum.m)
        )
    error = np.where(coherence == 0, 0.0, error)
    return coherence, error


def mask_legacy_low_count_rms(spectrum, events, segment_size, warning_list):
    """Backport the 10-photon/segment safety policy absent from older releases."""
    if hasattr(spectrum, "min_phot_per_segment"):
        return
    from stingray.gti import generate_indices_of_segment_boundaries_unbinned

    times = np.asarray(events.time)
    energies = np.asarray(events.energy)
    counts = np.zeros(len(spectrum.energy_intervals), dtype=int)
    segments = 0
    for _, _, first, last in generate_indices_of_segment_boundaries_unbinned(
        times, events.gti, segment_size
    ):
        segments += 1
        values = energies[first:last]
        for index, (low, high) in enumerate(spectrum.energy_intervals):
            counts[index] += np.count_nonzero((values >= low) & (values < high))
    if not segments:
        return
    for index, count in enumerate(counts):
        if count / segments < 10:
            spectrum.spectrum[index] = np.nan
            spectrum.spectrum_error[index] = np.nan
            warning_list.append(
                f"Low count rate in subject band {index + 1}: fewer than 10 ct/segment. RMS estimate is unavailable under the application low-count policy."
            )


def compatible_event_lightcurve(events, dt):
    """Apply the same instrument-clock rounding on every supported release."""
    resolution = getattr(events, "dt", 0) or 0
    actual = dt
    if np.ndim(resolution) == 0 and np.isfinite(resolution) and resolution > 0:
        actual = float(resolution * max(np.rint(dt / resolution), 1))
        if not np.isclose(actual, dt, rtol=1e-4):
            warnings.warn(
                f"The input event list has a time resolution of {resolution}. Using a multiple as dt ({actual}).",
                UserWarning,
            )
    return events.to_lc(dt=actual)


def rebin_lightcurve_with_standard_errors(lightcurve, factor):
    """Rebin detached inputs with standard errors on both sides of upstream #953."""
    import copy
    from .misc_service import LINEAR_REBIN_NEEDS_VARIANCE_INPUT

    working = copy.copy(lightcurve)
    errors = np.asarray(lightcurve.counts_err, dtype=float)
    finite = np.abs(errors[np.isfinite(errors)])
    scale = float(np.max(finite)) if finite.size else 1.0
    if scale == 0:
        scale = 1.0
    normalized = errors / scale
    working.counts_err = (
        normalized**2 if LINEAR_REBIN_NEEDS_VARIANCE_INPUT else normalized
    )
    result = working.rebin(f=factor)
    result.counts_err = np.asarray(result.counts_err) * scale
    result.err_dist = lightcurve.err_dist
    return result, LINEAR_REBIN_NEEDS_VARIANCE_INPUT


@lru_cache(maxsize=1)
def _zhang_coefficient():
    """Selectively accelerate unchanged upstream kernels when its import broke.

    Registering existing pure numerical functions with Numba's public API does
    not replace their implementations or modify the upstream module namespace.
    It avoids enabling the separate broken 2.3.0 Fourier vectorize decorator.
    """
    from stingray.deadtime import model
    from stingray.utils import HAS_NUMBA

    if HAS_NUMBA:
        return model._safe_B_single_k
    try:
        from numba import njit
        from numba.extending import register_jitable
    except ImportError:
        return model._safe_B_single_k
    for name in (
        "_stirling_factor",
        "e_m_x_x_over_factorial",
        "_Gn",
        "_h",
        "A0",
        "A_single_k",
        "_B_raw",
        "_safe_B_single_k",
    ):
        register_jitable(getattr(model, name))
    return njit(model._safe_B_single_k)


def cached_zhang_deadtime_model(
    freqs, dead_time, rate, bin_time, limit_k, background_rate=0.0
):
    """Exact Zhang series with frequency-independent B coefficients cached.

    The unaccelerated 2.3.0 loop recalculates the same expensive B_k at every
    frequency. Keep its physics, summation order, grid and interpolation while
    computing each coefficient once. No installed module is modified.
    """
    from stingray.deadtime import model
    from scipy.interpolate import interp1d

    if rate + background_rate >= 1 / dead_time:
        raise ValueError("Detected rate and dead time describe an unphysical model")
    n = int(max(float(np.max(freqs)), 10)) * 2
    detected = rate + background_rate
    tau = 1 / model.r_in(dead_time, detected)
    coefficient_function = _zhang_coefficient()
    constant = coefficient_function(0, detected, dead_time, bin_time, tau)
    power = np.zeros(n // 2)
    frequencies = np.arange(n // 2, dtype=float)
    for k in range(1, min(n, limit_k)):
        coefficient = coefficient_function(
            k, detected, dead_time, bin_time, tau, limit_k=limit_k
        )
        power += (n - k) / n * coefficient * np.cos(2 * np.pi * frequencies * k / n)
    power += constant
    if background_rate > 0:
        power = (power - 2) * rate / detected + 2
    grid = frequencies / (bin_time * n)
    return interp1d(grid, power, bounds_error=False, fill_value="extrapolate")(freqs)


def correct_pds_deadtime(pds, **options):
    import copy
    import stingray
    from packaging.version import Version

    if Version(stingray.__version__) != Version("2.3.0") or stingray.utils.HAS_NUMBA:
        return pds.deadtime_correct(**options)
    factor = 2 / cached_zhang_deadtime_model(pds.freq, bin_time=pds.dt, **options)
    result = copy.deepcopy(pds)
    result.power *= factor
    for attribute in ("unnorm_power", "power_err", "unnorm_power_err"):
        value = getattr(result, attribute, None)
        if value is not None:
            setattr(result, attribute, value * factor)
    return result
