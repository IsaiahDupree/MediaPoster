"""
Music API Endpoints
==================
REST API endpoints for music service.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.event_bus import EventBus, Topics
from services.music.models import MusicSource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/music", tags=["music"])


class MusicSearchCriteriaRequest(BaseModel):
    """Music search criteria."""
    mood: Optional[str] = None
    genre: Optional[str] = None
    bpm_min: Optional[int] = None
    bpm_max: Optional[int] = None
    duration_min: Optional[float] = None
    duration_max: Optional[float] = None
    tags: Optional[List[str]] = None
    trending: bool = False
    platform: Optional[str] = None


class MusicRequest(BaseModel):
    """Music request."""
    source: str = Field(..., description="Music source: suno, soundcloud, social_platform")
    search_criteria: Optional[MusicSearchCriteriaRequest] = None
    suno_file_path: Optional[str] = None
    track_id: Optional[str] = None
    search_query: Optional[str] = None
    output_path: Optional[str] = None
    duration: Optional[float] = None


class MusicResponse(BaseModel):
    """Music response."""
    job_id: str
    status: str
    message: str
    correlation_id: str


@router.post("/request", response_model=MusicResponse)
async def request_music(request: MusicRequest, http_request: Request):
    """
    Request music generation/selection.
    
    Publishes a music.requested event and returns immediately with job_id.
    Use GET /api/music/status/{job_id} to check status.
    """
    event_bus = EventBus.get_instance()
    
    # Build payload
    payload = {
        "source": request.source,
    }
    
    if request.search_criteria:
        payload["search_criteria"] = request.search_criteria.model_dump()
    
    if request.suno_file_path:
        payload["suno_file_path"] = request.suno_file_path
    
    if request.track_id:
        payload["track_id"] = request.track_id
    
    if request.search_query:
        payload["search_query"] = request.search_query
    
    if request.output_path:
        payload["output_path"] = request.output_path
    
    if request.duration:
        payload["duration"] = request.duration
    
    # Get correlation ID from request state
    correlation_id = getattr(http_request.state, "correlation_id", None)
    if correlation_id:
        payload["correlation_id"] = correlation_id
    
    # Publish event
    event_id = await event_bus.publish(
        topic=Topics.MUSIC_REQUESTED,
        payload=payload,
        correlation_id=correlation_id,
        source="api"
    )
    
    job_id = payload.get("job_id", event_id)
    
    logger.info(f"Music request: job_id={job_id}, source={request.source}")
    
    return MusicResponse(
        job_id=job_id,
        status="queued",
        message="Music request queued",
        correlation_id=correlation_id or event_id
    )


@router.get("/sources")
async def list_music_sources():
    """List available music sources."""
    return {
        "sources": [
            {
                "id": source.value,
                "name": source.name,
                "description": _get_source_description(source)
            }
            for source in MusicSource
        ]
    }


def _get_source_description(source: MusicSource) -> str:
    """Get description for music source."""
    descriptions = {
        MusicSource.SUNO: "Local Suno downloaded files",
        MusicSource.SOUNDCLOUD: "SoundCloud via RapidAPI",
        MusicSource.SOCIAL_PLATFORM: "Social platforms via RapidAPI (TikTok, Instagram, etc.)",
        MusicSource.LOCAL: "Generic local file",
    }
    return descriptions.get(source, f"{source.value} source type")

