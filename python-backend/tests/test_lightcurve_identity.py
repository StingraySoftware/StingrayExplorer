"""Stable light-curve handles and immutable calculation records."""

import json

import httpx
import numpy as np
import pytest
from stingray import EventList

from services.lightcurve_service import LightcurveService


def _create(service, name="base", **kwargs):
    response = service.create_lightcurve_from_event_list(
        "ev1", dt=0.5, output_name=name, **kwargs
    )
    assert response["success"], response
    return response["data"]


def test_lightcurve_identity_is_stable_across_create_get_and_list(loaded_state):
    service = LightcurveService(loaded_state)
    created = _create(service, gti=[[2, 10]])
    viewed = service.get_lightcurve_data("base")["data"]
    listed = service.list_lightcurves()["data"][0]

    for payload in (created, viewed, listed):
        json.dumps(payload, allow_nan=False)
        assert payload["result_id"] == loaded_state.get_lightcurve_identity("base")
        assert payload["backend_session_id"] == loaded_state.session_id
        assert payload["inputs"][0]["name"] == "ev1"
        assert payload["inputs"][0]["dataset_id"] == loaded_state.get_event_identity(
            "ev1"
        )
        assert payload["parameters"]["requested_dt"] == 0.5
        assert payload["parameters"]["dt"] == 0.5
        assert payload["parameters"]["gti"] == [[2, 10]]


def test_returned_parameters_and_inputs_do_not_mutate_saved_calculation(loaded_state):
    service = LightcurveService(loaded_state)
    created = _create(service, gti=[[2, 10]])
    original_input_id = created["inputs"][0]["dataset_id"]
    created["inputs"][0]["name"] = "edited in response"
    created["inputs"][0]["timing"]["mjdref"] = "99999"
    created["parameters"]["gti"][0][0] = 8
    created["parameters"]["dt"] = 9
    created["provenance"]["original_parameters"]["dt"] = 10

    assert loaded_state.remove_event_data("ev1")
    loaded_state.add_event_data(
        "ev1", EventList(time=np.arange(0.1, 64, 0.1), gti=[[0, 64]])
    )
    viewed = service.get_lightcurve_data("base")["data"]
    assert viewed["inputs"][0]["name"] == "ev1"
    assert viewed["inputs"][0]["dataset_id"] == original_input_id
    assert viewed["inputs"][0]["dataset_id"] != loaded_state.get_event_identity("ev1")
    assert viewed["inputs"][0]["timing"]["mjdref"] == "0.0"
    assert viewed["parameters"]["dt"] == 0.5
    assert viewed["parameters"]["gti"] == [[2, 10]]
    assert viewed["provenance"]["original_parameters"]["dt"] == 0.5


def test_rebin_rejects_a_deleted_and_reused_name(loaded_state):
    service = LightcurveService(loaded_state)
    old = _create(service)
    assert service.delete_lightcurve("base")["success"]
    replacement = _create(service)
    assert replacement["result_id"] != old["result_id"]

    response = service.rebin_lightcurve(
        "base", 2, "stale_rebin", expected_result_id=old["result_id"]
    )
    assert not response["success"], response
    assert "no longer available" in response["error"]
    assert not loaded_state.has_lightcurve_data("stale_rebin")


def test_rebin_records_parent_and_preserves_original_creation_parameters(loaded_state):
    service = LightcurveService(loaded_state)
    created = _create(service, gti=[[2, 10]])
    rebinned = service.rebin_lightcurve(
        "base", 2, "rebinned", expected_result_id=created["result_id"]
    )
    assert rebinned["success"], rebinned
    data = rebinned["data"]
    assert data["result_id"] != created["result_id"]
    assert data["result_id"] == loaded_state.get_lightcurve_identity("rebinned")
    assert data["parameters"]["rebin_factor"] == 2
    assert data["parameters"]["dt"] == 1
    assert data["provenance"]["parent_result"]["result_id"] == created["result_id"]
    assert data["provenance"]["original_parameters"] == created["parameters"]
    assert data["inputs"] == created["inputs"]
    data["inputs"][0]["name"] = "response edit"
    viewed = service.get_lightcurve_data("rebinned")["data"]
    assert viewed["inputs"][0]["name"] == "ev1"
    np.testing.assert_array_equal(
        loaded_state.get_lightcurve_data("rebinned").gti, [[2, 10]]
    )


def test_rebin_preserves_timing_and_selection_metadata_and_actual_tail_exposure(
    loaded_state,
):
    events = loaded_state.get_event_data("ev1")
    events.timesys = "TDB"
    events.timeref = "SOLARSYSTEM"
    events.ephem = "DE430"
    service = LightcurveService(loaded_state)
    created = _create(service, gti=[[2, 10]])
    response = service.rebin_lightcurve(
        "base", 3, "factor_three", expected_result_id=created["result_id"]
    )

    assert response["success"], response
    stored = loaded_state.get_lightcurve_data("factor_three")
    assert stored.timesys == "TDB"
    assert stored.timeref == "SOLARSYSTEM"
    assert stored.ephem == "DE430"
    np.testing.assert_array_equal(stored.gti, [[2, 9.5]])
    assert stored.exposure == pytest.approx(5 * 1.5)
    assert (
        stored.gti_selection == loaded_state.get_lightcurve_data("base").gti_selection
    )
    assert response["data"]["parameters"]["dt"] == 1.5
    assert (
        response["data"]["provenance"]["original_parameters"] == created["parameters"]
    )


def test_legacy_lightcurve_gets_registry_handle_without_invented_history(state_manager):
    from stingray import Lightcurve

    state_manager.add_lightcurve_data(
        "legacy", Lightcurve([0.5, 1.5, 2.5], [1, 2, 3], dt=1)
    )
    response = LightcurveService(state_manager).get_lightcurve_data("legacy")
    assert response["success"], response
    data = response["data"]
    assert data["result_id"] == state_manager.get_lightcurve_identity("legacy")
    assert data["operation"] == "unrecorded_lightcurve"
    assert data["inputs"] == []
    assert data["parameters"] == {}
    assert data["warnings"]


@pytest.mark.parametrize("operation", ["create", "arrays", "rebin"])
def test_named_lightcurve_products_are_never_silently_replaced(loaded_state, operation):
    service = LightcurveService(loaded_state)
    original = _create(service)
    if operation == "create":
        response = service.create_lightcurve_from_event_list("ev1", 1, "base")
    elif operation == "arrays":
        response = service.create_lightcurve_from_arrays([0.5, 1.5], [9, 10], 1, "base")
    else:
        response = service.rebin_lightcurve("base", 2, "base")
    assert not response["success"], response
    viewed = service.get_lightcurve_data("base")["data"]
    assert viewed["result_id"] == original["result_id"]
    assert viewed["dt"] == 0.5


def test_array_input_record_is_frozen_and_identifies_actual_numeric_inputs(
    state_manager,
):
    service = LightcurveService(state_manager)
    times = [0.5, 1.5, 2.5, 3.5]
    counts = [2, 3, 4, 5]
    created = service.create_lightcurve_from_arrays(times, counts, 1, "arrays")
    assert created["success"], created
    data = created["data"]
    assert data["result_id"] == state_manager.get_lightcurve_identity("arrays")
    assert data["backend_session_id"] == state_manager.session_id
    assert data["operation"] == "lightcurve_from_arrays"
    assert data["inputs"][0]["n_bins"] == 4
    assert len(data["inputs"][0]["time_sha256"]) == 64
    assert len(data["inputs"][0]["counts_sha256"]) == 64
    times[0] = 99
    counts[0] = 999
    viewed = service.get_lightcurve_data("arrays")["data"]
    assert viewed["inputs"] == data["inputs"]
    assert viewed["time"] == [0.5, 1.5, 2.5, 3.5]
    assert viewed["counts"] == [2, 3, 4, 5]


@pytest.mark.asyncio
async def test_rebin_route_enforces_the_expected_result_identity(loaded_state):
    from main import create_app
    from tests.backend_auth import (
        TEST_BACKEND_AUTH_HEADERS,
        TEST_BACKEND_SESSION_SECRET,
    )

    app = create_app(session_secret=TEST_BACKEND_SESSION_SECRET)
    app.state.state_manager = loaded_state
    app.state.performance_monitor = None
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", headers=TEST_BACKEND_AUTH_HEADERS
    ) as client:
        parameters = {"event_list_name": "ev1", "dt": 0.5, "output_name": "route_base"}
        created = (
            await client.post("/api/lightcurve/from-event-list", json=parameters)
        ).json()
        assert created["success"], created
        deleted = (await client.delete("/api/lightcurve/route_base")).json()
        assert deleted["success"], deleted
        replacement = (
            await client.post("/api/lightcurve/from-event-list", json=parameters)
        ).json()
        assert replacement["success"], replacement
        response = await client.post(
            "/api/lightcurve/rebin",
            json={
                "name": "route_base",
                "rebin_factor": 2,
                "output_name": "route_stale",
                "expected_result_id": created["data"]["result_id"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert not data["success"], data
        assert "no longer available" in data["error"]
        assert not loaded_state.has_lightcurve_data("route_stale")
