
"""Compatibility policy, lossless migration, and persisted origin regressions."""

import stingray
import json
import zipfile
from copy import deepcopy

import numpy as np
import pytest
from stingray import EventList
from services.project_compatibility import (
    compatibility,
    checked_version,
    migrate_defaults,
)
from services.project_service import ProjectService, CLASSES
from services.state_manager import StateManager
from services.spectrum_service import SpectrumService
from tests.test_io_utility_service import TEST_SECRET, make_grant


@pytest.mark.parametrize(
    "version", ["2.2", "2.2.0", "2.2.7", "2.2.10", "2.3", "2.3.1", "2.3.2"]
)
def test_supported_versions_have_explicit_bidirectional_policy(version):
    assert compatibility(version, "2.2.10")["source_stingray_version"] == version
    assert compatibility("2.2.10", version)["runtime_stingray_version"] == version


@pytest.mark.parametrize(
    "version",
    [
        None,
        "",
        "nonsense",
        "2.1",
        "2.2.8",
        "2.3.3",
        "3.0",
        "2.4.0",
        "2.3.2rc1",
        "2.3.2+custom",
    ],
)
def test_unknown_or_untested_releases_are_rejected(version):
    with pytest.raises(ValueError):
        checked_version(version)


def test_runtime_default_migration_never_rewrites_saved_data_or_identity():
    state = StateManager()
    state.add_event_data("a", EventList(time=np.arange(0.01, 16, 0.02), gti=[[0, 16]]))
    created = SpectrumService(state_manager=state).create_power_spectrum(
        "a", 0.125, output_name="power"
    )
    assert created["success"]
    spectrum = state.get_spectrum_data("power")
    original = deepcopy(spectrum.result_identity)
    power = spectrum.power.copy()
    # A missing runtime default simulates an older serialized object layout.
    del vars(spectrum)["k"]
    report = migrate_defaults(
        {"power": spectrum}, compatibility("2.2", "2.2.10"), CLASSES
    )
    assert spectrum.k == 1
    assert spectrum.norm == original["parameters"]["norm"]
    assert report["actions"]
    assert spectrum.result_identity == original
    np.testing.assert_array_equal(spectrum.power, power)


def test_cross_version_reopen_retains_origin_through_resave(tmp_path, monkeypatch):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    state = StateManager()
    state.add_event_data("a", EventList(time=[1.0, 2.0, 3.0], gti=[[0, 4]]))
    path = tmp_path / "source.srproj"
    assert ProjectService(state_manager=state).save(
        str(path), make_grant(path, "write"), {}
    )["success"]
    edited = tmp_path / "older.srproj"
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(edited, "w") as target:
        for name in source.namelist():
            value = source.read(name)
            if name == "manifest.json":
                metadata = json.loads(value)
                metadata["stingray_version"] = "2.2"
                value = json.dumps(metadata).encode()
            target.writestr(name, value)
    restored = StateManager()
    opened = ProjectService(state_manager=restored).reopen(
        str(edited), make_grant(edited, "read")
    )
    assert opened["success"], opened
    assert bool(opened["warnings"]) == (stingray.__version__ not in {"2.2", "2.2.0"})
    assert opened["data"]["compatibility"]["source_stingray_version"] == "2.2"
    assert restored.get_event_identity("a") == state.get_event_identity("a")
    resaved = tmp_path / "resaved.srproj"
    assert ProjectService(state_manager=restored).save(
        str(resaved), make_grant(resaved, "write"), {}
    )["success"]
    with zipfile.ZipFile(resaved) as archive:
        history = json.loads(archive.read("manifest.json"))["compatibility_history"]
    assert history[0]["source_stingray_version"] == "2.2"


def test_unsupported_runtime_fails_without_publishing(tmp_path, monkeypatch):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    monkeypatch.setattr("services.project_service.stingray.__version__", "9.0")
    path = tmp_path / "unsupported.srproj"
    assert not ProjectService(state_manager=StateManager()).save(
        str(path), make_grant(path, "write"), {}
    )["success"]
    assert not path.exists()


def test_unsupported_producer_rejected_before_decode_and_without_state_change(
    tmp_path, monkeypatch
):
    from services import project_archive

    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    original = tmp_path / "source.srproj"
    assert ProjectService(state_manager=StateManager()).save(
        str(original), make_grant(original, "write"), {}
    )["success"]
    path = tmp_path / "future.srproj"
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(path, "w") as target:
        for name in source.namelist():
            value = source.read(name)
            if name == "manifest.json":
                metadata = json.loads(value)
                metadata["stingray_version"] = "9.0"
                value = json.dumps(metadata).encode()
            target.writestr(name, value)

    def forbidden(*args, **kwargs):
        raise AssertionError("Must reject unsupported producers before decoding")

    monkeypatch.setattr(project_archive.ArrayReader, "__call__", forbidden)
    state = StateManager()
    state.add_analysis_result("keep", {"value": 42})
    result = ProjectService(state_manager=state).reopen(
        str(path), make_grant(path, "read")
    )
    assert not result["success"]
    assert "Unsupported Stingray version" in result["error"]
    assert state.get_analysis_result("keep") == {"value": 42}


def test_legacy_json_cross_version_preserves_input_identity(tmp_path, monkeypatch):
    from services.project_service import encode, SCHEMA, GROUPS

    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    source = StateManager()
    source.add_event_data(
        "input",
        EventList(
            time=[1.0, 2.0], gti=[[0, 3]], mjdref=np.longdouble("55000.123456789012345")
        ),
    )
    path = tmp_path / "legacy.srproj"
    path.write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "stingray_version": "2.2",
                "state": encode({key: getattr(source, "_" + key) for key in GROUPS}),
                "event_ids": source._event_identities,
                "lightcurve_ids": {},
                "renderer": encode({}),
            }
        )
    )
    target = StateManager()
    result = ProjectService(state_manager=target).reopen(
        str(path), make_grant(path, "read")
    )
    assert result["success"], result
    assert (
        result["data"]["compatibility"]["runtime_stingray_version"]
        == stingray.__version__
    )
    assert target.get_event_identity("input") == source.get_event_identity("input")
    assert (
        target.get_event_data("input").mjdref == source.get_event_data("input").mjdref
    )
