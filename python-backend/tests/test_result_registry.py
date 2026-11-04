"""Every stored result kind is registered once with its identity, codec, export and plot."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pytest
from astropy.table import Table
from stingray import EventList

from services.project_service import CLASSES, ProjectService
from services.result_registry import (
    REGISTRY,
    UnregisteredResultKind,
    kind_of,
    project_classes,
)
from services.io_utility_service import EXPORT_OBJECT_TYPES, IOUtilityService
from services.state_manager import StateManager
from tests.test_io_utility_service import TEST_SECRET, make_grant

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PROJECT = FIXTURES / "pre_registry_project.srproj"
MANIFEST = json.loads((FIXTURES / "pre_registry_project.manifest.json").read_text())
GETTERS = {
    "event_data": "get_event_data",
    "lightcurve_data": "get_lightcurve_data",
    "spectrum_data": "get_spectrum_data",
    "analysis_results": "get_analysis_result",
}


@pytest.fixture
def reopened(tmp_path, monkeypatch):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    copy = tmp_path / "old.srproj"
    shutil.copy(PROJECT, copy)
    state = StateManager()
    opened = ProjectService(state_manager=state).reopen(
        str(copy), make_grant(copy, "read")
    )
    assert opened["success"], opened
    return state, opened, tmp_path


def _normalized_state(path):
    """The saved state with array file references replaced by content digests."""
    with zipfile.ZipFile(path) as archive:
        state = json.loads(archive.read("manifest.json"))

        def normalize(value):
            if isinstance(value, dict):
                return {
                    key: (
                        hashlib.sha256(archive.read(item)).hexdigest()
                        if key == "$array_file"
                        else normalize(item)
                    )
                    for key, item in value.items()
                }
            if isinstance(value, list):
                return [normalize(item) for item in value]
            return value

        return normalize(state)


def _added_keys(old, new, path=""):
    """Paths new adds to old; every value old saved must be preserved exactly."""
    if isinstance(old, dict):
        assert isinstance(new, dict), path
        added = [f"{path}/{key}" for key in new if key not in old]
        for key, value in old.items():
            assert key in new, f"{path}/{key} was dropped"
            added += _added_keys(value, new[key], f"{path}/{key}")
        return added
    if isinstance(old, list):
        assert isinstance(new, list) and len(new) == len(old), path
        return [
            p
            for index, (a, b) in enumerate(zip(old, new))
            for p in _added_keys(a, b, f"{path}[{index}]")
        ]
    assert old == new, path
    return []


# --- registry contents ---------------------------------------------------


def test_registry_keys_are_unique_and_complete():
    keys = [kind.key for kind in REGISTRY]
    assert len(keys) == len(set(keys))
    for kind in REGISTRY:
        assert kind.store in GETTERS
        assert kind.export_object_type in EXPORT_OBJECT_TYPES
        assert kind.default_plot
        assert kind.identity in {"dataset", "result_identity", "provenance", "none"}


def test_project_codec_classes_come_from_the_registry():
    assert CLASSES == project_classes()


def test_every_kind_in_an_old_project_is_registered(reopened):
    state, _, _ = reopened
    for group, getter in GETTERS.items():
        for name, obj in getattr(state, getter)():
            kind = kind_of(group, obj)
            assert kind.store == group, (group, name, kind.key)


def test_dict_results_are_identified_by_their_operation():
    assert (
        kind_of(
            "analysis_results", {"provenance": {"operation": "timing_time_lags"}}
        ).key
        == "time_lags"
    )
    assert kind_of("analysis_results", {"value": [1, 2]}).key == "table"
    assert kind_of("analysis_results", Table({"value": [1, 2]})).key == "table"


# --- enforcement ---------------------------------------------------------


class Unregistered:
    pass


@pytest.mark.parametrize(
    "method,obj",
    [
        ("add_event_data", Unregistered()),
        ("add_lightcurve_data", EventList(time=[1.0, 2.0])),
        ("add_spectrum_data", EventList(time=[1.0, 2.0])),
        ("add_analysis_result", Unregistered()),
        ("add_analysis_result_if_absent", Unregistered()),
        ("add_spectrum_data_if_absent", {"value": 1}),
    ],
)
def test_publishing_an_unregistered_kind_fails(method, obj):
    state = StateManager()
    with pytest.raises(UnregisteredResultKind):
        getattr(state, method)("x", obj)


def test_unregistered_kinds_never_reach_state():
    state = StateManager()
    with pytest.raises(UnregisteredResultKind):
        state.add_analysis_result("x", Unregistered())
    assert state.get_analysis_result() == []


# --- backward compatibility ----------------------------------------------


def test_a_project_saved_before_the_registry_reopens_unchanged(reopened):
    state, opened, _ = reopened
    for group, getter in GETTERS.items():
        restored = {name: type(obj).__name__ for name, obj in getattr(state, getter)()}
        assert restored == MANIFEST[group], group
    record = opened["data"]["renderer"]["Power Spectrum"]
    assert record["settings"] == {"dt": 0.125}
    assert record["result"]["name"] == "ps"
    assert (
        state.get_lightcurve_data("lc file").result_identity["inputs"][0]["source_name"]
        == "nicer.lc"
    )
    assert state.get_event_data("a mid").event_lineage["operation"] == "filter"


def test_resaving_an_old_project_keeps_its_saved_format(reopened):
    state, opened, tmp_path = reopened
    copy = tmp_path / "resaved.srproj"
    saved = ProjectService(state_manager=state).save(
        str(copy), make_grant(copy, "write"), opened["data"]["renderer"], None
    )
    assert saved["success"], saved
    old, new = _normalized_state(PROJECT), _normalized_state(copy)
    assert new["schema"] == old["schema"]
    assert new["event_ids"] == old["event_ids"]
    assert new["lightcurve_ids"] == old["lightcurve_ids"]
    # Reopening fills defaults that older Stingray objects lacked (the existing
    # compatibility migration, unchanged by the registry); nothing else changes.
    added = _added_keys(old["state"], new["state"])
    assert added and all("/dps/attributes/" in path for path in added), added


def test_export_listing_names_each_kind_and_its_default_plot(reopened):
    state, _, _ = reopened
    listed = IOUtilityService(state).list_exportable_objects()["data"]["objects"]
    by_name = {entry["name"]: entry for entry in listed}
    assert by_name["dps"]["kind"] == "dynamical_power_spectrum"
    assert by_name["dps"]["default_plot"] == "image_2d"
    assert by_name["lags"]["kind"] == "time_lags"
    assert by_name["a"]["kind"] == "event_list"
    assert by_name["lc file"]["default_plot"] == "lightcurve"


def test_kinds_route_describes_the_registry():
    from routes.result_routes import list_result_kinds

    import asyncio

    described = asyncio.run(list_result_kinds())["data"]
    assert {kind["key"] for kind in described} == {kind.key for kind in REGISTRY}
    assert all(
        set(kind)
        == {"key", "label", "store", "export_object_type", "default_plot", "identity"}
        for kind in described
    )


def test_every_default_plot_has_a_renderer_component():
    import re

    source = (
        Path(__file__).resolve().parents[2]
        / "src/components/plots/kit/defaultPlots.ts"
    ).read_text()
    renderer_ids = set(re.findall(r"^  (\w+): '", source, re.M))
    assert {kind.default_plot for kind in REGISTRY} <= renderer_ids
