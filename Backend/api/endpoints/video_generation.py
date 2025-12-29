"""
Video Generation API Endpoints
Provides REST API for AI video generation across multiple providers
Includes format-agnostic IR pipeline for Sora + Remotion
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from loguru import logger

from modules.ai.video_model_factory import VideoModelFactory, create_video_model
from modules.ai.video_model_interface import VideoGenerationRequest, VideoGenerationJob, VideoStatus
from services.event_bus import EventBus, Topics

# Import IR pipeline services
try:
    from services.video_generation import (
        TrendItemV1,
        ContentBriefV1,
        StoryIRV1,
        FormatPackV1,
        ShotPlanV1,
        AssetManifestV1,
        RenderPlanRemotionV1,
        make_story_ir,
        make_shot_plan,
        make_render_plan,
        select_format,
        get_available_formats,
    )
    IR_PIPELINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"IR pipeline not available: {e}")
    IR_PIPELINE_AVAILABLE = False

router = APIRouter(prefix="/video-generation", tags=["AI Video Generation"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateVideoRequest(BaseModel):
    prompt: str
    provider: str = "sora"  # sora, runway, pika, luma
    model_variant: Optional[str] = None
    width: int = 1280
    height: int = 720
    duration_seconds: int = 8
    input_image: Optional[str] = None
    seed: Optional[int] = None
    additional_params: Optional[Dict[str, Any]] = None


class VideoJobResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[int] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProviderInfo(BaseModel):
    name: str
    models: List[str]
    max_duration: int
    supported_resolutions: List[tuple]
    supports_image_input: bool
    supports_remix: bool


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/create", response_model=VideoJobResponse)
async def create_video_generation(request: CreateVideoRequest):
    """
    Create a new video generation job
    
    - **prompt**: Text description of the video
    - **provider**: AI provider (sora, runway, pika, luma)
    - **model_variant**: Specific model version (optional)
    - **width/height**: Video resolution
    - **duration_seconds**: Video length
    - **input_image**: URL or path for image-to-video (optional)
    - **seed**: Random seed for reproducibility (optional)
    """
    try:
        logger.info(f"Creating video with {request.provider}: {request.prompt[:50]}...")
        
        # Create model instance
        model = create_video_model(
            provider=request.provider,
            model_variant=request.model_variant
        )
        
        # Create generation request
        gen_request = VideoGenerationRequest(
            prompt=request.prompt,
            model=request.model_variant or request.provider,
            width=request.width,
            height=request.height,
            duration_seconds=request.duration_seconds,
            input_image=request.input_image,
            seed=request.seed,
            additional_params=request.additional_params
        )
        
        # Start generation
        job = model.create_video(gen_request)
        
        # Emit AI_GENERATION_REQUESTED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.AI_GENERATION_REQUESTED, {
                "job_id": job.job_id,
                "provider": request.provider,
                "prompt": request.prompt[:100],
                "duration_seconds": request.duration_seconds,
            })
            logger.info(f"[PubSub] Emitted AI_GENERATION_REQUESTED for {job.job_id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit video gen event: {e}")
        
        return VideoJobResponse(
            job_id=job.job_id,
            status=job.status.value,
            progress=job.progress,
            video_url=job.video_url,
            thumbnail_url=job.thumbnail_url,
            error_message=job.error_message,
            metadata=job.metadata
        )
        
    except Exception as e:
        logger.error(f"Error creating video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=VideoJobResponse)
async def get_video_status(job_id: str, provider: str = "sora"):
    """
    Get status of a video generation job
    
    - **job_id**: Job identifier
    - **provider**: Which provider the job belongs to
    """
    try:
        model = create_video_model(provider=provider)
        job = model.get_status(job_id)
        
        return VideoJobResponse(
            job_id=job.job_id,
            status=job.status.value,
            progress=job.progress,
            video_url=job.video_url,
            thumbnail_url=job.thumbnail_url,
            error_message=job.error_message,
            metadata=job.metadata
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/jobs", response_model=List[VideoJobResponse])
async def list_video_jobs(provider: str = "sora", limit: int = 20):
    """
    List recent video generation jobs
    
    - **provider**: Filter by provider
    - **limit**: Max number of jobs to return
    """
    try:
        model = create_video_model(provider=provider)
        jobs = model.list_jobs(limit=limit)
        
        return [
            VideoJobResponse(
                job_id=job.job_id,
                status=job.status.value,
                progress=job.progress,
                video_url=job.video_url,
                thumbnail_url=job.thumbnail_url,
                error_message=job.error_message,
                metadata=job.metadata
            )
            for job in jobs
        ]
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
async def delete_video(job_id: str, provider: str = "sora"):
    """
    Delete a video generation job
    
    - **job_id**: Job identifier
    - **provider**: Which provider the job belongs to
    """
    try:
        model = create_video_model(provider=provider)
        success = model.delete_video(job_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete video")
        
        return {"success": True, "job_id": job_id}
    except Exception as e:
        logger.error(f"Error deleting video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers", response_model=List[str])
async def list_providers():
    """Get list of available video generation providers"""
    return VideoModelFactory.get_available_providers()


@router.get("/providers/{provider_name}", response_model=ProviderInfo)
async def get_provider_capabilities(provider_name: str):
    """
    Get capabilities and specifications for a provider
    
    - **provider_name**: Provider to query (sora, runway, pika, luma)
    """
    try:
        model = create_video_model(provider=provider_name)
        models = VideoModelFactory.get_provider_models(provider_name)
        
        return ProviderInfo(
            name=provider_name,
            models=models,
            max_duration=model.get_max_duration(),
            supported_resolutions=model.get_supported_resolutions(),
            supports_image_input=model.supports_image_input(),
            supports_remix=model.supports_remix()
        )
    except Exception as e:
        logger.error(f"Error getting provider info: {e}")
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_name}")


# ============================================================================
# IR PIPELINE ENDPOINTS (Format-Agnostic Video Generation)
# ============================================================================

class GenerateStoryIRRequest(BaseModel):
    """Request to generate a Story IR from trend + brief."""
    trend: Dict[str, Any]
    brief: Dict[str, Any]
    fps: int = 30
    aspect: str = "9:16"


class GenerateShotPlanRequest(BaseModel):
    """Request to generate a shot plan from Story IR."""
    story_ir: Dict[str, Any] = Field(alias="storyIR")
    format_pack_id: str = Field(alias="formatPackId")
    model: str = "sora-2"
    reference_file_ids: Optional[List[str]] = Field(None, alias="referenceFileIds")
    
    class Config:
        populate_by_name = True


class GenerateRenderPlanRequest(BaseModel):
    """Request to generate a render plan."""
    story_ir: Dict[str, Any] = Field(alias="storyIR")
    format_pack_id: str = Field(alias="formatPackId")
    assets: Dict[str, Any]
    
    class Config:
        populate_by_name = True


class SelectFormatRequest(BaseModel):
    """Request to auto-select a format pack."""
    trend: Dict[str, Any]
    brief: Dict[str, Any]
    prefer_sora: bool = Field(default=True, alias="preferSora")
    have_screen_record: bool = Field(default=False, alias="haveScreenRecord")
    
    class Config:
        populate_by_name = True


@router.get("/ir/formats")
async def list_format_packs():
    """
    List all available format packs for video generation.
    """
    if not IR_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="IR pipeline not available")
    
    formats = get_available_formats()
    return {
        "formats": [
            {
                "id": f.id,
                "label": f.label,
                "family": f.family,
                "soraBeatTypes": [bt.value for bt in f.render_strategy.sora_beat_types],
                "nativeBeatTypes": [bt.value for bt in f.render_strategy.native_beat_types],
            }
            for f in formats
        ]
    }


@router.post("/ir/select-format")
async def select_format_pack(request: SelectFormatRequest):
    """
    Auto-select the best format pack based on trend + brief.
    
    Returns ranked list of formats with scores.
    """
    if not IR_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="IR pipeline not available")
    
    try:
        trend = TrendItemV1.model_validate(request.trend)
        brief = ContentBriefV1.model_validate(request.brief)
        
        result = select_format(
            trend=trend,
            brief=brief,
            prefer_sora=request.prefer_sora,
            have_screen_record=request.have_screen_record,
        )
        
        return {
            "selectedFormatId": result["selectedFormatId"],
            "format": result["format"].model_dump(by_alias=True),
            "ranked": result["ranked"],
        }
    except Exception as e:
        logger.error(f"Error selecting format: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ir/story-ir")
async def generate_story_ir(request: GenerateStoryIRRequest):
    """
    Generate a Story IR (semantic timeline) from trend data and content brief.
    
    The Story IR is the format-agnostic intermediate representation.
    """
    if not IR_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="IR pipeline not available")
    
    try:
        trend = TrendItemV1.model_validate(request.trend)
        brief = ContentBriefV1.model_validate(request.brief)
        
        ir = make_story_ir(
            trend=trend,
            brief=brief,
            fps=request.fps,
            aspect=request.aspect,
        )
        
        return {
            "storyIR": ir.model_dump(by_alias=True),
            "stats": {
                "totalBeats": len(ir.beats),
                "totalDurationS": ir.total_duration_s(),
                "totalFrames": ir.total_frames(),
            }
        }
    except Exception as e:
        logger.error(f"Error generating story IR: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ir/shot-plan")
async def generate_shot_plan(request: GenerateShotPlanRequest):
    """
    Generate a Sora shot plan from Story IR + format pack.
    
    Returns the shots that need to be generated by Sora.
    """
    if not IR_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="IR pipeline not available")
    
    try:
        ir = StoryIRV1.model_validate(request.story_ir)
        
        # Get format pack
        formats = {f.id: f for f in get_available_formats()}
        format_pack = formats.get(request.format_pack_id)
        
        if not format_pack:
            raise HTTPException(
                status_code=404,
                detail=f"Format pack not found: {request.format_pack_id}"
            )
        
        shot_plan = make_shot_plan(
            ir=ir,
            format_pack=format_pack,
            model=request.model,
            reference_file_ids=request.reference_file_ids,
        )
        
        return {
            "shotPlan": shot_plan.model_dump(by_alias=True),
            "stats": {
                "totalShots": len(shot_plan.shots),
                "totalSeconds": sum(s.seconds for s in shot_plan.shots),
                "cacheKeys": [s.cache_key for s in shot_plan.shots],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating shot plan: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ir/render-plan")
async def generate_render_plan(request: GenerateRenderPlanRequest):
    """
    Generate a Remotion render plan from Story IR + assets.
    
    This is the final step that creates the timeline for Remotion.
    """
    if not IR_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="IR pipeline not available")
    
    try:
        ir = StoryIRV1.model_validate(request.story_ir)
        assets = AssetManifestV1.model_validate(request.assets)
        
        # Get format pack
        formats = {f.id: f for f in get_available_formats()}
        format_pack = formats.get(request.format_pack_id)
        
        if not format_pack:
            raise HTTPException(
                status_code=404,
                detail=f"Format pack not found: {request.format_pack_id}"
            )
        
        render_plan = make_render_plan(
            ir=ir,
            format_pack=format_pack,
            assets=assets,
        )
        
        return {
            "renderPlan": render_plan.model_dump(by_alias=True),
            "stats": {
                "totalFrames": render_plan.total_frames(),
                "durationSeconds": render_plan.total_frames() / render_plan.meta.fps,
                "videoItems": len([i for i in render_plan.timeline if i.kind == "video"]),
                "nativeItems": len([i for i in render_plan.timeline if i.kind == "native"]),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating render plan: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ir/pipeline-status")
async def get_pipeline_status():
    """
    Check if the IR pipeline is available and get configuration.
    """
    return {
        "available": IR_PIPELINE_AVAILABLE,
        "features": {
            "storyIR": IR_PIPELINE_AVAILABLE,
            "shotPlan": IR_PIPELINE_AVAILABLE,
            "renderPlan": IR_PIPELINE_AVAILABLE,
            "formatSelection": IR_PIPELINE_AVAILABLE,
        },
        "formatsCount": len(get_available_formats()) if IR_PIPELINE_AVAILABLE else 0,
    }
