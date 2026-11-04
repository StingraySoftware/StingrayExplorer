"""Immutable spectrum calculation records and lossless real-valued projections.

The browser's magnitude/phase plot is not a serialization of a complex cross
spectrum. Numeric exports therefore retain real and imaginary components, and
the spectrum's original calculation record travels with every projection.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import platform
from uuid import uuid4

import astropy
from astropy import units as u
from astropy.table import MaskedColumn, Table
import numpy as np
import scipy
import stingray

from .analysis_helpers import event_gtis


def _decimal(value):
    """Keep reference epochs and event-time precision outside float64 JSON."""
    return str(np.longdouble(value)) if value is not None else None


def _plain(value):
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, np.ndarray) and value.ndim == 0:
        return _plain(value.item())
    if isinstance(value, (tuple, list, np.ndarray)):
        return [_plain(item) for item in value]
    if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if value is None or isinstance(value, (str, bool)):
        return value
    raise ValueError("Spectrum metadata contains an unsupported non-JSON value")


def _public_lineage(value):
    """Retain known scientific lineage without native paths or capabilities."""
    if isinstance(value, dict):
        return {
            str(key): _public_lineage(item)
            for key, item in value.items()
            if not any(
                word in str(key).lower()
                for word in ("grant", "secret", "token", "credential", "password")
            )
            and not str(key).lower().endswith(("path", "filename", "file"))
        }
    if isinstance(value, (list, tuple)):
        return [_public_lineage(item) for item in value]
    return _plain(value)


def input_snapshot(name, events, dataset_id):
    """Describe the exact detached input, never re-resolving its mutable name."""
    times = np.asarray(events.time)
    timing = {
        "mjdref": _decimal(getattr(events, "mjdref", None)),
        **{
            field: getattr(events, field, None)
            for field in ("timesys", "timeref", "ephem", "mission", "instr")
        },
    }
    snapshot = {
        "name": name,
        "dataset_id": dataset_id,
        "n_events": int(times.size),
        "time_range": [_decimal(np.min(times)), _decimal(np.max(times))],
        "gti": [
            [_decimal(start), _decimal(stop)] for start, stop in event_gtis(events)
        ],
        "timing": timing,
        "instrument_time_resolution": _plain(getattr(events, "dt", None)),
    }
    for column in ("energy", "pi"):
        values = getattr(events, column, None)
        if values is not None:
            values = np.asarray(values)
            snapshot[f"{column}_range"] = _plain([np.min(values), np.max(values)])
    # Selection provenance is explicit application metadata. Do not copy raw
    # FITS headers, paths, temporary file grants, or arbitrary object attributes.
    if getattr(events, "gti_selection", None) is not None:
        snapshot["gti_selection"] = _public_lineage(events.gti_selection)
    if getattr(events, "event_selection", None) is not None:
        snapshot["selection"] = _public_lineage(events.event_selection)
    calibration = getattr(events, "rmf_conversion_provenance", None)
    if calibration is not None:
        snapshot["rmf_conversion_provenance"] = _public_lineage(calibration)
    mission_lineage = getattr(events, "mission_io_provenance_json", None)
    if mission_lineage:
        try:
            snapshot["mission_io_provenance"] = _public_lineage(
                json.loads(mission_lineage)
            )
        except (TypeError, ValueError):
            snapshot["mission_io_provenance"] = {
                "available": False,
                "reason": "Stored mission calibration provenance is malformed",
            }
    return _plain(snapshot)


def attach_spectrum_identity(
    spectrum,
    *,
    operation,
    backend_session_id,
    inputs,
    parameters,
    warnings,
    parent=None,
    result_kind="spectrum",
    input_kind="event_lists",
):
    """Attach a private copy before publishing; callers receive another copy."""
    parameters = _plain(parameters)
    provenance = {
        "operation": operation,
        "input_source": {
            "kind": input_kind,
            "names": [item["name"] for item in inputs if "name" in item],
        },
        "parameters": deepcopy(parameters),
        "original_parameters": deepcopy(parameters),
        "stingray_version": stingray.__version__,
        "versions": {
            "python": platform.python_version(),
            "stingray": stingray.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "astropy": astropy.__version__,
        },
    }
    if parent is not None:
        parent_identity, parent_name = parent
        provenance["parent_result"] = {
            "result_id": parent_identity["result_id"],
            "backend_session_id": parent_identity["backend_session_id"],
            "name": parent_name,
        }
        provenance["original_parameters"] = deepcopy(
            parent_identity["provenance"].get(
                "original_parameters", parent_identity["parameters"]
            )
        )
        provenance["parent_provenance"] = deepcopy(parent_identity["provenance"])
    identity = {
        "schema": f"stingray-explorer.{result_kind}-result.v1",
        "result_id": str(uuid4()),
        "backend_session_id": backend_session_id,
        "operation": operation,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inputs": deepcopy(inputs),
        "parameters": parameters,
        "warnings": list(dict.fromkeys(str(warning) for warning in warnings)),
        "provenance": provenance,
    }
    spectrum.result_identity = deepcopy(identity)
    return deepcopy(identity)


def spectrum_identity(spectrum):
    identity = getattr(spectrum, "result_identity", None)
    if not isinstance(identity, dict) or not identity.get("result_id"):
        raise ValueError(
            "Spectrum has no recorded result identity; recreate the spectrum"
        )
    return deepcopy(identity)


def _unit(norm):
    return {
        "leahy": u.dimensionless_unscaled,
        "none": u.ct**2,
        "frac": 1 / u.Hz,
        "abs": (u.ct / u.s) ** 2 / u.Hz,
    }.get(norm)


def _numeric_column(value, length, name, unit):
    array = np.asarray(value)
    if array.ndim == 0:
        array = np.full(length, array.item(), dtype=array.dtype)
    if array.ndim != 1 or len(array) != length or array.dtype.kind not in "fiu":
        raise ValueError(
            f"Spectrum column '{name}' must be real and aligned with frequency"
        )
    mask = ~np.isfinite(array)
    return MaskedColumn(
        np.where(mask, np.zeros((), dtype=array.dtype), array),
        mask=mask,
        name=name,
        unit=unit,
        fill_value=np.nan if array.dtype.kind == "f" else 0,
    )


def spectrum_table(spectrum):
    """Project a one-dimensional spectrum without discarding complex components."""
    identity = spectrum_identity(spectrum)
    if getattr(spectrum, "dyn_ps", None) is not None:
        raise ValueError(
            "Dynamical spectra require a two-dimensional export and are not supported by this table exporter"
        )
    frequency = np.asarray(getattr(spectrum, "freq", None))
    power = np.asarray(getattr(spectrum, "power", None))
    if (
        frequency.ndim != 1
        or not frequency.size
        or frequency.dtype.kind not in "fiu"
        or not np.isfinite(frequency).all()
    ):
        raise ValueError(
            "Spectrum frequencies must be a nonempty finite one-dimensional array"
        )
    if power.ndim != 1 or power.shape != frequency.shape:
        raise ValueError(
            "Spectrum power must be one-dimensional and aligned with frequency"
        )
    unit = _unit(getattr(spectrum, "norm", None))
    if unit is None:
        raise ValueError(
            "Spectrum normalization is unsupported for a scientific export"
        )
    table = Table()
    table["freq"] = frequency.copy()
    table["freq"].unit = u.Hz
    if np.iscomplexobj(power):
        for name, values, column_unit in (
            ("power_real", power.real, unit),
            ("power_imag", power.imag, unit),
            ("power_magnitude", np.abs(power), unit),
            ("power_phase", np.angle(power), u.rad),
        ):
            table[name] = _numeric_column(values, len(table), name, column_unit)
    else:
        table["power"] = _numeric_column(power, len(table), "power", unit)
    error = getattr(spectrum, "power_err", None)
    if error is not None:
        error = np.asarray(error)
        if np.iscomplexobj(error):
            table["power_err_real"] = _numeric_column(
                error.real, len(table), "power_err_real", unit
            )
            table["power_err_imag"] = _numeric_column(
                error.imag, len(table), "power_err_imag", unit
            )
        else:
            table["power_err"] = _numeric_column(error, len(table), "power_err", unit)
    for name, attribute, column_unit in (
        ("df", "df", u.Hz),
        ("n_averaged", "m", u.dimensionless_unscaled),
        ("rebin_count", "k", u.dimensionless_unscaled),
    ):
        value = getattr(spectrum, attribute, None)
        if value is not None:
            table[name] = _numeric_column(value, len(table), name, column_unit)
    table.meta.update(deepcopy(identity))
    table.meta["result_identity"] = deepcopy(identity)
    table.meta["norm"] = str(spectrum.norm)
    table.meta["spectrum_type"] = type(spectrum).__name__
    table.meta["units"] = {
        name: column.unit.to_string() if column.unit is not None else ""
        for name, column in table.columns.items()
    }
    if getattr(spectrum, "gti", None) is not None:
        table.meta["gti"] = [
            [_decimal(start), _decimal(stop)] for start, stop in spectrum.gti
        ]
    table.meta["uncertainty_convention"] = (
        "power_err is the upstream Stingray estimate; complex errors retain separate "
        "real/imaginary components and are not magnitude or phase uncertainties"
    )
    return table


spectrum_export_table = spectrum_table


def spectrum_projection(spectrum):
    """Keep the renderer's magnitude/phase contract while adding exact components."""
    frequency = np.asarray(spectrum.freq)
    power = np.asarray(spectrum.power)
    if frequency.ndim != 1 or not frequency.size or power.shape != frequency.shape:
        raise ValueError(
            "Spectrum power must be one-dimensional and aligned with frequency"
        )
    if frequency.dtype.kind not in "fiu" or not np.isfinite(frequency).all():
        raise ValueError("Spectrum frequencies must be a finite real numeric array")
    power_unit = _unit(spectrum.norm)
    if power_unit is None:
        raise ValueError("Spectrum normalization is unsupported")
    complex_power = np.iscomplexobj(power)

    def values(array):
        return [float(value) if np.isfinite(value) else None for value in array]

    data = {
        "freq": values(frequency),
        "power": values(np.abs(power) if complex_power else power),
        "power_phase": values(np.angle(power)) if complex_power else None,
    }
    data.update(spectrum_identity(spectrum))
    data["norm"] = str(spectrum.norm)
    data["n_freq"] = len(frequency)
    data["metadata"] = {
        "units": {
            "freq": "Hz",
            "power": u.Unit(power_unit).to_string(),
            **({"power_phase": "rad"} if complex_power else {}),
        },
        "power_representation": (
            "complex magnitude and phase for plotting; General I/O preserves real and imaginary components"
            if complex_power
            else "real power"
        ),
    }
    # Existing callers expect scalar df on un-rebinned spectra. A log rebin
    # instead exposes its widths under an explicit aligned-array field; export
    # tables always retain df as a column.
    if np.ndim(spectrum.df) == 0:
        data["df"] = float(spectrum.df)
    else:
        data["frequency_bin_width"] = _plain(np.asarray(spectrum.df))
        data["metadata"]["units"]["frequency_bin_width"] = "Hz"
    return data
