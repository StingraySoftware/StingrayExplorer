"""Apply an EventSelection to a detached EventList and record what was kept.

Every supported Stingray release (2.2 - 2.3.2) provides
``EventList.get_energy_mask`` and ``apply_mask``. ``filter_detector_id``
(2.2.9+) and ``filter_at_time_intervals`` (2.2.4+, which splits rather than
filters) are not available or not suitable everywhere, so detector and time
selections use explicit masks with the same half-open convention.
"""

from copy import deepcopy

import numpy as np
from stingray.gti import cross_two_gtis

from .analysis_helpers import event_gtis
from .spectrum_products import _decimal, _plain

# Application metadata that must follow the photons onto the selected copy.
_PRESERVED_FIELDS = (
    "mjdref",
    "timesys",
    "timeref",
    "ephem",
    "mission",
    "instr",
    "dt",
    "header",
    "gti_selection",
    "rmf_conversion_provenance",
    "mission_io_provenance_json",
)


class EventSelectionError(ValueError):
    """A selection that cannot be applied to this EventList."""


def _column(events, name):
    values = getattr(events, name, None)
    return None if values is None else np.asarray(values)


def _within(times, intervals):
    """Half-open [start, stop) membership in sorted, disjoint intervals."""
    intervals = np.asarray(intervals, dtype=np.longdouble)
    index = np.searchsorted(intervals[:, 0], times, side="right") - 1
    valid = index >= 0
    inside = np.zeros(times.shape, dtype=bool)
    inside[valid] = times[valid] < intervals[index[valid], 1]
    return inside


def selection_mask(events, selection):
    """Return (mask, gti) for ``selection`` without copying any photon arrays."""
    times = np.asarray(events.time)
    mask = np.ones(times.shape, dtype=bool)
    gti = event_gtis(events)
    if selection is None or selection.is_empty():
        return mask, gti

    if selection.energy_range is not None:
        if _column(events, "energy") is None:
            hint = (
                " Use a PI range instead."
                if _column(events, "pi") is not None
                else " Calibrate it with an RMF in General I/O first."
            )
            raise EventSelectionError(
                f"This EventList has no calibrated energy column.{hint}"
            )
        mask &= np.asarray(events.get_energy_mask(list(selection.energy_range)))
    if selection.pi_range is not None:
        if _column(events, "pi") is None:
            raise EventSelectionError(
                "This EventList has no PI column. Use an energy range instead."
            )
        mask &= np.asarray(
            events.get_energy_mask(list(selection.pi_range), use_pi=True)
        )
    if selection.detector_ids is not None:
        detectors = _column(events, "detector_id")
        if detectors is None:
            raise EventSelectionError("This EventList has no detector ID column.")
        mask &= np.isin(detectors, selection.detector_ids)

    for label, intervals in (
        ("time intervals", selection.time_intervals),
        ("GTI list", selection.gti),
    ):
        if intervals is None:
            continue
        gti = cross_two_gtis(gti, np.asarray(intervals, dtype=np.longdouble))
        if len(gti) == 0:
            raise EventSelectionError(
                f"The selected {label} does not overlap the EventList's GTIs."
            )
    if selection.time_intervals is not None or selection.gti is not None:
        mask &= _within(times, gti)

    if not np.any(mask):
        raise EventSelectionError("The selection leaves no events.")
    return mask, gti


def apply_event_selection(events, selection):
    """Return a selected copy of ``events``, or ``events`` itself when unselected.

    The copy carries an ``event_selection`` record, which ``input_snapshot``
    publishes in every result identity built from it.
    """
    if selection is None or selection.is_empty():
        return events

    mask, gti = selection_mask(events, selection)
    selected = events.apply_mask(mask, inplace=False)
    selected.gti = np.asarray(gti)
    for field in _PRESERVED_FIELDS:
        if hasattr(events, field):
            setattr(selected, field, deepcopy(getattr(events, field)))
    selected.event_selection = {
        "energy_range_kev": _plain(selection.energy_range),
        "pi_range": _plain(selection.pi_range),
        "detector_ids": _plain(selection.detector_ids),
        "time_intervals": _plain(selection.time_intervals),
        "gti": _plain(selection.gti),
        "parent_n_events": int(mask.size),
        "n_events": int(np.count_nonzero(mask)),
        "effective_gti": [[_decimal(start), _decimal(stop)] for start, stop in gti],
    }
    return selected


def selection_record(events):
    """The applied-selection record carried by a selected copy, if any."""
    record = getattr(events, "event_selection", None)
    return deepcopy(record) if record is not None else None


def band_overlap_warning(events, name_1, selection_1, name_2, selection_2):
    """Warn when two selections of the same EventList share photons.

    Shared photons make the two bands' Poisson noise correlated, which biases
    cross spectra, lags, coherence and cross-correlations. Selections of two
    different EventLists, or two unselected inputs, are not checked here.
    """
    if name_1 != name_2 or (selection_1 is None and selection_2 is None):
        return None
    first, _ = selection_mask(events, selection_1)
    second, _ = selection_mask(events, selection_2)
    shared = int(np.count_nonzero(first & second))
    if shared == 0:
        return None
    return (
        f"The two bands of '{name_1}' share photons ({shared} events). Their "
        "Poisson noise is correlated, which biases cross spectra, lags, "
        "coherence and cross-correlation; use disjoint bands."
    )
