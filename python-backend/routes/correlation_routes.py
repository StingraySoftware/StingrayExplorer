"""
API routes for correlation operations.

Implemented per docs/superpowers/plans/2026-07-29-quicklook-remaining-pages.md.
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from models.event_selection import EventSelection
from services.correlation_service import CorrelationService

router = APIRouter()


def get_correlation_service(request: Request) -> CorrelationService:
    """Get CorrelationService instance from app state."""
    return CorrelationService(
        state_manager=request.app.state.state_manager,
        performance_monitor=request.app.state.performance_monitor,
    )


# Form metadata for generated parameter forms. It is JSON-schema
# documentation only: the services validate these values themselves, so
# requests are accepted and rejected exactly as before.
DT_FIELD = Field(
    title="Time bin dt (s)",
    description="Light-curve bin width; the lag axis is sampled at this step",
    json_schema_extra={"exclusiveMinimum": 0, "examples": [0.1]},
)
MODE_FIELD = Field(
    "same",
    title="Mode",
    description="'same' keeps the input length; 'full' keeps every overlap",
    json_schema_extra={"enum": ["same", "full"]},
)
NORM_FIELD = Field(
    "none",
    title="Normalization",
    description="'variance' divides by the light curves' variances",
    json_schema_extra={"enum": ["none", "variance"]},
)


# Request Models
class AutoCorrelationRequest(BaseModel):
    event_list_name: str
    selection: Optional[EventSelection] = None
    dt: float = DT_FIELD
    mode: str = MODE_FIELD
    norm: str = NORM_FIELD


class CrossCorrelationRequest(BaseModel):
    event_list_1_name: str
    event_list_2_name: str
    selection_1: Optional[EventSelection] = None
    selection_2: Optional[EventSelection] = None
    dt: float = DT_FIELD
    mode: str = MODE_FIELD
    norm: str = NORM_FIELD


# Routes
@router.post("/auto-correlation")
async def auto_correlation(
    request: AutoCorrelationRequest,
    service: CorrelationService = Depends(get_correlation_service),
):
    """Auto-correlate an EventList's light curve with itself."""
    return await asyncio.to_thread(
        service.auto_correlation,
        event_list_name=request.event_list_name,
        selection=request.selection,
        dt=request.dt,
        mode=request.mode,
        norm=request.norm,
    )


@router.post("/cross-correlation")
async def cross_correlation(
    request: CrossCorrelationRequest,
    service: CorrelationService = Depends(get_correlation_service),
):
    """Cross-correlate two EventLists binned onto a shared time grid."""
    return await asyncio.to_thread(
        service.cross_correlation,
        event_list_1_name=request.event_list_1_name,
        event_list_2_name=request.event_list_2_name,
        selection_1=request.selection_1,
        selection_2=request.selection_2,
        dt=request.dt,
        mode=request.mode,
        norm=request.norm,
    )
