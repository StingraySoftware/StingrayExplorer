"""Stored spectra retain the identity of the calculation that produced them."""

from copy import deepcopy
import json
from uuid import UUID

import numpy as np
import pytest
from stingray import EventList

from services.spectrum_service import SpectrumService
from services.state_manager import StateManager


SPECTRUM_METHODS = [
    "create_power_spectrum",
    "create_averaged_power_spectrum",
    "create_cross_spectrum",
    "create_averaged_cross_spectrum",
]


def create_spectrum(service, method, output_name=None):
    arguments = {"dt": 0.125, "norm": "frac", "output_name": output_name}
    if "cross" in method:
        arguments.update(event_list_1_name="ev1", event_list_2_name="ev2")
    else:
        arguments["event_list_name"] = "ev1"
    if "averaged" in method:
        arguments["segment_size"] = 8.0
    return getattr(service, method)(**arguments)


@pytest.mark.parametrize("method", SPECTRUM_METHODS)
@pytest.mark.parametrize("named", [False, True])
def test_spectrum_responses_have_unique_result_and_backend_identity(
    loaded_state, method, named
):
    service = SpectrumService(loaded_state)
    first = create_spectrum(service, method, "first" if named else None)
    second = create_spectrum(service, method, "second" if named else None)
    assert first["success"], first
    assert second["success"], second
    data = first["data"]
    assert str(UUID(data["result_id"])) == data["result_id"]
    assert str(UUID(data["backend_session_id"])) == loaded_state.session_id
    assert data["result_id"] != second["data"]["result_id"]
    assert data["backend_session_id"] == second["data"]["backend_session_id"]
    assert data["parameters"]["dt"] == 0.125
    assert data["parameters"]["norm"] == "frac"
    assert data["provenance"]["operation"]
    assert data["provenance"]["stingray_version"]
    assert data["metadata"]["units"]["freq"] == "Hz"
    json.dumps(first, allow_nan=False)
    if named:
        stored = loaded_state.get_spectrum_data("first")
        assert stored.result_identity["result_id"] == data["result_id"]
        assert stored.result_identity["inputs"] == data["inputs"]


def test_source_snapshot_survives_mutation_deletion_and_name_reuse(loaded_state):
    original = loaded_state.get_event_data("ev1")
    original.mjdref = np.longdouble("55000.12345678912345")
    original.timesys = "TDB"
    original.timeref = "SOLARSYSTEM"
    original.ephem = "DE430"
    result = create_spectrum(
        SpectrumService(loaded_state), "create_power_spectrum", "original_psd"
    )
    assert result["success"], result
    snapshot = deepcopy(result["data"]["inputs"][0])
    assert snapshot["name"] == "ev1"
    assert snapshot["dataset_id"] == loaded_state.get_event_identity("ev1")
    assert snapshot["n_events"] == 20_000
    assert np.longdouble(snapshot["timing"]["mjdref"]) == original.mjdref
    assert snapshot["timing"]["timesys"] == "TDB"
    np.testing.assert_array_equal(
        np.asarray(snapshot["gti"], dtype=np.longdouble), [[0, 64]]
    )
    assert all(
        isinstance(value, str) for interval in snapshot["gti"] for value in interval
    )
    assert all(isinstance(value, str) for value in snapshot["time_range"])

    original.gti = [[2.0, 4.0]]
    original.timesys = "TT"
    original.mjdref = 56000
    assert loaded_state.remove_event_data("ev1")
    replacement = EventList(time=np.linspace(0.1, 63.9, 500), gti=[[0.0, 64.0]])
    loaded_state.add_event_data("ev1", replacement)
    assert loaded_state.get_event_identity("ev1") != snapshot["dataset_id"]

    stored = loaded_state.get_spectrum_data("original_psd")
    assert stored.result_identity["inputs"][0] == snapshot
    assert result["data"]["inputs"][0] == snapshot


def test_response_metadata_cannot_mutate_stored_result_identity(loaded_state):
    result = create_spectrum(
        SpectrumService(loaded_state), "create_cross_spectrum", "cross"
    )
    assert result["success"], result
    stored = loaded_state.get_spectrum_data("cross")
    original_identity = deepcopy(stored.result_identity)
    result["data"]["inputs"][0]["name"] = "edited_in_the_renderer"
    result["data"]["inputs"][0]["gti"][0][0] = "999"
    result["data"]["parameters"]["norm"] = "none"
    result["data"]["provenance"]["parameters"]["dt"] = 1.0
    assert stored.result_identity == original_identity


def test_replacing_source_during_calculation_does_not_relabel_original_photons(
    loaded_state, monkeypatch
):
    from stingray import Powerspectrum

    source = loaded_state.get_event_data("ev1")
    original_dataset_id = loaded_state.get_event_identity("ev1")
    expected = Powerspectrum(source.to_lc(dt=0.125), norm="frac")
    replacement = EventList(
        time=np.linspace(0.25, 63.75, 500), gti=[[0.0, 64.0]], mjdref=56000
    )
    copy_source = loaded_state.copy_event_data_with_identity
    replacements = []

    def copy_then_replace(name, selection=None):
        # Deterministically interleave another source publication after the
        # calculation has taken its atomic input snapshot, before its FFT.
        # The service still performs the actual scientific calculation.
        copied = copy_source(name, selection)
        if name == "ev1" and not replacements:
            loaded_state.add_event_data(name, replacement)
            replacements.append(name)
        return copied

    monkeypatch.setattr(
        loaded_state, "copy_event_data_with_identity", copy_then_replace
    )
    result = create_spectrum(
        SpectrumService(loaded_state), "create_power_spectrum", "in_flight"
    )
    assert result["success"], result
    assert replacements == ["ev1"]
    assert loaded_state.get_event_identity("ev1") != original_dataset_id
    assert result["data"]["inputs"][0]["dataset_id"] == original_dataset_id
    assert np.longdouble(result["data"]["inputs"][0]["timing"]["mjdref"]) == 0
    np.testing.assert_allclose(result["data"]["power"], expected.power)


def test_rebin_creates_new_identity_and_retains_original_inputs(loaded_state):
    service = SpectrumService(loaded_state)
    created = create_spectrum(service, "create_cross_spectrum", "parent")
    assert created["success"], created
    original = deepcopy(created["data"])
    loaded_state.remove_event_data("ev1")
    loaded_state.remove_event_data("ev2")

    rebinned = service.rebin_spectrum(
        "parent", rebin_factor=2.0, output_name="rebinned"
    )
    assert rebinned["success"], rebinned
    data = rebinned["data"]
    assert data["result_id"] != original["result_id"]
    assert data["backend_session_id"] == original["backend_session_id"]
    assert data["inputs"] == original["inputs"]
    assert data["parameters"]["rebin_factor"] == 2.0
    assert data["provenance"]["parent_result"] == {
        "result_id": original["result_id"],
        "backend_session_id": original["backend_session_id"],
        "name": "parent",
    }
    assert data["provenance"]["original_parameters"] == original["parameters"]
    assert (
        loaded_state.get_spectrum_data("parent").result_identity["inputs"]
        == original["inputs"]
    )
    assert (
        loaded_state.get_spectrum_data("parent").result_identity["parameters"]
        == original["parameters"]
    )
    json.dumps(rebinned, allow_nan=False)


@pytest.mark.parametrize("method", SPECTRUM_METHODS)
def test_duplicate_spectrum_names_are_rejected_without_replacement(
    loaded_state, method
):
    service = SpectrumService(loaded_state)
    first = create_spectrum(service, method, "kept")
    assert first["success"], first
    stored = loaded_state.get_spectrum_data("kept")
    original_power = stored.power.copy()
    second = create_spectrum(service, method, "kept")
    assert second["success"] is False, second
    assert "exist" in f"{second['message']} {second.get('error', '')}".lower()
    assert loaded_state.get_spectrum_data("kept") is stored
    assert stored.result_identity["result_id"] == first["data"]["result_id"]
    np.testing.assert_array_equal(stored.power, original_power)


def test_rebin_cannot_replace_its_parent_result(loaded_state):
    service = SpectrumService(loaded_state)
    first = create_spectrum(service, "create_power_spectrum", "kept")
    assert first["success"], first
    result = service.rebin_spectrum("kept", rebin_factor=2.0, output_name="kept")
    assert result["success"] is False, result
    stored = loaded_state.get_spectrum_data("kept")
    assert stored.result_identity["result_id"] == first["data"]["result_id"]
    assert len(stored.freq) == len(first["data"]["freq"])


def test_spectrum_inventory_identifies_the_stored_result(loaded_state):
    service = SpectrumService(loaded_state)
    created = create_spectrum(service, "create_averaged_power_spectrum", "listed")
    assert created["success"], created
    inventory = service.list_spectra()
    assert inventory["success"], inventory
    listed = next(item for item in inventory["data"] if item["name"] == "listed")
    assert listed["result_id"] == created["data"]["result_id"]
    assert listed["backend_session_id"] == loaded_state.session_id


def test_source_identity_is_per_insertion_and_backend_session_is_per_state_manager():
    state = StateManager()
    other = StateManager()
    assert str(UUID(state.session_id)) == state.session_id
    assert state.session_id != other.session_id
    first = EventList(time=[0.5, 1.5], gti=[[0.0, 2.0]])
    second = EventList(time=[0.75, 1.75], gti=[[0.0, 2.0]])
    state.add_event_data("source", first)
    initial = state.get_event_identity("source")
    assert str(UUID(initial)) == initial
    assert state.add_event_data_if_absent("source", second) is False
    assert state.get_event_identity("source") == initial
    state.add_event_data("source", second)
    assert state.get_event_identity("source") != initial
    state.remove_event_data("source")
    assert state.get_event_identity("source") is None


def test_cross_spectrum_export_projection_preserves_true_complex_power(loaded_state):
    from services.spectrum_products import spectrum_export_table

    result = create_spectrum(
        SpectrumService(loaded_state), "create_cross_spectrum", "complex_cross"
    )
    assert result["success"], result
    stored = loaded_state.get_spectrum_data("complex_cross")
    expected = np.asarray(stored.power)
    assert np.iscomplexobj(expected) and np.any(expected.imag != 0)
    table = spectrum_export_table(stored)
    power_real = np.asarray(table["power_real"])
    power_imag = np.asarray(table["power_imag"])
    np.testing.assert_allclose(power_real + 1j * power_imag, expected)
    np.testing.assert_allclose(table["power_magnitude"], np.abs(expected))
    np.testing.assert_allclose(table["power_phase"], np.angle(expected))
    assert str(table["freq"].unit) == "Hz"
    assert table.meta["result_id"] == result["data"]["result_id"]
    assert table.meta["inputs"] == result["data"]["inputs"]


def test_log_rebin_export_retains_aligned_bin_widths_and_averaging_counts(loaded_state):
    from services.spectrum_products import spectrum_table

    service = SpectrumService(loaded_state)
    original = create_spectrum(service, "create_averaged_cross_spectrum", "averaged")
    assert original["success"], original
    result = service.rebin_spectrum(
        "averaged",
        rebin_factor=0.2,
        log=True,
        output_name="log_rebinned",
        expected_result_id=original["data"]["result_id"],
    )
    assert result["success"], result
    stored = loaded_state.get_spectrum_data("log_rebinned")
    table = spectrum_table(stored)
    assert len(table) < len(original["data"]["freq"])
    for column, attribute in (("df", "df"), ("n_averaged", "m"), ("rebin_count", "k")):
        expected = np.broadcast_to(
            np.asarray(getattr(stored, attribute)), (len(table),)
        )
        np.testing.assert_array_equal(table[column], expected)
    assert np.max(table["rebin_count"]) > 1
    assert str(table["df"].unit) == "Hz"
    assert table.meta["result_id"] == result["data"]["result_id"]
    assert (
        table.meta["provenance"]["parent_result"]["result_id"]
        == original["data"]["result_id"]
    )


@pytest.mark.parametrize("log, factor", [(False, 2.0), (True, 0.2)])
def test_rebin_leaves_every_parent_spectrum_array_and_identity_unchanged(
    loaded_state, log, factor
):
    service = SpectrumService(loaded_state)
    original = create_spectrum(
        service, "create_averaged_cross_spectrum", "parent_arrays"
    )
    assert original["success"], original
    stored = loaded_state.get_spectrum_data("parent_arrays")
    identity = deepcopy(stored.result_identity)
    snapshots = {}
    for name in ("freq", "power", "power_err", "df", "m", "k", "gti"):
        array = np.asarray(getattr(stored, name))
        snapshots[name] = (array.dtype, array.shape, array.tobytes())

    result = service.rebin_spectrum(
        "parent_arrays",
        rebin_factor=factor,
        log=log,
        output_name="child_arrays",
        expected_result_id=original["data"]["result_id"],
    )
    assert result["success"], result
    assert loaded_state.get_spectrum_data("parent_arrays") is stored
    for name, expected in snapshots.items():
        actual = np.asarray(getattr(stored, name))
        assert (actual.dtype, actual.shape, actual.tobytes()) == expected, name
    assert stored.result_identity == identity
    assert result["data"]["result_id"] != original["data"]["result_id"]


@pytest.mark.parametrize("reuse_name", [False, True])
def test_rebin_rejects_deleted_or_reused_result_identity_without_publication(
    loaded_state, reuse_name
):
    service = SpectrumService(loaded_state)
    original = create_spectrum(service, "create_power_spectrum", "selected")
    assert original["success"], original
    assert service.delete_spectrum("selected")["success"]
    replacement = None
    if reuse_name:
        replacement = create_spectrum(service, "create_power_spectrum", "selected")
        assert replacement["success"], replacement
        assert replacement["data"]["result_id"] != original["data"]["result_id"]
    result = service.rebin_spectrum(
        "selected",
        rebin_factor=2.0,
        output_name="stale_child",
        expected_result_id=original["data"]["result_id"],
    )
    assert result["success"] is False, result
    assert loaded_state.get_spectrum_data("stale_child") is None
    if replacement is not None:
        assert (
            loaded_state.get_spectrum_data("selected").result_identity["result_id"]
            == replacement["data"]["result_id"]
        )


@pytest.mark.parametrize("count", [2**53 + 123, 2**63 + 123])
def test_export_projection_preserves_integer_precision_above_javascript_range(
    loaded_state, count
):
    from services.spectrum_products import spectrum_table

    result = create_spectrum(
        SpectrumService(loaded_state),
        "create_averaged_power_spectrum",
        "integer_counts",
    )
    assert result["success"], result
    stored = loaded_state.copy_spectrum_data("integer_counts")
    stored.m = np.uint64(count)
    stored.k = np.full(len(stored.freq), count + 2, dtype=np.uint64)
    table = spectrum_table(stored)
    assert table["n_averaged"].dtype == np.dtype("uint64")
    assert table["rebin_count"].dtype == np.dtype("uint64")
    assert int(table["n_averaged"][0]) == count
    assert int(table["rebin_count"][0]) == count + 2
    np.testing.assert_array_equal(
        table["n_averaged"], np.full(len(table), count, dtype=np.uint64)
    )
    np.testing.assert_array_equal(table["rebin_count"], stored.k)
