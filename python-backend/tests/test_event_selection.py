"""EventSelection request model, its application to a detached copy, and lineage."""

from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError
from stingray import EventList

from models.event_selection import EventSelection
from services.event_selection import EventSelectionError, apply_event_selection
from services.project_service import decode, encode
from services.spectrum_products import input_snapshot
from services.state_manager import StateManager

REPOSITORY_DATA = Path(__file__).resolve().parents[2] / "files" / "data"


def _events(**columns):
    times = np.arange(10, dtype=float) + 0.5
    return EventList(time=times, gti=[[0.0, 10.0]], **columns)


# --- request model -------------------------------------------------------


def test_energy_and_pi_ranges_are_mutually_exclusive():
    with pytest.raises(ValidationError, match="energy_range or pi_range"):
        EventSelection(energy_range=[0.5, 2.0], pi_range=[10, 50])


@pytest.mark.parametrize(
    "fields",
    [
        {"energy_range": [2.0, 0.5]},
        {"energy_range": [2.0, 2.0]},
        {"pi_range": [50, 10]},
        {"time_intervals": [[5.0, 1.0]]},
        {"gti": [[3.0, 3.0]]},
    ],
)
def test_inverted_or_empty_ranges_are_rejected(fields):
    with pytest.raises(ValidationError, match="lower bound must be below"):
        EventSelection(**fields)


@pytest.mark.parametrize(
    "fields",
    [
        {"energy_range": [-1.0, 2.0]},
        {"energy_range": [0.5, float("inf")]},
        {"energy_range": [float("nan"), 2.0]},
        {"pi_range": [-1, 10]},
        {"detector_ids": []},
        {"time_intervals": []},
        {"time_intervals": [[0.0, 5.0], [4.0, 8.0]]},
        {"time_intervals": [[6.0, 8.0], [0.0, 5.0]]},
        {"unknown_field": 1},
    ],
)
def test_malformed_selections_are_rejected(fields):
    with pytest.raises(ValidationError):
        EventSelection(**fields)


def test_detector_ids_are_deduplicated_and_sorted():
    assert EventSelection(detector_ids=[3, 1, 3]).detector_ids == [1, 3]


def test_empty_selection_reports_no_criteria():
    assert EventSelection().is_empty()
    assert not EventSelection(pi_range=[0, 10]).is_empty()


# --- application ---------------------------------------------------------


def test_no_selection_returns_the_same_events():
    events = _events(energy=np.linspace(0.5, 9.5, 10))
    assert apply_event_selection(events, None) is events
    assert apply_event_selection(events, EventSelection()) is events


def test_energy_selection_is_half_open_and_leaves_input_untouched():
    events = _events(energy=np.arange(10, dtype=float))
    selected = apply_event_selection(events, EventSelection(energy_range=[2.0, 5.0]))
    np.testing.assert_array_equal(selected.energy, [2.0, 3.0, 4.0])
    np.testing.assert_array_equal(selected.time, [2.5, 3.5, 4.5])
    assert len(events.time) == 10
    assert getattr(events, "event_selection", None) is None


def test_pi_selection_uses_the_pi_column():
    events = _events(pi=np.arange(10), energy=np.arange(10, dtype=float) * 10)
    selected = apply_event_selection(events, EventSelection(pi_range=[3, 6]))
    np.testing.assert_array_equal(selected.pi, [3, 4, 5])
    np.testing.assert_array_equal(selected.energy, [30.0, 40.0, 50.0])


def test_detector_selection_keeps_requested_detectors():
    events = _events(energy=np.ones(10))
    events.detector_id = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2, 0])
    selected = apply_event_selection(events, EventSelection(detector_ids=[0, 2]))
    np.testing.assert_array_equal(selected.detector_id, [0, 2, 0, 2, 0, 2, 0])


def test_time_intervals_and_extra_gti_restrict_events_and_exposure():
    events = _events(energy=np.ones(10))
    selected = apply_event_selection(
        events,
        EventSelection(time_intervals=[[1.0, 6.0]], gti=[[0.0, 3.0], [4.0, 9.0]]),
    )
    np.testing.assert_array_equal(selected.time, [1.5, 2.5, 4.5, 5.5])
    np.testing.assert_array_equal(np.asarray(selected.gti, dtype=float), [[1, 3], [4, 6]])


def test_selection_record_describes_exactly_what_was_applied():
    events = _events(energy=np.arange(10, dtype=float))
    selected = apply_event_selection(
        events, EventSelection(energy_range=[2.0, 5.0], time_intervals=[[0, 4]])
    )
    record = selected.event_selection
    assert record["energy_range_kev"] == [2.0, 5.0]
    assert record["pi_range"] is None
    assert record["time_intervals"] == [[0.0, 4.0]]
    assert record["parent_n_events"] == 10
    assert record["n_events"] == 2
    assert [[float(start), float(stop)] for start, stop in record["effective_gti"]] == [
        [0.0, 4.0]
    ]
    snapshot = input_snapshot("ev", selected, "dataset")
    assert snapshot["selection"] == record
    assert snapshot["n_events"] == 2


def test_selection_keeps_timing_metadata():
    events = _events(energy=np.arange(10, dtype=float))
    events.mjdref = 55000.5
    events.mission = "nustar"
    events.dt = 0.25
    selected = apply_event_selection(events, EventSelection(energy_range=[0, 5]))
    assert selected.mjdref == 55000.5
    assert selected.mission == "nustar"
    assert selected.dt == 0.25


# --- errors --------------------------------------------------------------


def test_energy_cut_without_energy_column_suggests_pi_range():
    events = _events(pi=np.arange(10))
    with pytest.raises(EventSelectionError, match="PI range"):
        apply_event_selection(events, EventSelection(energy_range=[0.5, 2.0]))


def test_pi_cut_without_pi_column_is_reported():
    events = _events(energy=np.arange(10, dtype=float))
    with pytest.raises(EventSelectionError, match="no PI column"):
        apply_event_selection(events, EventSelection(pi_range=[0, 5]))


def test_detector_cut_without_detector_column_is_reported():
    events = _events(energy=np.ones(10))
    with pytest.raises(EventSelectionError, match="no detector ID column"):
        apply_event_selection(events, EventSelection(detector_ids=[0]))


def test_selection_leaving_zero_events_is_reported():
    events = _events(energy=np.arange(10, dtype=float))
    with pytest.raises(EventSelectionError, match="leaves no events"):
        apply_event_selection(events, EventSelection(energy_range=[50.0, 60.0]))


def test_time_selection_outside_the_gtis_is_reported():
    events = _events(energy=np.arange(10, dtype=float))
    with pytest.raises(EventSelectionError, match="does not overlap"):
        apply_event_selection(events, EventSelection(time_intervals=[[20.0, 30.0]]))


# --- state, projects and science -----------------------------------------


def test_state_copy_applies_selection_without_touching_stored_events():
    state = StateManager()
    state.add_event_data("ev", _events(energy=np.arange(10, dtype=float)))
    selected, dataset_id = state.copy_event_data_with_identity(
        "ev", selection=EventSelection(energy_range=[0.0, 3.0])
    )
    assert len(selected.time) == 3
    assert dataset_id == state.get_event_identity("ev")
    assert len(state.get_event_data("ev").time) == 10
    unselected, _ = state.copy_event_data_with_identity("ev")
    assert len(unselected.time) == 10


def test_selection_record_round_trips_through_project_codec():
    events = _events(energy=np.arange(10, dtype=float))
    selected = apply_event_selection(events, EventSelection(energy_range=[1.0, 4.0]))
    restored = decode(encode(selected))
    assert restored.event_selection == selected.event_selection
    np.testing.assert_array_equal(restored.energy, selected.energy)


def _monol():
    return EventList.read(str(REPOSITORY_DATA / "monol_testA.evt"), fmt="ogip")


@pytest.mark.parametrize("edges", [(1.0, 3.0, 10.0, 80.0), (0.0, 5.0, 100.0)])
def test_disjoint_bands_partition_the_union(edges):
    events = _monol()
    union = apply_event_selection(
        events, EventSelection(energy_range=[edges[0], edges[-1]])
    )
    counts = [
        len(
            apply_event_selection(
                events, EventSelection(energy_range=[low, high])
            ).time
        )
        for low, high in zip(edges[:-1], edges[1:])
    ]
    assert sum(counts) == len(union.time)


def test_band_light_curves_sum_to_the_union_light_curve():
    events = _monol()
    soft = apply_event_selection(events, EventSelection(energy_range=[1.0, 5.0]))
    hard = apply_event_selection(events, EventSelection(energy_range=[5.0, 80.0]))
    both = apply_event_selection(events, EventSelection(energy_range=[1.0, 80.0]))
    edges = np.arange(80000000.0, 80001026.0, 8.0)
    soft_lc = np.histogram(soft.time, edges)[0]
    hard_lc = np.histogram(hard.time, edges)[0]
    both_lc = np.histogram(both.time, edges)[0]
    np.testing.assert_array_equal(soft_lc + hard_lc, both_lc)
