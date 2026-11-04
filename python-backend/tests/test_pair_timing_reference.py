"""Physical-time and exposure preflight for paired scientific analyses."""

import copy

import numpy as np
import pytest
from stingray import EventList

from services.analysis_helpers import (
    analysis_event_copy,
    common_gtis,
    event_gtis,
    overlap_error,
    pair_binning_error,
)
from services.spectrum_service import SpectrumService


def events(**metadata):
    return EventList(
        time=np.linspace(0.1, 63.9, 1000),
        gti=[[0.0, 64.0]],
        **metadata,
    )


@pytest.mark.parametrize(
    "field,first,second",
    [
        ("mjdref", 55000.0, 55001.0),
        ("timesys", "tt", "tdb"),
        ("timeref", "local", "solarsystem"),
        ("ephem", "de200", "de430"),
    ],
)
def test_same_numeric_times_do_not_establish_physical_compatibility(
    field, first, second
):
    left, right = events(), events()
    setattr(left, field, first)
    setattr(right, field, second)
    message = overlap_error(left, right)
    assert message is not None
    assert field.upper() in message


@pytest.mark.parametrize(
    "field,value",
    [("mjdref", 55000.0), ("timesys", "tt"), ("timeref", "local"), ("ephem", "de430")],
)
def test_known_reference_on_only_one_input_is_rejected(field, value):
    left, right = events(), events()
    setattr(left, field, value)
    setattr(right, field, None)
    message = overlap_error(left, right)
    assert message is not None
    assert field.upper() in message
    assert "only one" in message


@pytest.mark.parametrize(
    "field,value",
    [
        ("mjdref", np.nan),
        ("mjdref", np.inf),
        ("mjdref", [55000.0]),
        ("timesys", "not-a-time-scale"),
        ("timesys", ["tt"]),
        ("timeref", "unknown-coordinate-frame"),
        ("ephem", "not-an-ephemeris"),
    ],
)
def test_malformed_or_unsupported_reference_is_not_assumed_compatible(field, value):
    left, right = events(), events()
    setattr(left, field, value)
    setattr(right, field, copy.deepcopy(value))
    message = overlap_error(left, right)
    assert message is not None
    assert field.upper() in message


def test_equivalent_metadata_spelling_is_accepted_without_mutation():
    left = events(
        mjdref=55000.0, timesys=" TT ", timeref="SOLARSYSTEM", ephem="JPL-DE430"
    )
    right = events(mjdref=55000.0, timesys="tt", timeref="solarsystem", ephem="de430")
    snapshots = [copy.deepcopy(vars(value)) for value in (left, right)]
    assert overlap_error(left, right, segment_size=64.0) is None
    for value, snapshot in zip((left, right), snapshots):
        assert vars(value).keys() == snapshot.keys()
        for key in snapshot:
            if isinstance(snapshot[key], np.ndarray):
                np.testing.assert_array_equal(vars(value)[key], snapshot[key])
            else:
                assert vars(value)[key] == snapshot[key]


def test_synthetic_defaults_and_both_unknown_metadata_remain_compatible():
    left, right = events(), events()
    assert overlap_error(left, right) is None
    left.mjdref = right.mjdref = None
    assert overlap_error(left, right) is None


def test_unsorted_arrays_use_true_bounds_without_creating_lazy_gtis():
    left = EventList(time=[9.0, 0.0, 10.0, 1.0], skip_checks=True)
    right = EventList(time=[2.0, 3.0, 4.0], skip_checks=True)
    assert left._gti is None and right._gti is None
    assert overlap_error(left, right, segment_size=2.0) is None
    assert left._gti is None and right._gti is None
    np.testing.assert_array_equal(left.time, [9.0, 0.0, 10.0, 1.0])


def test_disjoint_gtis_rejected_even_when_photon_spans_overlap():
    left, right = events(), events()
    left.gti = [[0.0, 10.0], [30.0, 40.0]]
    right.gti = [[10.0, 20.0], [40.0, 50.0]]
    message = overlap_error(left, right)
    assert message is not None
    assert "no overlapping" in message
    assert "good-time" in message


def test_segment_must_fit_one_common_gti_not_total_span_or_exposure():
    left, right = events(), events()
    left.gti = [[0.0, 10.0], [30.0, 50.0]]
    right.gti = [[5.0, 15.0], [40.0, 60.0]]
    assert overlap_error(left, right, segment_size=10.0) is None
    message = overlap_error(left, right, segment_size=12.0)
    assert message is not None
    assert "shorter than the segment size" in message


@pytest.mark.parametrize(
    "gti",
    [
        [],
        [[1.0]],
        [[5.0, 4.0]],
        [[1.0, 1.0]],
        [[0.0, np.inf]],
        [[5.0, 8.0], [1.0, 3.0]],
        [[0.0, 5.0], [4.0, 8.0]],
    ],
)
def test_invalid_gtis_fail_preflight(gti):
    left, right = events(), events()
    left.gti = gti
    message = overlap_error(left, right)
    assert message is not None
    assert "GTI" in message


@pytest.mark.parametrize("times", [[0.0, np.nan], [0.0, np.inf], [[0.0, 1.0]]])
def test_invalid_time_arrays_fail_preflight(times):
    left, right = events(), events()
    left._time = np.asarray(times)
    message = overlap_error(left, right)
    assert message is not None
    assert "time" in message.lower()


@pytest.mark.parametrize(
    "method", ["create_cross_spectrum", "create_averaged_cross_spectrum"]
)
def test_cross_spectrum_rejects_different_days_before_publishing(state_manager, method):
    state_manager.add_event_data("left", events(mjdref=55000.0))
    state_manager.add_event_data("right", events(mjdref=55001.0))
    arguments = dict(
        event_list_1_name="left", event_list_2_name="right", dt=0.125, output_name="bad"
    )
    if method == "create_averaged_cross_spectrum":
        arguments["segment_size"] = 8.0
    result = getattr(SpectrumService(state_manager), method)(**arguments)
    assert not result["success"]
    assert "MJDREF" in result["message"]
    assert state_manager.get_spectrum_data("bad") is None


def test_averaged_cross_uses_one_grid_for_noninteger_gti_start_offset(state_manager):
    rng = np.random.default_rng(123)
    photons = np.sort(rng.uniform(0.1, 63.9, 10000))
    left = EventList(time=photons, gti=[[0.0, 64.0]])
    right = EventList(time=photons, gti=[[0.1, 64.0]])
    state_manager.add_event_data("left", left)
    state_manager.add_event_data("right", right)
    result = SpectrumService(state_manager).create_averaged_cross_spectrum(
        "left", "right", dt=0.0625, segment_size=8.0
    )
    assert result["success"], result
    np.testing.assert_allclose(result["data"]["power_phase"], 0.0, atol=1e-14)
    np.testing.assert_array_equal(left.gti, [[0.0, 64.0]])
    np.testing.assert_array_equal(right.gti, [[0.1, 64.0]])


def test_averaged_cross_is_invariant_to_event_order_and_preserves_parents(
    state_manager,
):
    rng = np.random.default_rng(123)
    photons = np.sort(rng.uniform(0.0, 64.0, 10000))
    order = rng.permutation(len(photons))
    sorted_events = EventList(time=photons, gti=[[0.0, 64.0]], energy=photons + 1)
    shuffled = EventList(
        time=photons[order],
        gti=[[0.0, 64.0]],
        energy=(photons + 1)[order],
        skip_checks=True,
    )
    state_manager.add_event_data("sorted", sorted_events)
    state_manager.add_event_data("shuffled", shuffled)
    service = SpectrumService(state_manager)
    reference = service.create_averaged_cross_spectrum(
        "sorted", "sorted", dt=0.125, segment_size=8.0
    )
    permuted = service.create_averaged_cross_spectrum(
        "shuffled", "sorted", dt=0.125, segment_size=8.0
    )
    assert reference["success"] and permuted["success"], (reference, permuted)
    np.testing.assert_allclose(permuted["data"]["power"], reference["data"]["power"])
    np.testing.assert_allclose(permuted["data"]["power_phase"], 0.0, atol=1e-14)
    np.testing.assert_array_equal(shuffled.time, photons[order])
    np.testing.assert_array_equal(shuffled.energy, (photons + 1)[order])


@pytest.mark.parametrize("resolutions", [(0.1, 0.0), (0.0, 0.1), (0.1, 0.03)])
def test_cross_spectrum_rejects_bin_width_incompatible_with_either_clock(
    state_manager, resolutions
):
    for name, resolution in zip(("left", "right"), resolutions):
        state_manager.add_event_data(name, events(dt=resolution))
    result = SpectrumService(state_manager).create_averaged_cross_spectrum(
        "left", "right", dt=0.125, segment_size=8.0, output_name="bad"
    )
    assert not result["success"]
    assert "time resolutions" in result["message"]
    assert state_manager.get_spectrum_data("bad") is None


def test_cross_spectrum_reports_effective_segment_length(state_manager):
    state_manager.add_event_data("left", events())
    result = SpectrumService(state_manager).create_averaged_cross_spectrum(
        "left", "left", dt=0.125, segment_size=8.03
    )
    assert result["success"], result
    data = result["data"]
    assert data["dt"] == 0.125
    assert data["segment_size"] == pytest.approx(1 / data["df"])
    assert data["segment_size"] != 8.03
    assert data["requested_segment_size"] == 8.03


def test_touching_gtis_describe_continuous_exposure_but_positive_gaps_do_not():
    left, right = events(), events()
    left.gti = [[0.0, 5.0], [5.0, 10.0], [10.001, 20.0]]
    right.gti = [[0.0, 20.0]]
    np.testing.assert_array_equal(
        common_gtis(left, right), [[0.0, 10.0], [10.001, 20.0]]
    )
    assert overlap_error(left, right, segment_size=10.0) is None
    assert overlap_error(left, right, segment_size=10.01) is not None
    np.testing.assert_array_equal(left.gti, [[0.0, 5.0], [5.0, 10.0], [10.001, 20.0]])


def test_analysis_copy_sorts_all_event_columns_stably_without_materializing_parent_gti():
    original = EventList(
        time=[2.0, 0.0, 1.0, 1.0],
        energy=[20.0, 0.0, 10.0, 11.0],
        pi=[200, 0, 100, 101],
        detector_id=[2, 0, 1, 3],
        mjdref=55000,
        timesys="tdb",
        timeref="solarsystem",
        ephem="de430",
        dt=0.1,
        skip_checks=True,
    )
    assert original._gti is None
    detached = analysis_event_copy(original)
    np.testing.assert_array_equal(detached.time, [0.0, 1.0, 1.0, 2.0])
    np.testing.assert_array_equal(detached.energy, [0.0, 10.0, 11.0, 20.0])
    np.testing.assert_array_equal(detached.pi, [0, 100, 101, 200])
    np.testing.assert_array_equal(detached.detector_id, [0, 1, 3, 2])
    assert detached.dt == original.dt
    assert detached.mjdref == original.mjdref
    assert detached.timesys == original.timesys
    assert detached.timeref == original.timeref
    assert detached.ephem == original.ephem
    assert original._gti is None
    np.testing.assert_array_equal(original.time, [2.0, 0.0, 1.0, 1.0])
    detached.gti[0, 0] = -100
    assert original._gti is None


def test_gtis_are_detached_even_for_sorted_events():
    original = events()
    intervals = event_gtis(original)
    intervals[0, 0] = -100
    np.testing.assert_array_equal(original.gti, [[0.0, 64.0]])
    detached = analysis_event_copy(original)
    detached.gti[0, 0] = -50
    np.testing.assert_array_equal(original.gti, [[0.0, 64.0]])


@pytest.mark.parametrize("dt", [0.0, -1.0, np.nan, np.inf, [1.0], "0.1"])
def test_invalid_pair_bin_width_rejected(dt):
    assert pair_binning_error(events(), events(), dt) is not None


def test_pair_binning_accepts_a_requested_multiple_of_both_clocks():
    assert pair_binning_error(events(dt=0.1), events(dt=0.03), 0.3) is None


def test_epoch_comparison_does_not_round_away_input_precision():
    left, right = events(), events()
    left.mjdref = np.longdouble(55000)
    right.mjdref = np.nextafter(left.mjdref, np.longdouble(np.inf))
    assert overlap_error(left, right) is not None
