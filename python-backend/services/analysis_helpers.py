"""
Shared helpers for analysis services.

Paired analyses validate the physical time reference and actual common exposure
before binning. These checks never convert reference frames or mutate inputs.
"""

import sys as _sys
import threading as _threading
import warnings as _warnings
import re
import copy
from contextlib import contextmanager
from typing import Iterator, List, Optional

import numpy as np

# CPython 3.14 added "context-aware warnings": when enabled, catch_warnings
# stores its saved state in a contextvars.ContextVar instead of module globals,
# which makes concurrent captures genuinely isolated (asyncio.to_thread copies
# the caller's context per call, and a plain threading.Thread starts with its
# own context, so neither can see another block's saved state).
#
# The flag is off by default. It can be turned on with -X context_aware_warnings=1
# or PYTHON_CONTEXT_AWARE_WARNINGS=1; electron/pythonManager.ts and the
# `python:dev` npm script set it so real launches get the fast path.
# getattr() keeps this importable on Python < 3.14, where the flag does not exist.
#
# Caveat that mode carries: the legacy catch_warnings(record=True) resets
# warnings.showwarning to the default on entry so recording cannot be bypassed,
# but the context-aware path does not. So in that mode anything which replaces
# the global warnings.showwarning must chain to the handler it displaced, or
# capture here silently yields an empty list. utils/log_stream.py (installed for
# the whole process by main.py's lifespan) does chain - see its _capture_warning
# - and tests/test_analysis_helpers.py pins that down in both modes.
CONTEXT_AWARE_WARNINGS = bool(getattr(_sys.flags, "context_aware_warnings", 0))

# Fallback for interpreters without that mode: serialize warning capture.
#
# warnings.catch_warnings(record=True) mutates PROCESS-GLOBAL state
# (warnings.filters, warnings.showwarning, warnings._showwarnmsg_impl) on entry
# and restores whatever it saw on exit. Every analysis service runs its stingray
# call inside collect_warnings, and every route dispatches through
# asyncio.to_thread onto the default multi-worker executor, so two in-flight
# requests really do execute these blocks concurrently. Without serialization
# that produces two verified failure modes:
#
#   1. Misattribution - if block B enters while block A is still open, A's
#      warnings are recorded into B's sink and A's sink comes back empty. A
#      stingray advisory about one request's data is then rendered in another
#      request's warning Alert, and dropped from the response it belongs to.
#   2. Permanent global corruption - with a non-LIFO interleave (A enters, B
#      enters, A exits, B exits), B's __exit__ restores the _showwarnmsg_impl it
#      captured on entry, which is A's now-orphaned record list. Every warning
#      raised anywhere in the process afterwards is silently appended to that
#      dead list instead of reaching stderr/the server log, for the lifetime of
#      the backend.
#
# An RLock (not a plain Lock) so that a future nested collect_warnings on the
# same thread cannot deadlock; nesting within a single thread is already safe
# because catch_warnings restores in LIFO order there.
_CAPTURE_LOCK = None if CONTEXT_AWARE_WARNINGS else _threading.RLock()


def finite_list(arr) -> list:
    """Convert a float array to a list, replacing non-finite values with None."""
    values = np.asarray(arr, dtype=float)
    if np.isfinite(values).all():
        return values.tolist()
    return [float(v) if np.isfinite(v) else None for v in values]


def segment_size_error(segment_size: float, dt: float) -> Optional[str]:
    """Human-readable rejection for segment sizes that stingray fails on cryptically.

    Needs at least 3 time bins per segment to produce a non-empty spectrum.
    """
    if not np.isfinite(dt) or dt <= 0:
        return "dt must be a finite positive number of seconds"
    if not np.isfinite(segment_size) or segment_size <= 0:
        return "segment_size must be a finite positive number of seconds"
    if segment_size / dt < 3:
        return (
            f"segment_size ({segment_size}s) must be at least 3x dt ({dt}s) "
            "to produce a non-empty spectrum"
        )
    return None


_UNKNOWN_REFERENCE = {"", "unknown", "none", "null", "n/a"}
_TIME_SYSTEMS = {"tai", "tt", "tdb", "tcb", "tcg", "utc", "ut1", "gps"}
_TIME_REFERENCES = {
    "local": "local",
    "solarsystem": "solarsystem",
    "barycenter": "solarsystem",
    "barycentre": "solarsystem",
    "barycentric": "solarsystem",
    "ssb": "solarsystem",
    "geocenter": "geocenter",
    "geocentre": "geocenter",
    "geocentric": "geocenter",
    "heliocenter": "heliocenter",
    "heliocentre": "heliocenter",
    "heliocentric": "heliocenter",
    "topocenter": "topocenter",
    "topocentre": "topocenter",
    "topocentric": "topocenter",
}


def _reference_value(events, field):
    value = getattr(events, field, None)
    label = field.upper()
    if value is None:
        return None
    if field == "mjdref":
        array = np.asarray(value)
        if array.ndim != 0 or array.dtype.kind not in "fiu" or not np.isfinite(array):
            raise ValueError(f"{label} must be a finite numeric scalar")
        # Preserve long-double reference epochs. A float64 cast can hide a
        # scientifically relevant difference between high-precision origins.
        return np.longdouble(value)
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a recognized string or unknown")
    value = value.strip().lower()
    if value in _UNKNOWN_REFERENCE:
        return None
    if field == "timesys":
        value = "tt" if value == "tdt" else value
        if value in _TIME_SYSTEMS:
            return value
    elif field == "timeref":
        value = value.replace(" ", "").replace("_", "").replace("-", "")
        if value in _TIME_REFERENCES:
            return _TIME_REFERENCES[value]
    elif field == "ephem":
        value = re.sub(r"^jpl[\s_-]*", "", value)
        value = re.sub(r"^de[\s_-]*", "de", value)
        if re.fullmatch(r"de[0-9]{3,4}[a-z]?", value):
            return value
    raise ValueError(f"{label} contains an unsupported timing reference")


def timing_reference_error(events1, events2) -> Optional[str]:
    """Reject incompatible physical time references without inventing conversions.

    Equal default MJDREF=0 and unknown/unknown optional metadata remain useful
    for synthetic data and same-reference files with incomplete headers. Known
    metadata on only one input is insufficient to establish compatibility.
    MJDREF must match exactly: aligning different origins or time scales is an
    explicit preprocessing operation, not an invisible analysis side effect.
    """
    for field in ("mjdref", "timesys", "timeref", "ephem"):
        try:
            first = _reference_value(events1, field)
            second = _reference_value(events2, field)
        except (TypeError, ValueError, OverflowError) as exception:
            return f"Cannot compare event lists: {exception}"
        if (first is None) != (second is None):
            return (
                f"Cannot compare event lists: {field.upper()} is known for only one "
                "input; timing-reference compatibility cannot be established"
            )
        if first != second:
            return (
                f"Cannot compare event lists with different {field.upper()} values; "
                "align their physical time references before analysis"
            )
    return None


def event_gtis(events) -> np.ndarray:
    """Return validated detached GTIs without populating Stingray's lazy cache.

    Explicit GTIs describe exposure, including empty photon bins near their
    boundaries. With no supplied GTI, infer a conservative min/max photon span,
    preserving unsorted input order and leaving the original object untouched.
    """
    times = getattr(events, "time", None)
    if times is None:
        raise ValueError("one of the event lists contains no events")
    times = np.asarray(times)
    if times.size == 0:
        raise ValueError("one of the event lists contains no events")
    if times.ndim != 1 or times.dtype.kind not in "fiu" or not np.isfinite(times).all():
        raise ValueError("event times must be a one-dimensional finite numeric array")
    # Reading .gti on a Stingray object with no explicit GTIs writes to _gti.
    # Read the backing attribute directly so preflight stays non-mutating.
    if hasattr(events, "_gti"):
        intervals = events._gti
    else:
        intervals = getattr(events, "gti", None)
    if intervals is None:
        intervals = [[np.min(times), np.max(times)]]
    try:
        raw = np.asarray(intervals)
        if raw.dtype.kind not in "fiu":
            raise ValueError
        intervals = np.array(raw, dtype=np.longdouble, copy=True)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(
            "GTIs must be a finite numeric array of start/stop pairs"
        ) from None
    if intervals.ndim != 2 or intervals.shape[1] != 2 or intervals.shape[0] == 0:
        raise ValueError("GTIs must contain at least one start/stop pair")
    if not np.isfinite(intervals).all() or np.any(intervals[:, 1] <= intervals[:, 0]):
        raise ValueError("GTI boundaries must be finite with start strictly below stop")
    if np.any(intervals[1:, 0] < intervals[:-1, 1]):
        raise ValueError("GTIs must be ordered and non-overlapping")
    # Adjacent rows encode continuous exposure. Keep real gaps, however small,
    # while avoiding false segment failures for a mere interval boundary.
    merged = [intervals[0].copy()]
    for start, stop in intervals[1:]:
        if start == merged[-1][1]:
            merged[-1][1] = stop
        else:
            merged.append(np.array([start, stop], dtype=np.longdouble))
    return np.asarray(merged, dtype=np.longdouble)


def common_gtis(events1, events2) -> np.ndarray:
    """Intersect valid exposure intervals; raise ValueError for malformed inputs."""
    first, second = event_gtis(events1), event_gtis(events2)
    result = []
    left = right = 0
    while left < len(first) and right < len(second):
        start = max(first[left, 0], second[right, 0])
        stop = min(first[left, 1], second[right, 1])
        if stop > start:
            result.append((start, stop))
        if first[left, 1] < second[right, 1]:
            left += 1
        else:
            right += 1
    return np.asarray(result, dtype=np.longdouble).reshape(-1, 2)


def pair_binning_error(events1, events2, dt: float) -> Optional[str]:
    """Require the requested common bin width to fit both instrument clocks.

    Stingray's from_events path snaps dt using only the first event list. Reject
    requests needing that adjustment instead of silently using an asymmetric or
    changed grid; the caller can choose an explicit multiple of both clocks.
    """
    requested = np.asarray(dt)
    if (
        requested.ndim != 0
        or requested.dtype.kind not in "fiu"
        or not np.isfinite(requested)
        or dt <= 0
    ):
        return "dt must be a finite positive number of seconds"
    for events in (events1, events2):
        resolution = getattr(events, "dt", 0.0)
        if resolution is None:
            continue
        array = np.asarray(resolution)
        if array.ndim != 0 or array.dtype.kind not in "fiu" or not np.isfinite(array):
            return "event time resolution must be a finite non-negative scalar"
        if resolution < 0:
            return "event time resolution must be a finite non-negative scalar"
        if resolution > 0:
            with np.errstate(over="ignore", invalid="ignore"):
                ratio = np.longdouble(dt) / np.longdouble(resolution)
            if (
                not np.isfinite(ratio)
                or ratio < 1
                or not np.isclose(ratio, np.rint(ratio), rtol=0, atol=1e-7)
            ):
                return (
                    "dt must be a multiple of both event time resolutions; "
                    "automatic adjustment of only one input would change the shared bin grid"
                )
    return None


def analysis_event_copy(events):
    """Make a spectral-analysis wrapper with explicit GTIs and sorted photons.

    Stingray's averaged event FFT slices with searchsorted and silently assumes
    sorted times. Sort every aligned event attribute on a detached wrapper so
    photon permutations cannot change a spectrum or mutate the saved dataset.
    Already sorted arrays can remain shared because these analysis paths only
    read them; GTIs and lazy caches belong to the wrapper in all cases.
    """
    intervals = event_gtis(events)
    detached = copy.copy(events)
    detached.gti = intervals
    times = np.asarray(events.time)
    if np.any(times[1:] < times[:-1]):
        order = np.argsort(times, kind="stable")
        detached = detached.apply_mask(order, inplace=False)
    return detached


def overlap_error(
    events1, events2, segment_size: Optional[float] = None
) -> Optional[str]:
    """Readable rejection for reference, exposure, or segment incompatibility."""
    reference_error = timing_reference_error(events1, events2)
    if reference_error:
        return reference_error
    try:
        intervals = common_gtis(events1, events2)
    except (TypeError, ValueError, OverflowError) as exception:
        return str(exception)
    if len(intervals) == 0:
        first, second = event_gtis(events1), event_gtis(events2)
        return (
            "the two event lists have no overlapping time range in their good-time intervals "
            f"({first[0, 0]:.1f}-{first[-1, 1]:.1f}s vs "
            f"{second[0, 0]:.1f}-{second[-1, 1]:.1f}s)"
        )
    if segment_size is not None:
        if not np.isfinite(segment_size) or segment_size <= 0:
            return "segment_size must be a finite positive number of seconds"
        longest = np.max(intervals[:, 1] - intervals[:, 0])
        if longest < segment_size:
            return (
                f"the longest overlapping good-time interval ({longest:.1f}s) is shorter than "
                f"the segment size ({segment_size}s)"
            )
    return None


@contextmanager
def collect_warnings(sink: List[str]) -> Iterator[None]:
    """Capture warnings raised inside the block into `sink` (deduplicated).

    Lets services surface stingray's low-count / NaN advisories to the UI
    instead of losing them to the server log.

    Thread safety: catch_warnings is only safe to run concurrently when the
    interpreter has context-aware warnings enabled (see CONTEXT_AWARE_WARNINGS
    above). When it does not, the capture is serialized on _CAPTURE_LOCK, which
    is held for the whole block so that entry and exit are strictly LIFO across
    threads. That costs concurrency on the analysis call inside, but it is the
    only way to stop concurrent requests from stealing each other's warnings and
    from permanently corrupting the process-global warning hooks.
    """
    if _CAPTURE_LOCK is None:
        with _capture_warnings(sink):
            yield
    else:
        with _CAPTURE_LOCK:
            with _capture_warnings(sink):
                yield


@contextmanager
def _capture_warnings(sink: List[str]) -> Iterator[None]:
    """The raw catch_warnings capture, without any locking."""
    with _warnings.catch_warnings(record=True) as caught:
        _warnings.simplefilter("always")
        try:
            yield
        finally:
            # A failed calculation still has useful advisories. Drain the
            # capture while unwinding without intercepting the original error.
            for warning in caught:
                message = str(warning.message)
                if message not in sink:
                    sink.append(message)
