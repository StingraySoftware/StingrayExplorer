"""One registration per stored result kind.

Each kind names the state store it lives in, how its identity is recorded,
the class the project codec may rebuild (which keeps the saved format
stable), the General I/O object type that exports it, and the default plot
the renderer uses for it. Publishing an object no kind recognises fails, so
a new result kind cannot reach saved projects or exports unregistered.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

from astropy.table import Table
from stingray import (
    AveragedCrossspectrum,
    AveragedPowerspectrum,
    Crossspectrum,
    DynamicalPowerspectrum,
    EventList,
    Lightcurve,
    Powerspectrum,
)
from stingray.bispectrum import Bispectrum

STORES = ("event_data", "lightcurve_data", "spectrum_data", "analysis_results")


class UnregisteredResultKind(TypeError):
    """An object that no registered result kind describes."""


@dataclass(frozen=True)
class ResultKind:
    key: str
    label: str
    store: str
    #: dataset (EventList identity), result_identity (attached record),
    #: provenance (dict carrying its own provenance) or none.
    identity: str
    export_object_type: str
    default_plot: str
    matches: Callable[[Any], bool]
    #: Class the project codec may rebuild; None for plain JSON-like values.
    project_class: Optional[type] = None


def _exactly(cls):
    return lambda obj: type(obj) is cls


def _operation(name):
    return lambda obj: (
        isinstance(obj, dict)
        and isinstance(obj.get("provenance"), dict)
        and obj["provenance"].get("operation") == name
    )


def _tabular(obj):
    return isinstance(obj, (dict, list, tuple, Table))


REGISTRY: Tuple[ResultKind, ...] = (
    ResultKind(
        "event_list",
        "Event list",
        "event_data",
        "dataset",
        "event_list",
        "event_list",
        _exactly(EventList),
        EventList,
    ),
    ResultKind(
        "lightcurve",
        "Light curve",
        "lightcurve_data",
        "result_identity",
        "lightcurve",
        "lightcurve",
        _exactly(Lightcurve),
        Lightcurve,
    ),
    ResultKind(
        "power_spectrum",
        "Power spectrum",
        "spectrum_data",
        "result_identity",
        "spectrum",
        "spectrum",
        _exactly(Powerspectrum),
        Powerspectrum,
    ),
    ResultKind(
        "averaged_power_spectrum",
        "Averaged power spectrum",
        "spectrum_data",
        "result_identity",
        "spectrum",
        "spectrum",
        _exactly(AveragedPowerspectrum),
        AveragedPowerspectrum,
    ),
    ResultKind(
        "cross_spectrum",
        "Cross spectrum",
        "spectrum_data",
        "result_identity",
        "spectrum",
        "cross_spectrum",
        _exactly(Crossspectrum),
        Crossspectrum,
    ),
    ResultKind(
        "averaged_cross_spectrum",
        "Averaged cross spectrum",
        "spectrum_data",
        "result_identity",
        "spectrum",
        "cross_spectrum",
        _exactly(AveragedCrossspectrum),
        AveragedCrossspectrum,
    ),
    ResultKind(
        "dynamical_power_spectrum",
        "Dynamical power spectrum",
        "spectrum_data",
        "result_identity",
        "spectrum",
        "image_2d",
        _exactly(DynamicalPowerspectrum),
        DynamicalPowerspectrum,
    ),
    ResultKind(
        "bispectrum",
        "Bispectrum",
        "analysis_results",
        "none",
        "analysis_result",
        "image_2d",
        _exactly(Bispectrum),
        Bispectrum,
    ),
    ResultKind(
        "power_colors",
        "Power colours",
        "analysis_results",
        "provenance",
        "analysis_result",
        "power_colors",
        _operation("timing_power_colors"),
    ),
    ResultKind(
        "time_lags",
        "Time lags",
        "analysis_results",
        "provenance",
        "analysis_result",
        "time_lags",
        _operation("timing_time_lags"),
    ),
    ResultKind(
        "coherence",
        "Coherence",
        "analysis_results",
        "provenance",
        "analysis_result",
        "coherence",
        _operation("timing_coherence"),
    ),
    # Generic tables last: any other JSON-like or astropy table result.
    ResultKind(
        "table",
        "Table",
        "analysis_results",
        "none",
        "analysis_result",
        "table",
        _tabular,
    ),
)


def kind_of(store: str, obj: Any) -> ResultKind:
    """The registered kind of ``obj`` in ``store``, or UnregisteredResultKind."""
    for kind in REGISTRY:
        if kind.store == store and kind.matches(obj):
            return kind
    raise UnregisteredResultKind(
        f"{type(obj).__name__} is not a registered result kind for {store}; "
        "register it in services/result_registry.py"
    )


def project_classes() -> dict:
    """Classes the project codec may rebuild, keyed by saved class name."""
    return {
        kind.project_class.__name__: kind.project_class
        for kind in REGISTRY
        if kind.project_class is not None
    }


def describe_kinds() -> list:
    return [
        {
            "key": kind.key,
            "label": kind.label,
            "store": kind.store,
            "export_object_type": kind.export_object_type,
            "default_plot": kind.default_plot,
            "identity": kind.identity,
        }
        for kind in REGISTRY
    ]
