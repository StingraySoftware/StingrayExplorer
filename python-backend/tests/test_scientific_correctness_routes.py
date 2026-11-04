"""Exercise scientific preflights through the authenticated application routes.

The calculations are real: these regressions must reject incompatible input
before a plausible-looking spectrum, lag, or detector correction is published.
"""

import json

import httpx
import numpy as np
import pytest
from stingray import EventList

from main import create_app
from services.state_manager import StateManager
from tests.backend_auth import (
    TEST_BACKEND_AUTH_HEADERS,
    TEST_BACKEND_SESSION_SECRET,
)


PAIR_REQUESTS = [
    ("/api/spectrum/cross-spectrum", {}),
    ("/api/spectrum/averaged-cross-spectrum", {"segment_size": 8.0}),
    ("/api/timing/time-lags", {"segment_size": 8.0}),
    ("/api/timing/coherence", {"segment_size": 8.0}),
    ("/api/correlation/cross-correlation", {}),
    ("/api/deadtime/fad-correction", {"segment_size": 8.0}),
]


@pytest.fixture
def scientific_app():
    app = create_app(session_secret=TEST_BACKEND_SESSION_SECRET)
    app.state.state_manager = StateManager()
    app.state.performance_monitor = None
    return app


def strict_payload(response):
    def reject_constant(value):
        raise AssertionError(f"Nonfinite JSON constant: {value}")

    return json.loads(response.content, parse_constant=reject_constant)


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint,extra", PAIR_REQUESTS)
@pytest.mark.parametrize("mismatch", ["mjdref", "timesys", "missing_timesys"])
async def test_pair_routes_reject_incompatible_physical_time(
    scientific_app, endpoint, extra, mismatch
):
    rng = np.random.default_rng(20261029)
    times = np.sort(rng.uniform(0.0, 64.0, 5_000))
    first = EventList(time=times, gti=[[0.0, 64.0]], mjdref=55000, timesys="TDB")
    second = EventList(
        time=times.copy(), gti=[[0.0, 64.0]], mjdref=55000, timesys="TDB"
    )
    if mismatch == "mjdref":
        second.mjdref = 55001
    elif mismatch == "timesys":
        second.timesys = "TT"
    else:
        second.timesys = None
    state = scientific_app.state.state_manager
    state.add_event_data("first", first)
    state.add_event_data("second", second)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=scientific_app),
        base_url="http://test",
        headers=TEST_BACKEND_AUTH_HEADERS,
    ) as client:
        response = await client.post(
            endpoint,
            json={
                "event_list_1_name": "first",
                "event_list_2_name": "second",
                "dt": 0.125,
                **extra,
            },
        )

    assert response.status_code == 200, response.text
    payload = strict_payload(response)
    assert payload["success"] is False, payload
    assert payload["data"] is None
    explanation = f"{payload['message']} {payload.get('error', '')}".lower()
    assert ("mjdref" if mismatch == "mjdref" else "timesys") in explanation
    assert state.list_spectrum_names() == []
    assert state.list_analysis_result_names() == []
    np.testing.assert_array_equal(first.time, times)
    np.testing.assert_array_equal(second.time, times)


@pytest.mark.asyncio
async def test_custom_gti_route_intersects_native_exposure(scientific_app):
    events = EventList(
        time=np.arange(0.125, 16.0, 0.25),
        gti=[[0.0, 8.0], [12.0, 16.0]],
        mjdref=55000,
    )
    state = scientific_app.state.state_manager
    state.add_event_data("screened", events)
    original_times = events.time.copy()
    original_gti = events.gti.copy()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=scientific_app),
        base_url="http://test",
        headers=TEST_BACKEND_AUTH_HEADERS,
    ) as client:
        response = await client.post(
            "/api/lightcurve/from-event-list",
            json={
                "event_list_name": "screened",
                "dt": 0.5,
                "output_name": "selected",
                "gti": [[2.0, 14.0]],
            },
        )

    assert response.status_code == 200, response.text
    payload = strict_payload(response)
    assert payload["success"] is True, payload
    selected = state.get_lightcurve_data("selected")
    np.testing.assert_array_equal(selected.gti, [[2.0, 8.0], [12.0, 14.0]])
    assert len(selected.time) == 16
    assert np.sum(selected.counts) == 32
    assert selected.mjdref == events.mjdref
    np.testing.assert_array_equal(events.time, original_times)
    np.testing.assert_array_equal(events.gti, original_gti)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "band_a,band_d",
    [((0.001, 0.01), (2.0, 4.0)), ((0.125, 0.5), (2.0, 9.0))],
)
async def test_power_colour_route_rejects_unavailable_frequency_coverage(
    scientific_app, band_a, band_d
):
    rng = np.random.default_rng(29)
    events = EventList(time=np.sort(rng.uniform(0.0, 64.0, 5_000)), gti=[[0.0, 64.0]])
    state = scientific_app.state.state_manager
    state.add_event_data("observation", events)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=scientific_app),
        base_url="http://test",
        headers=TEST_BACKEND_AUTH_HEADERS,
    ) as client:
        response = await client.post(
            "/api/timing/power-colors",
            json={
                "event_list_name": "observation",
                "dt": 0.0625,
                "segment_size": 8.0,
                "freq_ranges": {
                    "A": band_a,
                    "B": (0.5, 1.0),
                    "C": (1.0, 2.0),
                    "D": band_d,
                },
                "output_name": "invalid_colours",
            },
        )

    assert response.status_code == 200, response.text
    payload = strict_payload(response)
    assert payload["success"] is False, payload
    assert state.get_analysis_result("invalid_colours") is None
