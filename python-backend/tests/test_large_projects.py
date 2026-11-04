"""Real ZIP64 round trips crossing the former 128 MiB project limit."""

import json
import zipfile

import numpy as np
import pytest
import stingray
from stingray import EventList
from services.project_service import ProjectService, SCHEMA, encode
from services.state_manager import StateManager
from tests.test_io_utility_service import TEST_SECRET, make_grant


def test_large_session_roundtrip_preserves_arrays_results_and_workspace(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    state = StateManager()
    # One input array alone exceeds the previous cap; all data are actually written.
    times = np.arange(17_000_000, dtype=np.float64)
    state.add_event_data(
        "large", EventList(time=times, gti=[[0, 17_000_000]], skip_checks=True)
    )
    state.add_analysis_result(
        "complex",
        {
            "values": np.array([1 + 2j, 3 - 4j]),
            "provenance": {"original_input": state.get_event_identity("large")},
        },
    )
    renderer = {
        "analysis": {
            "result": {"power": [1, 2]},
            "resultInputs": {"name": "large"},
            "stale": False,
        }
    }
    workspace = {"version": 1, "fields": {"draft": "unfinished."}}
    path = tmp_path / "large.srproj"
    saved = ProjectService(state_manager=state).save(
        str(path), make_grant(path, "write"), renderer, workspace
    )
    assert saved["success"], saved
    assert path.stat().st_size > 128 * 1024**2
    assert saved["data"]["bytes"] == path.stat().st_size
    target = StateManager()
    opened = ProjectService(state_manager=target).reopen(
        str(path), make_grant(path, "read")
    )
    assert opened["success"], opened
    np.testing.assert_array_equal(target.get_event_data("large").time, times)
    np.testing.assert_array_equal(
        target.get_analysis_result("complex")["values"], [1 + 2j, 3 - 4j]
    )
    assert target.get_event_identity("large") == state.get_event_identity("large")
    assert opened["data"]["renderer"] == renderer
    assert opened["data"]["workspace"] == workspace


def make_project(tmp_path, monkeypatch):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    state = StateManager()
    state.add_event_data("input", EventList(time=[1.0, 2.0, 3.0], gti=[[0, 4]]))
    path = tmp_path / "source.srproj"
    result = ProjectService(state_manager=state).save(
        str(path), make_grant(path, "write"), {}
    )
    assert result["success"], result
    return path


@pytest.mark.parametrize("corruption", ["checksum", "missing", "shape", "duplicate"])
def test_corrupt_archives_do_not_publish_partial_state(
    tmp_path, monkeypatch, corruption
):
    original = make_project(tmp_path, monkeypatch)
    path = tmp_path / "corrupt.srproj"
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(path, "w") as target:
        names = source.namelist()
        array = next(
            name
            for name in names
            if name.endswith(".npy") and b"(3,)" in source.read(name)
        )
        for name in names:
            value = source.read(name)
            if name == array:
                if corruption == "missing":
                    continue
                if corruption == "checksum":
                    value = value[:-1] + bytes([value[-1] ^ 1])
                if corruption == "shape":
                    value = value.replace(b"(3,)", b"(9,)", 1)
            target.writestr(name, value)
        if corruption == "duplicate":
            target.writestr(array, source.read(array))
    state = StateManager()
    state.add_analysis_result("keep", {"value": 42})
    opened = ProjectService(state_manager=state).reopen(
        str(path), make_grant(path, "read")
    )
    assert not opened["success"]
    assert state.list_event_names() == []
    assert state.get_analysis_result("keep") == {"value": 42}


def test_original_json_projects_remain_readable(tmp_path, monkeypatch):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    state = StateManager()
    state.add_event_data("legacy", EventList(time=[1.0, 2.0], gti=[[0, 3]]))
    payload = {
        "schema": SCHEMA,
        "stingray_version": stingray.__version__,
        "state": encode(
            {
                group: getattr(state, "_" + group)
                for group in (
                    "event_data",
                    "lightcurve_data",
                    "spectrum_data",
                    "analysis_results",
                )
            }
        ),
        "event_ids": state._event_identities,
        "lightcurve_ids": {},
        "renderer": encode({}),
    }
    path = tmp_path / "legacy.srproj"
    path.write_text(json.dumps(payload))
    restored = StateManager()
    result = ProjectService(state_manager=restored).reopen(
        str(path), make_grant(path, "read")
    )
    assert result["success"], result
    np.testing.assert_array_equal(restored.get_event_data("legacy").time, [1, 2])


def test_memory_preflight_rejects_before_array_allocation(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from services import project_archive

    path = make_project(tmp_path, monkeypatch)
    monkeypatch.setattr(
        project_archive.psutil, "virtual_memory", lambda: SimpleNamespace(available=1)
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Arrays must not be allocated before the memory preflight")

    monkeypatch.setattr(project_archive.np.lib.format, "read_array", forbidden)
    state = StateManager()
    result = ProjectService(state_manager=state).reopen(
        str(path), make_grant(path, "read")
    )
    assert not result["success"]
    assert "memory" in result["error"].lower()
    assert state.list_event_names() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("declared", [True, False])
async def test_larger_metadata_body_allowance_applies_only_to_project_save(declared):
    from main import RequestBodyLimitMiddleware

    async def app(scope, receive, send):
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = RequestBodyLimitMiddleware(app, max_body_size=8, project_body_size=64)
    for path, size, expected in [
        ("/api/projects/save", 32, 200),
        ("/api/projects/save", 65, 413),
        ("/api/data/load", 32, 413),
    ]:
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"x" * size, "more_body": False}

        async def send(message):
            messages.append(message)

        await middleware(
            {
                "type": "http",
                "path": path,
                "method": "POST",
                "headers": [(b"content-length", str(size).encode())]
                if declared
                else [],
            },
            receive,
            send,
        )
        assert messages[0]["status"] == expected
