"""Real spectrum exports retain complex values and immutable result identity."""

import copy
import json

import httpx
import numpy as np
import pytest
from astropy.io import fits
from astropy.table import Table
from fastapi import FastAPI

from routes import io_utility_routes
from services import io_utility_service as io_module
from services.io_utility_service import IOUtilityService
from services.lightcurve_service import LightcurveService
from services.spectrum_service import SpectrumService
from tests.test_io_utility_service import TEST_SECRET, make_grant


@pytest.fixture(autouse=True)
def file_grant_secret(monkeypatch):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)


@pytest.fixture
def spectra(loaded_state):
    service = SpectrumService(loaded_state)
    for name, method, extra in (
        ("power", service.create_power_spectrum, {}),
        ("average_power", service.create_averaged_power_spectrum, {"segment_size": 8}),
        ("cross", service.create_cross_spectrum, {"event_list_2_name": "ev2"}),
        (
            "average_cross",
            service.create_averaged_cross_spectrum,
            {"event_list_2_name": "ev2", "segment_size": 8},
        ),
    ):
        first_name = "event_list_1_name" if "cross" in name else "event_list_name"
        result = method(
            **{first_name: "ev1", "dt": 0.0625, "output_name": name, **extra}
        )
        assert result["success"], result
    return loaded_state


def _export(service, state, name, destination, format):
    spectrum = state.get_spectrum_data(name)
    identity = getattr(spectrum, "result_identity", {})
    return service.export_object(
        "spectrum",
        name,
        format,
        str(destination),
        make_grant(destination, "write"),
        expected_result_id=identity.get("result_id", "missing-result-id"),
    )


def test_inventory_includes_named_power_cross_and_rebinned_products(spectra):
    result = SpectrumService(spectra).rebin_spectrum(
        "average_cross", 2, output_name="rebinned_cross"
    )
    assert result["success"], result
    catalog = IOUtilityService(spectra).list_exportable_objects()
    assert catalog["success"], catalog
    entries = {
        row["name"]: row
        for row in catalog["data"]["objects"]
        if row["object_type"] == "spectrum"
    }
    assert set(entries) == {
        "power",
        "average_power",
        "cross",
        "average_cross",
        "rebinned_cross",
    }
    for name, entry in entries.items():
        assert entry["exportable"], entry
        assert entry["formats"][:4] == ["csv", "ecsv", "json", "fits"]
        assert (
            entry["result_id"]
            == spectra.get_spectrum_data(name).result_identity["result_id"]
        )
        assert entry["backend_session_id"]


@pytest.mark.parametrize("name", ["power", "average_power", "cross", "average_cross"])
@pytest.mark.parametrize("format", ["csv", "ecsv", "json", "fits", "hdf5"])
def test_real_spectrum_exports_preserve_numeric_products_and_original_inputs(
    spectra, tmp_path, name, format
):
    if format == "hdf5" and io_module._optional_hdf5_runtime()[0] is None:
        pytest.skip("Optional h5py runtime is unavailable")
    spectrum = spectra.get_spectrum_data(name)
    identity = copy.deepcopy(getattr(spectrum, "result_identity", {}))
    # The export must read the saved product's provenance rather than the
    # current mutable dataset or current parameters in a UI.
    spectra.get_event_data("ev1").mission = "CHANGED AFTER CALCULATION"
    destination = tmp_path / f"{name}.{format}"
    result = _export(IOUtilityService(spectra), spectra, name, destination, format)
    assert result["success"], result
    assert result["data"]["verified"]
    assert result["data"]["verification"]["semantic_round_trip"]

    metadata = None
    if format in {"csv", "ecsv"}:
        table = Table.read(destination, format=f"ascii.{format}")
        metadata = table.meta if format == "ecsv" else None
    elif format == "fits":
        table = Table.read(destination, format="fits", hdu=1)
        with fits.open(destination) as hdul:
            text = hdul["METADATA"].data["JSON"][0]
            metadata = json.loads(text)
    elif format == "hdf5":
        with destination.open("rb") as stream:
            table, _ = io_module._read_hdf5_table(
                stream,
                io_module._optional_hdf5_runtime()[0],
                object_type="spectrum",
                object_name=name,
            )
        metadata = table.meta
    else:
        payload = json.loads(destination.read_text())
        table = Table(payload["columns"])
        metadata = payload["metadata"]
        assert payload["object_type"] == "spectrum"
    np.testing.assert_array_equal(table["freq"], spectrum.freq)
    if "cross" in name:
        restored = np.asarray(table["power_real"]) + 1j * np.asarray(
            table["power_imag"]
        )
        np.testing.assert_array_equal(restored, spectrum.power)
        np.testing.assert_allclose(
            table["power_magnitude"], np.abs(spectrum.power), rtol=0, atol=0
        )
        np.testing.assert_allclose(
            table["power_phase"], np.angle(spectrum.power), rtol=0, atol=0
        )
        assert np.any(np.abs(table["power_imag"]) > 0)
    else:
        np.testing.assert_array_equal(table["power"], spectrum.power)
    if metadata is not None:
        assert metadata["result_identity"] == identity
        assert "CHANGED AFTER CALCULATION" not in json.dumps(metadata)
    else:
        assert any("metadata" in warning for warning in result["data"]["warnings"])


def test_export_rejects_missing_or_stale_spectrum_identity_before_publication(
    spectra, tmp_path
):
    service = IOUtilityService(spectra)
    destination = tmp_path / "stale.ecsv"
    for expected_id in (None, "different-result-id"):
        arguments = {} if expected_id is None else {"expected_result_id": expected_id}
        result = service.export_object(
            "spectrum",
            "power",
            "ecsv",
            str(destination),
            make_grant(destination, "write"),
            **arguments,
        )
        assert not result["success"], result
        assert not destination.exists()
        assert list(tmp_path.glob(".stingray-export-*")) == []


def test_spectrum_export_refuses_overwrite(spectra, tmp_path):
    destination = tmp_path / "power.ecsv"
    destination.write_text("preserve existing artifact")
    result = _export(IOUtilityService(spectra), spectra, "power", destination, "ecsv")
    assert not result["success"]
    assert destination.read_text() == "preserve existing artifact"


def test_deleted_then_recreated_name_cannot_export_a_stale_catalog_identity(
    spectra, tmp_path
):
    previous = spectra.get_spectrum_data("power").result_identity["result_id"]
    spectra.remove_spectrum_data("power")
    created = SpectrumService(spectra).create_power_spectrum(
        "ev1", 0.125, output_name="power"
    )
    assert created["success"], created
    assert spectra.get_spectrum_data("power").result_identity["result_id"] != previous
    destination = tmp_path / "reused-name.ecsv"
    result = IOUtilityService(spectra).export_object(
        "spectrum",
        "power",
        "ecsv",
        str(destination),
        make_grant(destination, "write"),
        expected_result_id=previous,
    )
    assert not result["success"], result
    assert not destination.exists()


@pytest.mark.parametrize("corruption", ["numeric", "identity", "units"])
def test_spectrum_semantic_reopen_rejects_same_size_corruption(
    spectra, tmp_path, monkeypatch, corruption
):
    original_read = Table.read

    def corrupted_read(*args, **kwargs):
        reopened = original_read(*args, **kwargs)
        if corruption == "numeric":
            reopened["power_real"][0] += 1
        elif corruption == "identity":
            reopened.meta["result_identity"]["result_id"] = "wrong-result"
        else:
            reopened["freq"].unit = "s"
        return reopened

    monkeypatch.setattr(io_module.Table, "read", corrupted_read)
    destination = tmp_path / f"corrupt-{corruption}.ecsv"
    result = _export(IOUtilityService(spectra), spectra, "cross", destination, "ecsv")
    assert not result["success"], result
    assert "semantic verification" in result["error"]
    assert not destination.exists()
    assert list(tmp_path.glob(".stingray-export-*")) == []


@pytest.mark.parametrize("corruption", ["numeric", "identity", "column_order"])
def test_json_spectrum_verifies_values_identity_and_column_order(
    spectra, tmp_path, monkeypatch, corruption
):
    original_load = json.load

    def corrupted_load(*args, **kwargs):
        payload = original_load(*args, **kwargs)
        if corruption == "numeric":
            payload["columns"]["power_real"][0] += 1
        elif corruption == "identity":
            payload["metadata"]["result_identity"]["result_id"] = "wrong-result"
        else:
            payload["columns"] = dict(reversed(list(payload["columns"].items())))
        return payload

    monkeypatch.setattr(io_module.json, "load", corrupted_load)
    destination = tmp_path / f"corrupt-{corruption}.json"
    result = _export(IOUtilityService(spectra), spectra, "cross", destination, "json")
    assert not result["success"], result
    assert "semantic verification" in result["error"]
    assert not destination.exists()
    assert list(tmp_path.glob(".stingray-export-*")) == []


def test_spectrum_snapshot_caps_run_before_deepcopy_or_projection(
    spectra, tmp_path, monkeypatch
):
    def unexpected_allocation(*args, **kwargs):
        raise AssertionError(
            "A rejected export must not allocate a snapshot or projection"
        )

    monkeypatch.setattr(io_module, "MAX_EXPORT_ROWS", 2)
    monkeypatch.setattr(io_module.copy, "deepcopy", unexpected_allocation)
    monkeypatch.setattr(io_module, "spectrum_table", unexpected_allocation)
    destination = tmp_path / "too-large.ecsv"
    result = _export(IOUtilityService(spectra), spectra, "power", destination, "ecsv")
    assert not result["success"], result
    assert "cap" in result["error"].lower()
    assert not destination.exists()


@pytest.mark.parametrize(
    "expected,actual",
    [
        (np.asarray([2**53 + 1], dtype=np.int64), np.asarray([float(2**53)])),
        (np.asarray([2**63 - 1], dtype=np.int64), np.asarray([2**63], dtype=np.uint64)),
    ],
)
def test_semantic_verifier_does_not_round_distinct_large_numeric_values(
    expected, actual
):
    original = Table({"freq": [1.0], "n_averaged": expected})
    reopened = Table({"freq": [1.0], "n_averaged": actual})
    with pytest.raises(ValueError, match="values"):
        io_module._verify_spectrum_table(original, reopened, "csv")


@pytest.mark.parametrize("corruption", ["shape", "normalization"])
def test_inventory_disables_invalid_projection_even_without_optional_hdf5(
    spectra, monkeypatch, corruption
):
    spectrum = spectra.get_spectrum_data("power")
    if corruption == "shape":
        spectrum.power = spectrum.power[:-1]
    else:
        spectrum.norm = "unrecognized"
    monkeypatch.setattr(
        io_module, "_optional_hdf5_runtime", lambda: (None, "not installed")
    )
    catalog = IOUtilityService(spectra).list_exportable_objects()
    assert catalog["success"], catalog
    entry = next(row for row in catalog["data"]["objects"] if row["name"] == "power")
    assert not entry["exportable"]
    assert entry["formats"] == []
    assert "aligned" in entry["reason"] or "normalization" in entry["reason"]


def test_dynamical_spectrum_is_explicitly_nonexportable_until_2d_projection_supported(
    spectra,
):
    result = SpectrumService(spectra).create_dynamical_power_spectrum(
        "ev1", 0.0625, 8, output_name="dynamic"
    )
    assert result["success"], result
    catalog = IOUtilityService(spectra).list_exportable_objects()
    entry = next(row for row in catalog["data"]["objects"] if row["name"] == "dynamic")
    assert not entry["exportable"]
    assert entry["formats"] == []
    assert (
        "dynamical" in entry["reason"].lower()
        or "two-dimensional" in entry["reason"].lower()
    )


def test_identified_lightcurve_catalog_export_and_stale_guard_preserve_original_inputs(
    spectra, tmp_path
):
    curves = LightcurveService(spectra)
    created = curves.create_lightcurve_from_event_list("ev1", 0.5, "selected_curve")
    assert created["success"], created
    identity = copy.deepcopy(
        spectra.get_lightcurve_data("selected_curve").result_identity
    )
    service = IOUtilityService(spectra)
    catalog = service.list_exportable_objects()
    entry = next(
        row for row in catalog["data"]["objects"] if row["name"] == "selected_curve"
    )
    assert entry["result_id"] == identity["result_id"]
    assert entry["backend_session_id"] == identity["backend_session_id"]

    destination = tmp_path / "selected_curve.ecsv"
    exported = service.export_object(
        "lightcurve",
        "selected_curve",
        "ecsv",
        str(destination),
        make_grant(destination, "write"),
        expected_result_id=identity["result_id"],
    )
    assert exported["success"], exported
    assert exported["data"]["result_id"] == identity["result_id"]
    assert (
        Table.read(destination, format="ascii.ecsv").meta["result_identity"] == identity
    )

    spectra.remove_lightcurve_data("selected_curve")
    recreated = curves.create_lightcurve_from_event_list("ev1", 1.0, "selected_curve")
    assert recreated["success"], recreated
    stale_destination = tmp_path / "stale_curve.ecsv"
    rejected = service.export_object(
        "lightcurve",
        "selected_curve",
        "ecsv",
        str(stale_destination),
        make_grant(stale_destination, "write"),
        expected_result_id=identity["result_id"],
    )
    assert not rejected["success"], rejected
    assert not stale_destination.exists()


@pytest.mark.asyncio
async def test_export_route_forwards_exact_selected_spectrum_identity(
    spectra, tmp_path
):
    app = FastAPI()
    app.state.state_manager = spectra
    app.state.performance_monitor = None
    app.include_router(io_utility_routes.router)
    destination = tmp_path / "route-spectrum.json"
    request = {
        "object_type": "spectrum",
        "object_name": "cross",
        "format": "json",
        "destination_path": str(destination),
        "destination_grant": make_grant(destination, "write"),
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        rejected = await client.post("/export", json=request)
        assert rejected.status_code == 200
        assert rejected.json()["success"] is False
        assert not destination.exists()
        identity = spectra.get_spectrum_data("cross").result_identity
        response = await client.post(
            "/export", json={**request, "expected_result_id": identity["result_id"]}
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True, payload
    assert payload["data"]["result_id"] == identity["result_id"]
    assert (
        json.loads(destination.read_text())["metadata"]["result_identity"] == identity
    )
