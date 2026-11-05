"""The repository must never track local assistant or reference material."""

from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_repository_hygiene.py"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _git(repository, *args):
    subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
    )


def _repository(tmp_path, tracked_files):
    _git(tmp_path, "init", "-q")
    for relative_path in tracked_files:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content\n", encoding="utf-8")
        _git(tmp_path, "add", "--force", relative_path)
    return tmp_path


def _check(repository):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repository", str(repository)],
        capture_output=True,
        text=True,
    )


def test_clean_repository_passes(tmp_path):
    result = _check(_repository(tmp_path, ["README.md", "docs/claude.txt"]))

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "private_path",
    [
        "AI_DOCS/guide.md",
        ".claude/settings.local.json",
        "ai_docs/notes.md",
        "nested/AI_DOCS/notes.md",
        "nested/.claude/launch.json",
    ],
)
def test_tracked_private_material_fails_and_is_named(tmp_path, private_path):
    result = _check(_repository(tmp_path, ["README.md", private_path]))

    assert result.returncode == 1
    assert private_path in result.stderr


def test_this_repository_tracks_no_private_material():
    result = _check(ROOT)

    assert result.returncode == 0, result.stderr


def test_ci_runs_the_hygiene_check():
    workflow = (ROOT / ".github/workflows/cross-platform.yml").read_text(
        encoding="utf-8"
    )

    assert "python scripts/check_repository_hygiene.py" in workflow
