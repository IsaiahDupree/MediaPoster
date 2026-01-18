"""
Sora Video Pipeline API
========================
API endpoints for creating multi-clip videos with Sora and Remotion.
"""
import os
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from loguru import logger

from services.sora_video_pipeline import (
    SoraVideoPipeline,
    VideoProject,
    ClipSpec,
    VideoStyle,
    get_pipeline,
)


router = APIRouter(prefix="/sora-pipeline", tags=["Sora Video Pipeline"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateProjectRequest(BaseModel):
    """Request to create a video project"""
    character: str = Field("@isaiahdupree", description="Main character name/handle")
    total_duration: int = Field(30, ge=12, le=120, description="Target video duration in seconds")
    num_clips: int = Field(3, ge=1, le=10, description="Number of clips to generate")
    style: str = Field("motivational", description="Video style: cinematic, documentary, vlog, motivational, tech")
    topic: Optional[str] = Field(None, description="Topic focus for the video")
    custom_scripts: Optional[List[str]] = Field(None, description="Custom scripts for each clip")


class ClipResponse(BaseModel):
    """Response for a single clip"""
    clip_id: str
    sequence_number: int
    role: str
    duration_seconds: int
    script_text: str
    status: str
    video_url: Optional[str] = None
    error: Optional[str] = None


class ProjectResponse(BaseModel):
    """Response for a video project"""
    project_id: str
    title: str
    description: str
    main_character: str
    total_duration_seconds: int
    clips: List[ClipResponse]
    style: str
    status: str
    output_path: Optional[str] = None
    final_video_url: Optional[str] = None


class GenerateRequest(BaseModel):
    """Request to generate clips for a project"""
    project_id: str


class DemoVideoRequest(BaseModel):
    """Request to create a demo video using B-roll"""
    character: str = Field("@isaiahdupree", description="Main character name")
    topic: str = Field("productivity", description="Video topic")


# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================

@router.post("/projects", response_model=ProjectResponse)
async def create_project(request: CreateProjectRequest):
    """
    Create a new video project with AI-designed scene structure.
    
    This designs the clips, scripts, and Sora prompts but does NOT generate videos yet.
    
    Example:
    ```
    POST /api/sora-pipeline/projects
    {
        "character": "@isaiahdupree",
        "total_duration": 30,
        "num_clips": 3,
        "style": "motivational",
        "topic": "success mindset"
    }
    ```
    """
    try:
        pipeline = get_pipeline()
        
        project = await pipeline.create_video_project(
            character=request.character,
            total_duration=request.total_duration,
            num_clips=request.num_clips,
            style=request.style,
            topic=request.topic,
            custom_scripts=request.custom_scripts,
        )
        
        return _project_to_response(project)
        
    except Exception as e:
        logger.error(f"Project creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a project by ID."""
    pipeline = get_pipeline()
    project = pipeline.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return _project_to_response(project)


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects():
    """List all projects."""
    pipeline = get_pipeline()
    projects = pipeline.list_projects()
    
    return [
        ProjectResponse(
            project_id=p["project_id"],
            title=p["title"],
            description=p["description"],
            main_character=p["main_character"],
            total_duration_seconds=p["total_duration_seconds"],
            clips=[ClipResponse(**c) for c in p["clips"]],
            style=p["style"],
            status=p["status"],
            output_path=p.get("output_path"),
            final_video_url=p.get("final_video_url"),
        )
        for p in projects
    ]


# =============================================================================
# GENERATION ENDPOINTS
# =============================================================================

@router.post("/generate/{project_id}")
async def generate_clips(project_id: str):
    """
    Start generating clips for a project using Sora API.
    
    This makes real API calls to OpenAI Sora and may take several minutes.
    """
    import asyncio
    
    pipeline = get_pipeline()
    project = pipeline.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Use asyncio.create_task for proper async background execution
    asyncio.create_task(pipeline.generate_clips(project))
    
    return {
        "project_id": project_id,
        "status": "generation_started",
        "message": f"Generating {len(project.clips)} clips. This may take several minutes.",
        "poll_url": f"/api/sora-pipeline/projects/{project_id}"
    }


@router.post("/compose/{project_id}")
async def compose_video(project_id: str):
    """
    Compose all generated clips into final video.
    
    This adds text overlays and combines clips with FFmpeg.
    """
    import asyncio
    
    pipeline = get_pipeline()
    project = pipeline.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if clips are generated
    completed_clips = [c for c in project.clips if c.status == "completed"]
    if not completed_clips:
        raise HTTPException(
            status_code=400, 
            detail="No completed clips to compose. Run generation first."
        )
    
    # Use asyncio.create_task for proper async background execution
    asyncio.create_task(pipeline.compose_video(project))
    
    return {
        "project_id": project_id,
        "status": "composition_started",
        "clips_to_compose": len(completed_clips),
        "poll_url": f"/api/sora-pipeline/projects/{project_id}"
    }


# =============================================================================
# DEMO VIDEO (Uses B-Roll instead of Sora)
# =============================================================================

@router.post("/demo", response_model=ProjectResponse)
async def create_demo_video(request: DemoVideoRequest):
    """
    Create a demo video using B-roll footage instead of Sora.
    
    This is useful for testing the pipeline without Sora API costs.
    Uses existing videos from the media library with AI-generated text overlays.
    
    Example:
    ```
    POST /api/sora-pipeline/demo
    {
        "character": "@isaiahdupree",
        "topic": "productivity"
    }
    ```
    """
    try:
        pipeline = get_pipeline()
        
        project = await pipeline.create_demo_video(
            character=request.character,
            topic=request.topic,
        )
        
        return _project_to_response(project)
        
    except Exception as e:
        logger.error(f"Demo video creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-video")
async def quick_video(
    character: str = Query("@isaiahdupree", description="Main character"),
    topic: str = Query("motivation", description="Video topic"),
    duration: int = Query(30, ge=12, le=60, description="Target duration"),
    use_sora: bool = Query(False, description="Use Sora API (costs money) or B-roll (free)")
):
    """
    Quick endpoint to create a video in one call.
    
    If use_sora=False (default), uses B-roll from media library.
    If use_sora=True, uses Sora API (requires OpenAI credits).
    """
    try:
        pipeline = get_pipeline()
        
        if use_sora:
            # Create and generate with Sora
            project = await pipeline.create_video_project(
                character=character,
                total_duration=duration,
                num_clips=3,
                style="motivational",
                topic=topic,
            )
            project = await pipeline.generate_clips(project)
            project = await pipeline.compose_video(project)
        else:
            # Use B-roll demo
            project = await pipeline.create_demo_video(
                character=character,
                topic=topic,
            )
        
        return _project_to_response(project)
        
    except Exception as e:
        logger.error(f"Quick video failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# OUTPUT ENDPOINTS
# =============================================================================

@router.get("/output/{project_id}")
async def get_output_video(project_id: str):
    """Download the final composed video."""
    output_dir = Path("data/sora_videos")
    video_path = output_dir / f"{project_id}.mp4"
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"sora_video_{project_id}.mp4"
    )


@router.get("/output/{project_id}/stream")
async def stream_output_video(project_id: str):
    """Stream the final video."""
    output_dir = Path("data/sora_videos")
    video_path = output_dir / f"{project_id}.mp4"
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _project_to_response(project: VideoProject) -> ProjectResponse:
    """Convert VideoProject to API response."""
    return ProjectResponse(
        project_id=project.project_id,
        title=project.title,
        description=project.description,
        main_character=project.main_character,
        total_duration_seconds=project.total_duration_seconds,
        clips=[
            ClipResponse(
                clip_id=c.clip_id,
                sequence_number=c.sequence_number,
                role=c.role.value if hasattr(c.role, 'value') else c.role,
                duration_seconds=c.duration_seconds,
                script_text=c.script_text,
                status=c.status,
                video_url=c.video_url,
                error=c.error,
            )
            for c in project.clips
        ],
        style=project.style.value if hasattr(project.style, 'value') else project.style,
        status=project.status,
        output_path=project.output_path,
        final_video_url=project.final_video_url,
    )
