"""Every application route that reads an EventList accepts and applies a selection."""

import itertools
import json

import httpx
import numpy as np
import pytest
from stingray import EventList

from main import create_app
from services.state_manager import StateManager
from tests.backend_auth import TEST_BACKEND_AUTH_HEADERS, TEST_BACKEND_SESSION_SECRET
from tests.conftest import make_event_list
from tests.test_varenergy_service import modulated_event_list

_names = (f"out{index}" for index in itertools.count())

SINGLE = {
    "/api/lightcurve/from-event-list": {"dt": 0.5},
    "/api/spectrum/power-spectrum": {"dt": 0.125},
    "/api/spectrum/averaged-power-spectrum": {"dt": 0.125, "segment_size": 8.0},
    "/api/spectrum/dynamical-power-spectrum": {"dt": 0.125, "segment_size": 8.0},
    "/api/timing/bispectrum": {"dt": 0.25, "maxlag": 10},
    "/api/timing/power-colors": {
        "dt": 0.0625,
        "segment_size": 8.0,
        "freq_ranges": {
            "A": (0.125, 0.5),
            "B": (0.5, 1.0),
            "C": (1.0, 2.0),
            "D": (2.0, 4.0),
        },
    },
    "/api/correlation/auto-correlation": {"dt": 0.125},
    "/api/deadtime/pds-correction": {
        "dt": 0.0625,
        "segment_size": 8.0,
        "dead_time": 0.0001,
    },
}
PAIR = {
    "/api/spectrum/cross-spectrum": {"dt": 0.125},
    "/api/spectrum/averaged-cross-spectrum": {"dt": 0.125, "segment_size": 8.0},
    "/api/timing/time-lags": {"dt": 0.125, "segment_size": 8.0},
    "/api/timing/coherence": {"dt": 0.125, "segment_size": 8.0},
    "/api/correlation/cross-correlation": {"dt": 0.125},
    "/api/deadtime/fad-correction": {"dt": 0.125, "segment_size": 8.0},
}
_BANDS = {"freq_min": 0.125, "freq_max": 2.0, "energy_min": 0.5, "energy_max": 10.0}
ENERGY_RESOLVED = {
    "/api/varenergy/rms-spectrum": {"bin_time": 0.125, "segment_size": 8.0, **_BANDS},
    "/api/varenergy/lag-spectrum": {"bin_time": 0.125, "segment_size": 8.0, **_BANDS},
    "/api/varenergy/excess-variance": {
        "bin_time": 0.125,
        "energy_min": 0.5,
        "energy_max": 10.0,
    },
    "/api/varenergy/variable-energy-spectrum": {
        "bin_time": 0.125,
        "segment_size": 8.0,
        **_BANDS,
    },
    "/api/varenergy/covariance-spectrum": {"bin_time": 0.125, **_BANDS},
    "/api/varenergy/avg-covariance-spectrum": {
        "bin_time": 0.125,
        "segment_size": 8.0,
        **_BANDS,
    },
}
# Routes that read an EventList but deliberately take no selection.
EXEMPT = {
    "/api/utilities/gti/inspect": "reports the stored EventList's exposure exactly",
    "/api/utilities/gti/mask/preview": (
        "GTI masking is itself a time selection that derives a new EventList"
    ),
    "/api/utilities/gti/mask/save": (
        "GTI masking is itself a time selection that derives a new EventList"
    ),
    "/api/utilities/io/convert-event-list": (
        "converts or calibrates the stored object; derive a filtered EventList "
        "first to convert a selection"
    ),
    "/api/utilities/misc/energy-ranges": "describes the stored energy coverage",
    "/api/utilities/mission-io/convert-pi": (
        "calibrates the stored PI column; selections apply to its result"
    ),
    "/api/utilities/mission-io/identify": "reads the stored mission metadata",
}
# Counts a selection for the renderer's live preview; publishes nothing.
PREVIEW = "/api/data/selection-preview"
EVENT_LIST_FIELDS = {"event_list_name", "event_list_1_name", "event_list_2_name"}
ENERGY_CUT = {"energy_range": [2.0, 5.0]}
TIME_CUT = {"time_intervals": [[0.0, 32.0]]}


@pytest.fixture
def selection_app():
    app = create_app(session_secret=TEST_BACKEND_SESSION_SECRET)
    app.state.state_manager = StateManager()
    app.state.performance_monitor = None
    app.state.state_manager.add_event_data("a", make_event_list(1))
    app.state.state_manager.add_event_data("b", make_event_list(2))
    # Energy-resolved spectra need real variability to produce finite values.
    app.state.state_manager.add_event_data("v", modulated_event_list())
    return app


async def _post(app, path, body):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers=TEST_BACKEND_AUTH_HEADERS,
    ) as client:
        return await client.post(path, json=body)


def _body(path, **extra):
    if path in PAIR:
        names = {"event_list_1_name": "a", "event_list_2_name": "b"}
    elif path in ENERGY_RESOLVED:
        names = {"event_list_name": "v"}
    else:
        names = {"event_list_name": "a"}
    params = {**SINGLE, **PAIR, **ENERGY_RESOLVED}[path]
    body = {**names, **params, **extra}
    if path == "/api/lightcurve/from-event-list":
        body["output_name"] = next(_names)
    return body


_IGNORED = {
    "result_id",
    "backend_session_id",
    "dataset_id",
    "selection",
    "selections",
    "inputs",
    "provenance",
    "parameters",
    "original_parameters",
    "name",
    "output_name",
    "warnings",
}


def _numbers(value, key=None):
    """Numeric result leaves, ignoring identity and request echoes."""
    if key in _IGNORED:
        return []
    if isinstance(value, dict):
        return [n for k, v in sorted(value.items()) for n in _numbers(v, k)]
    if isinstance(value, list):
        return [n for item in value for n in _numbers(item)]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [value]
    return []


def _selection_records(value):
    """Distinct applied-selection records published anywhere in a payload."""
    unique = {json.dumps(record, sort_keys=True): record for record in _records(value)}
    return list(unique.values())


def _records(value):
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "selection" and isinstance(item, dict):
                found.append(item)
            elif key == "selections" and isinstance(item, list):
                found.extend(record for record in item if record)
            else:
                found.extend(_records(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_records(item))
    return found


def _payload(response):
    assert response.status_code == 200, response.text
    payload = json.loads(response.content)
    assert payload["success"] is True, payload
    return payload


def _request_fields(app):
    """Body fields of every JSON POST route, from the public OpenAPI schema."""
    schema = app.openapi()
    components = schema["components"]["schemas"]
    fields = {}
    for path, operations in schema["paths"].items():
        body = operations.get("post", {}).get("requestBody")
        if body is None:
            continue
        reference = body["content"]["application/json"]["schema"].get("$ref", "")
        model = components.get(reference.rsplit("/", 1)[-1], {})
        fields[path] = set(model.get("properties", {}))
    return fields


def test_every_event_list_route_is_covered_or_exempt(selection_app):
    covered = set(SINGLE) | set(PAIR) | set(ENERGY_RESOLVED) | {PREVIEW}
    fields = _request_fields(selection_app)
    readers = {path for path, names in fields.items() if names & EVENT_LIST_FIELDS}
    for path in covered:
        expected = {"selection_1", "selection_2"} if path in PAIR else {"selection"}
        assert expected <= fields[path], path
    assert readers - covered - set(EXEMPT) == set()
    assert set(EXEMPT) <= readers
    assert covered <= readers


@pytest.mark.asyncio
@pytest.mark.parametrize("path", sorted(SINGLE) + sorted(ENERGY_RESOLVED))
async def test_single_list_routes_apply_the_selection(selection_app, path):
    cut = TIME_CUT if path in ENERGY_RESOLVED else ENERGY_CUT
    plain = _payload(await _post(selection_app, path, _body(path)))
    selected = _payload(await _post(selection_app, path, _body(path, selection=cut)))

    records = _selection_records(selected["data"])
    assert len(records) == 1, records
    assert 0 < records[0]["n_events"] < records[0]["parent_n_events"]
    assert _selection_records(plain["data"]) == []
    assert _numbers(selected["data"]) != _numbers(plain["data"])


@pytest.mark.asyncio
@pytest.mark.parametrize("path", sorted(PAIR))
@pytest.mark.parametrize("side", ["selection_1", "selection_2"])
async def test_pair_routes_apply_each_selection(selection_app, path, side):
    plain = _payload(await _post(selection_app, path, _body(path)))
    selected = _payload(
        await _post(selection_app, path, _body(path, **{side: TIME_CUT}))
    )
    records = _selection_records(selected["data"])
    assert len(records) == 1, records
    assert records[0]["time_intervals"] == [[0.0, 32.0]]
    assert _numbers(selected["data"]) != _numbers(plain["data"])


@pytest.mark.asyncio
@pytest.mark.parametrize("path", sorted(ENERGY_RESOLVED))
@pytest.mark.parametrize("cut", [ENERGY_CUT, {"pi_range": [0, 10]}])
async def test_energy_resolved_routes_reject_spectral_selection(
    selection_app, path, cut
):
    response = await _post(selection_app, path, _body(path, selection=cut))
    assert response.status_code == 422
    assert "energy settings" in response.text


@pytest.mark.asyncio
async def test_energy_cut_without_energy_column_is_a_422(selection_app):
    times = np.sort(np.random.default_rng(3).uniform(0, 64, 2000))
    selection_app.state.state_manager.add_event_data(
        "pi_only",
        EventList(time=times, pi=np.arange(2000) % 100, gti=[[0.0, 64.0]]),
    )
    body = {"event_list_name": "pi_only", "dt": 0.125, "selection": ENERGY_CUT}
    response = await _post(selection_app, "/api/spectrum/power-spectrum", body)
    assert response.status_code == 422
    assert "PI range" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "selection,message",
    [
        ({"energy_range": [50.0, 60.0]}, "leaves no events"),
        ({"time_intervals": [[100.0, 200.0]]}, "does not overlap"),
    ],
)
async def test_empty_selections_are_a_422(selection_app, selection, message):
    body = {"event_list_name": "a", "dt": 0.125, "selection": selection}
    response = await _post(selection_app, "/api/spectrum/power-spectrum", body)
    assert response.status_code == 422
    assert message in response.json()["detail"]


@pytest.mark.asyncio
async def test_inverted_ranges_are_a_422(selection_app):
    body = {"event_list_name": "a", "dt": 0.125, "selection": {"energy_range": [5, 2]}}
    response = await _post(selection_app, "/api/spectrum/power-spectrum", body)
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path", sorted(path for path in PAIR if path != "/api/deadtime/fad-correction")
)
@pytest.mark.parametrize(
    "reference,overlaps",
    [([4.0, 10.0], True), ([5.0, 10.0], False)],
)
async def test_two_bands_of_one_list_warn_only_when_they_overlap(
    selection_app, path, reference, overlaps
):
    body = _body(
        path,
        event_list_2_name="a",
        selection_1={"energy_range": [0.5, 5.0]},
        selection_2={"energy_range": reference},
    )
    payload = _payload(await _post(selection_app, path, body))
    warnings = " ".join(payload["data"].get("warnings", []))
    assert ("share photons" in warnings) is overlaps
    assert len(_selection_records(payload["data"])) == 2


@pytest.mark.asyncio
async def test_fad_rejects_two_selections_of_one_detector(selection_app):
    body = _body(
        "/api/deadtime/fad-correction",
        event_list_2_name="a",
        selection_1={"energy_range": [0.5, 5.0]},
        selection_2={"energy_range": [5.0, 10.0]},
    )
    payload = json.loads(
        (await _post(selection_app, "/api/deadtime/fad-correction", body)).content
    )
    assert payload["success"] is False
    assert "independent detectors" in payload["message"]
    assert "dead time" in payload["message"]


@pytest.mark.asyncio
async def test_band_light_curves_sum_to_the_union_light_curve(selection_app):
    def curve(energy_range):
        return _post(
            selection_app,
            "/api/lightcurve/from-event-list",
            {
                "event_list_name": "a",
                "dt": 1.0,
                "output_name": next(_names),
                "max_points": 0,
                "selection": {"energy_range": energy_range},
            },
        )

    soft = _payload(await curve([0.5, 4.0]))["data"]
    hard = _payload(await curve([4.0, 10.5]))["data"]
    union = _payload(await curve([0.5, 10.5]))["data"]
    np.testing.assert_array_equal(
        np.add(soft["counts"], hard["counts"]), union["counts"]
    )
    assert soft["inputs"][0]["selection"]["energy_range_kev"] == [0.5, 4.0]


@pytest.mark.asyncio
async def test_selection_preview_counts_without_publishing(selection_app):
    state = selection_app.state.state_manager
    stored = state.get_event_data("a")
    response = await _post(
        selection_app,
        "/api/data/selection-preview",
        {"event_list_name": "a", "selection": {"energy_range": [2.0, 5.0]}},
    )
    payload = _payload(response)["data"]
    energy = np.asarray(stored.energy)
    expected = int(np.count_nonzero((energy >= 2.0) & (energy < 5.0)))
    assert payload["n_events"] == expected
    assert payload["parent_n_events"] == 20000
    assert 2.0 <= payload["energy_coverage"][0] <= payload["energy_coverage"][1] < 5.0
    assert payload["pi_coverage"] is None
    assert payload["exposure"] == pytest.approx(64.0)
    assert {name for name, _ in state.get_event_data()} == {"a", "b", "v"}


@pytest.mark.asyncio
async def test_selection_preview_reports_selection_errors(selection_app):
    response = await _post(
        selection_app,
        "/api/data/selection-preview",
        {"event_list_name": "a", "selection": {"energy_range": [50.0, 60.0]}},
    )
    assert response.status_code == 422
    assert "leaves no events" in response.json()["detail"]
