"""One photon-selection request shared by every endpoint that reads an EventList."""

from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NonNegativeFloat = Annotated[float, Field(ge=0)]
NonNegativeInt = Annotated[int, Field(ge=0)]


def _ordered_pair(value, label):
    if value is not None and not value[0] < value[1]:
        raise ValueError(f"{label}: lower bound must be below the upper bound")
    return value


def _ordered_intervals(value, label):
    """Require sorted, disjoint [start, stop) intervals, like a GTI list."""
    if value is None:
        return value
    if not value:
        raise ValueError(f"{label} must contain at least one interval")
    for start, stop in value:
        _ordered_pair((start, stop), label)
    for (_, previous_stop), (next_start, _) in zip(value[:-1], value[1:]):
        if next_start < previous_stop:
            raise ValueError(f"{label} must be sorted and must not overlap")
    return value


class EventSelection(BaseModel):
    """Photons to keep, applied to a detached copy of the stored EventList.

    Ranges are half-open, [low, high), matching Stingray's
    ``EventList.get_energy_mask``. Adjacent bands therefore never share a
    photon. ``energy_range`` is in keV and needs a calibrated energy column;
    ``pi_range`` selects instrument PI channels instead. Time intervals and the
    extra GTI list are intersected with the EventList's own GTIs.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    energy_range: Optional[tuple[NonNegativeFloat, NonNegativeFloat]] = None
    pi_range: Optional[tuple[NonNegativeInt, NonNegativeInt]] = None
    detector_ids: Optional[List[NonNegativeInt]] = Field(default=None, min_length=1)
    time_intervals: Optional[List[tuple[float, float]]] = None
    gti: Optional[List[tuple[float, float]]] = None

    @field_validator("energy_range", "pi_range")
    @classmethod
    def _range_is_ordered(cls, value, info):
        return _ordered_pair(value, info.field_name)

    @field_validator("time_intervals", "gti")
    @classmethod
    def _intervals_are_ordered(cls, value, info):
        return _ordered_intervals(value, info.field_name)

    @field_validator("detector_ids")
    @classmethod
    def _unique_detectors(cls, value):
        return sorted(set(value)) if value is not None else value

    @model_validator(mode="after")
    def _one_spectral_axis(self):
        if self.energy_range is not None and self.pi_range is not None:
            raise ValueError("Select either an energy_range or pi_range, not both")
        return self

    def is_empty(self) -> bool:
        return all(
            getattr(self, field) is None for field in type(self).model_fields
        )


class NonSpectralEventSelection(EventSelection):
    """Selection for energy-resolved pages, which define their own energy bands."""

    @model_validator(mode="after")
    def _no_spectral_cut(self):
        if self.energy_range is not None or self.pi_range is not None:
            raise ValueError(
                "Energy-resolved spectra choose photons with this page's energy "
                "settings (energy_min, energy_max and bands); remove "
                "energy_range/pi_range from the selection and use those settings"
            )
        return self
