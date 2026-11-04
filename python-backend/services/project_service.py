"""Versioned, non-executable, self-contained analysis session persistence."""

import base64
import io
import math
import json
import zipfile
from datetime import datetime, timezone

from astropy.io import fits
from astropy.io.fits.header import _HeaderCommentaryCards
import numpy as np
import stingray
from stingray.bispectrum import Bispectrum
from stingray import EventList, Lightcurve, Powerspectrum, AveragedPowerspectrum
from stingray import Crossspectrum, AveragedCrossspectrum, DynamicalPowerspectrum

from .base_service import BaseService
from .project_compatibility import compatibility, migrate_defaults, checked_version
from .secure_publication import open_secure_publication
from .utility_helpers import open_verified_read_grant

SCHEMA = "stingray-explorer.project.v1"
MAX_BYTES = 128 * 1024**2
CLASSES = {
    cls.__name__: cls
    for cls in (
        Bispectrum,
        EventList,
        Lightcurve,
        Powerspectrum,
        AveragedPowerspectrum,
        Crossspectrum,
        AveragedCrossspectrum,
        DynamicalPowerspectrum,
    )
}
GROUPS = ("event_data", "lightcurve_data", "spectrum_data", "analysis_results")


def encode(value, depth=0, budget=None, arrays=None):
    if depth > 40:
        raise ValueError("Project nesting exceeds the supported limit")
    if budget is None:
        budget = [0]
    budget[0] += (
        value.nbytes
        if isinstance(value, (np.ndarray, np.generic))
        else len(value)
        if isinstance(value, str)
        else 16
    )
    if arrays is None and budget[0] > MAX_BYTES:
        raise ValueError("Project exceeds the allocation limit")

    def child(item):
        return encode(item, depth + 1, budget, arrays)

    if isinstance(value, _HeaderCommentaryCards):
        return child(list(value))
    if isinstance(value, fits.Header):
        return {"$fits_header": value.tostring(sep="\n", endcard=False, padding=False)}
    if np.ma.isMaskedArray(value):
        return {
            "$masked": child(value.data),
            "mask": child(np.ma.getmaskarray(value)),
            "fill": child(value.fill_value),
        }
    if isinstance(value, (np.ndarray, np.generic)):
        if arrays is not None:
            return arrays(value)
        array = np.asarray(value)
        if array.dtype.hasobject or array.nbytes > MAX_BYTES:
            raise ValueError("Unsupported or oversized project array")
        stream = io.BytesIO()
        np.save(stream, array, allow_pickle=False)
        return {
            "$array": base64.b64encode(stream.getvalue()).decode("ascii"),
            "scalar": isinstance(value, np.generic),
        }
    if type(value).__name__ in CLASSES and type(value) is CLASSES[type(value).__name__]:
        return {"$object": type(value).__name__, "attributes": child(vars(value))}
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("Project mappings require string keys")
        return {
            "$dict": {
                key: child(item)
                for key, item in value.items()
                if not any(
                    word in key.lower()
                    for word in ("grant", "secret", "credential", "password", "token")
                )
            }
        }
    if isinstance(value, tuple):
        return {"$tuple": [child(item) for item in value]}
    if isinstance(value, list):
        return [child(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {"$float": str(value)}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, complex):
        return {"$complex": [value.real, value.imag]}
    raise ValueError(f"Unsupported project value: {type(value).__name__}")


def decode(value, depth=0, arrays=None):
    if depth > 40:
        raise ValueError("Project nesting exceeds the supported limit")

    def child(item):
        return decode(item, depth + 1, arrays)

    if isinstance(value, list):
        return [child(item) for item in value]
    if not isinstance(value, dict):
        return value
    if "$fits_header" in value and len(value) == 1:
        return fits.Header.fromstring(value["$fits_header"], sep="\n")
    if "$masked" in value and set(value) == {"$masked", "mask", "fill"}:
        return np.ma.array(
            child(value["$masked"]),
            mask=child(value["mask"]),
            fill_value=child(value["fill"]),
        )
    if "$tuple" in value and len(value) == 1:
        return tuple(child(item) for item in value["$tuple"])
    if "$array_file" in value:
        if arrays is None:
            raise ValueError("External array outside a project archive")
        return arrays(value)
    if "$array" in value:
        if set(value) != {"$array", "scalar"} or not isinstance(value["scalar"], bool):
            raise ValueError("Invalid project array record")
        raw = base64.b64decode(value["$array"], validate=True)
        # Read and validate the header before allocating an array from untrusted dimensions.
        stream = io.BytesIO(raw)
        version = np.lib.format.read_magic(stream)
        if version == (1, 0):
            shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
        elif version == (2, 0):
            shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
        else:
            raise ValueError("Unsupported array encoding")

        size = math.prod(shape) * dtype.itemsize
        if dtype.hasobject or size > MAX_BYTES or size != len(raw) - stream.tell():
            raise ValueError("Invalid or oversized project array")
        array = np.load(io.BytesIO(raw), allow_pickle=False)
        return array[()] if value.get("scalar") else array
    if "$dict" in value and len(value) == 1:
        return {key: child(item) for key, item in value["$dict"].items()}
    if (
        "$float" in value
        and len(value) == 1
        and value["$float"] in {"nan", "inf", "-inf"}
    ):
        return float(value["$float"])
    if "$complex" in value and len(value) == 1:
        return complex(*value["$complex"])
    if "$object" in value and set(value) == {"$object", "attributes"}:
        cls = CLASSES.get(value["$object"])
        if cls is None:
            raise ValueError("Unsupported scientific object class")
        attributes = child(value["attributes"])
        if not isinstance(attributes, dict) or any(
            key.startswith("__") for key in attributes
        ):
            raise ValueError("Invalid scientific attributes")
        obj = cls.__new__(cls)
        vars(obj).update(attributes)
        return obj
    raise ValueError("Invalid project value encoding")


def validate_workspace(workspace):
    if workspace is not None:
        if (
            not isinstance(workspace, dict)
            or workspace.get("version") != 1
            or not isinstance(workspace.get("fields"), dict)
        ):
            raise ValueError("Unsupported workspace session")
        if "path" in workspace and (
            not isinstance(workspace["path"], str)
            or not workspace["path"].startswith("/")
            or workspace["path"].startswith("//")
        ):
            raise ValueError("Invalid workspace route")
        preferences = workspace.get("preferences", {})
        if (
            not isinstance(preferences, dict)
            or set(preferences) - {"logPanelOpen", "rightToolbarCollapsed"}
            or any(not isinstance(value, bool) for value in preferences.values())
        ):
            raise ValueError("Invalid workspace preferences")
        json.dumps(workspace, allow_nan=False)


class ProjectService(BaseService):
    def save(self, destination_path, destination_grant, renderer, workspace=None):
        try:
            validate_workspace(workspace)
            checked_version(stingray.__version__)
            from .project_archive import (
                ArrayWriter,
                SCHEMA as ARCHIVE_SCHEMA,
                MANIFEST_LIMIT,
                verify,
            )

            with open_secure_publication(
                destination_path, destination_grant
            ) as publication:
                publication.assert_destination_available()
                publication.reserve_staging(".srproj")
                with publication.open_writer("wb", encoding=None) as stream:
                    with zipfile.ZipFile(
                        stream, "w", compression=zipfile.ZIP_STORED, allowZip64=True
                    ) as archive:
                        writer = ArrayWriter(archive)
                        # Serialize under the state lock: deletion must not clear
                        # source arrays during this coherent streaming snapshot.
                        with self.state._lock:
                            payload = {
                                "schema": ARCHIVE_SCHEMA,
                                "stingray_version": stingray.__version__,
                                "compatibility_history": getattr(
                                    self.state, "_project_compatibility_history", []
                                ),
                                "created_at": datetime.now(timezone.utc).isoformat(),
                                "state": encode(
                                    {
                                        group: getattr(self.state, "_" + group)
                                        for group in GROUPS
                                    },
                                    arrays=writer,
                                ),
                                "event_ids": dict(self.state._event_identities),
                                "lightcurve_ids": dict(
                                    self.state._lightcurve_identities
                                ),
                                "renderer": encode(renderer, arrays=writer),
                                "workspace": encode(workspace, arrays=writer),
                                "arrays": writer.records,
                            }
                        metadata = json.dumps(payload, allow_nan=False).encode("utf-8")
                        if len(metadata) > MANIFEST_LIMIT:
                            raise ValueError(
                                "Project metadata exceeds the 64 MiB limit"
                            )
                        archive.writestr("manifest.json", metadata)
                with publication.open_reader("rb", encoding=None) as stream:
                    with zipfile.ZipFile(stream) as archive:
                        if verify(archive) != payload:
                            raise ValueError("Project manifest verification failed")
                byte_size = publication.verified_size()
                publication.publish()
            return self.create_result(
                success=True, data={"bytes": byte_size}, message="Project saved"
            )
        except Exception as error:
            return self.handle_error(error, "Saving project")

    def reopen(self, file_path, file_grant):
        try:
            from .project_archive import ArrayReader, verify

            with open_verified_read_grant(file_path, file_grant) as granted:
                if zipfile.is_zipfile(granted.stream):
                    granted.stream.seek(0)
                    with zipfile.ZipFile(granted.stream) as archive:
                        payload = verify(archive, allocating=True)
                        report = compatibility(payload.get("stingray_version"))
                        reader = ArrayReader(archive, payload)
                        state = decode(payload["state"], arrays=reader)
                        renderer = decode(payload["renderer"], arrays=reader)
                        workspace = decode(payload.get("workspace"), arrays=reader)
                else:
                    # Preserve compatibility with the original bounded JSON format.
                    granted.stream.seek(0)
                    raw = granted.stream.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES:
                        raise ValueError("Legacy JSON project exceeds its size limit")

                    def reject_constant(value):
                        raise ValueError("Non-finite JSON constants are unsupported")

                    payload = json.loads(raw, parse_constant=reject_constant)
                    if payload.get("schema") != SCHEMA:
                        raise ValueError(
                            "Unsupported project schema or Stingray version"
                        )
                    report = compatibility(payload.get("stingray_version"))
                    state = decode(payload["state"])
                    renderer = decode(payload["renderer"])
                    workspace = (
                        decode(payload["workspace"]) if "workspace" in payload else None
                    )
            history = payload.get("compatibility_history", [])
            if not isinstance(history, list) or any(
                not isinstance(item, dict) for item in history
            ):
                raise ValueError("Invalid project compatibility history")
            if len(history) > 1000:
                raise ValueError(
                    "Project compatibility history exceeds the supported limit"
                )
            json.dumps(history, allow_nan=False)
            report["source_project_schema"] = payload["schema"]
            report["source_project_created_at"] = payload.get("created_at")
            migrate_defaults(state, report, CLASSES)
            validate_workspace(workspace)
            if set(state) != set(GROUPS) or not isinstance(renderer, dict):
                raise ValueError("Invalid project workspace")
            json.dumps(renderer, allow_nan=False)
            if any(
                not isinstance(record, dict) or "result" not in record
                for record in renderer.values()
            ):
                raise ValueError("Invalid saved analysis records")
            for record in renderer.values():
                if (
                    not isinstance(record.get("resultInputs"), (dict, type(None)))
                    or not isinstance(record.get("resultIdentity"), (dict, type(None)))
                    or not isinstance(record.get("warnings", []), list)
                    or not isinstance(record.get("stale", False), bool)
                ):
                    raise ValueError("Invalid saved analysis metadata")
            for group in GROUPS:
                if not isinstance(state[group], dict) or any(
                    not isinstance(name, str) or not name for name in state[group]
                ):
                    raise ValueError("Invalid project object names")
                expected = (
                    EventList
                    if group == "event_data"
                    else Lightcurve
                    if group == "lightcurve_data"
                    else None
                )
                if expected and any(
                    not isinstance(obj, expected) for obj in state[group].values()
                ):
                    raise ValueError("Invalid project scientific object")
                if group == "spectrum_data" and any(
                    type(obj).__name__ not in CLASSES
                    or isinstance(obj, (EventList, Lightcurve))
                    for obj in state[group].values()
                ):
                    raise ValueError("Invalid project spectrum")
            from .spectrum_products import spectrum_identity

            for obj in state["event_data"].values():
                times = np.asarray(obj.time)
                if (
                    times.ndim != 1
                    or times.dtype.kind not in "fiu"
                    or not np.isfinite(times).all()
                ):
                    raise ValueError("Invalid saved event times")
            for obj in state["lightcurve_data"].values():
                if (
                    np.ndim(obj.time) != 1
                    or np.shape(obj.time) != np.shape(obj.counts)
                    or not np.isfinite(obj.dt)
                    or obj.dt <= 0
                ):
                    raise ValueError("Invalid saved light curve")
            for obj in state["spectrum_data"].values():
                if not isinstance(obj, DynamicalPowerspectrum):
                    # Validate the saved object without building a second full
                    # export table for a potentially multi-gigabyte spectrum.
                    spectrum_identity(obj)
                    frequency = np.asarray(obj.freq)
                    power = np.asarray(obj.power)
                    if (
                        frequency.ndim != 1
                        or not frequency.size
                        or frequency.dtype.kind not in "fiu"
                        or power.shape != frequency.shape
                        or power.dtype.kind not in "fiuc"
                        or obj.norm not in {"leahy", "frac", "abs", "none"}
                    ):
                        raise ValueError("Invalid saved spectrum")
                    for offset in range(0, len(frequency), 131072):
                        if not np.isfinite(frequency[offset : offset + 131072]).all():
                            raise ValueError("Invalid saved spectrum frequencies")
                    for attribute in ("power_err", "df", "m", "k"):
                        value = getattr(obj, attribute, None)
                        if value is not None:
                            array = np.asarray(value)
                            if array.dtype.kind not in "fiuc" or (
                                array.ndim != 0 and array.shape != frequency.shape
                            ):
                                raise ValueError("Invalid saved spectrum column")
            for group, key in (
                ("event_data", "event_ids"),
                ("lightcurve_data", "lightcurve_ids"),
            ):
                if set(payload[key]) != set(state[group]) or any(
                    not isinstance(item, str) or not item
                    for item in payload[key].values()
                ):
                    raise ValueError("Invalid project dataset identities")
            with self.state._lock:
                for group in GROUPS:
                    if set(getattr(self.state, "_" + group)) & set(state[group]):
                        raise ValueError(
                            "Project names conflict with the current workspace; reopen in an empty backend"
                        )
                for group in GROUPS:
                    getattr(self.state, "_" + group).update(state[group])
                self.state._project_compatibility_history = [
                    *getattr(self.state, "_project_compatibility_history", []),
                    *history,
                    report,
                ]
                self.state._event_identities.update(payload["event_ids"])
                self.state._lightcurve_identities.update(payload["lightcurve_ids"])
            return self.create_result(
                success=True,
                data={
                    "compatibility": report,
                    "renderer": renderer,
                    "workspace": workspace,
                    "counts": {key: len(value) for key, value in state.items()},
                },
                message=(
                    f"Project reopened: saved with Stingray {report['source_stingray_version']}, running {report['runtime_stingray_version']}. Original results and provenance preserved."
                    if report["cross_version"]
                    else "Project reopened"
                ),
                warnings=[
                    f"Saved with Stingray {report['source_stingray_version']}; reopened with {report['runtime_stingray_version']}. Saved values and original provenance are preserved; new calculations use the current runtime."
                ]
                if report["cross_version"]
                else [],
            )
        except Exception as error:
            return self.handle_error(error, "Reopening project")
