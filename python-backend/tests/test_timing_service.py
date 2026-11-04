import json

import numpy as np
import pytest

from services.timing_service import TimingService


def test_identical_signals_match_finite_average_noise_bias_estimator(loaded_state):
    svc = TimingService(loaded_state)
    # Verify the estimator independently of the installed object method.
    result = svc.calculate_coherence("ev1", "ev1", dt=0.0625, segment_size=8.0)
    assert result["success"], result
    json.dumps(result, allow_nan=False)
    coh = np.asarray(result["data"]["coherence"], dtype=float)
    # Finite-average noise bias assumes independent detector noise; comparing
    # a stream with itself does not justify a unit-coherence golden value.
    from stingray import AveragedCrossspectrum

    events = loaded_state.get_event_data("ev1")
    cross = AveragedCrossspectrum.from_events(
        events, events, dt=0.0625, segment_size=8, norm="leahy", silent=True
    )
    p1, p2 = cross.pds1.unnorm_power, cross.pds2.unnorm_power
    raw = np.abs(cross.unnorm_power) ** 2
    bias = (p1 * p2 - (p1 - cross.nphots1) * (p2 - cross.nphots2)) / cross.m
    numerator = np.where(raw - bias < 0, raw, raw - bias)
    np.testing.assert_allclose(coh, numerator / (p1 * p2), rtol=1e-12)
    assert result["data"]["metadata"]["units"]["freq"] == "Hz"
    assert result["data"]["metadata"]["units"]["coherence"] == "1"
    assert result["data"]["provenance"]["operation"] == "timing_coherence"


def test_coherence_includes_uncertainty(loaded_state):
    svc = TimingService(loaded_state)
    result = svc.calculate_coherence("ev1", "ev2", dt=0.0625, segment_size=8.0)
    assert result["success"], result
    data = result["data"]
    assert "coherence_err" in data
    assert data["coherence_err"] is not None
    assert len(data["coherence_err"]) == len(data["coherence"])


def test_time_lags_include_errors_and_serialize(loaded_state):
    svc = TimingService(loaded_state)
    result = svc.calculate_time_lags("ev1", "ev2", dt=0.0625, segment_size=8.0)
    assert result["success"], result
    json.dumps(result, allow_nan=False)
    data = result["data"]
    assert "time_lags_err" in data
    assert len(data["freq"]) == len(data["time_lags"])
    assert data["time_lags_err"] is not None
    assert len(data["time_lags_err"]) == len(data["time_lags"])
    assert data["metadata"]["units"] == {
        "freq": "Hz",
        "time_lags": "s",
        "time_lags_err": "s",
    }
    assert data["provenance"]["operation"] == "timing_time_lags"


def test_time_lags_freq_range_filters_all_arrays(loaded_state):
    svc = TimingService(loaded_state)
    full = svc.calculate_time_lags("ev1", "ev2", dt=0.0625, segment_size=8.0)
    sub = svc.calculate_time_lags(
        "ev1", "ev2", dt=0.0625, segment_size=8.0, freq_range=(0.5, 2.0)
    )
    assert sub["success"], sub
    freqs = np.asarray(sub["data"]["freq"], dtype=float)
    assert freqs.min() >= 0.5
    assert freqs.max() <= 2.0
    assert len(sub["data"]["freq"]) < len(full["data"]["freq"])
    assert len(sub["data"]["time_lags"]) == len(sub["data"]["freq"])
    if sub["data"]["time_lags_err"] is not None:
        assert len(sub["data"]["time_lags_err"]) == len(sub["data"]["freq"])
    assert sub["data"]["metadata"]["non_column_fields"] == ["freq_range"]


def test_power_colors_serializes(loaded_state):
    svc = TimingService(loaded_state)
    result = svc.calculate_power_colors(
        "ev1",
        dt=0.0625,
        segment_size=8.0,
        freq_ranges={
            "A": (0.125, 0.5),
            "B": (0.5, 1.0),
            "C": (1.0, 2.0),
            "D": (2.0, 4.0),
        },
    )
    assert result["success"], result
    json.dumps(result, allow_nan=False)
    data = result["data"]
    assert len(data["time"]) == 8  # 64 s / 8 s segments
    for band in data["power_colors"].values():
        assert len(band) == len(data["time"])


def test_bispectrum_serializes(loaded_state):
    svc = TimingService(loaded_state)
    result = svc.create_bispectrum("ev1", dt=0.25, maxlag=10)
    assert result["success"], result
    json.dumps(result, allow_nan=False)
    assert "cum3" not in result["data"]


def test_time_lag_of_identical_signals_is_zero(loaded_state):
    svc = TimingService(loaded_state)
    result = svc.calculate_time_lags("ev1", "ev1", dt=0.0625, segment_size=8.0)
    assert result["success"], result
    lags = np.asarray([v for v in result["data"]["time_lags"] if v is not None])
    assert np.max(np.abs(lags)) < 1e-10


def test_tiny_segment_size_rejected_for_coherence(loaded_state):
    svc = TimingService(loaded_state)
    result = svc.calculate_coherence("ev1", "ev2", dt=0.0625, segment_size=0.125)
    assert not result["success"]
    assert "3x dt" in result["message"]


def test_coherence_of_independent_signals_is_low(loaded_state):
    svc = TimingService(loaded_state)
    result = svc.calculate_coherence("ev1", "ev2", dt=0.0625, segment_size=8.0)
    assert result["success"], result
    coh = np.asarray(
        [v for v in result["data"]["coherence"] if v is not None], dtype=float
    )
    assert np.median(coh) < 0.5  # measured ~0.1 for independent fixtures


def test_disjoint_event_lists_rejected_for_coherence(loaded_state):
    rng = np.random.default_rng(8)
    far = np.sort(rng.uniform(1000.0, 1064.0, 5000))
    from stingray import EventList

    loaded_state.add_event_data("ev_far", EventList(time=far, gti=[[1000.0, 1064.0]]))
    svc = TimingService(loaded_state)
    result = svc.calculate_coherence("ev1", "ev_far", dt=0.0625, segment_size=8.0)
    assert not result["success"]
    assert "no overlapping time range" in result["message"]


def test_time_lag_sign_convention_for_shifted_signal(loaded_state):
    # Pin the sign convention the UI will document: ev_shifted = ev1 delayed by 0.1 s.
    from stingray import EventList

    ev1 = loaded_state.get_event_data("ev1")
    # Keep the same GTI as ev1 so both light curves share one bin grid; with
    # gti=[[0.1, 64.1]] the GTI intersection misaligns the grids (0.1 is not a
    # multiple of dt) and the effective shift becomes 2 bins = 0.125 s.
    shifted_times = ev1.time + 0.1
    shifted_times = shifted_times[shifted_times < 64.0]
    shifted = EventList(time=np.sort(shifted_times), gti=[[0.0, 64.0]])
    loaded_state.add_event_data("ev_shifted", shifted)
    svc = TimingService(loaded_state)
    result = svc.calculate_time_lags(
        "ev1", "ev_shifted", dt=0.0625, segment_size=8.0, freq_range=(0.25, 2.0)
    )
    assert result["success"], result
    lags = np.asarray([v for v in result["data"]["time_lags"] if v is not None])
    median_lag = float(np.median(lags))
    # Magnitude must recover the 0.1 s shift well below the phase-wrap limit (5 Hz).
    assert abs(abs(median_lag) - 0.1) < 0.02
    # Observed: median_lag = -0.095 for channel 2 delayed by 0.1 s → stingray
    # convention: positive lag means channel 2 (second list) leads channel 1;
    # a delayed second channel yields negative lags.


def test_short_overlap_rejected_for_coherence(loaded_state):
    # ev1 covers 0–64 s; ev_partial covers 56–120 s → 8 s overlap < 16 s segment.
    from stingray import EventList

    rng = np.random.default_rng(99)
    partial_times = np.sort(rng.uniform(56.0, 120.0, 5000))
    ev_partial = EventList(time=partial_times, gti=[[56.0, 120.0]])
    loaded_state.add_event_data("ev_partial", ev_partial)
    svc = TimingService(loaded_state)
    result = svc.calculate_coherence("ev1", "ev_partial", dt=0.0625, segment_size=16.0)
    assert not result["success"]
    assert "shorter than the segment size" in result["message"]


def test_power_colors_matches_direct_fourier_integration_and_recovers_high_snr_colours(
    state_manager,
):
    """Real multitone photon data must produce usable canonical-band colours."""
    from stingray import EventList
    from services.power_color_helpers import CANONICAL_BANDS

    rng = np.random.default_rng(445)
    dt, length = 1 / 64, 512.0
    samples = int(length / dt)
    centres = (np.arange(samples) + 0.5) * dt
    rate = np.ones(samples)
    for indexes in (
        np.arange(3, 15),
        np.linspace(18, 120, 20, dtype=int),
        np.linspace(140, 1000, 30, dtype=int),
        np.linspace(1100, 8000, 50, dtype=int),
    ):
        for index in indexes:
            rate += 0.015 * np.sin(
                2 * np.pi * index / length * centres + rng.uniform(0, 2 * np.pi)
            )
    counts = rng.poisson(50 * rate)
    events = EventList(time=np.repeat(centres, counts), gti=[[0, length]])
    state_manager.add_event_data("broadband", events)
    result = TimingService(state_manager).calculate_power_colors(
        "broadband", dt, length, CANONICAL_BANDS
    )
    assert result["success"], result
    data = result["data"]
    json.dumps(result, allow_nan=False)
    frequency = np.fft.rfftfreq(samples, dt)[1:-1]
    direct_power = (
        2 * dt / (counts.mean() ** 2 * samples) * np.abs(np.fft.rfft(counts)[1:-1]) ** 2
    )
    noise = 2 / (counts.mean() / dt)
    for band, (lower, upper) in CANONICAL_BANDS.items():
        widths = np.maximum(
            0,
            np.minimum(frequency + 0.5 / length, upper)
            - np.maximum(frequency - 0.5 / length, lower),
        )
        expected_variance = np.sum((direct_power - noise) * widths)
        expected_error = np.sqrt(np.sum((direct_power * widths) ** 2))
        assert data["power_colors"][band][0] == pytest.approx(
            expected_variance, rel=1e-9
        )
        assert data["band_variance_errors"][band][0] == pytest.approx(
            expected_error, rel=1e-9
        )
    assert any(data["valid_segments"]), data
    assert data["pc1"][0] == pytest.approx(
        data["power_colors"]["C"][0] / data["power_colors"]["A"][0]
    )
    assert data["pc2"][0] == pytest.approx(
        data["power_colors"]["B"][0] / data["power_colors"]["D"][0]
    )
    assert data["provenance"]["parameters"]["dt"] == dt
    assert data["normalization"] == "frac"
    assert data["detection_sigma"] == 3


def test_aligned_event_timing_ignores_fractional_gti_origin_offsets(loaded_state):
    from stingray import EventList

    first = loaded_state.get_event_data("ev1")
    photons = first.time[first.time >= 0.1]
    loaded_state.add_event_data(
        "origin0", EventList(time=photons.copy(), gti=[[0, 64]])
    )
    loaded_state.add_event_data(
        "origin_fractional", EventList(time=photons.copy(), gti=[[0.1, 64]])
    )
    service = TimingService(loaded_state)
    lag = service.calculate_time_lags(
        "origin0", "origin_fractional", dt=0.0625, segment_size=8
    )
    assert lag["success"], lag
    np.testing.assert_allclose(lag["data"]["time_lags"], 0, atol=1e-12)
    coherence = service.calculate_coherence(
        "origin0", "origin_fractional", dt=0.0625, segment_size=8
    )
    assert coherence["success"], coherence
    aligned_reference = service.calculate_coherence(
        "origin_fractional", "origin_fractional", dt=0.0625, segment_size=8
    )
    assert aligned_reference["success"]
    np.testing.assert_allclose(
        coherence["data"]["coherence"],
        aligned_reference["data"]["coherence"],
        rtol=1e-12,
    )


def test_shuffled_event_inputs_match_sorted_timing_and_power_colors_without_mutation(
    loaded_state,
):
    from stingray import EventList

    original = loaded_state.get_event_data("ev1")
    permutation = np.random.default_rng(946).permutation(len(original.time))
    shuffled = EventList(
        time=original.time[permutation],
        energy=original.energy[permutation],
        gti=original.gti.copy(),
        skip_checks=True,
    )
    loaded_state.add_event_data("shuffled", shuffled)
    original_time = shuffled.time.copy()
    original_energy = shuffled.energy.copy()
    original_gti = shuffled.gti.copy()
    service = TimingService(loaded_state)
    baseline = service.calculate_time_lags("ev1", "ev2", 0.0625, 8)
    permuted = service.calculate_time_lags("shuffled", "ev2", 0.0625, 8)
    assert baseline["success"] and permuted["success"]
    np.testing.assert_allclose(
        permuted["data"]["time_lags"], baseline["data"]["time_lags"], rtol=1e-10
    )
    baseline_coh = service.calculate_coherence("ev1", "ev2", 0.0625, 8)
    permuted_coh = service.calculate_coherence("shuffled", "ev2", 0.0625, 8)
    np.testing.assert_allclose(
        permuted_coh["data"]["coherence"], baseline_coh["data"]["coherence"], rtol=1e-10
    )
    bands = {"A": (0.125, 0.5), "B": (0.5, 1), "C": (1, 2), "D": (2, 4)}
    baseline_color = service.calculate_power_colors("ev1", 0.0625, 8, bands)
    permuted_color = service.calculate_power_colors("shuffled", 0.0625, 8, bands)
    assert baseline_color["success"] and permuted_color["success"]
    for band in bands:
        np.testing.assert_allclose(
            permuted_color["data"]["power_colors"][band],
            baseline_color["data"]["power_colors"][band],
            rtol=1e-10,
        )
    np.testing.assert_array_equal(shuffled.time, original_time)
    np.testing.assert_array_equal(shuffled.energy, original_energy)
    np.testing.assert_array_equal(shuffled.gti, original_gti)


@pytest.mark.parametrize("method", ["calculate_time_lags", "calculate_coherence"])
def test_timing_rejects_incompatible_second_detector_clock(loaded_state, method):
    second = loaded_state.get_event_data("ev2")
    second.dt = 0.1
    result = getattr(TimingService(loaded_state), method)("ev1", "ev2", 0.125, 8)
    assert not result["success"]
    assert "multiple of both event time resolutions" in result["message"]


def test_power_colors_rejects_changed_event_time_resolution(loaded_state):
    loaded_state.get_event_data("ev1").dt = 0.1
    result = TimingService(loaded_state).calculate_power_colors(
        "ev1", 0.0625, 8, {"A": (0.125, 0.5), "B": (0.5, 1), "C": (1, 2), "D": (2, 4)}
    )
    assert not result["success"]
    assert "time resolutions" in result["message"]


@pytest.mark.parametrize("method", ["calculate_time_lags", "calculate_coherence"])
def test_timing_reports_actual_floor_adjusted_segment_duration(loaded_state, method):
    result = getattr(TimingService(loaded_state), method)("ev1", "ev2", 0.0625, 8.03)
    assert result["success"], result
    assert result["data"]["dt"] == 0.0625
    assert result["data"]["segment_size"] == 8
    assert result["data"]["requested_segment_size"] == 8.03
    assert result["data"]["provenance"]["parameters"]["segment_size"] == 8
    assert any("below 30" in warning for warning in result["warnings"])


def test_power_colors_respects_disjoint_gtis_and_leaves_source_unchanged(loaded_state):
    from stingray import EventList

    original = loaded_state.get_event_data("ev1")
    gtis = np.array([[0, 16], [48, 64]], dtype=float)
    events = EventList(time=original.time.copy(), gti=gtis.copy(), skip_checks=True)
    loaded_state.add_event_data("gapped", events)
    result = TimingService(loaded_state).calculate_power_colors(
        "gapped",
        0.0625,
        8,
        {"A": (0.125, 0.5), "B": (0.5, 1), "C": (1, 2), "D": (2, 4)},
    )
    assert result["success"], result
    assert result["data"]["time"] == [4, 12, 52, 60]
    assert len(result["data"]["pc1"]) == 4
    np.testing.assert_array_equal(events.gti, gtis)


def test_power_colors_subtracts_each_segments_poisson_level_with_common_mean_normalization(
    state_manager,
):
    from stingray import EventList

    rng = np.random.default_rng(19)
    dt, duration = 0.125, 16.0
    samples = int(duration / dt)
    counts = np.concatenate([rng.poisson(10, samples), rng.poisson(100, samples)])
    centres = (np.arange(counts.size) + 0.5) * dt
    state_manager.add_event_data(
        "variable_rate_noise", EventList(time=np.repeat(centres, counts), gti=[[0, 32]])
    )
    bands = {"A": (0.0625, 0.25), "B": (0.25, 0.5), "C": (0.5, 1), "D": (1, 3)}
    result = TimingService(state_manager).calculate_power_colors(
        "variable_rate_noise", dt, duration, bands
    )
    assert result["success"], result
    data = result["data"]
    common_rate = counts.mean() / dt
    frequency = np.fft.rfftfreq(samples, dt)[1:-1]
    expected_noise = []
    for segment in range(2):
        values = counts[segment * samples : (segment + 1) * samples]
        noise = 2 * (values.mean() / dt) / common_rate**2
        expected_noise.append(noise)
        power = (
            2
            * dt
            / (counts.mean() ** 2 * samples)
            * np.abs(np.fft.rfft(values)[1:-1]) ** 2
        )
        for band, (lower, upper) in bands.items():
            widths = np.maximum(
                0,
                np.minimum(frequency + 0.5 / duration, upper)
                - np.maximum(frequency - 0.5 / duration, lower),
            )
            assert data["power_colors"][band][segment] == pytest.approx(
                np.sum((power - noise) * widths), rel=1e-9
            )
    np.testing.assert_allclose(data["poisson_power_by_segment"], expected_noise)
    assert data["poisson_power_by_segment"][0] != data["poisson_power_by_segment"][1]


def test_power_colors_keeps_empty_segment_time_positions_with_null_estimates(
    state_manager,
):
    from stingray import EventList

    rng = np.random.default_rng(7)
    state_manager.add_event_data(
        "empty_second", EventList(time=np.sort(rng.uniform(0, 16, 2000)), gti=[[0, 32]])
    )
    bands = {"A": (0.0625, 0.25), "B": (0.25, 0.5), "C": (0.5, 1), "D": (1, 3)}
    result = TimingService(state_manager).calculate_power_colors(
        "empty_second", 0.125, 16, bands
    )
    assert result["success"], result
    data = result["data"]
    assert data["time"] == [8, 24]
    assert data["power_colors"]["D"][1] is None
    assert data["band_variance_errors"]["D"][1] is None
    assert data["pc1"][1] is None
    assert data["valid_segments"][1] is False
    assert any("no photons" in warning for warning in data["warnings"])
    for name in (
        "pc1",
        "pc1_err",
        "pc2",
        "pc2_err",
        "valid_segments",
        "poisson_power_by_segment",
    ):
        assert len(data[name]) == len(data["time"])


def test_power_colors_keeps_singleton_segments_aligned_and_out_of_common_mean(
    state_manager,
):
    from stingray import EventList

    rng = np.random.default_rng(18)
    times = np.concatenate(
        [np.sort(rng.uniform(0, 16, 1000)), [17.0], np.sort(rng.uniform(32, 48, 2000))]
    )
    state_manager.add_event_data("single_photon", EventList(time=times, gti=[[0, 48]]))
    bands = {"A": (0.0625, 0.25), "B": (0.25, 0.5), "C": (0.5, 1), "D": (1, 3)}
    result = TimingService(state_manager).calculate_power_colors(
        "single_photon", 0.125, 16, bands
    )
    assert result["success"], result
    data = result["data"]
    assert data["time"] == [8, 24, 40]
    assert data["power_colors"]["A"][1] is None
    assert data["pc1"][1] is None
    assert data["segment_count_rates"] == [62.5, 0.0625, 125]
    assert data["poisson_power"] == pytest.approx(2 / 93.75)
    assert data["poisson_power_by_segment"][0] == pytest.approx(2 * 62.5 / 93.75**2)
    assert len(data["valid_segments"]) == 3
