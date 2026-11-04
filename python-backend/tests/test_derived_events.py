"""Derived EventLists: filtered, joined, sorted and dead-time-applied copies."""

import json

import httpx
import numpy as np
import pytest
from stingray import EventList

from main import create_app
from models.event_selection import EventSelection
from services.data_service import DataService
from services.derived_events import DerivedEventService
from services.project_service import decode, encode
from services.spectrum_service import SpectrumService
from services.state_manager import StateManager
from tests.backend_auth import TEST_BACKEND_AUTH_HEADERS, TEST_BACKEND_SESSION_SECRET
from tests.conftest import make_event_list


@pytest.fixture
def state():
    manager = StateManager()
    manager.add_event_data("a", make_event_list(1))
    manager.add_event_data("b", make_event_list(2))
    return manager


@pytest.fixture
def service(state):
    return DerivedEventService(state)


def _ok(result):
    assert result["success"], result
    json.dumps(result, allow_nan=False)
    return result["data"]


def _lineage(state, name):
    return state.get_event_data(name).event_lineage


# --- filter --------------------------------------------------------------


def test_filter_stores_a_selected_copy_with_lineage(state, service):
    data = _ok(
        service.derive_filtered(
            "a", EventSelection(energy_range=[2.0, 5.0]), output_name="a 2-5 keV"
        )
    )
    derived = state.get_event_data("a 2-5 keV")
    assert data["name"] == "a 2-5 keV"
    assert data["n_events"] == len(derived.time)
    assert np.all((derived.energy >= 2.0) & (derived.energy < 5.0))
    assert len(state.get_event_data("a").time) == 20000
    lineage = _lineage(state, "a 2-5 keV")
    assert lineage["operation"] == "filter"
    assert lineage["parents"] == [
        {"name": "a", "dataset_id": state.get_event_identity("a"), "n_events": 20000}
    ]
    assert lineage["parameters"]["selection"]["energy_range_kev"] == [2.0, 5.0]
    assert data["lineage"] == lineage


def test_filter_requires_a_selection(service):
    result = service.derive_filtered("a", EventSelection(), output_name="nothing")
    assert result["success"] is False
    assert "selection" in result["message"].lower()


# --- join ----------------------------------------------------------------


def test_join_merges_detectors_into_one_time_ordered_list(state, service):
    data = _ok(
        service.derive_joined(["a", "b"], output_name="FPMA and FPMB", gti_strategy="infer")
    )
    joined = state.get_event_data("FPMA and FPMB")
    assert data["n_events"] == 40000 == len(joined.time)
    assert np.all(np.diff(joined.time) >= 0)
    lineage = _lineage(state, "FPMA and FPMB")
    assert lineage["operation"] == "join"
    assert [parent["name"] for parent in lineage["parents"]] == ["a", "b"]
    assert lineage["parameters"] == {"gti_strategy": "infer"}


def test_join_needs_two_distinct_lists(service):
    result = service.derive_joined(["a", "a"], output_name="twice")
    assert result["success"] is False
    assert "two different" in result["message"]


# --- sort ----------------------------------------------------------------


def test_sort_orders_photons_and_keeps_their_columns(state, service):
    rng = np.random.default_rng(5)
    times = rng.uniform(0, 10, 500)
    energy = times * 2
    state.add_event_data(
        "shuffled", EventList(time=times, energy=energy, gti=[[0.0, 10.0]])
    )
    _ok(service.derive_sorted("shuffled", output_name="sorted"))
    ordered = state.get_event_data("sorted")
    assert np.all(np.diff(ordered.time) >= 0)
    np.testing.assert_allclose(ordered.energy, ordered.time * 2)
    assert _lineage(state, "sorted")["operation"] == "sort"


# --- dead time -----------------------------------------------------------


@pytest.mark.parametrize("paralyzable", [False, True])
def test_dead_time_removes_photons_inside_the_dead_window(state, service, paralyzable):
    data = _ok(
        service.derive_deadtime(
            "a", dead_time=0.01, paralyzable=paralyzable, output_name="dead"
        )
    )
    dead = state.get_event_data("dead")
    assert 0 < data["n_events"] == len(dead.time) < 20000
    assert np.min(np.diff(dead.time)) >= 0.01 or paralyzable
    lineage = _lineage(state, "dead")
    assert lineage["operation"] == "apply_deadtime"
    assert lineage["parameters"] == {
        "dead_time": 0.01,
        "paralyzable": paralyzable,
        "dt_sigma": None,
    }


# --- shared behaviour ----------------------------------------------------


def test_existing_names_and_invalid_names_are_rejected(service):
    taken = service.derive_sorted("a", output_name="b")
    assert taken["success"] is False and "already exists" in taken["message"]
    invalid = service.derive_sorted("a", output_name=" spaced")
    assert invalid["success"] is False and "whitespace" in invalid["message"]


def test_missing_parent_is_reported(service):
    result = service.derive_sorted("missing", output_name="sorted")
    assert result["success"] is False and "not found" in result["message"]


def test_derived_lists_appear_in_pickers_with_lineage(state, service):
    _ok(service.derive_sorted("a", output_name="a sorted"))
    listed = DataService(state).list_event_lists()["data"]
    entry = next(item for item in listed if item["name"] == "a sorted")
    assert entry["lineage"]["operation"] == "sort"
    assert next(item for item in listed if item["name"] == "a")["lineage"] is None


def test_analyses_of_derived_lists_record_their_lineage(state, service):
    _ok(service.derive_sorted("a", output_name="a sorted"))
    result = SpectrumService(state).create_power_spectrum("a sorted", dt=0.125)
    assert result["success"], result
    assert result["data"]["inputs"][0]["lineage"]["operation"] == "sort"


def test_lineage_round_trips_through_the_project_codec(state, service):
    _ok(service.derive_joined(["a", "b"], output_name="joined"))
    restored = decode(encode(state.get_event_data("joined")))
    assert restored.event_lineage == _lineage(state, "joined")


def test_lineage_chains_through_derived_parents(state, service):
    _ok(service.derive_filtered("a", EventSelection(pi_range=None, energy_range=[1, 4]), output_name="soft"))
    _ok(service.derive_sorted("soft", output_name="soft sorted"))
    lineage = _lineage(state, "soft sorted")
    assert lineage["parents"][0]["name"] == "soft"
    assert lineage["parents"][0]["lineage"]["operation"] == "filter"


# --- routes --------------------------------------------------------------


@pytest.fixture
def app(state):
    application = create_app(session_secret=TEST_BACKEND_SESSION_SECRET)
    application.state.state_manager = state
    application.state.performance_monitor = None
    return application


async def _post(app, path, body):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers=TEST_BACKEND_AUTH_HEADERS,
    ) as client:
        return await client.post(path, json=body)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,body",
    [
        (
            "/api/data/derived/filter",
            {"event_list_name": "a", "selection": {"energy_range": [2, 5]}},
        ),
        ("/api/data/derived/join", {"event_list_names": ["a", "b"]}),
        ("/api/data/derived/sort", {"event_list_name": "a"}),
        ("/api/data/derived/deadtime", {"event_list_name": "a", "dead_time": 0.01}),
    ],
)
async def test_derived_routes_store_new_lists(app, state, path, body):
    response = await _post(app, path, {**body, "output_name": "derived"})
    assert response.status_code == 200, response.text
    assert response.json()["success"], response.json()
    assert state.get_event_data("derived").event_lineage["parents"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/data/derived/deadtime", {"event_list_name": "a", "dead_time": 0}),
        ("/api/data/derived/deadtime", {"event_list_name": "a", "dead_time": -1}),
        ("/api/data/derived/join", {"event_list_names": ["a"]}),
        (
            "/api/data/derived/join",
            {"event_list_names": ["a", "b"], "gti_strategy": "guess"},
        ),
        (
            "/api/data/derived/filter",
            {"event_list_name": "a", "selection": {"energy_range": [5, 2]}},
        ),
    ],
)
async def test_derived_routes_reject_invalid_requests(app, path, body):
    response = await _post(app, path, {**body, "output_name": "derived"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_filter_route_reports_inapplicable_selection_as_422(app):
    response = await _post(
        app,
        "/api/data/derived/filter",
        {
            "event_list_name": "a",
            "selection": {"energy_range": [50, 60]},
            "output_name": "empty",
        },
    )
    assert response.status_code == 422
    assert "leaves no events" in response.json()["detail"]


def test_derived_lists_and_selected_results_survive_a_saved_project(
    tmp_path, monkeypatch, state, service
):
    from services.project_service import ProjectService
    from tests.test_io_utility_service import TEST_SECRET, make_grant

    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    _ok(service.derive_filtered("a", EventSelection(energy_range=[2, 5]), "a mid"))
    _ok(service.derive_joined(["a mid", "b"], output_name="joined"))
    spectrum = SpectrumService(state).create_power_spectrum(
        "a",
        dt=0.125,
        output_name="soft pds",
        selection=EventSelection(energy_range=[0.5, 2.0]),
    )
    assert spectrum["success"], spectrum

    path = tmp_path / "selection.srproj"
    saved = ProjectService(state_manager=state).save(
        str(path), make_grant(path, "write"), {}, None
    )
    assert saved["success"], saved
    target = StateManager()
    opened = ProjectService(state_manager=target).reopen(
        str(path), make_grant(path, "read")
    )
    assert opened["success"], opened

    for name in ("a mid", "joined"):
        assert target.get_event_data(name).event_lineage == _lineage(state, name)
        assert target.get_event_identity(name) == state.get_event_identity(name)
    joined_parents = target.get_event_data("joined").event_lineage["parents"]
    assert joined_parents[0]["lineage"]["operation"] == "filter"
    identity = target.get_spectrum_data("soft pds").result_identity
    assert identity["inputs"][0]["selection"]["energy_range_kev"] == [0.5, 2.0]
