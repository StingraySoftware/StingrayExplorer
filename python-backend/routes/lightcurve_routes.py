"""
API routes for Lightcurve operations.
"""

import asyncio
from typing import Annotated, List, Optional, Union

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from models.event_selection import EventSelection

from services.lightcurve_service import DEFAULT_MAX_PLOT_POINTS, LightcurveService

router = APIRouter()


def get_lightcurve_service(request: Request) -> LightcurveService:
    """Get LightcurveService instance from app state."""
    return LightcurveService(
        state_manager=request.app.state.state_manager,
        performance_monitor=request.app.state.performance_monitor,
    )


# Request Models
class CreateLightcurveFromEventListRequest(BaseModel):
    event_list_name: str
    selection: Optional[EventSelection] = None
    dt: float
    output_name: str
    gti: Optional[List[List[float]]] = None
    max_points: Optional[int] = Field(default=DEFAULT_MAX_PLOT_POINTS, ge=0)


GrantText = Annotated[str, Field(min_length=1, max_length=512)]


class LightcurveFileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    file_path: str = Field(min_length=1, max_length=4_096)
    file_grant: GrantText


class LoadLightcurveFileRequest(LightcurveFileRequest):
    output_name: str = Field(min_length=1, max_length=64)
    hdu: Optional[Union[int, str]] = None
    rate_column: Optional[str] = None
    band: Optional[int] = Field(default=None, ge=0)
    mjdref: Optional[float] = None
    max_points: Optional[int] = Field(default=DEFAULT_MAX_PLOT_POINTS, ge=0)


class CreateLightcurveFromArraysRequest(BaseModel):
    times: List[float]
    counts: List[float]
    dt: float
    output_name: str


class RebinLightcurveRequest(BaseModel):
    name: str
    rebin_factor: float
    output_name: str
    max_points: Optional[int] = Field(default=DEFAULT_MAX_PLOT_POINTS, ge=0)
    expected_result_id: Optional[str] = None


# Routes
@router.post("/from-event-list")
async def create_lightcurve_from_event_list(
    request: CreateLightcurveFromEventListRequest,
    service: LightcurveService = Depends(get_lightcurve_service),
):
    """Create a Lightcurve from an EventList."""
    return await asyncio.to_thread(
        service.create_lightcurve_from_event_list,
        event_list_name=request.event_list_name,
        selection=request.selection,
        dt=request.dt,
        output_name=request.output_name,
        gti=request.gti,
        max_points=request.max_points,
    )


@router.post("/inspect-file")
async def inspect_lightcurve_file(
    request: LightcurveFileRequest,
    service: LightcurveService = Depends(get_lightcurve_service),
):
    """List the light-curve tables (HDUs, rate columns, bands) in a FITS file."""
    return await asyncio.to_thread(
        service.inspect_lightcurve_file, request.file_path, request.file_grant
    )


@router.post("/from-file")
async def load_lightcurve_file(
    request: LoadLightcurveFileRequest,
    service: LightcurveService = Depends(get_lightcurve_service),
):
    """Store a light curve read from a natively selected mission FITS file."""
    return await asyncio.to_thread(
        service.load_lightcurve_file,
        file_path=request.file_path,
        file_grant=request.file_grant,
        output_name=request.output_name,
        hdu=request.hdu,
        rate_column=request.rate_column,
        band=request.band,
        mjdref=request.mjdref,
        max_points=request.max_points,
    )


@router.post("/from-arrays")
async def create_lightcurve_from_arrays(
    request: CreateLightcurveFromArraysRequest,
    service: LightcurveService = Depends(get_lightcurve_service),
):
    """Create a Lightcurve from time and count arrays."""
    return await asyncio.to_thread(
        service.create_lightcurve_from_arrays,
        times=request.times,
        counts=request.counts,
        dt=request.dt,
        output_name=request.output_name,
    )


@router.post("/rebin")
async def rebin_lightcurve(
    request: RebinLightcurveRequest,
    service: LightcurveService = Depends(get_lightcurve_service),
):
    """Rebin a lightcurve."""
    return await asyncio.to_thread(
        service.rebin_lightcurve,
        name=request.name,
        rebin_factor=request.rebin_factor,
        output_name=request.output_name,
        max_points=request.max_points,
        expected_result_id=request.expected_result_id,
    )


@router.get("/{name}")
async def get_lightcurve_data(
    name: str,
    max_points: int = Query(default=DEFAULT_MAX_PLOT_POINTS, ge=0),
    service: LightcurveService = Depends(get_lightcurve_service),
):
    """Get lightcurve data for plotting."""
    return await asyncio.to_thread(
        service.get_lightcurve_data, name, max_points=max_points
    )


@router.get("/")
async def list_lightcurves(
    service: LightcurveService = Depends(get_lightcurve_service),
):
    """List all loaded lightcurves."""
    return await asyncio.to_thread(service.list_lightcurves)


@router.delete("/{name}")
async def delete_lightcurve(
    name: str,
    service: LightcurveService = Depends(get_lightcurve_service),
):
    """Delete a lightcurve from state."""
    return await asyncio.to_thread(service.delete_lightcurve, name)
