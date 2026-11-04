"""Registered result kinds, for renderer plots and the General I/O workbench."""

from fastapi import APIRouter

from services.result_registry import describe_kinds

router = APIRouter()


@router.get("/kinds")
async def list_result_kinds():
    """Every stored result kind with its store, exporter and default plot."""
    kinds = describe_kinds()
    return {
        "success": True,
        "data": kinds,
        "message": f"{len(kinds)} result kinds",
        "error": None,
    }
