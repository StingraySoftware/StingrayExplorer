"""Explicit native-grant project save and reopen endpoints."""

import asyncio
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from services.project_service import ProjectService
from routes.utility_models import UtilityResponse

router = APIRouter()


def service(request: Request):
    return ProjectService(state_manager=request.app.state.state_manager)


class SaveProject(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    destination_path: str = Field(min_length=1, max_length=4096)
    destination_grant: str = Field(min_length=1, max_length=512)
    renderer: dict = Field(default_factory=dict)
    workspace: dict | None = None


class OpenProject(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    file_path: str = Field(min_length=1, max_length=4096)
    file_grant: str = Field(min_length=1, max_length=512)


@router.post("/save", response_model=UtilityResponse)
async def save_project(request: SaveProject, projects=Depends(service)):
    return await asyncio.to_thread(projects.save, **request.model_dump())


@router.post("/open", response_model=UtilityResponse)
async def open_project(request: OpenProject, projects=Depends(service)):
    return await asyncio.to_thread(projects.reopen, **request.model_dump())
