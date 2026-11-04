"""Streaming ZIP64 project arrays, bounded metadata, and verified manifests."""

import hashlib
import json
import math
import re
import zipfile

import numpy as np
import psutil

SCHEMA = "stingray-explorer.project.v2"
MANIFEST_LIMIT = 64 * 1024**2
CHUNK = 1024**2


def floating_format(dtype):
    """Describe the floating ABI: f16 can mean x87 or IEEE quad."""
    info = np.finfo(dtype)
    return {"mantissa": info.nmant, "maxexp": info.maxexp}


def compatible_numeric_dtype(record):
    try:
        dtype = np.dtype(record["numeric_dtype"])
        if floating_format(dtype) == record["numeric_format"]:
            return dtype
    except (TypeError, ValueError):
        pass
    return None


def exact_portable_dtype(array):
    """Check in bounded chunks, including each complex component separately."""
    dtype = np.dtype("complex128" if array.dtype.kind == "c" else "float64")
    block = max(1, CHUNK // array.dtype.itemsize)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        for start in range(0, array.size, block):
            original = array.flat[start : start + block]
            restored = original.astype(dtype).astype(array.dtype)
            components = ("real", "imag") if array.dtype.kind == "c" else ("real",)
            if any(
                not np.array_equal(
                    getattr(original, part), getattr(restored, part), equal_nan=True
                )
                for part in components
            ):
                return None
    return dtype


class HashWriter:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.size = 0

    def write(self, data):
        self.digest.update(data)
        self.size += len(data)
        return self.stream.write(data)

    def flush(self):
        self.stream.flush()


class ArrayWriter:
    def __init__(self, archive):
        self.archive = archive
        self.records = {}
        self.seen = {}

    def __call__(self, value):
        identity = id(value)
        if identity in self.seen:
            return self.seen[identity][1]
        array = np.asarray(value)
        if array.dtype.hasobject:
            raise ValueError("Object arrays cannot be saved in a project")
        numeric_record = {}
        stored = array
        if array.dtype.kind in "fc" and array.dtype.itemsize > (
            16 if array.dtype.kind == "c" else 8
        ):
            # Keep the original bytes readable even on NumPy builds without
            # this dtype. A void array has a portable, non-executable header.
            stored = array.view(f"V{array.dtype.itemsize}")
            numeric_record = {
                "numeric_dtype": array.dtype.str,
                "numeric_format": floating_format(array.dtype),
            }
            portable_dtype = exact_portable_dtype(array)
            if portable_dtype is not None:
                numeric_record["portable_file"] = self.write_array(
                    array, cast_dtype=portable_dtype
                )
        name = self.write_array(stored, numeric_record)
        reference = {"$array_file": name, "scalar": isinstance(value, np.generic)}
        if numeric_record:
            # Older application readers reject this reference instead of
            # accidentally importing the opaque raw bytes as scientific data.
            reference["numeric"] = True
        # Retain the object while writing so Python cannot reuse an identifier.
        self.seen[identity] = (value, reference)
        return reference

    def write_array(self, array, metadata=None, *, cast_dtype=None):
        name = f"arrays/{len(self.records):08d}.npy"
        with self.archive.open(name, "w", force_zip64=True) as stream:
            writer = HashWriter(stream)
            if cast_dtype is None:
                np.lib.format.write_array(writer, array, allow_pickle=False)
            else:
                np.lib.format.write_array_header_2_0(
                    writer,
                    {
                        "descr": np.lib.format.dtype_to_descr(cast_dtype),
                        "fortran_order": False,
                        "shape": array.shape,
                    },
                )
                block = max(1, CHUNK // array.dtype.itemsize)
                for start in range(0, array.size, block):
                    writer.write(
                        array.flat[start : start + block].astype(cast_dtype).tobytes()
                    )
        self.records[name] = {
            "sha256": writer.digest.hexdigest(),
            "size": writer.size,
            **(metadata or {}),
        }
        return name


def verify(archive, *, allocating=False):
    infos = archive.infolist()
    names = [info.filename for info in infos]
    if len(names) != len(set(names)) or "manifest.json" not in names:
        raise ValueError("Invalid or duplicate project archive entries")
    info = archive.getinfo("manifest.json")
    if info.file_size > MANIFEST_LIMIT:
        raise ValueError("Project metadata exceeds the 64 MiB limit")

    def reject(value):
        raise ValueError("Non-finite project JSON constant")

    payload = json.loads(archive.read(info), parse_constant=reject)
    if payload.get("schema") != SCHEMA or not isinstance(payload.get("arrays"), dict):
        raise ValueError("Unsupported project archive schema")
    if set(names) != {"manifest.json", *payload["arrays"]}:
        raise ValueError("Project archive entries do not match its manifest")
    total = 0
    for name, record in payload["arrays"].items():
        if not name.startswith("arrays/") or not name.endswith(".npy") or ".." in name:
            raise ValueError("Invalid project array reference")
        info = archive.getinfo(name)
        if info.compress_type != zipfile.ZIP_STORED or info.file_size != record["size"]:
            raise ValueError("Invalid project array size or compression")
        with archive.open(info) as stream:
            version = np.lib.format.read_magic(stream)
            if version == (1, 0):
                shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
            elif version == (2, 0):
                shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
            else:
                raise ValueError("Unsupported project array encoding")
            size = math.prod(shape) * dtype.itemsize
            if (
                dtype.hasobject
                or any(dimension < 0 for dimension in shape)
                or size != info.file_size - stream.tell()
            ):
                raise ValueError("Invalid project array dimensions or dtype")
            total += size
            if "numeric_dtype" in record:
                descriptor = record["numeric_dtype"]
                if (
                    not isinstance(descriptor, str)
                    or re.fullmatch(r"[<>][fc](12|16|24|32)", descriptor) is None
                    or dtype.kind != "V"
                    or dtype.itemsize != int(descriptor[2:])
                    or not isinstance(record.get("numeric_format"), dict)
                    or set(record["numeric_format"]) != {"mantissa", "maxexp"}
                ):
                    raise ValueError("Invalid extended floating project array")
                portable = record.get("portable_file")
                if portable is not None and (
                    portable == name or portable not in payload["arrays"]
                ):
                    raise ValueError("Invalid portable project array reference")
                if compatible_numeric_dtype(record) is None and portable is None:
                    raise ValueError(
                        "This project's extended floating values cannot be represented exactly on this platform; reopen it on the original platform"
                    )
        with archive.open(info) as stream:
            digest = hashlib.sha256()
            while chunk := stream.read(CHUNK):
                digest.update(chunk)
            if digest.hexdigest() != record["sha256"]:
                raise ValueError("Project array checksum mismatch")
    if allocating and total > psutil.virtual_memory().available * 0.75:
        raise ValueError("Not enough available memory to reopen this project safely")
    return payload


class ArrayReader:
    def __init__(self, archive, manifest):
        self.archive = archive
        self.manifest = manifest
        self.cache = {}

    def __call__(self, reference):
        name = reference["$array_file"]
        if (
            set(reference)
            not in ({"$array_file", "scalar"}, {"$array_file", "scalar", "numeric"})
            or not isinstance(reference["scalar"], bool)
            or name not in self.manifest["arrays"]
        ):
            raise ValueError("Invalid project array reference")
        record = self.manifest["arrays"][name]
        if ("numeric_dtype" in record) != (reference.get("numeric") is True):
            raise ValueError("Invalid project numeric array reference")
        if name not in self.cache:
            with self.archive.open(name) as stream:
                array = np.lib.format.read_array(stream, allow_pickle=False)
            record = self.manifest["arrays"][name]
            if "numeric_dtype" in record:
                dtype = compatible_numeric_dtype(record)
                if dtype is not None:
                    array = array.view(dtype)
                else:
                    portable_name = record["portable_file"]
                    portable_record = self.manifest["arrays"][portable_name]
                    if "numeric_dtype" in portable_record:
                        raise ValueError("Invalid nested portable array reference")
                    with self.archive.open(portable_name) as stream:
                        portable = np.lib.format.read_array(stream, allow_pickle=False)
                    expected = np.dtype(
                        "complex128" if record["numeric_dtype"][1] == "c" else "float64"
                    )
                    if portable.shape != array.shape or portable.dtype != expected:
                        raise ValueError("Invalid portable array shape or dtype")
                    array = portable
            self.cache[name] = array
        array = self.cache[name]
        if reference["scalar"] and array.shape != ():
            raise ValueError("Invalid project scalar shape")
        return array[()] if reference["scalar"] else array
