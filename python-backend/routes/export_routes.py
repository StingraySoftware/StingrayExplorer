"""
API routes for data export operations.
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from services.export_service import ExportService

router = APIRouter()


def get_export_service(request: Request) -> ExportService:
    """Get ExportService instance from app state."""
    return ExportService(
        state_manager=request.app.state.state_manager,
        performance_monitor=request.app.state.performance_monitor,
    )


# Request Models
class ExportToCsvRequest(BaseModel):
    name: str
    file_path: str


class ExportToHdf5Request(BaseModel):
    name: str
    file_path: str
    data_type: str = "event_list"


class ExportToFitsRequest(BaseModel):
    name: str
    file_path: str
    data_type: str = "event_list"


# Routes
@router.post("/event-list/csv")
async def export_event_list_to_csv(
    request: ExportToCsvRequest,
    service: ExportService = Depends(get_export_service),
):
    """Export an EventList to CSV file."""
    return service.export_event_list_to_csv(
        name=request.name,
        file_path=request.file_path,
    )


@router.post("/lightcurve/csv")
async def export_lightcurve_to_csv(
    request: ExportToCsvRequest,
    service: ExportService = Depends(get_export_service),
):
    """Export a Lightcurve to CSV file."""
    return service.export_lightcurve_to_csv(
        name=request.name,
        file_path=request.file_path,
    )


@router.post("/spectrum/csv")
async def export_spectrum_to_csv(
    request: ExportToCsvRequest,
    service: ExportService = Depends(get_export_service),
):
    """Export a spectrum to CSV file."""
    return service.export_power_spectrum_to_csv(
        name=request.name,
        file_path=request.file_path,
    )


@router.post("/bispectrum/csv")
async def export_bispectrum_to_csv(
    request: ExportToCsvRequest,
    service: ExportService = Depends(get_export_service),
):
    """Export a bispectrum to CSV file."""
    return service.export_bispectrum_to_csv(
        name=request.name,
        file_path=request.file_path,
    )


@router.post("/hdf5")
async def export_to_hdf5(
    request: ExportToHdf5Request,
    service: ExportService = Depends(get_export_service),
):
    """Export data to HDF5 file."""
    return service.export_to_hdf5(
        name=request.name,
        file_path=request.file_path,
        data_type=request.data_type,
    )


@router.post("/fits")
async def export_to_fits(
    request: ExportToFitsRequest,
    service: ExportService = Depends(get_export_service),
):
    """Export data to FITS file."""
    return service.export_to_fits(
        name=request.name,
        file_path=request.file_path,
        data_type=request.data_type,
    )
