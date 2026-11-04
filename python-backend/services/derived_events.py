"""Derive new named EventLists from loaded ones, recording their parentage.

Each product is a new stored EventList with an ``event_lineage`` record: the
operation, its parameters and each parent's name, dataset identity and size
(and the parent's own lineage when it was itself derived). Parents are never
modified. Every operation used here exists in all supported Stingray releases.
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional

import numpy as np
import stingray

from models.event_selection import EventSelection

from .base_service import BaseService
from .event_selection import _PRESERVED_FIELDS
from .spectrum_products import _public_lineage
from .utility_helpers import validate_derived_name

GTI_STRATEGIES = ("infer", "intersection", "union", "append", "none")


def parent_record(name, events, dataset_id):
    """Describe one parent without copying photons or private file details."""
    record = {"name": name, "dataset_id": dataset_id, "n_events": len(events.time)}
    lineage = getattr(events, "event_lineage", None)
    if lineage is not None:
        record["lineage"] = deepcopy(lineage)
    return record


def make_lineage(operation, parents, parameters):
    return _public_lineage(
        {
            "operation": operation,
            "parents": parents,
            "parameters": parameters,
            "stingray_version": stingray.__version__,
        }
    )


class DerivedEventService(BaseService):
    """Create filtered, joined, sorted and dead-time-applied EventLists."""

    def _capture(self, name, selection=None):
        captured = self.state.copy_event_data_with_identity(name, selection)
        if captured is None:
            raise ValueError(f"EventList '{name}' not found")
        return captured

    def _publish(self, output_name, events, operation, parents, parameters):
        # A stored product's history lives in its lineage; a selection record
        # describes only what one analysis applied to its input.
        if hasattr(events, "event_selection"):
            del events.event_selection
        events.event_lineage = make_lineage(operation, parents, parameters)
        if not self.state.add_event_data_if_absent(output_name, events):
            raise ValueError(f"EventList name '{output_name}' already exists")
        data = {
            "name": output_name,
            "dataset_id": self.state.get_event_identity(output_name),
            "n_events": int(len(events.time)),
            "lineage": deepcopy(events.event_lineage),
        }
        return self.create_result(
            success=True,
            data=data,
            message=(
                f"Created EventList '{output_name}' ({data['n_events']:,} events) "
                f"by {operation.replace('_', ' ')}"
            ),
        )

    @staticmethod
    def _check_name(output_name):
        problem = validate_derived_name(output_name)
        if problem:
            raise ValueError(problem)

    def derive_filtered(
        self, event_list_name: str, selection: EventSelection, output_name: str
    ) -> Dict[str, Any]:
        """Store the photons a selection keeps as a new EventList."""
        try:
            self._check_name(output_name)
            if selection is None or selection.is_empty():
                raise ValueError("Filtering needs a selection with at least one criterion")
            parent, dataset_id = self._capture(event_list_name)
            selected, _ = self._capture(event_list_name, selection)
            return self._publish(
                output_name,
                selected,
                "filter",
                [parent_record(event_list_name, parent, dataset_id)],
                {"selection": deepcopy(selected.event_selection)},
            )
        except Exception as error:
            return self.handle_error(
                error, "Filtering an EventList", event_list=event_list_name
            )

    def derive_joined(
        self,
        event_list_names: List[str],
        output_name: str,
        gti_strategy: str = "infer",
    ) -> Dict[str, Any]:
        """Join EventLists (e.g. NuSTAR FPMA and FPMB) into one time-ordered list."""
        try:
            self._check_name(output_name)
            if len(event_list_names) < 2 or len(set(event_list_names)) != len(
                event_list_names
            ):
                raise ValueError("Joining needs at least two different EventLists")
            if gti_strategy not in GTI_STRATEGIES:
                raise ValueError(
                    "gti_strategy must be one of: " + ", ".join(GTI_STRATEGIES)
                )
            captured = [(name, *self._capture(name)) for name in event_list_names]
            joined = captured[0][1]
            for _, events, _ in captured[1:]:
                joined = joined.join(events, strategy=gti_strategy)
            return self._publish(
                output_name,
                joined,
                "join",
                [parent_record(name, events, dataset) for name, events, dataset in captured],
                {"gti_strategy": gti_strategy},
            )
        except Exception as error:
            return self.handle_error(
                error, "Joining EventLists", event_lists=", ".join(event_list_names)
            )

    def derive_sorted(self, event_list_name: str, output_name: str) -> Dict[str, Any]:
        """Store a copy with photons in time order, keeping every column aligned."""
        try:
            self._check_name(output_name)
            parent, dataset_id = self._capture(event_list_name)
            ordered = parent.sort(inplace=False)
            self._keep_metadata(parent, ordered)
            return self._publish(
                output_name,
                ordered,
                "sort",
                [parent_record(event_list_name, parent, dataset_id)],
                {},
            )
        except Exception as error:
            return self.handle_error(
                error, "Sorting an EventList", event_list=event_list_name
            )

    def derive_deadtime(
        self,
        event_list_name: str,
        dead_time: float,
        output_name: str,
        paralyzable: bool = False,
        dt_sigma: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Simulate detector dead time by removing photons inside dead windows."""
        try:
            self._check_name(output_name)
            if not np.isfinite(dead_time) or dead_time <= 0:
                raise ValueError("dead_time must be finite and greater than zero")
            parent, dataset_id = self._capture(event_list_name)
            if not np.all(np.diff(np.asarray(parent.time)) >= 0):
                raise ValueError(
                    "Dead time needs time-ordered photons; sort the EventList first"
                )
            dead = parent.apply_deadtime(
                dead_time,
                inplace=False,
                paralyzable=paralyzable,
                dt_sigma=dt_sigma,
            )
            self._keep_metadata(parent, dead)
            return self._publish(
                output_name,
                dead,
                "apply_deadtime",
                [parent_record(event_list_name, parent, dataset_id)],
                {
                    "dead_time": float(dead_time),
                    "paralyzable": bool(paralyzable),
                    "dt_sigma": None if dt_sigma is None else float(dt_sigma),
                },
            )
        except Exception as error:
            return self.handle_error(
                error, "Applying dead time", event_list=event_list_name
            )

    @staticmethod
    def _keep_metadata(source, product):
        for field in _PRESERVED_FIELDS:
            if hasattr(source, field):
                setattr(product, field, deepcopy(getattr(source, field)))
