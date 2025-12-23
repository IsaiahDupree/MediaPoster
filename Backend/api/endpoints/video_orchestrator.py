"""
Video Orchestrator API Endpoints
================================
REST API for Sora video generation and orchestration.

Endpoints:
- Single generation (Sora panel)
- Storyboard workflow (ClipPlan management)
- Project/brief/script management
- Generation status and history
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video", tags=["video-orchestrator"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateProjectRequest(BaseModel):
    """Create a new video project."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ProjectResponse(BaseModel):
    """Video project response."""
    id: str
    title: str
    description: Optional[str]
    tags: List[str]
    created_at: str
    updated_at: str


class CreateBriefRequest(BaseModel):
    """Create content brief."""
    project_id: str
    objective: str = Field(..., min_length=1)
    audience: str = Field(..., min_length=1)
    tone: Optional[str] = None
    cta: Optional[str] = None
    key_points: List[str] = Field(default_factory=list)


class BriefResponse(BaseModel):
    """Content brief response."""
    id: str
    project_id: str
    objective: str
    audience: str
    tone: Optional[str]
    cta: Optional[str]
    key_points: List[str]
    created_at: str


class CreateScriptRequest(BaseModel):
    """Create script."""
    project_id: str
    brief_id: Optional[str] = None
    title: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    language: str = "en"


class ScriptResponse(BaseModel):
    """Script response."""
    id: str
    project_id: str
    brief_id: Optional[str]
    title: str
    body: str
    language: str
    word_count: int
    estimated_duration_seconds: int
    created_at: str


class PacingConfig(BaseModel):
    """Pacing configuration."""
    words_per_minute: int = Field(default=150, ge=90, le=200)
    max_words_per_clip: int = Field(default=30, ge=5, le=80)


class ConstraintsConfig(BaseModel):
    """Plan constraints."""
    max_total_seconds: int = Field(default=300, ge=1, le=300)
    default_clip_seconds: int = Field(default=8, ge=4, le=12)
    aspect_ratio: str = Field(default="16:9")
    resolution: str = Field(default="1080p")
    pacing: Optional[PacingConfig] = None


class CreateClipPlanRequest(BaseModel):
    """Create clip plan from script."""
    project_id: str
    script_id: str
    brief_id: Optional[str] = None
    style_bible_id: Optional[str] = None
    character_bible_id: Optional[str] = None
    constraints: Optional[ConstraintsConfig] = None


class ClipSummary(BaseModel):
    """Summary of a clip in a plan."""
    id: str
    order: int
    target_seconds: int
    state: str
    narration_preview: str
    visual_prompt_preview: str


class SceneSummary(BaseModel):
    """Summary of a scene in a plan."""
    id: str
    name: str
    order: int
    clips: List[ClipSummary]


class ClipPlanResponse(BaseModel):
    """Clip plan response."""
    id: str
    project_id: str
    script_id: Optional[str]
    brief_id: Optional[str]
    status: str
    total_clips: int
    total_duration_seconds: int
    clips_passed: int
    clips_failed: int
    clips_pending: int
    scenes: List[SceneSummary]
    created_at: str
    updated_at: str


class StartGenerationRequest(BaseModel):
    """Start clip plan generation."""
    clip_plan_id: str
    max_concurrent: int = Field(default=3, ge=1, le=10)


class GenerationStatusResponse(BaseModel):
    """Generation progress status."""
    clip_plan_id: str
    status: str
    total_clips: int
    completed_clips: int
    failed_clips: int
    current_clip_id: Optional[str]
    current_clip_status: Optional[str]
    estimated_remaining_seconds: Optional[int]


# =============================================================================
# SORA SINGLE GENERATION MODELS
# =============================================================================

class SoraGenerateRequest(BaseModel):
    """Generate a single Sora video."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    model: str = Field(default="sora-2")
    size: str = Field(default="1280x720")
    seconds: int = Field(default=8, ge=4, le=12)
    project_id: Optional[str] = None
    image_base64: Optional[str] = None
    image_mime_type: Optional[str] = None


class SoraRemixRequest(BaseModel):
    """Remix an existing Sora video."""
    video_id: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1, max_length=2000)
    model: str = Field(default="sora-2")
    size: str = Field(default="1280x720")
    seconds: int = Field(default=8, ge=4, le=12)


class OptimizePromptRequest(BaseModel):
    """Optimize a video prompt."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    model: str = Field(default="sora-2")
    size: str = Field(default="1280x720")
    seconds: int = Field(default=8)


class SoraVideoResponse(BaseModel):
    """Sora video generation response."""
    id: str
    status: str
    prompt: str
    model: str
    size: str
    seconds: int
    created_at: str
    completed_at: Optional[str]
    download_url: Optional[str]
    thumbnail_url: Optional[str]
    error: Optional[Dict[str, Any]]


class OptimizePromptResponse(BaseModel):
    """Optimized prompt response."""
    original_prompt: str
    optimized_prompt: str


# =============================================================================
# IN-MEMORY STORAGE (Replace with database in production)
# =============================================================================

# Simple in-memory storage for demo
_projects: Dict[str, Dict] = {}
_briefs: Dict[str, Dict] = {}
_scripts: Dict[str, Dict] = {}
_clip_plans: Dict[str, Dict] = {}
_generations: Dict[str, Dict] = {}


# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================

@router.post("/projects", response_model=ProjectResponse)
async def create_project(request: CreateProjectRequest):
    """Create a new video project."""
    from uuid import uuid4
    
    project_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    
    project = {
        "id": project_id,
        "title": request.title,
        "description": request.description,
        "tags": request.tags,
        "created_at": now,
        "updated_at": now
    }
    
    _projects[project_id] = project
    logger.info(f"Created project: {project_id}")
    
    return ProjectResponse(**project)


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects():
    """List all video projects."""
    return [ProjectResponse(**p) for p in _projects.values()]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a video project by ID."""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**_projects[project_id])


# =============================================================================
# BRIEF ENDPOINTS
# =============================================================================

@router.post("/briefs", response_model=BriefResponse)
async def create_brief(request: CreateBriefRequest):
    """Create a content brief."""
    from uuid import uuid4
    
    if request.project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    brief_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    
    brief = {
        "id": brief_id,
        "project_id": request.project_id,
        "objective": request.objective,
        "audience": request.audience,
        "tone": request.tone,
        "cta": request.cta,
        "key_points": request.key_points,
        "created_at": now
    }
    
    _briefs[brief_id] = brief
    logger.info(f"Created brief: {brief_id}")
    
    return BriefResponse(**brief)


@router.get("/briefs/{brief_id}", response_model=BriefResponse)
async def get_brief(brief_id: str):
    """Get a content brief by ID."""
    if brief_id not in _briefs:
        raise HTTPException(status_code=404, detail="Brief not found")
    return BriefResponse(**_briefs[brief_id])


# =============================================================================
# SCRIPT ENDPOINTS
# =============================================================================

@router.post("/scripts", response_model=ScriptResponse)
async def create_script(request: CreateScriptRequest):
    """Create a script."""
    from uuid import uuid4
    from services.video_orchestrator.director import DirectorService
    
    if request.project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    script_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    
    # Estimate duration
    director = DirectorService()
    estimate = director.estimate_duration(request.body)
    
    script = {
        "id": script_id,
        "project_id": request.project_id,
        "brief_id": request.brief_id,
        "title": request.title,
        "body": request.body,
        "language": request.language,
        "word_count": estimate["word_count"],
        "estimated_duration_seconds": estimate["estimated_seconds"],
        "created_at": now
    }
    
    _scripts[script_id] = script
    logger.info(f"Created script: {script_id} ({estimate['word_count']} words)")
    
    return ScriptResponse(**script)


@router.get("/scripts/{script_id}", response_model=ScriptResponse)
async def get_script(script_id: str):
    """Get a script by ID."""
    if script_id not in _scripts:
        raise HTTPException(status_code=404, detail="Script not found")
    return ScriptResponse(**_scripts[script_id])


@router.post("/scripts/estimate")
async def estimate_script_duration(body: str = Query(..., min_length=1)):
    """Estimate duration for script text."""
    from services.video_orchestrator.director import DirectorService
    
    director = DirectorService()
    estimate = director.estimate_duration(body)
    
    return {
        "word_count": estimate["word_count"],
        "estimated_seconds": estimate["estimated_seconds"],
        "estimated_minutes": estimate["estimated_minutes"],
        "estimated_clips": estimate["estimated_clips"],
        "exceeds_max": estimate["exceeds_max"]
    }


# =============================================================================
# CLIP PLAN ENDPOINTS
# =============================================================================

@router.post("/clip-plans", response_model=ClipPlanResponse)
async def create_clip_plan(request: CreateClipPlanRequest):
    """Create a clip plan from a script."""
    from uuid import uuid4
    from services.video_orchestrator.director import DirectorService
    from services.video_orchestrator.models import (
        VideoScript, ContentBrief, PlanConstraints, PacingConstraints
    )
    
    if request.project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    if request.script_id not in _scripts:
        raise HTTPException(status_code=404, detail="Script not found")
    
    script_data = _scripts[request.script_id]
    brief_data = _briefs.get(request.brief_id) if request.brief_id else None
    
    # Build constraints
    constraints = None
    if request.constraints:
        pacing = PacingConstraints(
            words_per_minute=request.constraints.pacing.words_per_minute if request.constraints.pacing else 150,
            max_words_per_clip=request.constraints.pacing.max_words_per_clip if request.constraints.pacing else 30
        )
        constraints = PlanConstraints(
            max_total_seconds=request.constraints.max_total_seconds,
            default_clip_seconds=request.constraints.default_clip_seconds,
            aspect_ratio=request.constraints.aspect_ratio,
            resolution=request.constraints.resolution,
            pacing=pacing
        )
    
    # Create script model
    script = VideoScript(
        id=UUID(request.script_id),
        project_id=UUID(request.project_id),
        title=script_data["title"],
        body=script_data["body"],
        language=script_data["language"]
    )
    
    # Create brief model if provided
    brief = None
    if brief_data:
        brief = ContentBrief(
            id=UUID(brief_data["id"]),
            project_id=UUID(brief_data["project_id"]),
            objective=brief_data["objective"],
            audience=brief_data["audience"],
            tone=brief_data.get("tone", ""),
            key_points=brief_data.get("key_points", [])
        )
    
    # Generate clip plan
    director = DirectorService()
    plan, scene, clips = await director.create_clip_plan(script, brief, constraints)
    
    now = datetime.utcnow().isoformat()
    
    # Build response
    clip_summaries = [
        ClipSummary(
            id=str(clip.id),
            order=clip.clip_order,
            target_seconds=clip.target_seconds,
            state=clip.state.value,
            narration_preview=clip.narration.text[:50] + "..." if len(clip.narration.text) > 50 else clip.narration.text,
            visual_prompt_preview=clip.visual_intent.prompt[:50] + "..." if len(clip.visual_intent.prompt) > 50 else clip.visual_intent.prompt
        )
        for clip in clips
    ]
    
    scene_summary = SceneSummary(
        id=str(scene.id),
        name=scene.name,
        order=scene.scene_order,
        clips=clip_summaries
    )
    
    total_duration = sum(c.target_seconds for c in clips)
    
    plan_data = {
        "id": str(plan.id),
        "project_id": request.project_id,
        "script_id": request.script_id,
        "brief_id": request.brief_id,
        "status": plan.status.value,
        "total_clips": len(clips),
        "total_duration_seconds": total_duration,
        "clips_passed": 0,
        "clips_failed": 0,
        "clips_pending": len(clips),
        "scenes": [scene_summary],
        "created_at": now,
        "updated_at": now,
        "_clips": clips,
        "_scene": scene,
        "_plan": plan
    }
    
    _clip_plans[str(plan.id)] = plan_data
    logger.info(f"Created clip plan: {plan.id} with {len(clips)} clips")
    
    return ClipPlanResponse(
        id=plan_data["id"],
        project_id=plan_data["project_id"],
        script_id=plan_data["script_id"],
        brief_id=plan_data["brief_id"],
        status=plan_data["status"],
        total_clips=plan_data["total_clips"],
        total_duration_seconds=plan_data["total_duration_seconds"],
        clips_passed=plan_data["clips_passed"],
        clips_failed=plan_data["clips_failed"],
        clips_pending=plan_data["clips_pending"],
        scenes=plan_data["scenes"],
        created_at=plan_data["created_at"],
        updated_at=plan_data["updated_at"]
    )


@router.get("/clip-plans/{plan_id}", response_model=ClipPlanResponse)
async def get_clip_plan(plan_id: str):
    """Get a clip plan by ID."""
    if plan_id not in _clip_plans:
        raise HTTPException(status_code=404, detail="Clip plan not found")
    
    plan_data = _clip_plans[plan_id]
    return ClipPlanResponse(
        id=plan_data["id"],
        project_id=plan_data["project_id"],
        script_id=plan_data["script_id"],
        brief_id=plan_data["brief_id"],
        status=plan_data["status"],
        total_clips=plan_data["total_clips"],
        total_duration_seconds=plan_data["total_duration_seconds"],
        clips_passed=plan_data["clips_passed"],
        clips_failed=plan_data["clips_failed"],
        clips_pending=plan_data["clips_pending"],
        scenes=plan_data["scenes"],
        created_at=plan_data["created_at"],
        updated_at=plan_data["updated_at"]
    )


@router.post("/clip-plans/{plan_id}/start", response_model=GenerationStatusResponse)
async def start_generation(plan_id: str, background_tasks: BackgroundTasks):
    """Start generating clips for a plan."""
    if plan_id not in _clip_plans:
        raise HTTPException(status_code=404, detail="Clip plan not found")
    
    plan_data = _clip_plans[plan_id]
    
    if plan_data["status"] == "running":
        raise HTTPException(status_code=400, detail="Generation already in progress")
    
    # Update status
    plan_data["status"] = "running"
    plan_data["updated_at"] = datetime.utcnow().isoformat()
    
    # In production, this would start a background worker
    # background_tasks.add_task(run_generation, plan_id)
    
    logger.info(f"Started generation for plan: {plan_id}")
    
    return GenerationStatusResponse(
        clip_plan_id=plan_id,
        status="running",
        total_clips=plan_data["total_clips"],
        completed_clips=plan_data["clips_passed"],
        failed_clips=plan_data["clips_failed"],
        current_clip_id=None,
        current_clip_status=None,
        estimated_remaining_seconds=plan_data["total_duration_seconds"] * 10  # Rough estimate
    )


@router.get("/clip-plans/{plan_id}/status", response_model=GenerationStatusResponse)
async def get_generation_status(plan_id: str):
    """Get generation status for a plan."""
    if plan_id not in _clip_plans:
        raise HTTPException(status_code=404, detail="Clip plan not found")
    
    plan_data = _clip_plans[plan_id]
    
    return GenerationStatusResponse(
        clip_plan_id=plan_id,
        status=plan_data["status"],
        total_clips=plan_data["total_clips"],
        completed_clips=plan_data["clips_passed"],
        failed_clips=plan_data["clips_failed"],
        current_clip_id=None,
        current_clip_status=None,
        estimated_remaining_seconds=None
    )


# =============================================================================
# SORA SINGLE GENERATION ENDPOINTS
# =============================================================================

@router.post("/sora/generate", response_model=SoraVideoResponse)
async def sora_generate(request: SoraGenerateRequest):
    """Generate a single video with Sora."""
    from uuid import uuid4
    from services.video_providers import get_video_provider, ProviderName
    from services.video_providers.base import CreateClipInput, ProviderReference
    
    try:
        provider = get_video_provider(ProviderName.MOCK)  # Use mock for demo
    except Exception as e:
        logger.error(f"Failed to get provider: {e}")
        raise HTTPException(status_code=500, detail="Video provider unavailable")
    
    # Build input
    references = []
    if request.image_base64:
        references.append(ProviderReference(
            type="image",
            url=f"data:{request.image_mime_type or 'image/png'};base64,{request.image_base64}",
            weight=0.8
        ))
    
    clip_input = CreateClipInput(
        clip_id=str(uuid4()),
        prompt=request.prompt,
        seconds=request.seconds,
        model=request.model,
        size=request.size,
        references=references
    )
    
    try:
        generation = await provider.create_clip(clip_input)
        
        gen_id = generation.provider_generation_id
        now = datetime.utcnow().isoformat()
        
        # Store generation
        _generations[gen_id] = {
            "id": gen_id,
            "status": generation.status.value,
            "prompt": request.prompt,
            "model": request.model,
            "size": request.size,
            "seconds": request.seconds,
            "created_at": now,
            "completed_at": None,
            "download_url": None,
            "thumbnail_url": None,
            "error": None,
            "project_id": request.project_id
        }
        
        logger.info(f"Started Sora generation: {gen_id}")
        
        return SoraVideoResponse(**_generations[gen_id])
        
    except Exception as e:
        logger.error(f"Sora generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sora/remix", response_model=SoraVideoResponse)
async def sora_remix(request: SoraRemixRequest):
    """Remix an existing Sora video."""
    from services.video_providers import get_video_provider, ProviderName
    from services.video_providers.base import RemixClipInput
    
    try:
        provider = get_video_provider(ProviderName.MOCK)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Video provider unavailable")
    
    remix_input = RemixClipInput(
        source_generation_id=request.video_id,
        prompt_delta=request.prompt,
        seconds=request.seconds
    )
    
    try:
        generation = await provider.remix_clip(remix_input)
        
        gen_id = generation.provider_generation_id
        now = datetime.utcnow().isoformat()
        
        _generations[gen_id] = {
            "id": gen_id,
            "status": generation.status.value,
            "prompt": request.prompt,
            "model": request.model,
            "size": request.size,
            "seconds": request.seconds,
            "created_at": now,
            "completed_at": None,
            "download_url": None,
            "thumbnail_url": None,
            "error": None,
            "remix_of": request.video_id
        }
        
        logger.info(f"Started Sora remix: {gen_id} from {request.video_id}")
        
        return SoraVideoResponse(**_generations[gen_id])
        
    except Exception as e:
        logger.error(f"Sora remix failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sora/videos/{video_id}", response_model=SoraVideoResponse)
async def get_sora_video(video_id: str):
    """Get Sora video status."""
    from services.video_providers import get_video_provider, ProviderName
    
    # Check local storage first
    if video_id in _generations:
        gen_data = _generations[video_id]
        
        # Poll provider for status update
        try:
            provider = get_video_provider(ProviderName.MOCK)
            generation = await provider.get_generation(video_id)
            
            # Update status
            gen_data["status"] = generation.status.value
            if generation.is_complete:
                gen_data["completed_at"] = datetime.utcnow().isoformat()
                gen_data["download_url"] = generation.download_url
                gen_data["thumbnail_url"] = generation.thumbnail_url
                if generation.error:
                    gen_data["error"] = generation.error.to_dict()
            
            return SoraVideoResponse(**gen_data)
            
        except Exception as e:
            logger.warning(f"Failed to poll provider: {e}")
            return SoraVideoResponse(**gen_data)
    
    raise HTTPException(status_code=404, detail="Video not found")


@router.post("/sora/optimize-prompt", response_model=OptimizePromptResponse)
async def optimize_prompt(request: OptimizePromptRequest):
    """Optimize a prompt for Sora generation."""
    # Simple prompt enhancement (in production, use GPT)
    optimized = request.prompt
    
    # Add quality hints
    enhancements = []
    
    if "cinematic" not in request.prompt.lower():
        enhancements.append("cinematic quality")
    if "lighting" not in request.prompt.lower():
        enhancements.append("professional lighting")
    if "4k" not in request.prompt.lower() and "hd" not in request.prompt.lower():
        enhancements.append("high definition")
    
    if enhancements:
        optimized = f"{request.prompt}. Style: {', '.join(enhancements)}."
    
    return OptimizePromptResponse(
        original_prompt=request.prompt,
        optimized_prompt=optimized
    )


@router.get("/sora/history")
async def get_sora_history(
    project_id: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get Sora generation history."""
    generations = list(_generations.values())
    
    if project_id:
        generations = [g for g in generations if g.get("project_id") == project_id]
    
    # Sort by created_at descending
    generations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"generations": generations[:limit], "total": len(generations)}


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def health_check():
    """Check video orchestrator health."""
    from services.video_providers import get_video_provider, ProviderName
    
    try:
        provider = get_video_provider(ProviderName.MOCK)
        provider_health = await provider.health_check()
    except Exception as e:
        provider_health = {"status": "error", "error": str(e)}
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "provider": provider_health,
        "stats": {
            "projects": len(_projects),
            "scripts": len(_scripts),
            "clip_plans": len(_clip_plans),
            "generations": len(_generations)
        }
    }
