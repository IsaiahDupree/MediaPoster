"""
Remotion API Endpoints
======================
REST API endpoints for Remotion video rendering service.
"""

import logging
import json
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.event_bus import EventBus, Topics
from services.remotion.models import SourceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/remotion", tags=["remotion"])

# In-process job registry — updated by render endpoint + event subscriptions
_job_registry: Dict[str, Dict[str, Any]] = {}

# MCP server jobs file (cross-read for jobs submitted via MCP)
_MCP_JOBS_FILE = os.path.expanduser(
    "~/Documents/Software/Remotion/output/.mcp-jobs.json"
)


def _load_mcp_jobs() -> Dict[str, Dict[str, Any]]:
    try:
        if os.path.exists(_MCP_JOBS_FILE):
            with open(_MCP_JOBS_FILE) as f:
                return {j["id"]: j for j in json.load(f)}
    except Exception:
        pass
    return {}


def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    if job_id in _job_registry:
        return _job_registry[job_id]
    # Fall back to MCP jobs file
    mcp_jobs = _load_mcp_jobs()
    return mcp_jobs.get(job_id)


class LayerRequest(BaseModel):
    """Layer request."""
    id: str
    type: str = Field(..., description="Layer type: video, image, text, audio")
    source: Optional[str] = None
    source_type: Optional[str] = None
    position: Optional[Dict[str, Any]] = None
    start: float = 0.0
    end: Optional[float] = None
    opacity: float = 1.0
    style: Optional[Dict[str, Any]] = None
    animation: Optional[str] = None
    content: Optional[str] = None


class AudioTrackRequest(BaseModel):
    """Audio track request."""
    id: str
    source: str
    source_type: str
    start: float = 0.0
    volume: float = 1.0
    ducking: Optional[Dict[str, Any]] = None


class CaptionConfigRequest(BaseModel):
    """Caption configuration."""
    enabled: bool = True
    style: str = "burned_in"
    source: Optional[str] = None
    emphasis_words: bool = True
    position: str = "bottom"


class RemotionRenderRequest(BaseModel):
    """Remotion rendering request."""
    composition: str = Field(default="MainComposition", description="Composition name")
    timeline: Optional[Dict[str, Any]] = None  # Full timeline.json
    layers: Optional[List[LayerRequest]] = None  # Layers (alternative to timeline)
    audio: Optional[List[AudioTrackRequest]] = None  # Audio tracks
    captions: Optional[CaptionConfigRequest] = None  # Caption config
    output: Optional[Dict[str, Any]] = None  # Output config
    props: Optional[Dict[str, Any]] = None  # Composition props
    output_path: Optional[str] = None


class RemotionRenderResponse(BaseModel):
    """Remotion rendering response."""
    job_id: str
    status: str
    message: str
    correlation_id: str


@router.post("/render", response_model=RemotionRenderResponse)
async def render_video(request: RemotionRenderRequest, http_request: Request):
    """
    Render video using Remotion.
    
    Publishes a remotion.requested event and returns immediately with job_id.
    Use GET /api/remotion/status/{job_id} to check status.
    """
    event_bus = EventBus.get_instance()
    
    # Build payload
    payload = {
        "composition": request.composition,
    }
    
    if request.timeline:
        payload["timeline"] = request.timeline
    
    if request.layers:
        payload["layers"] = [layer.model_dump() for layer in request.layers]
    
    if request.audio:
        payload["audio"] = [audio.model_dump() for audio in request.audio]
    
    if request.captions:
        payload["captions"] = request.captions.model_dump()
    
    if request.output:
        payload["output"] = request.output
    else:
        payload["output"] = {
            "format": "mp4",
            "resolution": "1080x1920",
            "fps": 30
        }
    
    if request.props:
        payload["props"] = request.props
    
    if request.output_path:
        payload["output_path"] = request.output_path
    
    # Get correlation ID from request state
    correlation_id = getattr(http_request.state, "correlation_id", None)
    if correlation_id:
        payload["correlation_id"] = correlation_id
    
    # Publish event
    event_id = await event_bus.publish(
        topic=Topics.REMOTION_REQUESTED,
        payload=payload,
        correlation_id=correlation_id,
        source="api"
    )
    
    job_id = payload.get("job_id", event_id)

    # Register job in in-process registry
    _job_registry[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "composition": request.composition,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id or event_id,
    }

    logger.info(f"Remotion render requested: job_id={job_id}, composition={request.composition}")

    return RemotionRenderResponse(
        job_id=job_id,
        status="queued",
        message="Remotion render job queued",
        correlation_id=correlation_id or event_id
    )


@router.get("/status/{job_id}")
async def get_remotion_status(job_id: str):
    """Get status of a Remotion render job. Checks in-process registry and MCP jobs file."""
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@router.get("/jobs")
async def list_remotion_jobs():
    """List all Remotion render jobs (in-process + MCP-submitted)."""
    all_jobs = {**_load_mcp_jobs(), **_job_registry}
    jobs_list = sorted(
        all_jobs.values(),
        key=lambda j: j.get("startedAt") or j.get("queued_at") or "",
        reverse=True,
    )
    return {"jobs": jobs_list, "total": len(jobs_list)}


@router.get("/source-types")
async def list_source_types():
    """List available source types."""
    return {
        "source_types": [
            {
                "id": st.value,
                "name": st.name,
                "description": _get_source_type_description(st)
            }
            for st in SourceType
        ]
    }


def _get_source_type_description(source_type: SourceType) -> str:
    """Get description for source type."""
    descriptions = {
        SourceType.LOCAL: "Local file path",
        SourceType.URL: "HTTP/HTTPS URL (downloaded and cached)",
        SourceType.TTS: "TTS job output (from tts.completed event)",
        SourceType.MEDIAPOSTER: "MediaPoster media library",
        SourceType.MATTING: "Matting job output (from matting.completed event)",
    }
    return descriptions.get(source_type, f"{source_type.value} source type")

