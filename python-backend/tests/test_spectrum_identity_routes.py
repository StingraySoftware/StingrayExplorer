"""Registered HTTP workflows retain spectrum identity through export and rebin."""

import json

import httpx
import numpy as np
import pytest
from astropy.table import Table
from stingray import EventList

from main import create_app
from services.state_manager import StateManager
from tests.backend_auth import TEST_BACKEND_AUTH_HEADERS, TEST_BACKEND_SESSION_SECRET
from tests.test_io_utility_service import TEST_SECRET, make_grant


def scientific_app():
    app = create_app(session_secret=TEST_BACKEND_SESSION_SECRET)
    app.state.state_manager = StateManager()
    app.state.performance_monitor = None
    rng = np.random.default_rng(29)
    for name in ("first", "second"):
        app.state.state_manager.add_event_data(
            name,
            EventList(
                time=np.sort(rng.uniform(0.0, 64.0, 5_000)),
                gti=[[0.0, 64.0]],
                mjdref=55000,
                timesys="TDB",
            ),
        )
    return app


def client_for(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers=TEST_BACKEND_AUTH_HEADERS,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,inputs",
    [
        ("power-spectrum", {"event_list_name": "first"}),
        ("averaged-power-spectrum", {"event_list_name": "first", "segment_size": 8}),
        (
            "cross-spectrum",
            {"event_list_1_name": "first", "event_list_2_name": "second"},
        ),
        (
            "averaged-cross-spectrum",
            {
                "event_list_1_name": "first",
                "event_list_2_name": "second",
                "segment_size": 8,
            },
        ),
    ],
)
async def test_created_spectrum_exports_original_inputs_through_registered_routes(
    monkeypatch, tmp_path, path, inputs
):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    app = scientific_app()
    async with client_for(app) as client:
        created_response = await client.post(
            f"/api/spectrum/{path}",
            json={**inputs, "dt": 0.125, "norm": "frac", "output_name": "stored"},
        )
        assert created_response.status_code == 200
        created = created_response.json()
        assert created["success"], created
        original = created["data"]
        assert original["result_id"]
        original_dataset_id = original["inputs"][0]["dataset_id"]

        # Name reuse cannot rewrite the identity or epoch of the saved FFT.
        state = app.state.state_manager
        state.remove_event_data("first")
        state.add_event_data(
            "first", EventList(time=np.linspace(0.1, 63.9, 100), gti=[[0, 64]])
        )
        assert state.get_event_identity("first") != original_dataset_id
        catalog = (await client.get("/api/utilities/io/exportable-objects")).json()
        entry = next(
            item
            for item in catalog["data"]["objects"]
            if item["object_type"] == "spectrum"
        )
        assert entry["result_id"] == original["result_id"]

        destination = tmp_path / f"{path}.ecsv"
        exported_response = await client.post(
            "/api/utilities/io/export",
            json={
                "object_type": "spectrum",
                "object_name": "stored",
                "format": "ecsv",
                "destination_path": str(destination),
                "destination_grant": make_grant(destination, "write"),
                "expected_result_id": original["result_id"],
            },
        )
        assert exported_response.status_code == 200, exported_response.text
        exported = exported_response.json()
        assert exported["success"], exported
        assert exported["data"]["result_id"] == original["result_id"]

    table = Table.read(destination, format="ascii.ecsv")
    assert table.meta["result_id"] == original["result_id"]
    assert table.meta["backend_session_id"] == original["backend_session_id"]
    assert table.meta["inputs"] == original["inputs"]
    assert table.meta["parameters"]["norm"] == "frac"
    assert table["freq"].unit.to_string() == "Hz"
    if "cross" in path:
        values = np.asarray(table["power_real"]) + 1j * np.asarray(table["power_imag"])
        np.testing.assert_allclose(np.abs(values), original["power"])
        np.testing.assert_allclose(np.angle(values), original["power_phase"])
    json.dumps(exported, allow_nan=False)


@pytest.mark.asyncio
async def test_new_backend_rejects_old_result_handles_for_rebin_and_export(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    old_app, replacement_app = scientific_app(), scientific_app()
    async with (
        client_for(old_app) as old_client,
        client_for(replacement_app) as new_client,
    ):
        request = {"event_list_name": "first", "dt": 0.125, "output_name": "same_name"}
        old = (
            await old_client.post("/api/spectrum/power-spectrum", json=request)
        ).json()["data"]
        current = (
            await new_client.post("/api/spectrum/power-spectrum", json=request)
        ).json()["data"]
        assert old["backend_session_id"] != current["backend_session_id"]
        assert old["result_id"] != current["result_id"]

        rebinned = (
            await new_client.post(
                "/api/spectrum/rebin",
                json={
                    "name": "same_name",
                    "rebin_factor": 2,
                    "output_name": "wrong_parent",
                    "expected_result_id": old["result_id"],
                },
            )
        ).json()
        assert not rebinned["success"], rebinned
        assert (
            replacement_app.state.state_manager.get_spectrum_data("wrong_parent")
            is None
        )

        destination = tmp_path / "stale.ecsv"
        exported = (
            await new_client.post(
                "/api/utilities/io/export",
                json={
                    "object_type": "spectrum",
                    "object_name": "same_name",
                    "format": "ecsv",
                    "destination_path": str(destination),
                    "destination_grant": make_grant(destination, "write"),
                    "expected_result_id": old["result_id"],
                },
            )
        ).json()
        assert not exported["success"], exported
        assert not destination.exists()
        assert (
            replacement_app.state.state_manager.get_spectrum_data(
                "same_name"
            ).result_identity["result_id"]
            == current["result_id"]
        )
