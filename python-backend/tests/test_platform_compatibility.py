"""Platform boundary regressions that retain numerical and identity assertions."""

import ast
import io
from pathlib import Path
import platform
import re
import subprocess
import sys

import numpy as np
import pytest

from services import gti_service
from services.gti_service import GTIService
from services.project_compatibility import SUPPORTED
from services.state_manager import StateManager
from services.utility_helpers import verify_file_grant
from tests.file_grants import sign_grant
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]


def test_retained_fits_snapshot_preserves_binary_bytes_on_windows():
    from services.data_service import _scientific_reader_source

    original = b"SIMPLE  = T\n\r\n\x1a\x00" + bytes(range(256)) * 32
    with _scientific_reader_source(io.BytesIO(original), fmt="ogip") as path:
        assert Path(path).read_bytes() == original
    assert not Path(path).exists()


def test_manual_gti_upstream_precision_is_independent_of_native_longdouble(monkeypatch):
    original = gti_service.split_gtis_by_exposure
    observed = []

    def capture(gtis, *args, **kwargs):
        observed.append(gtis.dtype)
        return original(gtis, *args, **kwargs)

    monkeypatch.setattr(gti_service, "split_gtis_by_exposure", capture)
    source = np.array([[50000.0, 50001.8]], dtype=np.longdouble)
    before = source.copy()
    result = GTIService(StateManager()).split_by_exposure(source, 0.3)
    assert result["success"], result
    assert result["data"]["chunk_count"] == 6
    assert result["data"]["source_exposure_s"] == pytest.approx(
        result["data"]["output_exposure_s"]
    )
    assert observed == [np.dtype("float64")]
    np.testing.assert_array_equal(source, before)


def test_independent_native_grant_signer_roundtrips_unicode_and_spaces(
    tmp_path, monkeypatch
):
    secret = "cross-platform-synthetic-test-secret-32-bytes"
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", secret)
    path = tmp_path / "observation Ω with spaces.evt"
    path.write_bytes(b"original observation")
    grant = sign_grant(secret, path, "read")
    assert (
        verify_file_grant(str(path), grant, access="read", must_exist=True)
        == path.resolve()
    )


def test_full_suite_ci_matrix_matches_every_supported_stingray_release():
    workflow = (ROOT / ".github/workflows/cross-platform.yml").read_text(
        encoding="utf-8"
    )
    versions = ast.literal_eval(
        re.search(r"^        stingray: (\[.*\])$", workflow, re.M)[1]
    )
    assert {Version(value) for value in versions} == SUPPORTED
    assert len(versions) == len(SUPPORTED)
    assert '["ubuntu-24.04", "windows-2025"]' in workflow
    assert "inputs.include_windows" in workflow
    assert "default: false" in workflow
    assert "scripts/scientific_compatibility.py" in workflow
    assert "scripts/project_platform_fixture.py read" in workflow


def test_platform_gate_cannot_certify_the_wrong_operating_system():
    wrong = "Windows" if platform.system() != "Windows" else "Linux"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_platform.py"), "--expected", wrong],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert f"Expected a native {wrong} runtime" in result.stderr


def test_project_interchange_tool_preserves_saved_arrays_and_complete_identities(
    tmp_path,
):
    script = ROOT / "scripts/project_platform_fixture.py"
    for mode in ("write", "read"):
        result = subprocess.run(
            [sys.executable, str(script), mode, str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "PASS" in result.stdout


def test_project_interchange_tool_rejects_missing_fixtures(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/project_platform_fixture.py"),
            "read",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "No project fixtures found" in result.stderr
