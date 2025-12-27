"""
Formats API Endpoints
Manage video format templates and runs
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from loguru import logger
import uuid

from database.connection import get_db
from services.formats.sample_formats import SAMPLE_FORMATS, get_sample_format

router = APIRouter(prefix="/api/formats", tags=["Formats"])


class FormatResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    version: str
    definition_json: Dict[str, Any]
    quality_profile_id: Optional[str] = None
    remotion_composition_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_run: Optional[Dict[str, Any]] = None


class FormatListResponse(BaseModel):
    formats: List[FormatResponse]
    total: int


class RunRequest(BaseModel):
    params: Dict[str, Any] = {}
    trigger_type: str = "manual"
    variant_id: Optional[str] = None


class RunResponse(BaseModel):
    run_id: str
    format_id: str
    status: str
    message: str


# In-memory storage for seeded formats (would be DB in production)
_seeded_formats: Dict[str, Dict[str, Any]] = {}


def _sample_to_format_response(sample: Dict[str, Any]) -> FormatResponse:
    """Convert a sample format dict to FormatResponse"""
    composition = sample.get("composition", {})
    return FormatResponse(
        id=sample["id"],
        name=sample["name"],
        description=sample.get("description"),
        status=sample.get("status", "draft"),
        version=sample.get("version", "1.0.0"),
        definition_json=sample,
        quality_profile_id=sample.get("defaults", {}).get("qualityProfileId"),
        remotion_composition_id=composition.get("remotionCompositionId"),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        last_run=None
    )


@router.get("/list", response_model=FormatListResponse)
async def list_formats(
    status: Optional[str] = Query(default=None, description="Filter by status: active, draft, archived"),
):
    """
    List all available formats.
    Returns both seeded sample formats and any custom formats.
    """
    formats = []
    
    # Add seeded formats
    for format_id, format_data in _seeded_formats.items():
        fmt = _sample_to_format_response(format_data)
        if status is None or fmt.status == status:
            formats.append(fmt)
    
    # If no formats seeded yet, return empty list (user can click "Seed Samples")
    return FormatListResponse(
        formats=formats,
        total=len(formats)
    )


@router.post("/seed-samples")
async def seed_sample_formats():
    """
    Seed the database with sample format templates.
    """
    global _seeded_formats
    
    seeded = []
    for sample in SAMPLE_FORMATS:
        format_id = sample["id"]
        _seeded_formats[format_id] = sample
        seeded.append(format_id)
    
    logger.info(f"Seeded {len(seeded)} sample formats: {seeded}")
    
    return {
        "status": "success",
        "message": f"Seeded {len(seeded)} sample formats",
        "format_ids": seeded
    }


@router.get("/{format_id}")
async def get_format(format_id: str):
    """
    Get a single format by ID.
    """
    # Check seeded formats first
    if format_id in _seeded_formats:
        return _sample_to_format_response(_seeded_formats[format_id])
    
    # Check sample formats (even if not seeded)
    sample = get_sample_format(format_id)
    if sample:
        return _sample_to_format_response(sample)
    
    raise HTTPException(status_code=404, detail=f"Format '{format_id}' not found")


@router.post("/{format_id}/run", response_model=RunResponse)
async def run_format(
    format_id: str,
    request: RunRequest,
):
    """
    Trigger a new run for a format.
    This queues the format for processing with Remotion.
    """
    # Validate format exists
    format_data = _seeded_formats.get(format_id) or get_sample_format(format_id)
    if not format_data:
        raise HTTPException(status_code=404, detail=f"Format '{format_id}' not found")
    
    # Generate run ID
    run_id = str(uuid.uuid4())
    
    logger.info(f"Triggered run {run_id} for format {format_id}")
    
    return RunResponse(
        run_id=run_id,
        format_id=format_id,
        status="queued",
        message=f"Run queued for format '{format_data['name']}'"
    )


@router.get("/{format_id}/runs")
async def list_format_runs(
    format_id: str,
    limit: int = Query(default=20, le=100),
):
    """
    List recent runs for a format.
    """
    # Validate format exists
    format_data = _seeded_formats.get(format_id) or get_sample_format(format_id)
    if not format_data:
        raise HTTPException(status_code=404, detail=f"Format '{format_id}' not found")
    
    # Return empty runs for now (would be from DB in production)
    return {
        "format_id": format_id,
        "runs": [],
        "total": 0
    }


@router.delete("/{format_id}")
async def delete_format(format_id: str):
    """
    Delete a format (removes from seeded formats).
    """
    if format_id in _seeded_formats:
        del _seeded_formats[format_id]
        return {"status": "success", "message": f"Format '{format_id}' deleted"}
    
    raise HTTPException(status_code=404, detail=f"Format '{format_id}' not found")
