"""Long analyses in spawned worker processes: progress, partials, cancel, memory cap."""

import json
import time

import httpx
import numpy as np
import psutil
import pytest

from main import create_app
from services import process_jobs
from services.data_service import DataService
from services.job_manager import JobManager
from services.process_jobs import run_process_job
from services.state_manager import StateManager
from tests.backend_auth import TEST_BACKEND_AUTH_HEADERS, TEST_BACKEND_SESSION_SECRET
from tests.conftest import make_event_list

TARGETS = "tests.process_job_targets"


def _gone(pid, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if psutil.Process(pid).status() == psutil.STATUS_ZOMBIE:
                return True
        except psutil.NoSuchProcess:
            return True
        time.sleep(0.05)
    return False


def test_workers_use_the_spawn_start_method():
    assert process_jobs.CONTEXT.get_start_method() == "spawn"


def test_progress_and_partials_arrive_before_the_result():
    events = []
    outcome = run_process_job(
        f"{TARGETS}:staged",
        {"value": 2},
        on_progress=lambda fraction, message: events.append(("progress", fraction)),
        on_partial=lambda partial: events.append(("partial", partial["step"])),
    )
    assert outcome.status == "completed", outcome
    assert outcome.result == {"done": 4}
    assert [event for event in events if event[0] == "partial"] == [
        ("partial", 0),
        ("partial", 1),
        ("partial", 2),
    ]
    fractions = [value for kind, value in events if kind == "progress"]
    assert fractions == sorted(fractions)


def test_worker_errors_are_reported():
    outcome = run_process_job(f"{TARGETS}:failing", {})
    assert outcome.status == "failed"
    assert outcome.error == "ValueError: bad input"


def test_cancellation_terminates_the_worker_and_its_children():
    seen = {}
    outcome = run_process_job(
        f"{TARGETS}:sleeper_with_child",
        {},
        on_partial=seen.update,
        should_cancel=lambda: "child_pid" in seen,
    )
    assert outcome.status == "cancelled"
    assert _gone(seen["worker_pid"])
    assert _gone(seen["child_pid"])


def test_memory_cap_kills_a_runaway_worker_cleanly():
    started = time.monotonic()
    outcome = run_process_job(
        f"{TARGETS}:runaway", {}, memory_cap_bytes=400 * 1024**2
    )
    assert outcome.status == "memory_exceeded", outcome
    assert "400 MB" in outcome.error
    assert outcome.partials, "the worker started allocating before it was stopped"
    assert _gone(outcome.worker_pid)
    assert time.monotonic() - started < 60


# --- the dynamical power spectrum behind its existing endpoint ------------


@pytest.fixture
def app():
    application = create_app(session_secret=TEST_BACKEND_SESSION_SECRET)
    state = StateManager()
    state.add_event_data("ev", make_event_list(5, n_events=40000, length=256.0))
    application.state.state_manager = state
    application.state.performance_monitor = None
    application.state.job_manager = JobManager(state, DataService(state), max_workers=2)
    yield application
    application.state.job_manager.shutdown()


async def _client(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers=TEST_BACKEND_AUTH_HEADERS,
    )


async def _wait(client, job_id, timeout=120.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = (await client.get(f"/api/jobs/{job_id}")).json()["data"]
        if job["status"] in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish")


BODY = {"event_list_name": "ev", "dt": 0.0625, "segment_size": 4.0, "norm": "frac"}


@pytest.mark.asyncio
async def test_background_dynamical_power_spectrum_matches_the_direct_result(app):
    async with await _client(app) as client:
        direct = (
            await client.post(
                "/api/spectrum/dynamical-power-spectrum",
                json={**BODY, "output_name": "direct"},
            )
        ).json()
        assert direct["success"], direct
        submitted = (
            await client.post(
                "/api/spectrum/dynamical-power-spectrum",
                json={**BODY, "output_name": "background", "background": True},
            )
        ).json()
        assert submitted["success"], submitted
        job = await _wait(client, submitted["data"]["job_id"])
        assert job["status"] == "completed", job
        assert job["type"] == "analysis"
        assert job["result"]["name"] == "background"
        assert job["partial_count"] >= 1

        result = (await client.get(f"/api/jobs/{job['id']}/result")).json()
        assert result["success"], result
        payload = result["data"]
        for key in ("freq", "time", "dyn_ps"):
            np.testing.assert_array_equal(
                np.asarray(payload[key], dtype=float),
                np.asarray(direct["data"][key], dtype=float),
            )
        assert payload["inputs"] == direct["data"]["inputs"]
        assert payload["parameters"]["norm"] == "frac"
        stored = app.state.state_manager.get_spectrum_data("background")
        assert stored.result_identity["result_id"] == payload["result_id"]

        partials = (await client.get(f"/api/jobs/{job['id']}/partials")).json()["data"]
        assert partials[0]["preview"] is True
        assert partials[0]["n_segments"] <= 16
        json.dumps(partials, allow_nan=False)


@pytest.mark.asyncio
async def test_cancelled_background_job_publishes_nothing(app):
    app.state.state_manager.add_event_data(
        "big", make_event_list(6, n_events=400000, length=4096.0)
    )
    async with await _client(app) as client:
        submitted = (
            await client.post(
                "/api/spectrum/dynamical-power-spectrum",
                json={
                    **BODY,
                    "event_list_name": "big",
                    "dt": 0.001,
                    "segment_size": 2.0,
                    "output_name": "cancelled",
                    "background": True,
                },
            )
        ).json()
        job_id = submitted["data"]["job_id"]
        cancel = (await client.post(f"/api/jobs/{job_id}/cancel")).json()
        assert cancel["success"], cancel
        job = await _wait(client, job_id)
        assert job["status"] == "cancelled"
        time.sleep(0.5)
        assert app.state.state_manager.get_spectrum_data("cancelled") is None
        result = (await client.get(f"/api/jobs/{job_id}/result")).json()
        assert result["success"] is False


@pytest.mark.asyncio
async def test_background_jobs_report_scientific_errors(app):
    async with await _client(app) as client:
        submitted = (
            await client.post(
                "/api/spectrum/dynamical-power-spectrum",
                json={**BODY, "segment_size": 10000.0, "background": True},
            )
        ).json()
        job = await _wait(client, submitted["data"]["job_id"])
        assert job["status"] == "failed"
        assert "segment" in job["error"].lower()
