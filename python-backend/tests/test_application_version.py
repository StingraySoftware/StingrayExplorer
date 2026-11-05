"""package.json is the single source of the application version."""

import json
from pathlib import Path
import tomllib

import main
from main import APPLICATION_VERSION_ENV, application_version, create_app

ROOT = Path(__file__).resolve().parents[2]
SESSION_SECRET = "application-version-test-session-secret" * 2


def _package_version():
    return json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]


def test_api_reports_the_package_json_version(monkeypatch):
    monkeypatch.delenv(APPLICATION_VERSION_ENV, raising=False)

    app = create_app(session_secret=SESSION_SECRET)

    assert app.openapi()["info"]["version"] == _package_version()


def test_version_passed_by_electron_wins(monkeypatch):
    # A packaged backend has no package.json beside it, so Electron passes it.
    monkeypatch.setenv(APPLICATION_VERSION_ENV, "9.8.7")

    assert application_version() == "9.8.7"


def test_unknown_version_without_package_json_or_environment(monkeypatch, tmp_path):
    monkeypatch.delenv(APPLICATION_VERSION_ENV, raising=False)
    monkeypatch.setattr(main, "PACKAGE_JSON", tmp_path / "package.json")

    assert application_version() == "0+unknown"


def test_no_other_manifest_declares_an_application_version():
    pixi = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "version" not in pixi["workspace"]
    assert "project" not in pyproject
    assert not (ROOT / "setup.py").exists()
