"""
Visuals API Endpoints
=====================
REST API endpoints for visuals service.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.event_bus import EventBus, Topics
from services.visuals.models import VisualsType, VisualsSource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visuals", tags=["visuals"])


class VisualsSearchCriteriaRequest(BaseModel):
    """Visuals search criteria."""
    keywords: Optional[List[str]] = None
    mood: Optional[str] = None
    style: Optional[str] = None
    duration_min: Optional[float] = None
    duration_max: Optional[float] = None
    aspect_ratio: Optional[str] = None
    trending: bool = False
    platform: Optional[str] = None


class VisualsRequest(BaseModel):
    """Visuals request."""
    visuals_type: str = Field(..., description="Visual type: meme, broll, ugc, stock, generated")
    source: str = Field(..., description="Visual source: local, rapidapi, mediaposter, ugc_library")
    search_criteria: Optional[VisualsSearchCriteriaRequest] = None
    file_path: Optional[str] = None
    asset_id: Optional[str] = None
    ugc_source: Optional[str] = None
    output_path: Optional[str] = None


class VisualsResponse(BaseModel):
    """Visuals response."""
    job_id: str
    status: str
    message: str
    correlation_id: str


@router.post("/request", response_model=VisualsResponse)
async def request_visuals(request: VisualsRequest, http_request: Request):
    """
    Request visuals generation/selection.
    
    Publishes a visuals.requested event and returns immediately with job_id.
    Use GET /api/visuals/status/{job_id} to check status.
    """
    event_bus = EventBus.get_instance()
    
    # Build payload
    payload = {
        "visuals_type": request.visuals_type,
        "source": request.source,
    }
    
    if request.search_criteria:
        payload["search_criteria"] = request.search_criteria.model_dump()
    
    if request.file_path:
        payload["file_path"] = request.file_path
    
    if request.asset_id:
        payload["asset_id"] = request.asset_id
    
    if request.ugc_source:
        payload["ugc_source"] = request.ugc_source
    
    if request.output_path:
        payload["output_path"] = request.output_path
    
    # Get correlation ID from request state
    correlation_id = getattr(http_request.state, "correlation_id", None)
    if correlation_id:
        payload["correlation_id"] = correlation_id
    
    # Publish event
    event_id = await event_bus.publish(
        topic=Topics.VISUALS_REQUESTED,
        payload=payload,
        correlation_id=correlation_id,
        source="api"
    )
    
    job_id = payload.get("job_id", event_id)
    
    logger.info(f"Visuals request: job_id={job_id}, type={request.visuals_type}, source={request.source}")
    
    return VisualsResponse(
        job_id=job_id,
        status="queued",
        message="Visuals request queued",
        correlation_id=correlation_id or event_id
    )


@router.get("/types")
async def list_visuals_types():
    """List available visuals types."""
    return {
        "types": [
            {
                "id": vt.value,
                "name": vt.name,
                "description": _get_type_description(vt)
            }
            for vt in VisualsType
        ]
    }


@router.get("/sources")
async def list_visuals_sources():
    """List available visuals sources."""
    return {
        "sources": [
            {
                "id": vs.value,
                "name": vs.name,
                "description": _get_source_description(vs)
            }
            for vs in VisualsSource
        ]
    }


def _get_type_description(vt: VisualsType) -> str:
    """Get description for visuals type."""
    descriptions = {
        VisualsType.MEME: "Meme templates",
        VisualsType.BROLL: "B-roll footage",
        VisualsType.UGC: "User-generated content",
        VisualsType.STOCK: "Stock footage/images",
        VisualsType.GENERATED: "AI-generated visuals",
    }
    return descriptions.get(vt, f"{vt.value} visuals type")


def _get_source_description(vs: VisualsSource) -> str:
    """Get description for visuals source."""
    descriptions = {
        VisualsSource.LOCAL: "Local files",
        VisualsSource.RAPIDAPI: "RapidAPI (social platforms)",
        VisualsSource.MEDIAPOSTER: "MediaPoster media library",
        VisualsSource.UGC_LIBRARY: "UGC content library",
    }
    return descriptions.get(vs, f"{vs.value} source type")

