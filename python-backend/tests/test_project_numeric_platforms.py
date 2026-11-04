"""Lossless native extended arrays and exact-only foreign-platform projections."""

import io
import zipfile

import numpy as np
import pytest

from services import project_archive
from services.project_archive import ArrayReader, ArrayWriter, SCHEMA, verify
from services.project_service import encode, decode


def archive_value(value):
    import json

    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        writer = ArrayWriter(archive)
        record = encode(value, arrays=writer)
        manifest = {"schema": SCHEMA, "arrays": writer.records}
        archive.writestr("manifest.json", json.dumps(manifest))
    stream.seek(0)
    return stream, record


@pytest.mark.parametrize("kind", ["real", "complex"])
def test_extended_array_preserves_native_dtype_and_values(kind):
    dtype = np.longdouble if kind == "real" else np.clongdouble
    value = np.array([1.25, -2.5], dtype=dtype)
    stream, record = archive_value(value)
    with zipfile.ZipFile(stream) as archive:
        manifest = verify(archive)
        restored = decode(record, arrays=ArrayReader(archive, manifest))
        np.testing.assert_array_equal(restored, value)
        assert restored.dtype == value.dtype


@pytest.mark.parametrize("kind", ["real", "complex"])
def test_exact_extended_values_reopen_on_foreign_numeric_abi(monkeypatch, kind):
    dtype = np.longdouble if kind == "real" else np.clongdouble
    if np.dtype(dtype).itemsize <= (16 if kind == "complex" else 8):
        pytest.skip(
            "This runtime has no extended floating storage; actual Linux artifacts are exchanged in CI"
        )
    value = np.array([1.25, -2.5], dtype=dtype)
    stream, record = archive_value(value)
    monkeypatch.setattr(
        project_archive, "compatible_numeric_dtype", lambda _record: None
    )
    with zipfile.ZipFile(stream) as archive:
        manifest = verify(archive)
        restored = decode(record, arrays=ArrayReader(archive, manifest))
        np.testing.assert_array_equal(restored, value)
        assert restored.dtype == np.dtype(
            "complex128" if kind == "complex" else "float64"
        )


def test_unrepresentable_extended_value_fails_before_allocation(monkeypatch):
    if np.finfo(np.longdouble).nmant <= np.finfo(np.float64).nmant:
        pytest.skip("This runtime has no additional floating precision")
    value = np.array(
        [np.longdouble(1) + np.finfo(np.longdouble).eps], dtype=np.longdouble
    )
    stream, _record = archive_value(value)
    monkeypatch.setattr(
        project_archive, "compatible_numeric_dtype", lambda _record: None
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("No scientific arrays may be allocated")

    monkeypatch.setattr(np.lib.format, "read_array", forbidden)
    with (
        zipfile.ZipFile(stream) as archive,
        pytest.raises(ValueError, match="cannot be represented exactly"),
    ):
        verify(archive, allocating=True)


def test_portable_complex_nan_does_not_hide_loss_of_the_other_component():
    if np.finfo(np.longdouble).nmant <= np.finfo(np.float64).nmant:
        pytest.skip("This runtime has no additional floating precision")
    value = np.empty(1, dtype=np.clongdouble)
    value.real = np.nan
    value.imag = np.longdouble(1) + np.finfo(np.longdouble).eps
    assert project_archive.exact_portable_dtype(value) is None


@pytest.mark.parametrize("layout", ["fortran", "strided"])
def test_portable_projection_streams_multiple_chunks_in_array_order(
    monkeypatch, layout
):
    value = np.arange(24, dtype=np.longdouble).reshape(4, 6) / 4
    value = np.asfortranarray(value) if layout == "fortran" else value[:, ::2]
    monkeypatch.setattr(project_archive, "CHUNK", 16)
    stream, record = archive_value(value)
    monkeypatch.setattr(
        project_archive, "compatible_numeric_dtype", lambda _record: None
    )
    with zipfile.ZipFile(stream) as archive:
        manifest = verify(archive)
        restored = decode(record, arrays=ArrayReader(archive, manifest))
        np.testing.assert_array_equal(restored, value)
