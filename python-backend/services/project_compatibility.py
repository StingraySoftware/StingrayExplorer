"""Explicit project compatibility policy and lossless runtime-default migration.

Saved scientific values win over runtime defaults. No calculations are rerun and
no historical result identity or software-version provenance is rewritten.
"""

from copy import deepcopy
from datetime import datetime, timezone
import warnings

from packaging.version import Version, InvalidVersion
import stingray
from stingray.bispectrum import Bispectrum

SUPPORTED = frozenset(
    [Version(f"2.2.{patch}") for patch in (*range(8), 9, 10)]
    + [Version(f"2.3.{patch}") for patch in range(3)]
)
POLICY = "stingray-explorer.project-compatibility.v1"


def checked_version(value):
    if not isinstance(value, str):
        raise ValueError("Project Stingray version is missing or invalid")
    try:
        version = Version(value)
    except InvalidVersion as error:
        raise ValueError("Invalid project Stingray version") from error
    if (
        version.is_prerelease
        or version.is_devrelease
        or version.local
        or version not in SUPPORTED
    ):
        raise ValueError(
            f"Unsupported Stingray version '{value}'; supported project versions are released 2.2 through 2.2.10 (excluding 2.2.8), and 2.3.0 through 2.3.2"
        )
    return version


def compatibility(source, runtime=None):
    runtime = stingray.__version__ if runtime is None else runtime
    checked_version(source)
    checked_version(runtime)
    return {
        "policy": POLICY,
        "source_stingray_version": source,
        "runtime_stingray_version": runtime,
        "cross_version": Version(source) != Version(runtime),
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "actions": [],
    }


def migrate_defaults(state, report, classes):
    """Supply newly introduced defaults without overwriting a saved attribute.

    Visit nested light curves and spectra too. Bispectrum has no empty
    constructor; its complete saved numerical state is retained verbatim.
    """
    seen = set()
    templates = {}

    def visit(value):
        if id(value) in seen:
            return
        seen.add(id(value))
        if type(value) in classes.values():
            cls = type(value)
            if cls is not Bispectrum:
                if cls not in templates:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        templates[cls] = vars(cls())
                missing = sorted(set(templates[cls]) - set(vars(value)))
                for name in missing:
                    vars(value)[name] = deepcopy(templates[cls][name])
                if missing:
                    report["actions"].append(
                        {"object_type": cls.__name__, "added_defaults": missing}
                    )
            for child in list(vars(value).values()):
                visit(child)
        elif isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child)

    visit(state)
    return report
