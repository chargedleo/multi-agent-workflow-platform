"""API endpoints for analytical datasets and schema inspection."""

from typing import List
from fastapi import APIRouter, status

from backend.app.analysis.schemas import DatasetSchemaInfo
from backend.app.analysis.service import DataAnalysisService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/datasets",
    response_model=List[DatasetSchemaInfo],
    status_code=status.HTTP_200_OK,
    summary="List approved analytical datasets",
    description="Returns metadata, schema descriptors, available columns, and row counts for approved analytical datasets.",
)
async def list_datasets_endpoint() -> List[DatasetSchemaInfo]:
    """Retrieve all approved datasets and their schema metadata."""
    return DataAnalysisService.list_datasets()
