"""Real project round trips and transactional failure regressions."""

import json
import numpy as np
import pytest
from stingray import EventList
from services.project_service import ProjectService, encode, decode
from services.spectrum_service import SpectrumService
from services.state_manager import StateManager
from tests.test_io_utility_service import TEST_SECRET, make_grant


def test_project_roundtrip_retains_inputs_complex_results_and_rebin(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    state = StateManager()
    for name, offset in [("a", 0), ("b", 0.01)]:
        state.add_event_data(
            name,
            EventList(
                time=np.arange(0.05, 32, 0.03) + offset,
                gti=[[0, 32]],
                mjdref=np.longdouble("55000.123456789012345"),
            ),
        )
    result = SpectrumService(state_manager=state).create_cross_spectrum(
        "a", "b", 0.125, output_name="cross"
    )
    assert result["success"], result
    path = tmp_path / "project.srproj"
    renderer = {"Cross spectrum": {"result": result["data"], "settings": {"dt": 0.125}}}
    workspace = {
        "version": 1,
        "fields": {
            "QuickLook/PowerSpectrum:dt": "unfinished.",
            "selected": "a",
            "logX": False,
        },
        "path": "/quicklook/power-spectrum",
        "preferences": {"logPanelOpen": True, "rightToolbarCollapsed": False},
    }
    saved = ProjectService(state_manager=state).save(
        str(path), make_grant(path, "write"), renderer, workspace
    )
    assert saved["success"], saved
    target = StateManager()
    opened = ProjectService(state_manager=target).reopen(
        str(path), make_grant(path, "read")
    )
    assert opened["success"], opened
    assert opened["data"]["renderer"] == renderer
    assert opened["data"]["workspace"] == workspace
    assert target.get_event_identity("a") == state.get_event_identity("a")
    np.testing.assert_array_equal(
        target.get_event_data("a").time, state.get_event_data("a").time
    )
    assert target.get_event_data("a").mjdref == state.get_event_data("a").mjdref
    old, new = state.get_spectrum_data("cross"), target.get_spectrum_data("cross")
    np.testing.assert_array_equal(old.power, new.power)
    assert old.result_identity == new.result_identity
    rebinned = SpectrumService(state_manager=target).rebin_spectrum(
        "cross",
        2,
        output_name="derived",
        expected_result_id=new.result_identity["result_id"],
    )
    assert rebinned["success"], rebinned
    assert not ProjectService(state_manager=target).reopen(
        str(path), make_grant(path, "read")
    )["success"]
    assert not ProjectService(state_manager=state).save(
        str(path), make_grant(path, "write"), renderer
    )["success"]


@pytest.mark.parametrize(
    "bad",
    [
        {"$object": "os.system", "attributes": {"$dict": {}}},
        {"$array": "invalid"},
        {"$unknown": 1},
    ],
)
def test_unsupported_encodings_are_rejected(bad):
    with pytest.raises((ValueError, TypeError)):
        decode(bad)


def test_grants_excluded_and_numeric_dtypes_preserved():
    value = {
        "grant": "never persist",
        "nested": {"token": "omit"},
        "data": np.array([2**63 + 1], dtype=np.uint64),
    }
    restored = decode(encode(value))
    assert "grant" not in restored and "token" not in restored["nested"]
    np.testing.assert_array_equal(restored["data"], value["data"])
    assert restored["data"].dtype == np.uint64


def test_invalid_version_does_not_mutate_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    path = tmp_path / "bad.srproj"
    path.write_text(json.dumps({"schema": "future"}))
    state = StateManager()
    state.add_analysis_result("existing", {"value": 42})
    result = ProjectService(state_manager=state).reopen(
        str(path), make_grant(path, "read")
    )
    assert not result["success"]
    assert state.get_analysis_result("existing") == {"value": 42}


def test_codec_preserves_masks_tuples_and_nonfinite_scientific_values():
    original = (np.ma.array([1.0, 2.0], mask=[False, True]), float("nan"))
    restored = decode(encode(original))
    assert isinstance(restored, tuple)
    np.testing.assert_array_equal(restored[0].mask, original[0].mask)
    np.testing.assert_array_equal(restored[0].data, original[0].data)
    assert np.isnan(restored[1])


@pytest.mark.parametrize(
    "workspace",
    [
        {"version": 99, "fields": {}},
        {"version": 1, "fields": [], "path": "/"},
        {"version": 1, "fields": {}, "path": "//external.invalid"},
        {"version": 1, "fields": {}, "preferences": {"isProcessing": True}},
    ],
)
def test_invalid_workspace_is_rejected_before_creating_a_project(
    tmp_path, monkeypatch, workspace
):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    path = tmp_path / "bad-workspace.srproj"
    result = ProjectService(state_manager=StateManager()).save(
        str(path), make_grant(path, "write"), {}, workspace
    )
    assert not result["success"]
    assert not path.exists()
