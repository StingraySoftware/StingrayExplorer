"""Event-list summaries keep their insertion identity with the captured photons."""

import copy
from uuid import UUID

import numpy as np
from stingray import EventList

from services.data_service import DataService
from services.state_manager import StateManager


def _events(times, *, explicit_gti=True):
    return EventList(
        time=times,
        energy=np.arange(len(times), dtype=float) + 0.5,
        pi=np.arange(len(times)),
        gti=[[0.0, 20.0]] if explicit_gti else None,
        skip_checks=True,
    )


def _summaries(state):
    result = DataService(state_manager=state).list_event_lists()
    assert result["success"], result
    return result["data"]


def test_summary_dataset_identity_is_stable_and_preserves_existing_fields():
    state = StateManager()
    state.add_event_data("unsorted", _events([3.0, 1.0, 2.0]))
    first = _summaries(state)
    second = _summaries(state)

    assert first == second
    identity = first[0]["dataset_id"]
    assert str(UUID(identity)) == identity
    assert identity == state.get_event_identity("unsorted")
    assert first == [
        {
            "name": "unsorted",
            "dataset_id": identity,
            "n_events": 3,
            "time_range": [1.0, 3.0],
            "has_energy": True,
            "has_pi": True,
            "has_detector_id": False,
            "lineage": None,
            "mission": None,
            "gti_count": 1,
        }
    ]


def test_reusing_a_name_in_the_same_session_changes_its_summary_identity():
    state = StateManager()
    state.add_event_data("observation", _events([1.0, 2.0]))
    original = _summaries(state)[0]
    session = state.session_id
    state.add_event_data("observation", _events([5.0, 6.0, 7.0]))
    replacement = _summaries(state)[0]

    assert state.session_id == session
    assert replacement["name"] == original["name"]
    assert replacement["dataset_id"] != original["dataset_id"]
    assert replacement["dataset_id"] == state.get_event_identity("observation")
    assert replacement["n_events"] == 3
    assert replacement["time_range"] == [5.0, 7.0]


def test_summary_does_not_attach_identity_or_populate_parent_lazy_gti():
    state = StateManager()
    events = _events([3.0, 1.0, 2.0], explicit_gti=False)
    state.add_event_data("observation", events)
    before = copy.deepcopy(vars(events))

    summary = _summaries(state)[0]

    assert summary["dataset_id"] == state.get_event_identity("observation")
    assert summary["gti_count"] == 1
    assert events._gti is None
    assert vars(events).keys() == before.keys()
    for name, value in before.items():
        if isinstance(value, np.ndarray):
            np.testing.assert_array_equal(vars(events)[name], value)
        else:
            assert vars(events)[name] == value


def test_replacement_after_atomic_capture_cannot_relabel_the_captured_photons():
    class ReplacingState(StateManager):
        def copy_event_data_with_identity(self, name):
            captured = super().copy_event_data_with_identity(name)
            self.add_event_data(name, _events([10.0, 11.0, 12.0]))
            return captured

    state = ReplacingState()
    state.add_event_data("observation", _events([1.0, 2.0]))
    original_identity = state.get_event_identity("observation")

    summary = _summaries(state)[0]

    assert summary["dataset_id"] == original_identity
    assert summary["dataset_id"] != state.get_event_identity("observation")
    assert summary["n_events"] == 2
    assert summary["time_range"] == [1.0, 2.0]
    np.testing.assert_array_equal(
        state.get_event_data("observation").time, [10.0, 11.0, 12.0]
    )


def test_a_name_deleted_between_inventory_and_capture_is_skipped():
    class DeletingState(StateManager):
        def list_event_names(self):
            names = super().list_event_names()
            self.remove_event_data("vanishing")
            return names

    state = DeletingState()
    state.add_event_data("vanishing", _events([1.0, 2.0]))
    state.add_event_data("surviving", _events([3.0, 4.0]))

    summaries = _summaries(state)

    assert [entry["name"] for entry in summaries] == ["surviving"]
    assert summaries[0]["dataset_id"] == state.get_event_identity("surviving")
