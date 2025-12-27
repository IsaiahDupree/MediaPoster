"""
Pipeline API Endpoints
======================
REST API endpoints for media factory pipeline orchestration.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.pipeline import PipelineOrchestrator, PipelineRequest, PipelineStage
from services.pipeline.models import PipelineStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# Singleton orchestrator
_orchestrator: Optional[PipelineOrchestrator] = None


def get_orchestrator() -> PipelineOrchestrator:
    """Get singleton orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineOrchestrator()
    return _orchestrator


class PipelineExecuteRequest(BaseModel):
    """Pipeline execution request."""
    brief_id: Optional[str] = None
    brief_data: Optional[dict] = None
    stages: Optional[List[str]] = None  # List of stage names
    skip_stages: Optional[List[str]] = None


class PipelineExecuteResponse(BaseModel):
    """Pipeline execution response."""
    pipeline_id: str
    status: str
    correlation_id: str
    message: str


@router.post("/execute", response_model=PipelineExecuteResponse)
async def execute_pipeline(request: PipelineExecuteRequest, http_request: Request):
    """
    Execute the media factory pipeline.
    
    Pipeline stages:
    - brief: Generate content brief
    - script: Generate script.json
    - tts: Generate voice audio
    - music: Generate music bed (optional)
    - visuals: Generate visuals (optional)
    - remotion: Render video
    - publish: Publish to platforms
    """
    orchestrator = get_orchestrator()
    
    # Get correlation ID from request state
    correlation_id = getattr(http_request.state, "correlation_id", None)
    
    # Convert stage names to PipelineStage enums
    stages = None
    if request.stages:
        stages = [PipelineStage(s) for s in request.stages]
    
    skip_stages = None
    if request.skip_stages:
        skip_stages = [PipelineStage(s) for s in request.skip_stages]
    
    # Create pipeline request
    pipeline_request = PipelineRequest(
        brief_id=request.brief_id,
        brief_data=request.brief_data,
        correlation_id=correlation_id,
        stages=stages,
        skip_stages=skip_stages
    )
    
    # Execute pipeline (async)
    import asyncio
    status = await orchestrator.execute(pipeline_request)
    
    return PipelineExecuteResponse(
        pipeline_id=status.pipeline_id,
        status=status.status.value,
        correlation_id=status.correlation_id or pipeline_request.correlation_id,
        message=f"Pipeline {status.status.value}"
    )


@router.get("/status/{pipeline_id}")
async def get_pipeline_status(pipeline_id: str):
    """
    Get status of a pipeline execution.
    """
    orchestrator = get_orchestrator()
    status = orchestrator.get_pipeline_status(pipeline_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # Convert to dict for response
    return {
        "pipeline_id": status.pipeline_id,
        "status": status.status.value,
        "progress": status.get_progress(),
        "current_stage": status.get_current_stage().value if status.get_current_stage() else None,
        "stages": {
            stage.value: {
                "status": stage_status.status,
                "progress": stage_status.progress,
                "started_at": stage_status.started_at.isoformat() if stage_status.started_at else None,
                "completed_at": stage_status.completed_at.isoformat() if stage_status.completed_at else None,
                "error": stage_status.error
            }
            for stage, stage_status in status.stages.items()
        },
        "started_at": status.started_at.isoformat() if status.started_at else None,
        "completed_at": status.completed_at.isoformat() if status.completed_at else None,
        "error": status.error
    }

