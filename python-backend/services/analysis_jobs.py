"""Worker targets for long analyses run by services.process_jobs.

Each target rebuilds a private StateManager holding the caller's dataset
under its original identity and backend session, then runs the same
service method the direct endpoint uses, so background results are
identical to direct ones. Previews are published as partial results.
"""

import numpy as np

PREVIEW_SEGMENTS = 16
PREVIEW_MAX_FREQUENCIES = 512


def _finite(values):
    return [None if not np.isfinite(value) else float(value) for value in np.ravel(values)]


def _preview(events, dt, segment_size, norm):
    """A dynamical power spectrum of the first segments only, for early display."""
    from stingray import DynamicalPowerspectrum
    from stingray.gti import cross_two_gtis

    from services.analysis_helpers import event_gtis
    from services.scientific_compatibility import compatible_event_lightcurve

    gti = event_gtis(events)
    window = np.array([[gti[0, 0], gti[0, 0] + PREVIEW_SEGMENTS * segment_size]])
    preview_gti = cross_two_gtis(gti, window)
    lightcurve = compatible_event_lightcurve(events, dt)
    keep = (lightcurve.time >= preview_gti[0, 0]) & (lightcurve.time < preview_gti[-1, 1])
    lightcurve = lightcurve.apply_mask(keep)
    lightcurve.gti = preview_gti
    preview = DynamicalPowerspectrum(lightcurve, segment_size=segment_size, norm=norm)
    stride = max(1, int(np.ceil(len(preview.freq) / PREVIEW_MAX_FREQUENCIES)))
    return {
        "preview": True,
        "n_segments": int(len(preview.time)),
        "freq": _finite(preview.freq[::stride]),
        "time": _finite(preview.time),
        "dyn_ps": [_finite(row) for row in np.asarray(preview.dyn_ps)[::stride]],
        "frequency_stride": stride,
        "norm": norm,
    }


def dynamical_power_spectrum(payload, emit):
    """Run SpectrumService.create_dynamical_power_spectrum in a worker."""
    import warnings

    from models.event_selection import EventSelection
    from services.spectrum_service import SpectrumService
    from services.state_manager import StateManager

    name = payload["event_list_name"]
    params = payload["params"]
    selection = (
        EventSelection(**payload["selection"]) if payload.get("selection") else None
    )
    emit("progress", (0.05, "Preparing the event list"))
    state = StateManager()
    state.session_id = payload["session_id"]
    state.add_event_data_with_identity(name, payload["events"], payload["dataset_id"])

    events, _ = state.copy_event_data_with_identity(name, selection)
    emit("progress", (0.15, "Computing a preview of the first segments"))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            emit(
                "partial",
                _preview(events, params["dt"], params["segment_size"], params["norm"]),
            )
    except Exception as error:  # a preview must never stop the analysis
        emit("partial", {"preview": True, "n_segments": 0, "error": str(error)})

    emit("progress", (0.3, "Computing the dynamical power spectrum"))
    result = SpectrumService(state).create_dynamical_power_spectrum(
        name,
        params["dt"],
        params["segment_size"],
        norm=params["norm"],
        output_name=params.get("output_name"),
        selection=selection,
    )
    emit("progress", (0.95, "Returning the result"))
    stored = (
        state.get_spectrum_data(params["output_name"])
        if result.get("success") and params.get("output_name")
        else None
    )
    return {"response": result, "stored": stored}
