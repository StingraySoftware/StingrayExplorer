"""Numerical contracts independent of the Stingray power-colour wrapper."""

import numpy as np
import pytest

from services.power_color_helpers import (
    integrate_power_colors,
    validate_power_color_inputs,
)


def test_integrates_noise_subtracted_variance_with_bandwidth_and_quadrature_errors():
    frequency = np.arange(0.5, 8.0, 0.5)
    power = np.full((frequency.size, 1), 12.0)
    bands = {"A": (0.5, 1.0), "B": (1.0, 2.0), "C": (2.0, 4.0), "D": (4.0, 7.0)}
    result = integrate_power_colors(frequency, power, 0.5, bands, poisson_power=2.0)
    np.testing.assert_allclose(
        [result["power_colors"][key][0] for key in bands], [5, 10, 20, 30]
    )
    # A has two half-width bins, not their mean or a full-bin sum.
    assert result["band_variance_errors"]["A"][0] == pytest.approx(np.sqrt(2 * 3**2))


def test_single_fourier_bin_is_clipped_on_both_sides():
    frequency = np.array([1.0, 2.0, 3.0, 4.0])
    bands = {"A": (0.8, 1.2), "B": (1.8, 2.2), "C": (2.8, 3.2), "D": (3.8, 4.2)}
    result = integrate_power_colors(frequency, np.full((4, 1), 100.0), 1.0, bands, 2.0)
    assert result["power_colors"]["A"][0] == pytest.approx(39.2)
    assert result["band_variance_errors"]["A"][0] == pytest.approx(40.0)


def test_heil_ratios_use_c_over_a_and_b_over_d_with_covariance_aware_error():
    frequency = np.arange(0.5, 8.0, 0.01)
    bands = {"A": (0.5, 1.0), "B": (1.0, 2.0), "C": (2.0, 4.0), "D": (4.0, 7.0)}
    power = np.full((frequency.size, 1), 100.0)
    result = integrate_power_colors(frequency, power, 0.01, bands, 2.0)
    assert result["valid_segments"] == [True]
    assert result["pc1"][0] == pytest.approx(4.0)
    assert result["pc2"][0] == pytest.approx(1 / 3)
    variance = result["power_colors"]
    errors = result["band_variance_errors"]
    expected = 4.0 * np.hypot(
        errors["C"][0] / variance["C"][0], errors["A"][0] / variance["A"][0]
    )
    assert result["pc1_err"][0] == pytest.approx(expected)


def test_null_ratios_for_noise_or_undetected_variances_preserve_time_alignment():
    frequency = np.arange(0.5, 8.0, 0.01)
    bands = {"A": (0.5, 1.0), "B": (1.0, 2.0), "C": (2.0, 4.0), "D": (4.0, 7.0)}
    powers = np.column_stack(
        [
            np.full(frequency.size, 100.0),
            np.full(frequency.size, 2.0),
            np.full(frequency.size, 1.0),
        ]
    )
    result = integrate_power_colors(frequency, powers, 0.01, bands, 2.0)
    assert result["valid_segments"] == [True, False, False]
    assert result["pc1"][1:] == [None, None]
    assert result["pc2"][1:] == [None, None]
    assert result["power_colors"]["A"][2] < 0


@pytest.mark.parametrize(
    "dt, segment_size, bands, match",
    [
        (
            float("nan"),
            256,
            {"A": (1 / 256, 1 / 32), "B": (1 / 32, 0.25), "C": (0.25, 2), "D": (2, 16)},
            "dt",
        ),
        (
            0,
            256,
            {"A": (1 / 256, 1 / 32), "B": (1 / 32, 0.25), "C": (0.25, 2), "D": (2, 16)},
            "dt",
        ),
        (
            1 / 64,
            64,
            {"A": (1 / 256, 1 / 32), "B": (1 / 32, 0.25), "C": (0.25, 2), "D": (2, 16)},
            "resolution",
        ),
        (
            0.11,
            256,
            {"A": (1 / 256, 1 / 32), "B": (1 / 32, 0.25), "C": (0.25, 2), "D": (2, 16)},
            "integer",
        ),
        (
            1 / 32,
            256,
            {"A": (1 / 256, 1 / 32), "B": (1 / 32, 0.25), "C": (0.25, 2), "D": (2, 16)},
            "support",
        ),
        (
            1 / 64,
            256,
            {"A": (1 / 256, 0.25), "B": (1 / 32, 0.25), "C": (0.25, 2), "D": (2, 16)},
            "overlap",
        ),
        (
            1 / 64,
            256,
            {"A": (1 / 256, 1 / 32), "B": (0.04, 0.041), "C": (0.25, 2), "D": (2, 16)},
            "Fourier",
        ),
    ],
)
def test_rejects_unresolved_truncated_or_invalid_requests(
    dt, segment_size, bands, match
):
    with pytest.raises(ValueError, match=match):
        validate_power_color_inputs(dt, segment_size, bands)


def test_ratio_error_accounts_for_shared_fourier_bins():
    # A and C split the same Fourier ordinate: their measured powers are
    # perfectly correlated, so equal weights give a ratio with zero error.
    bands = {"A": (0.6, 0.8), "B": (0.8, 1.1), "C": (1.1, 1.3), "D": (1.3, 1.4)}
    result = integrate_power_colors(
        [1, 2, 3], np.full((3, 1), 100.0), 1.0, bands, 2.0, m=100
    )
    assert result["pc1"][0] == pytest.approx(1.0)
    assert result["pc1_err"][0] == pytest.approx(0.0, abs=1e-14)
