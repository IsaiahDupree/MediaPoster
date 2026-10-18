"""
Sora Automation API
====================
API endpoints for Sora video generation and usage tracking.

Uses pub/sub event architecture:
    - Emits events to EventBus for all operations
    - SoraWorker subscribes to handle requests
    - All operations are event-driven and can be monitored
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging
import asyncio

from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sora", tags=["Sora Automation"])

def get_event_bus() -> EventBus:
    """Get the singleton EventBus instance."""
    return EventBus.get_instance()


class VideoGenerateRequest(BaseModel):
    prompt: str
    character: Optional[str] = "isaiahdupree"
    style: Optional[str] = None
    duration: int = 15
    aspect_ratio: str = "Portrait"


class BatchGenerateRequest(BaseModel):
    prompts: List[str]
    character: Optional[str] = "isaiahdupree"
    auto_download: bool = True


@router.get("/usage")
async def get_usage():
    """Get current Sora usage (video gens left, resets date)"""
    try:
        from services.sora import get_sora_usage_tracker
        
        tracker = get_sora_usage_tracker()
        
        # Use cached if recent, otherwise check
        if not tracker.should_check() and tracker.get_cached_usage():
            usage = tracker.get_cached_usage()
            return {
                "success": True,
                "cached": True,
                "usage": usage.to_dict()
            }
        
        # Fresh check
        usage = await tracker.check_and_store()
        return {
            "success": True,
            "cached": False,
            "usage": usage.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to get Sora usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/cached")
async def get_cached_usage():
    """Get cached usage without checking (fast)"""
    from services.sora import get_sora_usage_tracker
    
    tracker = get_sora_usage_tracker()
    usage = tracker.get_cached_usage()
    
    if usage:
        return {"success": True, "usage": usage.to_dict()}
    else:
        return {"success": False, "message": "No cached usage available"}


@router.get("/timeouts")
async def get_timeouts():
    """Get all Sora automation timeouts"""
    from services.sora import SORA_TIMEOUTS
    return {"success": True, "timeouts": SORA_TIMEOUTS}


@router.post("/usage/check")
async def force_usage_check():
    """Force a fresh usage check"""
    try:
        from services.sora import get_sora_usage_tracker
        
        tracker = get_sora_usage_tracker()
        usage = await tracker.check_and_store()
        
        return {
            "success": True,
            "usage": usage.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to check Sora usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_video(request: VideoGenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate a single video with Sora.
    
    Emits: sora.video.requested → SoraWorker handles generation
    """
    try:
        bus = get_event_bus()
        
        # Emit event for SoraWorker to handle
        event_id = await bus.publish(
            Topics.SORA_VIDEO_REQUESTED,
            {
                "prompt": request.prompt,
                "character": request.character,
                "style": request.style,
                "duration": request.duration,
                "aspect_ratio": request.aspect_ratio
            },
            source="sora-api"
        )
        
        return {
            "success": True,
            "message": "Video generation requested",
            "event_id": event_id,
            "topic": Topics.SORA_VIDEO_REQUESTED,
            "prompt": request.prompt,
            "character": request.character
        }
        
    except Exception as e:
        logger.error(f"Failed to generate video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/batch")
async def generate_batch(request: BatchGenerateRequest):
    """
    Generate multiple videos as a batch.
    
    Emits: sora.batch.requested → SoraWorker handles batch
    """
    try:
        bus = get_event_bus()
        
        # Emit batch request event
        event_id = await bus.publish(
            Topics.SORA_BATCH_REQUESTED,
            {
                "prompts": request.prompts,
                "character": request.character,
                "auto_download": request.auto_download
            },
            source="sora-api"
        )
        
        return {
            "success": True,
            "message": "Batch generation requested",
            "event_id": event_id,
            "topic": Topics.SORA_BATCH_REQUESTED,
            "jobs_count": len(request.prompts)
        }
        
    except Exception as e:
        logger.error(f"Failed to generate batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/periodic-checks/start")
async def start_periodic_checks(interval_minutes: int = 30):
    """Start periodic Sora usage checks"""
    try:
        from services.sora import get_sora_usage_tracker
        
        tracker = get_sora_usage_tracker()
        await tracker.start_periodic_checks(interval_minutes)
        
        return {
            "success": True,
            "message": f"Started periodic checks every {interval_minutes} minutes"
        }
        
    except Exception as e:
        logger.error(f"Failed to start periodic checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/periodic-checks/stop")
async def stop_periodic_checks():
    """Stop periodic Sora usage checks"""
    try:
        from services.sora import get_sora_usage_tracker
        
        tracker = get_sora_usage_tracker()
        tracker.stop_periodic_checks()
        
        return {"success": True, "message": "Stopped periodic checks"}
        
    except Exception as e:
        logger.error(f"Failed to stop periodic checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# VIDEO POLLING & AUTO-DOWNLOAD
# =============================================================================

@router.post("/poll/start")
async def start_video_polling(timeout_minutes: int = 15):
    """
    Start polling /drafts for completed videos and auto-download them.
    
    Typical video generation takes 8-12 minutes.
    Default timeout: 15 minutes.
    """
    try:
        from services.sora import get_sora_video_poller
        
        poller = get_sora_video_poller()
        
        if poller.is_polling():
            return {"success": False, "message": "Already polling"}
        
        await poller.start_background_polling(timeout_minutes)
        
        return {
            "success": True,
            "message": f"Started video polling (timeout: {timeout_minutes} min)",
            "poll_interval_seconds": poller.POLL_INTERVAL_SECONDS
        }
        
    except Exception as e:
        logger.error(f"Failed to start polling: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/poll/stop")
async def stop_video_polling():
    """Stop video polling"""
    try:
        from services.sora import get_sora_video_poller
        
        poller = get_sora_video_poller()
        poller.stop_polling()
        
        return {"success": True, "message": "Stopped video polling"}
        
    except Exception as e:
        logger.error(f"Failed to stop polling: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/poll/status")
async def get_polling_status():
    """Get current polling status"""
    try:
        from services.sora import get_sora_video_poller
        
        poller = get_sora_video_poller()
        
        return {
            "success": True,
            "is_polling": poller.is_polling(),
            "downloaded_count": len(poller._downloaded_ids),
            "poll_interval_seconds": poller.POLL_INTERVAL_SECONDS
        }
        
    except Exception as e:
        logger.error(f"Failed to get polling status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/poll/download-now")
async def poll_and_download_now(timeout_minutes: int = 15):
    """
    Poll and download completed videos synchronously (blocking).
    Returns list of downloaded video paths.
    """
    try:
        from services.sora import get_sora_video_poller
        
        poller = get_sora_video_poller()
        downloaded = await poller.poll_and_download(timeout_minutes)
        
        return {
            "success": True,
            "downloaded_count": len(downloaded),
            "downloaded_paths": downloaded
        }
        
    except Exception as e:
        logger.error(f"Failed to poll/download: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 3-PART MOVIE PIPELINE (ARCH-002)
# =============================================================================

class MultiPartRequest(BaseModel):
    """Request model for 3-part video generation."""
    theme: str
    num_parts: int = 3
    character: Optional[str] = "isaiahdupree"
    part_prompts: Optional[List[str]] = None
    auto_stitch: bool = True
    auto_analyze: bool = True
    remove_watermarks: bool = True
    post_to_platforms: Optional[List[str]] = None  # e.g., ["tiktok", "instagram"]


class FullPipelineRequest(BaseModel):
    """Request model for full automation pipeline."""
    theme: str
    character: Optional[str] = "isaiahdupree"
    num_parts: int = 3
    post_to_platforms: List[str] = ["tiktok", "instagram", "youtube"]
    schedule_delay_minutes: int = 0  # 0 = post immediately


@router.post("/pipeline/multi-part")
async def generate_multi_part_video(request: MultiPartRequest, background_tasks: BackgroundTasks):
    """
    Generate a 3-part video series with stitching.
    
    Full pipeline:
    1. Generate AI prompts for each part (or use provided)
    2. Generate 3 videos with @character
    3. Remove watermarks
    4. Stitch into single video
    5. AI analysis for titles/hashtags
    6. Optionally post to platforms
    
    Returns job_id for status tracking.
    """
    try:
        from automation.sora.pipeline import SoraPipeline
        import uuid
        
        job_id = str(uuid.uuid4())[:8]
        
        # Run pipeline in background
        async def run_pipeline():
            pipeline = SoraPipeline()
            result = await pipeline.generate_multi_part(
                theme=request.theme,
                num_parts=request.num_parts,
                character=f"@{request.character}" if request.character and not request.character.startswith("@") else request.character,
                part_prompts=request.part_prompts,
                auto_stitch=request.auto_stitch,
                auto_analyze=request.auto_analyze,
                remove_watermarks=request.remove_watermarks,
                pipeline_id=job_id
            )
            
            # Post to platforms if requested
            if request.post_to_platforms and result.get("stitched_video"):
                await _post_video_to_platforms(
                    result["stitched_video"],
                    result.get("analysis", {}),
                    request.post_to_platforms
                )
            
            return result
        
        background_tasks.add_task(run_pipeline)
        
        return {
            "success": True,
            "message": f"Started {request.num_parts}-part video pipeline",
            "job_id": job_id,
            "theme": request.theme,
            "character": request.character,
            "will_post_to": request.post_to_platforms
        }
        
    except Exception as e:
        logger.error(f"Failed to start multi-part pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/full")
async def run_full_pipeline(request: FullPipelineRequest, background_tasks: BackgroundTasks):
    """
    Full automation pipeline: Generate → Watermark → Analyze → Post
    
    This is the main endpoint for complete automation.
    """
    try:
        import uuid
        job_id = str(uuid.uuid4())[:8]
        
        async def execute_full_pipeline():
            from automation.sora.pipeline import SoraPipeline
            
            logger.info(f"[Pipeline {job_id}] Starting full pipeline: {request.theme}")
            
            # Step 1: Generate multi-part video
            pipeline = SoraPipeline()
            result = await pipeline.generate_multi_part(
                theme=request.theme,
                num_parts=request.num_parts,
                character=f"@{request.character}" if request.character else None,
                auto_stitch=True,
                auto_analyze=True,
                remove_watermarks=True,
                pipeline_id=job_id
            )
            
            if result.get("status") not in ["completed", "partial"]:
                logger.error(f"[Pipeline {job_id}] Generation failed: {result.get('error')}")
                return result
            
            # Step 2: Post to platforms
            final_video = result.get("stitched_video")
            if final_video and request.post_to_platforms:
                logger.info(f"[Pipeline {job_id}] Posting to {request.post_to_platforms}")
                
                post_results = await _post_video_to_platforms(
                    final_video,
                    result.get("analysis", {}),
                    request.post_to_platforms,
                    delay_minutes=request.schedule_delay_minutes
                )
                result["post_results"] = post_results
            
            logger.info(f"[Pipeline {job_id}] Pipeline complete!")
            return result
        
        background_tasks.add_task(execute_full_pipeline)
        
        return {
            "success": True,
            "message": "Full pipeline started",
            "job_id": job_id,
            "theme": request.theme,
            "num_parts": request.num_parts,
            "will_post_to": request.post_to_platforms
        }
        
    except Exception as e:
        logger.error(f"Failed to start full pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/jobs")
async def list_pipeline_jobs():
    """List all pipeline jobs and their status."""
    try:
        from automation.sora.pipeline import SoraPipeline
        
        pipeline = SoraPipeline()
        jobs = pipeline.list_jobs()
        
        return {
            "success": True,
            "jobs_count": len(jobs),
            "jobs": jobs
        }
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/job/{job_id}")
async def get_pipeline_job(job_id: str):
    """Get status of a specific pipeline job."""
    try:
        from automation.sora.pipeline import SoraPipeline
        
        pipeline = SoraPipeline()
        job = pipeline.get_job_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {
            "success": True,
            "job": job
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# POSTING INTEGRATION
# =============================================================================

async def _post_video_to_platforms(
    video_path: str,
    analysis: dict,
    platforms: List[str],
    delay_minutes: int = 0
) -> dict:
    """
    Post video to specified platforms via Blotato.
    
    Uses AI analysis for platform-specific titles and hashtags.
    """
    results = {}
    
    try:
        from services.blotato_connector import BlotatoConnector
        
        connector = BlotatoConnector()
        
        for platform in platforms:
            try:
                # Get platform-specific title
                title_key = f"title_{platform}"
                title = analysis.get(title_key) or analysis.get("title_tiktok") or "New video"
                
                description = analysis.get("description", "")
                hashtags = analysis.get("hashtags", [])
                
                # Format caption with hashtags
                caption = f"{title}\n\n{description}\n\n" + " ".join([f"#{h}" for h in hashtags])
                
                logger.info(f"Posting to {platform}: {title[:50]}...")
                
                # Post via Blotato
                result = await connector.post_video(
                    video_path=video_path,
                    platform=platform,
                    caption=caption,
                    title=title
                )
                
                results[platform] = {
                    "success": result.get("success", False),
                    "post_id": result.get("post_id"),
                    "url": result.get("url")
                }
                
            except Exception as e:
                logger.error(f"Failed to post to {platform}: {e}")
                results[platform] = {
                    "success": False,
                    "error": str(e)
                }
        
    except ImportError:
        logger.warning("BlotatoConnector not available, skipping posting")
        for platform in platforms:
            results[platform] = {"success": False, "error": "BlotatoConnector not available"}
    
    return results


@router.post("/post")
async def post_existing_video(
    video_path: str,
    platforms: List[str],
    title: Optional[str] = None,
    description: Optional[str] = None
):
    """
    Post an existing video to platforms.
    
    Use this for videos already downloaded/processed.
    """
    try:
        from pathlib import Path
        
        if not Path(video_path).exists():
            raise HTTPException(status_code=404, detail=f"Video not found: {video_path}")
        
        analysis = {
            "title_tiktok": title or "New video",
            "description": description or "",
            "hashtags": ["fyp", "viral", "ai", "sora"]
        }
        
        results = await _post_video_to_platforms(video_path, analysis, platforms)
        
        return {
            "success": True,
            "video_path": video_path,
            "post_results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to post video: {e}")
        raise HTTPException(status_code=500, detail=str(e))
