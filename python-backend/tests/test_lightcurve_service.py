import json

import numpy as np
import pytest
from astropy.table import Table
from stingray import EventList

from services.io_utility_service import _table_for_object
from services.lightcurve_service import LightcurveService


def test_decimation_caps_returned_points(loaded_state):
    svc = LightcurveService(loaded_state)
    # 64 s span at dt=0.001 -> 64000 bins; cap at 5000 plot points.
    result = svc.create_lightcurve_from_event_list(
        "ev1", dt=0.001, output_name="lc_fine", max_points=5000
    )
    assert result["success"], result
    json.dumps(result, allow_nan=False)
    data = result["data"]
    assert data["n_bins"] == 64000  # true resolution is reported
    assert len(data["time"]) <= 5000  # transferred arrays are capped
    assert data["plot_stride"] == 13  # ceil(64000 / 5000)
    assert len(data["time"]) == len(data["counts"])


def test_no_decimation_below_cap(loaded_state):
    svc = LightcurveService(loaded_state)
    result = svc.create_lightcurve_from_event_list(
        "ev1", dt=1.0, output_name="lc_coarse"
    )
    assert result["success"], result
    json.dumps(result, allow_nan=False)
    data = result["data"]
    assert data["plot_stride"] == 1
    assert len(data["time"]) == data["n_bins"]


def test_get_lightcurve_data_decimates(loaded_state):
    svc = LightcurveService(loaded_state)
    svc.create_lightcurve_from_event_list("ev1", dt=0.001, output_name="lc_fine2")
    result = svc.get_lightcurve_data("lc_fine2", max_points=1000)
    assert result["success"], result
    json.dumps(result, allow_nan=False)
    assert len(result["data"]["time"]) <= 1000
    assert result["data"]["plot_stride"] == 64


def test_stats_use_full_resolution_and_zero_disables_decimation(loaded_state):
    svc = LightcurveService(loaded_state)
    decimated = svc.create_lightcurve_from_event_list(
        "ev1", dt=0.001, output_name="lc_stats_a", max_points=1000
    )
    full = svc.get_lightcurve_data("lc_stats_a", max_points=0)
    assert full["data"]["plot_stride"] == 1
    assert len(full["data"]["time"]) == full["data"]["n_bins"]
    # count_rate_mean must come from the FULL arrays, not the decimated payload
    assert decimated["data"]["count_rate_mean"] == (
        sum(full["data"]["counts"]) / (full["data"]["n_bins"] * full["data"]["dt"])
    )


def test_rebin_scales_dt_by_factor(loaded_state):
    svc = LightcurveService(loaded_state)
    svc.create_lightcurve_from_event_list("ev1", dt=0.5, output_name="lc_base")
    result = svc.rebin_lightcurve("lc_base", rebin_factor=2.0, output_name="lc_base_r2")
    assert result["success"], result
    assert result["data"]["dt"] == pytest.approx(1.0)  # 2 x 0.5, factor semantics
    assert "count_rate_mean" in result["data"]


def _counted_events(state_manager, gti=None):
    """Ten one-second bins with known counts 1, 2, ..., 10."""
    times = np.concatenate([np.full(index + 1, index + 0.5) for index in range(10)])
    events = EventList(
        time=times,
        gti=[[0, 10]] if gti is None else gti,
        mjdref=55000,
        timesys="TDB",
        timeref="SOLARSYSTEM",
        ephem="DE430",
        mission="NICER",
        instr="XTI",
    )
    state_manager.add_event_data("counted", events)
    return events


def test_custom_gti_selects_counts_on_original_bin_grid(state_manager):
    events = _counted_events(state_manager)
    original_times = events.time.copy()
    original_gtis = events.gti.copy()
    result = LightcurveService(state_manager).create_lightcurve_from_event_list(
        "counted", dt=1.0, output_name="selected", gti=[[2, 8]]
    )

    assert result["success"], result
    json.dumps(result, allow_nan=False)
    assert result["data"]["time"] == [2.5, 3.5, 4.5, 5.5, 6.5, 7.5]
    assert result["data"]["counts"] == [3, 4, 5, 6, 7, 8]
    selected = state_manager.get_lightcurve_data("selected")
    np.testing.assert_array_equal(selected.gti, [[2, 8]])
    np.testing.assert_array_equal(events.time, original_times)
    np.testing.assert_array_equal(events.gti, original_gtis)
    assert selected.mjdref == events.mjdref
    assert selected.timesys == "TDB"
    assert selected.timeref == "SOLARSYSTEM"
    assert selected.ephem == "DE430"
    assert selected.mission == "NICER"
    assert selected.instr == "XTI"
    assert selected.tstart == 2
    assert selected.tseg == 6


def test_multiple_custom_gtis_remove_gap_bins(state_manager):
    _counted_events(state_manager)
    result = LightcurveService(state_manager).create_lightcurve_from_event_list(
        "counted", dt=1.0, output_name="segments", gti=[[1, 3], [7, 9]]
    )

    assert result["success"], result
    assert result["data"]["time"] == [1.5, 2.5, 7.5, 8.5]
    assert result["data"]["counts"] == [2, 3, 8, 9]
    assert result["data"]["count_rate_mean"] == pytest.approx(5.5)
    np.testing.assert_array_equal(
        state_manager.get_lightcurve_data("segments").gti, [[1, 3], [7, 9]]
    )


def test_custom_gtis_intersect_native_exposure_without_restoring_gap_photons(
    state_manager,
):
    events = _counted_events(state_manager, gti=[[0, 3], [7, 10]])
    result = LightcurveService(state_manager).create_lightcurve_from_event_list(
        "counted", dt=1.0, output_name="intersection", gti=[[-1, 8]]
    )

    assert result["success"], result
    assert result["data"]["time"] == [0.5, 1.5, 2.5, 7.5]
    assert result["data"]["counts"] == [1, 2, 3, 8]
    np.testing.assert_array_equal(
        state_manager.get_lightcurve_data("intersection").gti, [[0, 3], [7, 8]]
    )
    np.testing.assert_array_equal(events.gti, [[0, 3], [7, 10]])


def test_native_gtis_are_applied_when_no_custom_selection_is_supplied(state_manager):
    _counted_events(state_manager, gti=[[0, 2], [8, 10]])
    result = LightcurveService(state_manager).create_lightcurve_from_event_list(
        "counted", dt=1.0, output_name="native"
    )

    assert result["success"], result
    assert result["data"]["time"] == [0.5, 1.5, 8.5, 9.5]
    assert result["data"]["counts"] == [1, 2, 9, 10]


def test_custom_gtis_keep_only_complete_bins_without_boundary_tolerance(state_manager):
    _counted_events(state_manager)
    result = LightcurveService(state_manager).create_lightcurve_from_event_list(
        "counted", dt=1.0, output_name="complete", gti=[[2.0001, 7.9999]]
    )

    assert result["success"], result
    # A bin centred at 2.5 starts before 2.0001, and one centred at 7.5 ends
    # after 7.9999. Neither is wholly observed within the selected interval.
    assert result["data"]["time"] == [3.5, 4.5, 5.5, 6.5]
    assert result["data"]["counts"] == [4, 5, 6, 7]
    selected = state_manager.get_lightcurve_data("complete")
    np.testing.assert_array_equal(selected.gti, [[3, 7]])
    assert selected.exposure == pytest.approx(4)
    assert selected.exposure == pytest.approx(len(selected.time) * selected.dt)


@pytest.mark.parametrize(
    "native, requested, expected_gtis, expected_counts",
    [
        ([[0, 3.1], [7.2, 10.1]], None, [[0, 3], [8, 10]], [1, 2, 3, 9, 10]),
        (
            [[0, 10]],
            [[1.0001, 3.9999], [7.0001, 9.9999]],
            [[2, 3], [8, 9]],
            [3, 9],
        ),
    ],
)
def test_stored_and_exported_gtis_describe_actual_complete_bin_exposure(
    state_manager, tmp_path, native, requested, expected_gtis, expected_counts
):
    events = _counted_events(state_manager, gti=native)
    result = LightcurveService(state_manager).create_lightcurve_from_event_list(
        "counted", dt=1.0, output_name="actual_exposure", gti=requested
    )

    assert result["success"], result
    selected = state_manager.get_lightcurve_data("actual_exposure")
    assert result["data"]["counts"] == expected_counts
    np.testing.assert_array_equal(selected.gti, expected_gtis)
    assert selected.exposure == pytest.approx(len(selected.time) * selected.dt)
    assert sum(selected.counts) / selected.exposure == pytest.approx(
        result["data"]["count_rate_mean"]
    )
    # The maintained export projection must not restore partly covered edges
    # or fill gaps when serializing the light curve's observing exposure.
    table = _table_for_object(selected, "lightcurve")
    path = tmp_path / "selected.ecsv"
    table.write(path, format="ascii.ecsv")
    exported = Table.read(path, format="ascii.ecsv")
    np.testing.assert_array_equal(exported.meta["gti"], expected_gtis)
    metadata = selected.gti_selection
    assert metadata["bin_policy"] == "retain_complete_original_grid_bins"
    if requested is None:
        assert metadata["requested_gti"] is None
    else:
        np.testing.assert_array_equal(
            np.asarray(metadata["requested_gti"], dtype=np.longdouble),
            np.asarray(requested, dtype=np.longdouble),
        )
    np.testing.assert_array_equal(events.gti, native)


def test_gti_edge_photons_follow_half_open_histogram_bins(state_manager):
    state_manager.add_event_data(
        "edges",
        EventList(time=[0.25, 1, 1.5, 2, 2.5, 3, 3.25], gti=[[0, 4]]),
    )
    result = LightcurveService(state_manager).create_lightcurve_from_event_list(
        "edges", dt=1.0, output_name="edge_selection", gti=[[1, 3]]
    )

    assert result["success"], result
    assert result["data"]["time"] == [1.5, 2.5]
    assert result["data"]["counts"] == [2, 2]


def test_missing_native_gtis_are_inferred_without_mutating_parent(state_manager):
    events = EventList(time=[0, 0.5, 1.5, 2.5, 3.5, 4])
    assert events._gti is None
    state_manager.add_event_data("no_gti", events)
    result = LightcurveService(state_manager).create_lightcurve_from_event_list(
        "no_gti", dt=1.0, output_name="inferred", gti=[[1, 3]]
    )

    assert result["success"], result
    assert result["data"]["time"] == [1.5, 2.5]
    assert result["data"]["counts"] == [1, 1]
    assert events._gti is None


def test_result_reports_instrument_compatible_dt(state_manager):
    events = _counted_events(state_manager)
    events.dt = 1.0
    with pytest.warns(UserWarning, match="time resolution"):
        result = LightcurveService(state_manager).create_lightcurve_from_event_list(
            "counted", dt=1.8, output_name="compatible", gti=[[2, 8]]
        )

    assert result["success"], result
    assert result["data"]["dt"] == 2.0
    assert result["data"]["parameters"]["dt"] == 2.0
    assert result["data"]["parameters"]["requested_dt"] == 1.8
    assert result["data"]["time"] == [3, 5, 7]
    assert "dt=2.0s" in result["message"]


def test_invalid_selection_does_not_replace_existing_product(state_manager):
    _counted_events(state_manager)
    service = LightcurveService(state_manager)
    original = service.create_lightcurve_from_event_list(
        "counted", dt=1.0, output_name="retained", gti=[[1, 3]]
    )
    assert original["success"], original
    stored = state_manager.get_lightcurve_data("retained")
    invalid = service.create_lightcurve_from_event_list(
        "counted", dt=1.0, output_name="retained", gti=[[20, 30]]
    )

    assert not invalid["success"], invalid
    assert state_manager.get_lightcurve_data("retained") is stored
    np.testing.assert_array_equal(stored.counts, [2, 3])


@pytest.mark.parametrize(
    "gti, message",
    [
        ([], "non-empty"),
        ([1, 3], "shape"),
        ([[1, 2, 3]], "shape"),
        ([[3, 1]], "start"),
        ([[1, 1]], "start"),
        ([[1, 4], [3, 6]], "overlap"),
        ([[5, 6], [1, 3]], "ordered"),
        ([[float("nan"), 3]], "finite"),
        ([[1, float("inf")]], "finite"),
        ([[20, 30]], "overlap"),
        ([[2.1, 2.9]], "complete"),
    ],
)
def test_invalid_or_empty_gti_selection_is_rejected_without_publication(
    state_manager, gti, message
):
    events = _counted_events(state_manager)
    original_times = events.time.copy()
    original_gtis = events.gti.copy()
    result = LightcurveService(state_manager).create_lightcurve_from_event_list(
        "counted", dt=1.0, output_name="invalid", gti=gti
    )

    assert not result["success"], result
    assert message in (result.get("error") or result.get("message") or "").lower()
    assert not state_manager.has_lightcurve_data("invalid")
    np.testing.assert_array_equal(events.time, original_times)
    np.testing.assert_array_equal(events.gti, original_gtis)


@pytest.mark.parametrize("dt", [0, -1, float("nan"), float("inf")])
def test_invalid_dt_is_rejected_before_binning(state_manager, dt):
    _counted_events(state_manager)
    result = LightcurveService(state_manager).create_lightcurve_from_event_list(
        "counted", dt=dt, output_name="invalid_dt", gti=[[1, 3]]
    )

    assert not result["success"], result
    assert "dt" in (result.get("error") or result.get("message") or "").lower()
    assert not state_manager.has_lightcurve_data("invalid_dt")
