"""Integrated, noise-subtracted power colours with explicit Heil conventions.

Heil et al. (2015), https://arxiv.org/html/1405.2024v2, defines C/A and
B/D and propagates variance errors in quadrature. The installed Stingray
power_color wrapper instead returns A/C and adds relative errors linearly.
Its Fourier integrator also overwrites the lower-edge correction when both
edges lie within one Fourier bin. Keep these small numerical operations explicit.
"""

import numpy as np

BAND_ORDER = ("A", "B", "C", "D")
CANONICAL_BANDS = {
    "A": (1 / 256, 1 / 32),
    "B": (1 / 32, 0.25),
    "C": (0.25, 2.0),
    "D": (2.0, 16.0),
}


def validate_power_color_inputs(dt, segment_size, freq_ranges):
    """Reject unresolved, unordered, or partially unavailable requested bands."""
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and positive")
    if not np.isfinite(segment_size) or segment_size <= 0:
        raise ValueError("segment_size must be finite and positive")
    bins = segment_size / dt
    if not np.isfinite(bins) or bins < 3:
        raise ValueError("segment_size must be at least 3x dt")
    if not np.isclose(bins, round(bins), rtol=0, atol=1e-7):
        raise ValueError("segment_size must contain an integer number of dt samples")
    if bins > 1_000_000:
        raise ValueError(
            "A power-colour segment is limited to 1,000,000 time bins; increase dt or reduce segment_size"
        )
    if not isinstance(freq_ranges, dict) or set(freq_ranges) != set(BAND_ORDER):
        raise ValueError("Exactly four frequency bands named A, B, C, D are required")
    count = int(round(bins))
    resolution = 1 / segment_size
    # Stingray excludes the even-length FFT's Nyquist ordinate. Its highest
    # positive bin's finite support therefore ends half a resolution below it.
    last_index = (count - 1) // 2
    support_max = (last_index + 0.5) * resolution
    previous_max = 0.0
    bands = {}
    for name in BAND_ORDER:
        limits = freq_ranges[name]
        if len(limits) != 2:
            raise ValueError(f"Band {name} must have two frequency bounds")
        lower, upper = map(float, limits)
        if not np.isfinite([lower, upper]).all() or not 0 < lower < upper:
            raise ValueError(
                f"Band {name} must have finite bounds with 0 < minimum < maximum"
            )
        if lower < previous_max:
            raise ValueError("Bands A, B, C, D must be ordered without overlap")
        if lower < resolution * (1 - 1e-12):
            raise ValueError(
                f"Band {name} starts below Fourier resolution 1/segment_size ({resolution:g} Hz); increase segment_size"
            )
        if upper > support_max * (1 + 1e-12):
            raise ValueError(
                f"Band {name} exceeds available Fourier support ({support_max:g} Hz; Nyquist {1 / (2 * dt):g} Hz); decrease dt"
            )
        # Require an actual Fourier ordinate in every requested band. Merely
        # overlapping the skirt of an adjacent bin is insufficient resolution.
        first = max(1, int(np.ceil(lower / resolution - 1e-10)))
        if first > last_index or first * resolution >= upper - resolution * 1e-10:
            raise ValueError(
                f"Band {name} contains no Fourier frequency bins; increase segment_size"
            )
        bands[name] = (lower, upper)
        previous_max = upper
    return bands


def _finite(values):
    return [float(value) if np.isfinite(value) else None for value in values]


def integrate_power_colors(frequency, power, df, bands, poisson_power, m=1):
    """Integrate fractional-rms PSDs; retain negative estimates and aligned nulls.

    Bin widths are exact intersections with the requested frequency ranges.
    sigma(P_i)=P_i/sqrt(m), the periodogram error model used by Stingray's
    Fourier integrator. Ratio derivatives include covariance when an editable
    band boundary splits one Fourier bin across numerator and denominator.
    Colours require all four variances positive and >=3 sigma, as in Heil.
    These propagated Gaussian errors are approximate for few Fourier bins.
    """
    frequency = np.asarray(frequency, dtype=float)
    power = np.asarray(power, dtype=float)
    if frequency.ndim != 1 or power.ndim != 2 or power.shape[0] != frequency.size:
        raise ValueError("Power must have frequency-by-segment shape")
    if (
        frequency.size == 0
        or not np.isfinite(frequency).all()
        or np.any(np.diff(frequency) <= 0)
    ):
        raise ValueError("Fourier frequencies must be finite and strictly increasing")
    poisson_power = np.asarray(poisson_power, dtype=float)
    if poisson_power.ndim == 0:
        poisson_power = np.full(power.shape[1], float(poisson_power))
    if (
        not np.isfinite([df, m]).all()
        or poisson_power.shape != (power.shape[1],)
        or not np.isfinite(poisson_power).all()
        or df <= 0
        or np.any(poisson_power < 0)
        or m <= 0
    ):
        raise ValueError(
            "Fourier resolution, Poisson level and averaging count must be finite and valid"
        )
    low_edges = frequency - df / 2
    high_edges = frequency + df / 2
    weights = {}
    variances = {}
    errors = {}
    for name in BAND_ORDER:
        lower, upper = bands[name]
        if lower < low_edges[0] - df * 1e-10 or upper > high_edges[-1] + df * 1e-10:
            raise ValueError(f"Band {name} exceeds available Fourier support")
        widths = np.maximum(
            0.0, np.minimum(high_edges, upper) - np.maximum(low_edges, lower)
        )
        if not np.any(widths > 0):
            raise ValueError(f"Band {name} contains no Fourier frequency bins")
        weights[name] = widths
        selected = widths > 0
        with np.errstate(over="ignore", invalid="ignore"):
            variances[name] = np.sum(
                (power[selected] - poisson_power) * widths[selected, None], axis=0
            )
            errors[name] = np.sqrt(
                np.sum((power[selected] * widths[selected, None]) ** 2 / m, axis=0)
            )
    valid = np.ones(power.shape[1], dtype=bool)
    for name in BAND_ORDER:
        valid &= np.isfinite(variances[name]) & np.isfinite(errors[name])
        valid &= (variances[name] > 0) & (variances[name] >= 3 * errors[name])
    ratios = {}
    for key, numerator_name, denominator_name in (("pc1", "C", "A"), ("pc2", "B", "D")):
        numerator, denominator = variances[numerator_name], variances[denominator_name]
        ratio = np.full(power.shape[1], np.nan)
        ratio_error = np.full(power.shape[1], np.nan)
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            ratio[valid] = numerator[valid] / denominator[valid]
            derivative = (
                weights[numerator_name][:, None] / denominator[None, valid]
                - numerator[None, valid]
                * weights[denominator_name][:, None]
                / denominator[None, valid] ** 2
            )
            selected = (weights[numerator_name] > 0) | (weights[denominator_name] > 0)
            ratio_error[valid] = np.sqrt(
                np.sum(
                    (derivative[selected] * power[selected][:, valid]) ** 2 / m, axis=0
                )
            )
        valid &= np.isfinite(ratio) & np.isfinite(ratio_error)
        ratios[key] = ratio
        ratios[f"{key}_err"] = ratio_error
    for values in ratios.values():
        values[~valid] = np.nan
    return {
        "power_colors": {name: _finite(variances[name]) for name in BAND_ORDER},
        "band_variance_errors": {name: _finite(errors[name]) for name in BAND_ORDER},
        **{name: _finite(values) for name, values in ratios.items()},
        "valid_segments": valid.tolist(),
        "band_bin_counts": {
            name: int(np.count_nonzero(weights[name] > 0)) for name in BAND_ORDER
        },
    }
