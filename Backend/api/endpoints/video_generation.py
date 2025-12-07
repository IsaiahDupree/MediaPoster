"""
Video Generation API Endpoints
Provides REST API for AI video generation across multiple providers
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from loguru import logger

from modules.ai.video_model_factory import VideoModelFactory, create_video_model
from modules.ai.video_model_interface import VideoGenerationRequest, VideoGenerationJob, VideoStatus

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
