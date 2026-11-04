"""
Correlation service for auto/cross-correlation analysis.

Implemented per docs/superpowers/plans/2026-07-29-quicklook-remaining-pages.md.

Sign convention (verified against stingray 2.2.10 by aligning a Gaussian pulse):
**a positive ``time_shift`` means the first event list lags behind the second**;
a negative ``time_shift`` means the first list leads. Surface this verbatim in
the UI -- it is easy to get backwards.

stingray's ``CrossCorrelation`` correlates the two ``counts`` arrays purely by
position and never looks at ``Lightcurve.time``, so two lists covering different
absolute time ranges would be silently mis-aligned. This service therefore bins
both event lists onto ONE shared bin-edge grid covering a single continuous
common good-time interval (GTI) before handing them to stingray. Multiple
disjoint common GTIs are rejected: this counts-array estimator has no exposure
weights, so filling gaps with zeros or concatenating intervals would invent
exposure or false adjacent time samples. Auto-correlation uses the same policy
for the event list's native GTI. Events outside the selected GTI are excluded,
and genuinely partial final bins are discarded.

Three properties of that binning are load-bearing and easy to break:

* Bounds come from validated GTIs, rather than event extrema: unobserved gaps
  are not zero-count exposure, and unscreened out-of-GTI photons cannot extend
  the observation. For lists without explicit GTIs the shared validator uses
  ``np.min``/``np.max``, never stored endpoints. ``np.histogram`` accepts
  unsorted input.
* The grid is built in time RELATIVE to the start of the range. ``np.arange``
  over absolute mission times quantises to the local float64 spacing (1.5e-8 s
  at MET 8e7), which makes the real bin width differ from the ``dt`` stamped on
  the ``Lightcurve`` -- and stingray derives ``time_lags`` from that stamped
  value, so the whole lag axis would be silently stretched.
* Both endpoints bin with the SAME helper at exactly the requested ``dt``.
  ``EventList.to_lc`` would instead snap ``dt`` to a multiple of the event
  list's instrument time resolution, so the auto- and cross-correlation pages
  would disagree on the lag axis for identical input. The snapping exists to
  avoid beat artefacts, so ``_resolution_warning`` surfaces the mismatch
  instead of silently changing the user's ``dt``.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from stingray import Lightcurve
from stingray.crosscorrelation import AutoCorrelation, CrossCorrelation

from .analysis_helpers import (
    collect_warnings,
    common_gtis,
    event_gtis,
    finite_list,
    overlap_error,
)
from .base_service import BaseService

# 'valid' is deliberately excluded: with equal-length inputs (which the shared
# grid always produces) it degenerates to a single point.
VALID_MODES = ("same", "full")
VALID_NORMS = ("none", "variance")

# Minimum number of shared bins before a correlation is worth computing.
MIN_BINS = 3

# Maximum number of bins one request may allocate. Nothing else bounds this:
# two 3 ks lists at dt=1e-3 already produce ~3e6 lags, a ~93 MB JSON body and
# several hundred MB of RSS, and a finer dt OOMs the backend outright. Mirrors
# the DEFAULT_MAX_PLOT_POINTS cap lightcurve_service applies to plot payloads.
MAX_BINS = 500_000


def _mode_error(mode: str) -> Optional[str]:
    """Readable rejection for correlation modes this endpoint does not expose."""
    if mode not in VALID_MODES:
        return (
            f"mode '{mode}' is not supported; use one of "
            f"{', '.join(repr(m) for m in VALID_MODES)}"
        )
    return None


def _norm_error(norm: str) -> Optional[str]:
    """Readable rejection for normalisations stingray's correlation cannot do."""
    if norm not in VALID_NORMS:
        return (
            f"norm '{norm}' is not supported; use one of "
            f"{', '.join(repr(n) for n in VALID_NORMS)}"
        )
    return None


def _dt_error(dt: float) -> Optional[str]:
    """Readable rejection for bin sizes that cannot produce a light curve."""
    if not np.isfinite(dt) or dt <= 0:
        return f"dt ({dt}) must be a positive number of seconds"
    return None


def _span_error(span: float, dt: float, what: str) -> Optional[str]:
    """Readable rejection when the time span cannot hold MIN_BINS bins."""
    if span / dt < MIN_BINS:
        return (
            f"dt ({dt}s) is too coarse for {what} ({span:.3f}s): "
            f"at least {MIN_BINS} bins are needed to correlate"
        )
    return None


def _bin_cap_error(span: float, dt: float, what: str) -> Optional[str]:
    """Readable rejection when a request would allocate an unusable grid.

    Formatted as a float so a pathologically small dt (span/dt = inf) still
    produces a sentence rather than an OverflowError from ``int()``.
    """
    n_bins = span / dt
    if n_bins <= MAX_BINS:
        return None
    return (
        f"dt ({dt}s) over {what} ({span:.3f}s) gives {n_bins:,.0f} bins; "
        f"increase dt or shorten the range (the cap is {MAX_BINS:,} bins)"
    )


def _time_bounds(event_list) -> Tuple[float, float]:
    """Photon extrema used only to describe cropping, never as GTI bounds.

    ``time[0]``/``time[-1]`` are NOT the bounds: stingray only sorts when
    ``skip_checks`` is False, and ``EventList.read`` never forwards it, so an
    unsorted file yields interior endpoints. Advisory ranges must describe all
    photons even when their stored order does not follow time.
    """
    times = np.asarray(event_list.time, dtype=np.longdouble)
    return np.min(times), np.max(times)


def _continuous_interval(events1, events2=None) -> Tuple[float, float]:
    """Require one continuous native/common GTI for this unweighted estimator.

    A gapped observation may still participate in cross-correlation when its
    intersection with the other observation is a single continuous interval.
    No input events or GTIs are changed to obtain this detached intersection.
    """
    gtis = event_gtis(events1) if events2 is None else common_gtis(events1, events2)
    if len(gtis) == 0:
        raise ValueError("The event lists have no overlapping good-time interval (GTI)")
    start, stop = gtis[0]
    for next_start, next_stop in gtis[1:]:
        # Separate metadata rows that touch exactly still describe continuous
        # exposure. Never bridge a positive gap, even one shorter than dt.
        if next_start != stop:
            raise ValueError(
                "Correlation requires one continuous good-time interval (GTI); "
                "multiple disjoint intervals cannot be correlated without treating "
                "gaps as exposure. Select one continuous interval with the GTI utility."
            )
        stop = next_stop
    return start, stop


def _resolution_warning(event_list, dt: float, label: str) -> Optional[str]:
    """Advisory when dt is not a multiple of the instrument time resolution.

    ``EventList.to_lc`` would snap dt to a multiple of ``EventList.dt`` (set
    from TIMEDEL for real HEASARC files) to avoid beat artefacts. This service
    bins on its own grid so the requested dt is always the dt used -- surface
    the mismatch rather than silently changing it behind the user's back.
    """
    resolution = float(getattr(event_list, "dt", 0.0) or 0.0)
    if resolution <= 0:
        return None
    ratio = dt / resolution
    if abs(ratio - round(ratio)) < 1e-6:
        return None
    return (
        f"dt ({dt}s) is not a multiple of {label}'s time resolution "
        f"({resolution}s), so bins hold unequal numbers of instrument ticks "
        f"and the correlation can show beat artefacts. Use a multiple of "
        f"{resolution}s."
    )


def _empty_error(event_list, name: str) -> Optional[str]:
    """Readable rejection for event lists with no photons."""
    times = getattr(event_list, "time", None)
    if times is None or len(times) == 0:
        return f"EventList '{name}' contains no events"
    return None


def _noise_subtracted_variance(lc: Lightcurve) -> float:
    """Reproduce stingray's norm='variance' denominator term for one curve.

    stingray computes ``var(counts) - mean(counts_err)**2`` and then takes
    ``sqrt(var1 * var2)``. A negative term is what makes the normalisation
    either meaningless (both negative) or NaN (exactly one negative).
    """
    counts = np.asarray(lc.counts, dtype=float)
    counts_err = np.asarray(lc.counts_err, dtype=float)
    return float(np.var(counts) - np.mean(counts_err) ** 2)


def _variance_warning(lc: Lightcurve, label: str) -> Optional[str]:
    """Advisory when a light curve is too flat/faint for norm='variance'."""
    variance = _noise_subtracted_variance(lc)
    if variance > 0:
        return None
    return (
        f"{label} has a negative noise-subtracted variance "
        f"(var - mean(err)^2 = {variance:.3g}), which happens for flat or "
        "low-count data; the 'variance' normalisation is not physically "
        "meaningful here. Try a larger dt or norm='none'."
    )


def _nan_corr_warning(corr) -> Optional[str]:
    """Advisory when stingray silently produced an all/partly-NaN correlation.

    Must be evaluated on the RAW stingray array, before finite_list() turns the
    NaNs into JSON nulls. stingray still reports an argmax-derived time_shift
    for an all-NaN corr, which is meaningless, so the caller nulls it out.
    """
    values = np.asarray(corr, dtype=float)
    if not np.isnan(values).any():
        return None
    return (
        "The correlation contains NaN values (stingray's 'variance' "
        "normalisation takes the square root of a negative variance product "
        "for flat or low-count light curves). The time shift is unreliable "
        "and has been omitted."
    )


def _grid_edges(start: float, stop: float, dt: float) -> np.ndarray:
    """Bin edges RELATIVE to ``start``, so ``edges[0]`` is exactly 0.0.

    ``np.arange`` derives its step from ``(start + dt) - start``, which at
    absolute mission times rounds to the local float64 spacing: at MET 8e7 a
    requested dt of 0.01 s really steps 0.010000005 s. Every edge inherits that
    error, so the histogram's true bin width no longer matches the dt stamped
    on the Lightcurve (from which stingray derives ``time_lags``) and the tail
    of the range is dropped. Starting from 0.0 keeps the step exact.
    """
    span = np.longdouble(stop) - np.longdouble(start)
    ratio = span / np.longdouble(dt)
    nearest = np.rint(ratio)
    # Decimal user inputs such as 64 / 0.05 can fall a few ulps below an integer.
    # Only correct arithmetic roundoff; a fixed tolerance in seconds could
    # admit genuinely partial bins when the requested dt is very small.
    tolerance = 8 * np.finfo(float).eps * max(np.longdouble(1), abs(ratio))
    n_bins = int(nearest if abs(ratio - nearest) <= tolerance else np.floor(ratio))
    return np.arange(n_bins + 1, dtype=np.longdouble) * np.longdouble(dt)


def _grid_lightcurve(
    event_list, start: float, stop: float, edges: np.ndarray, dt: float
) -> Lightcurve:
    """Histogram one event list onto ``edges`` (relative to ``start``).

    The selected continuous GTI supplies real exposure even in bins with no
    photons. Times are shifted before reducing precision and are explicitly
    restricted to half-open full-bin exposure: numpy.histogram would otherwise
    include a photon at the final bin's right edge. Parent arrays are untouched.
    """
    times = np.asarray(event_list.time, dtype=np.longdouble)
    relative = times - np.longdouble(start)
    inside = (relative >= 0) & (relative < edges[-1]) & (times < stop)
    counts, _ = np.histogram(relative[inside], bins=edges)
    centers = start + (edges[:-1] + dt / 2.0)
    gti = [[start, min(stop, start + edges[-1])]]
    return Lightcurve(
        time=centers,
        counts=counts,
        dt=dt,
        gti=gti,
        mjdref=getattr(event_list, "mjdref", 0),
        skip_checks=True,
    )


def _shared_grid_lightcurves(
    events1, events2, dt: float
) -> Tuple[Lightcurve, Lightcurve, float, float]:
    """Bin two event lists onto one grid in their continuous common GTI.

    stingray performs no time alignment whatsoever, so this is the only thing
    that makes a cross-correlation of two independently-loaded event lists
    physically meaningful.
    """
    start, stop = _continuous_interval(events1, events2)
    edges = _grid_edges(start, stop, dt)
    lc1 = _grid_lightcurve(events1, start, stop, edges, dt)
    lc2 = _grid_lightcurve(events2, start, stop, edges, dt)
    return lc1, lc2, start, min(stop, start + edges[-1])


class CorrelationService(BaseService):
    """Service for auto/cross-correlation operations."""

    def auto_correlation(
        self,
        event_list_name: str,
        dt: float,
        mode: str = "same",
        norm: str = "none",
    ) -> Dict[str, Any]:
        """Auto-correlate one event list's light curve with itself.

        ``norm='none'`` uses ``AutoCorrelation``; ``norm='variance'`` must go
        through ``CrossCorrelation(lc, lc, norm='variance')`` because
        ``AutoCorrelation.__init__`` does not forward ``norm`` (it is hardcoded
        to ``'none'`` upstream). ``time_shift`` is always 0 for an
        auto-correlation.

        The light curve is built with the same helper the cross path uses, NOT
        ``EventList.to_lc``: ``to_lc`` snaps dt to a multiple of the event
        list's instrument time resolution and sizes the curve from the GTI, so
        the two pages would report different lag axes -- and a different dt --
        for identical input.
        """
        try:
            for message in (_mode_error(mode), _norm_error(norm), _dt_error(dt)):
                if message:
                    return self.create_result(
                        success=False, data=None, message=message, error=None
                    )

            if not self.state.has_event_data(event_list_name):
                return self.create_result(
                    success=False,
                    data=None,
                    message=f"EventList '{event_list_name}' not found",
                    error=None,
                )

            event_list = self.state.get_event_data(event_list_name)
            empty = _empty_error(event_list, event_list_name)
            if empty:
                return self.create_result(
                    success=False, data=None, message=empty, error=None
                )

            try:
                start, stop = _continuous_interval(event_list)
            except ValueError as error:
                return self.create_result(
                    success=False, data=None, message=str(error), error=None
                )
            span = stop - start
            what = f"the span of '{event_list_name}'"
            for message in (
                _span_error(span, dt, what),
                _bin_cap_error(span, dt, what),
            ):
                if message:
                    return self.create_result(
                        success=False, data=None, message=message, error=None
                    )

            warnings_out: List[str] = []
            resolution = _resolution_warning(event_list, dt, f"'{event_list_name}'")
            if resolution:
                warnings_out.append(resolution)

            with collect_warnings(warnings_out):
                lc = _grid_lightcurve(
                    event_list, start, stop, _grid_edges(start, stop, dt), dt
                )
                if norm == "variance":
                    variance_warning = _variance_warning(lc, "The light curve")
                    if variance_warning:
                        warnings_out.append(variance_warning)
                    correlation = CrossCorrelation(lc, lc, mode=mode, norm="variance")
                else:
                    correlation = AutoCorrelation(lc, mode=mode)

            data = self._build_payload(correlation, mode, norm, warnings_out)
            return self.create_result(
                success=True,
                data=data,
                message=(
                    f"Auto-correlation computed for '{event_list_name}' "
                    # dt comes from the payload, i.e. the dt actually binned
                    # with, so the sentence can never contradict the result.
                    f"({data['n']} lags, dt={data['dt']}s)"
                ),
            )

        except Exception as exception:  # pragma: no cover - defensive
            return self.handle_error(
                exception,
                "Auto-correlation",
                event_list=event_list_name,
                dt=dt,
                mode=mode,
                norm=norm,
            )

    def cross_correlation(
        self,
        event_list_1_name: str,
        event_list_2_name: str,
        dt: float,
        mode: str = "same",
        norm: str = "none",
    ) -> Dict[str, Any]:
        """Cross-correlate two event lists binned onto one shared grid.

        A positive ``time_shift`` means the FIRST list lags behind the second.
        """
        try:
            for message in (_mode_error(mode), _norm_error(norm), _dt_error(dt)):
                if message:
                    return self.create_result(
                        success=False, data=None, message=message, error=None
                    )

            for name in (event_list_1_name, event_list_2_name):
                if not self.state.has_event_data(name):
                    return self.create_result(
                        success=False,
                        data=None,
                        message=f"EventList '{name}' not found",
                        error=None,
                    )

            events1 = self.state.get_event_data(event_list_1_name)
            events2 = self.state.get_event_data(event_list_2_name)
            for event_list, name in (
                (events1, event_list_1_name),
                (events2, event_list_2_name),
            ):
                empty = _empty_error(event_list, name)
                if empty:
                    return self.create_result(
                        success=False, data=None, message=empty, error=None
                    )

            # Runs on the RAW event lists, before any binning.
            overlap = overlap_error(events1, events2)
            if overlap:
                return self.create_result(
                    success=False, data=None, message=overlap, error=None
                )

            start1, stop1 = _time_bounds(events1)
            start2, stop2 = _time_bounds(events2)
            try:
                start, stop = _continuous_interval(events1, events2)
            except ValueError as error:
                return self.create_result(
                    success=False, data=None, message=str(error), error=None
                )
            span = stop - start
            what = "the overlapping time range"
            for message in (
                _span_error(span, dt, what),
                _bin_cap_error(span, dt, what),
            ):
                if message:
                    return self.create_result(
                        success=False, data=None, message=message, error=None
                    )

            warnings_out: List[str] = []
            for event_list, name in (
                (events1, event_list_1_name),
                (events2, event_list_2_name),
            ):
                resolution = _resolution_warning(event_list, dt, f"'{name}'")
                if resolution and resolution not in warnings_out:
                    warnings_out.append(resolution)

            with collect_warnings(warnings_out):
                lc1, lc2, grid_start, grid_stop = _shared_grid_lightcurves(
                    events1, events2, dt
                )

                cropped = any(
                    first < grid_start - dt or last > grid_stop + dt
                    for first, last in ((start1, stop1), (start2, stop2))
                )
                if cropped:
                    warnings_out.append(
                        "Both event lists were binned onto a shared "
                        f"{dt}s grid over their common time range "
                        f"{grid_start:.3f}-{grid_stop:.3f}s ({lc1.n} bins); "
                        "events outside that range were excluded."
                    )

                if norm == "variance":
                    for lc, label in (
                        (lc1, f"'{event_list_1_name}'"),
                        (lc2, f"'{event_list_2_name}'"),
                    ):
                        variance_warning = _variance_warning(lc, label)
                        if variance_warning:
                            warnings_out.append(variance_warning)

                correlation = CrossCorrelation(lc1, lc2, mode=mode, norm=norm)

            data = self._build_payload(correlation, mode, norm, warnings_out)
            return self.create_result(
                success=True,
                data=data,
                message=(
                    f"Cross-correlation computed for '{event_list_1_name}' x "
                    f"'{event_list_2_name}' ({data['n']} lags, dt={data['dt']}s)"
                ),
            )

        except Exception as exception:  # pragma: no cover - defensive
            return self.handle_error(
                exception,
                "Cross-correlation",
                event_list_1=event_list_1_name,
                event_list_2=event_list_2_name,
                dt=dt,
                mode=mode,
                norm=norm,
            )

    def _build_payload(
        self,
        correlation: CrossCorrelation,
        mode: str,
        norm: str,
        warnings_out: List[str],
    ) -> Dict[str, Any]:
        """Serialise a stingray correlation object into the API payload."""
        # Evaluated on the raw array: finite_list() replaces NaN with None.
        nan_warning = _nan_corr_warning(correlation.corr)
        if nan_warning and nan_warning not in warnings_out:
            warnings_out.append(nan_warning)

        time_shift: Optional[float] = None
        if nan_warning is None:
            shift = float(correlation.time_shift)
            if np.isfinite(shift):
                time_shift = shift

        return {
            "time_lags": finite_list(correlation.time_lags),
            "corr": finite_list(correlation.corr),
            "time_shift": time_shift,
            "dt": float(correlation.dt),
            "n": int(correlation.n),
            "mode": mode,
            "norm": norm,
            "warnings": warnings_out,
        }
