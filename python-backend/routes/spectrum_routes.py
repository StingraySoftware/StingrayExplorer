"""
API routes for spectrum operations.
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, model_validator
from models.event_selection import EventSelection

from services.spectrum_service import SpectrumService

router = APIRouter()


def get_spectrum_service(request: Request) -> SpectrumService:
    """Get SpectrumService instance from app state."""
    return SpectrumService(
        state_manager=request.app.state.state_manager,
        performance_monitor=request.app.state.performance_monitor,
    )


# Request Models
class _SingleSourceRequest(BaseModel):
    """An event list (binned at dt, optionally selected) or a stored light curve."""

    event_list_name: Optional[str] = None
    lightcurve_name: Optional[str] = None
    selection: Optional[EventSelection] = None
    dt: Optional[float] = None

    @model_validator(mode="after")
    def _one_source(self):
        if (self.event_list_name is None) == (self.lightcurve_name is None):
            raise ValueError("Give exactly one of event_list_name or lightcurve_name")
        if self.event_list_name is not None and self.dt is None:
            raise ValueError("dt is required to bin an event list")
        if self.lightcurve_name is not None and self.selection is not None:
            raise ValueError(
                "Photon selections apply to event lists; a light curve has no "
                "photons to select"
            )
        return self


class CreatePowerSpectrumRequest(_SingleSourceRequest):
    norm: str = "leahy"
    output_name: Optional[str] = None


class CreateAveragedPowerSpectrumRequest(_SingleSourceRequest):
    segment_size: float
    norm: str = "leahy"
    output_name: Optional[str] = None


class CreateCrossSpectrumRequest(BaseModel):
    event_list_1_name: str
    event_list_2_name: str
    selection_1: Optional[EventSelection] = None
    selection_2: Optional[EventSelection] = None
    dt: float
    norm: str = "leahy"
    output_name: Optional[str] = None


class CreateAveragedCrossSpectrumRequest(BaseModel):
    event_list_1_name: str
    event_list_2_name: str
    selection_1: Optional[EventSelection] = None
    selection_2: Optional[EventSelection] = None
    dt: float
    segment_size: float
    norm: str = "leahy"
    output_name: Optional[str] = None


class CreateDynamicalPowerSpectrumRequest(BaseModel):
    event_list_name: str
    selection: Optional[EventSelection] = None
    dt: float
    segment_size: float
    norm: str = "leahy"
    output_name: Optional[str] = None


class RebinSpectrumRequest(BaseModel):
    name: str
    rebin_factor: float
    log: bool = False
    output_name: Optional[str] = None
    expected_result_id: Optional[str] = None


# Routes
@router.post("/power-spectrum")
async def create_power_spectrum(
    request: CreatePowerSpectrumRequest,
    service: SpectrumService = Depends(get_spectrum_service),
):
    """Create a power spectrum from an EventList."""
    return await asyncio.to_thread(
        service.create_power_spectrum,
        event_list_name=request.event_list_name,
        lightcurve_name=request.lightcurve_name,
        selection=request.selection,
        dt=request.dt,
        norm=request.norm,
        output_name=request.output_name,
    )


@router.post("/averaged-power-spectrum")
async def create_averaged_power_spectrum(
    request: CreateAveragedPowerSpectrumRequest,
    service: SpectrumService = Depends(get_spectrum_service),
):
    """Create an averaged power spectrum from an EventList."""
    return await asyncio.to_thread(
        service.create_averaged_power_spectrum,
        event_list_name=request.event_list_name,
        lightcurve_name=request.lightcurve_name,
        selection=request.selection,
        dt=request.dt,
        segment_size=request.segment_size,
        norm=request.norm,
        output_name=request.output_name,
    )


@router.post("/cross-spectrum")
async def create_cross_spectrum(
    request: CreateCrossSpectrumRequest,
    service: SpectrumService = Depends(get_spectrum_service),
):
    """Create a cross spectrum from two EventLists."""
    return await asyncio.to_thread(
        service.create_cross_spectrum,
        event_list_1_name=request.event_list_1_name,
        event_list_2_name=request.event_list_2_name,
        selection_1=request.selection_1,
        selection_2=request.selection_2,
        dt=request.dt,
        norm=request.norm,
        output_name=request.output_name,
    )


@router.post("/averaged-cross-spectrum")
async def create_averaged_cross_spectrum(
    request: CreateAveragedCrossSpectrumRequest,
    service: SpectrumService = Depends(get_spectrum_service),
):
    """Create an averaged cross spectrum from two EventLists."""
    return await asyncio.to_thread(
        service.create_averaged_cross_spectrum,
        event_list_1_name=request.event_list_1_name,
        event_list_2_name=request.event_list_2_name,
        selection_1=request.selection_1,
        selection_2=request.selection_2,
        dt=request.dt,
        segment_size=request.segment_size,
        norm=request.norm,
        output_name=request.output_name,
    )


@router.post("/dynamical-power-spectrum")
async def create_dynamical_power_spectrum(
    request: CreateDynamicalPowerSpectrumRequest,
    service: SpectrumService = Depends(get_spectrum_service),
):
    """Create a dynamical power spectrum from an EventList."""
    return await asyncio.to_thread(
        service.create_dynamical_power_spectrum,
        event_list_name=request.event_list_name,
        selection=request.selection,
        dt=request.dt,
        segment_size=request.segment_size,
        norm=request.norm,
        output_name=request.output_name,
    )


@router.post("/rebin")
async def rebin_spectrum(
    request: RebinSpectrumRequest,
    service: SpectrumService = Depends(get_spectrum_service),
):
    """Rebin a spectrum."""
    return await asyncio.to_thread(
        service.rebin_spectrum,
        name=request.name,
        rebin_factor=request.rebin_factor,
        log=request.log,
        output_name=request.output_name,
        expected_result_id=request.expected_result_id,
    )


@router.get("/")
async def list_spectra(
    service: SpectrumService = Depends(get_spectrum_service),
):
    """List all loaded spectra."""
    return await asyncio.to_thread(service.list_spectra)


@router.delete("/{name}")
async def delete_spectrum(
    name: str,
    service: SpectrumService = Depends(get_spectrum_service),
):
    """Delete a spectrum from state."""
    return await asyncio.to_thread(service.delete_spectrum, name)
