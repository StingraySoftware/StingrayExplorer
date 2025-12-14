"""
API routes for EventList data operations.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from services.data_service import DataService
from services.state_manager import StateManager

router = APIRouter()


def get_data_service(request: Request) -> DataService:
    """Get DataService instance from app state."""
    return DataService(
        state_manager=request.app.state.state_manager,
        performance_monitor=request.app.state.performance_monitor,
    )


# Request/Response Models
class LoadEventListRequest(BaseModel):
    file_path: str
    name: str
    fmt: str = "ogip"
    rmf_file: Optional[str] = None
    additional_columns: Optional[List[str]] = None


class LoadEventListFromUrlRequest(BaseModel):
    url: str
    name: str
    fmt: str = "ogip"


class SaveEventListRequest(BaseModel):
    name: str
    file_path: str
    fmt: str = "ogip"


class CheckFileSizeRequest(BaseModel):
    file_path: str


# Routes
@router.post("/load")
async def load_event_list(
    request: LoadEventListRequest,
    service: DataService = Depends(get_data_service),
):
    """Load an EventList from a file."""
    return service.load_event_list(
        file_path=request.file_path,
        name=request.name,
        fmt=request.fmt,
        rmf_file=request.rmf_file,
        additional_columns=request.additional_columns,
    )


@router.post("/load-url")
async def load_event_list_from_url(
    request: LoadEventListFromUrlRequest,
    service: DataService = Depends(get_data_service),
):
    """Load an EventList from a URL."""
    return service.load_event_list_from_url(
        url=request.url,
        name=request.name,
        fmt=request.fmt,
    )


@router.post("/save")
async def save_event_list(
    request: SaveEventListRequest,
    service: DataService = Depends(get_data_service),
):
    """Save an EventList to disk."""
    return service.save_event_list(
        name=request.name,
        file_path=request.file_path,
        fmt=request.fmt,
    )


@router.delete("/{name}")
async def delete_event_list(
    name: str,
    service: DataService = Depends(get_data_service),
):
    """Delete an EventList from state."""
    return service.delete_event_list(name)


@router.get("/{name}")
async def get_event_list_info(
    name: str,
    service: DataService = Depends(get_data_service),
):
    """Get information about an EventList."""
    return service.get_event_list_info(name)


@router.get("/")
async def list_event_lists(
    service: DataService = Depends(get_data_service),
):
    """List all loaded EventLists."""
    return service.list_event_lists()


@router.post("/check-size")
async def check_file_size(
    request: CheckFileSizeRequest,
    service: DataService = Depends(get_data_service),
):
    """Check file size and get loading recommendations."""
    return service.check_file_size(request.file_path)
