# Sphinx configuration for the Stingray Explorer documentation.
#
# The documentation is prose only. It does not import the application, so
# Read the Docs installs nothing but docs/requirements.txt.

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

project = "Stingray Explorer"
author = "Kartik Mandar"
copyright = "2024–2026, Kartik Mandar"
# package.json is the application's only version source.
release = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
version = ".".join(release.split(".")[:2])

extensions = ["sphinx.ext.intersphinx"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "stingray": ("https://docs.stingray.science/en/stable/", None),
}

exclude_patterns = []

html_theme = "sphinx_rtd_theme"
