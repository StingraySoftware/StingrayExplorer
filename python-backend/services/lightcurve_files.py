"""Read light curves from mission FITS files (NICER, Swift-XRT, RXTE, OGIP tables).

Every supported Stingray release (2.2 - 2.3.2) provides
``stingray.io.lcurve_from_fits``, which is used whenever it can describe the
file: a one-dimensional RATE/RATE1/COUNTS column and a header stating
TIMEUNIT, TSTART/TSTOP and, for times in seconds, the reference epoch. Other
OGIP tables (multi-band rate columns, bare COUNTS tables, missing TSTART) use
an explicit reader following the same conventions. The reference epoch is
never guessed for times in seconds: a missing MJDREF is an error unless the
request supplies it or the header states the times are relative.

Times stay in extended precision (``np.longdouble``) wherever the installed
Stingray accepts them. Releases before 2.2.10 combined with a recent numba
reject 80-bit times (x86_64) in ``Lightcurve``'s checks; there times and GTIs
are built in float64 and the provenance records ``time_precision``.
"""

import warnings
from copy import deepcopy
from functools import lru_cache

import numpy as np
import stingray
from astropy.io import fits
from stingray import Lightcurve
from stingray.gti import create_gti_from_condition
from stingray.io import lcurve_from_fits

RATE_COLUMNS = ("RATE", "RATE1", "COUNTS")
ERROR_COLUMNS = {
    "RATE": ("ERROR", "RATE_ERR"),
    "RATE1": ("ERROR1",),
    "COUNTS": ("ERROR", "COUNTS_ERR"),
}
GTI_EXTENSIONS = ("GTI", "STDGTI")
SECONDS_PER = {"s": 1.0, "d": 86400.0}


@lru_cache(maxsize=1)
def lightcurve_accepts_longdouble():
    """Whether the installed Stingray builds a Lightcurve from longdouble times."""
    try:
        Lightcurve(
            np.array([0.5, 1.5], dtype=np.longdouble), [1.0, 1.0], dt=1.0, skip_checks=False
        )
    except Exception:  # numba typing errors escape older releases' checks
        return False
    return True


class LightcurveFileError(ValueError):
    """A FITS file that cannot be read as a light curve as requested."""


def _header_number(header, key):
    """Read KEY, or its KEYI + KEYF high-precision split, as a longdouble."""
    if header.get(key) is not None:
        return np.longdouble(header[key])
    integer, fraction = (
        ("TIMEZERI", "TIMEZERF") if key == "TIMEZERO" else (f"{key}I", f"{key}F")
    )
    if header.get(integer) is not None:
        return np.longdouble(header[integer]) + np.longdouble(header.get(fraction, 0))
    return None


def _rate_columns(hdu):
    names = [name.upper() for name in hdu.columns.names]
    return [name for name in RATE_COLUMNS if name in names] if "TIME" in names else []


def _bands(hdu, column):
    shape = hdu.data[column].shape
    return shape[1] if len(shape) == 2 else 1


def describe_lightcurve_hdus(hdul):
    """List table HDUs that look like light curves, for the HDU/band chooser."""
    found = []
    for index, hdu in enumerate(hdul):
        if not isinstance(hdu, fits.BinTableHDU):
            continue
        columns = _rate_columns(hdu)
        if not columns:
            continue
        header = hdu.header
        found.append(
            {
                "index": index,
                "name": hdu.name,
                "rate_columns": columns,
                "n_rows": int(len(hdu.data)),
                "n_bands": int(_bands(hdu, columns[0])),
                "timeunit": header.get("TIMEUNIT"),
                "has_mjdref": _header_number(header, "MJDREF") is not None,
                "telescope": header.get("TELESCOP"),
                "instrument": header.get("INSTRUME"),
            }
        )
    return found


def _choose_hdu(hdul, hdu):
    candidates = describe_lightcurve_hdus(hdul)
    if hdu is None:
        if not candidates:
            raise LightcurveFileError(
                "This file has no light-curve table: no extension has a TIME "
                "column and a RATE, RATE1 or COUNTS column."
            )
        return candidates[0]
    for candidate in candidates:
        if hdu in (candidate["index"], candidate["name"]):
            return candidate
    raise LightcurveFileError(f"Extension {hdu!r} is not a light-curve table")


def _gti_extension(hdul):
    names = {hdu.name.upper() for hdu in hdul}
    return next((name for name in GTI_EXTENSIONS if name in names), None)


def _epoch(header, timeunit, mjdref):
    """(mjdref, source) for the explicit reader, or a clear error."""
    if mjdref is not None:
        return float(mjdref), "request"
    in_header = _header_number(header, "MJDREF")
    if in_header is not None:
        return float(in_header), "header"
    if str(header.get("TIMESYS", "")).strip().upper() == "RELATIVE":
        return 0.0, "relative_time"
    raise LightcurveFileError(
        "The light-curve header has no MJDREF (or MJDREFI/MJDREFF), so its "
        f"times in {'seconds' if timeunit != 'd' else 'days'} have no known "
        "reference epoch. Enter the mission's reference MJD to load it."
    )


def _from_stingray(stream, candidate, column, gti_extension, fracexp_limit):
    stream.seek(0)
    data = lcurve_from_fits(
        stream,
        gtistring=gti_extension or "GTI",
        ratecolumn=column,
        ratehdu=candidate["index"],
        fracexp_limit=fracexp_limit,
    )
    errors = np.asarray(data["err"], dtype=float)
    return {
        "time": np.asarray(data["time"]),
        "counts": np.asarray(data["counts"], dtype=float),
        "err": errors if np.any(errors != 0) else None,
        "gti": np.asarray(data["gti"]),
        "mjdref": float(data["mjdref"]),
        "dt": float(data["dt"]),
    }


def _explicit(hdul, candidate, column, band, gti_extension, fracexp_limit, mjdref):
    hdu = hdul[candidate["index"]]
    header = hdu.header
    timeunit = str(header.get("TIMEUNIT", "s")).strip().lower()
    if timeunit not in SECONDS_PER:
        raise LightcurveFileError(f"Unsupported TIMEUNIT {timeunit!r}")
    if timeunit == "d":
        raise LightcurveFileError(
            "Light curves with times in days need TSTART, TSTOP and MJDREF in "
            "the header to be read"
        )
    epoch, epoch_source = _epoch(header, timeunit, mjdref)

    def column_values(name):
        values = np.asarray(hdu.data[name], dtype=float)
        if values.ndim == 2:
            values = values[:, band]
        return values

    time = np.asarray(hdu.data["TIME"], dtype=np.longdouble)
    timezero = _header_number(header, "TIMEZERO") or np.longdouble(0)
    tstart = _header_number(header, "TSTART")
    # Same convention as stingray.io.lcurve_from_fits: TIME is relative to
    # TSTART when every time precedes it.
    if tstart is not None and time[-1] < tstart:
        time = time + timezero + tstart
    else:
        time = time + timezero
    timedel = _header_number(header, "TIMEDEL")
    dt = float(timedel) if timedel is not None else float(np.median(np.diff(time)))

    values = column_values(column)
    error_name = next(
        (name for name in ERROR_COLUMNS[column] if name in hdu.columns.names), None
    )
    errors = column_values(error_name) if error_name else None
    if column.startswith("RATE"):
        values = values * dt
        errors = errors * dt if errors is not None else None
    fracexp = (
        column_values("FRACEXP") if "FRACEXP" in hdu.columns.names else np.ones_like(values)
    )
    good = np.isfinite(values) & (fracexp >= fracexp_limit)
    values = np.where(good, values / np.where(good, fracexp, 1), 0.0)
    if errors is not None:
        errors = np.where(good, errors / np.where(good, fracexp, 1), 0.0)

    if gti_extension:
        table = hdul[gti_extension].data
        gti = np.column_stack([table["START"], table["STOP"]]).astype(np.longdouble)
    else:
        # Bin-centred times: each good bin spans time +/- dt / 2.
        gti = create_gti_from_condition(time, good, dt=np.full(len(time), dt / 2))
    return {
        "time": time,
        "counts": values,
        "err": errors,
        "gti": gti,
        "mjdref": epoch,
        "dt": dt,
    }, epoch_source


def read_lightcurve_fits(
    stream,
    *,
    hdu=None,
    rate_column=None,
    band=None,
    mjdref=None,
    fracexp_limit=0.9,
):
    """Return (Lightcurve, provenance, warnings) read from an open FITS stream."""
    stream.seek(0)
    with fits.open(stream, memmap=False) as hdul:
        candidate = _choose_hdu(hdul, hdu)
        header = hdul[candidate["index"]].header
        column = (rate_column or candidate["rate_columns"][0]).upper()
        if column not in candidate["rate_columns"]:
            raise LightcurveFileError(
                f"Column {column!r} is not a rate column of extension "
                f"{candidate['name']!r}; choose one of "
                + ", ".join(candidate["rate_columns"])
            )
        n_bands = _bands(hdul[candidate["index"]], column)
        if n_bands > 1 and band is None:
            raise LightcurveFileError(
                f"Column {column!r} holds {n_bands} energy bands; choose a band "
                f"from 0 to {n_bands - 1}"
            )
        if n_bands > 1 and not 0 <= band < n_bands:
            raise LightcurveFileError(f"Band must be between 0 and {n_bands - 1}")
        if n_bands == 1:
            band = None
        gti_extension = _gti_extension(hdul)
        timeunit = str(header.get("TIMEUNIT", "")).strip().lower() or None
        has_epoch = _header_number(header, "MJDREF") is not None
        # Days-unit files state absolute times, so Stingray derives seconds
        # against its own epoch; times in seconds need the file's epoch.
        stingray_can_read = (
            n_bands == 1
            and mjdref is None
            and _header_number(header, "TSTART") is not None
            and _header_number(header, "TSTOP") is not None
            and (timeunit == "d" or (timeunit == "s" and has_epoch))
        )

        captured = []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            if stingray_can_read:
                fields = _from_stingray(
                    stream, candidate, column, gti_extension, fracexp_limit
                )
                reader = "stingray.io.lcurve_from_fits"
                epoch_source = "header" if has_epoch else "absolute_days"
            else:
                fields, epoch_source = _explicit(
                    hdul, candidate, column, band, gti_extension, fracexp_limit, mjdref
                )
                reader = "application_ogip"
            errors = fields.pop("err")
            time_precision = None
            if not lightcurve_accepts_longdouble():
                fields["time"] = np.asarray(fields["time"], dtype=np.float64)
                fields["gti"] = np.asarray(fields["gti"], dtype=np.float64)
                time_precision = "float64"
            lightcurve = Lightcurve(
                **fields,
                err=errors,
                input_counts=True,
                err_dist="gauss" if errors is not None else "poisson",
                skip_checks=False,
            )
        captured.extend(
            str(item.message)
            for item in caught
            if "still under testing" not in str(item.message)
            and "Absolute times might be incorrect" not in str(item.message)
        )

        span = np.asarray(lightcurve.gti, dtype=float)
        times = np.asarray(lightcurve.time, dtype=float)
        if span.size and (times[0] > span[-1, 1] or times[-1] < span[0, 0]):
            captured.append(
                "The light-curve times do not overlap the file's GTIs; check the "
                "file's TIMEZERO/TSTART convention."
            )
        provenance = {
            "reader": reader,
            "hdu": {"index": int(candidate["index"]), "name": candidate["name"]},
            "rate_column": column,
            "band": band,
            "gti_extension": gti_extension,
            "timeunit": timeunit or "s",
            "timezero": float(_header_number(header, "TIMEZERO") or 0.0),
            "mjdref": float(lightcurve.mjdref),
            "mjdref_source": epoch_source,
            "fracexp_limit": float(fracexp_limit),
            "telescope": header.get("TELESCOP"),
            "instrument": header.get("INSTRUME"),
            "timesys": header.get("TIMESYS"),
            "stingray_version": stingray.__version__,
        }
        if time_precision is not None:
            provenance["time_precision"] = time_precision
    for attribute, key in (("mission", "TELESCOP"), ("instr", "INSTRUME"), ("timesys", "TIMESYS")):
        if header.get(key) is not None:
            setattr(lightcurve, attribute, str(header.get(key)))
    return lightcurve, deepcopy(provenance), captured
