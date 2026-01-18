"""
Sora API Endpoints

REST API for Sora video generation automation.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import uuid

router = APIRouter(prefix="/api/sora", tags=["sora"])

# In-memory job storage (replace with database in production)
jobs: Dict[str, Dict] = {}
pipeline_instance = None


def get_pipeline():
    """Get or create pipeline instance."""
    global pipeline_instance
    if pipeline_instance is None:
        from automation.sora import SoraPipeline
        pipeline_instance = SoraPipeline()
    return pipeline_instance


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Video generation prompt")
    character: Optional[str] = Field(None, description="@ character to use (e.g., @isaiahdupree)")
    timeout_minutes: int = Field(10, description="Max wait time for generation")
    download: bool = Field(True, description="Download video after generation")
    remove_watermark: bool = Field(True, description="Remove Sora watermark")


class BatchGenerateRequest(BaseModel):
    prompts: List[Dict] = Field(..., description="List of {prompt, character} dicts")
    stitch_output: bool = Field(False, description="Stitch all videos into one")
    add_captions: bool = Field(False, description="Add captions to final video")
    schedule_to: Optional[List[str]] = Field(None, description="Platforms to schedule to")


class PipelineRequest(BaseModel):
    prompts: List[Dict] = Field(..., description="List of prompts with optional characters")
    stitch_videos: bool = Field(True, description="Combine videos into single output")
    add_captions: bool = Field(True, description="Add captions via Whisper")
    remove_watermark: bool = Field(True, description="Remove Sora watermarks")
    schedule: Optional[Dict] = Field(None, description="Schedule config: {platform, time}")


@router.post("/generate")
async def generate_video(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Start a video generation job.
    
    Returns job ID for tracking progress.
    """
    job_id = str(uuid.uuid4())[:8]
    
    jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "prompt": request.prompt,
        "character": request.character,
        "created_at": datetime.now().isoformat()
    }
    
    async def run_generation():
        try:
            pipeline = get_pipeline()
            result = await pipeline.generate_single(
                prompt=request.prompt,
                character=request.character,
                timeout_minutes=request.timeout_minutes,
                download=request.download,
                remove_watermark=request.remove_watermark
            )
            jobs[job_id].update(result)
        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)
    
    background_tasks.add_task(asyncio.create_task, run_generation())
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Generation started. Use /api/sora/status/{job_id} to track progress."
    }


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a generation job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = jobs[job_id]
    
    # Calculate progress percentage
    steps = ["launch", "prompt_submitted", "generation_complete", "downloaded", "watermark_removed"]
    completed_steps = job.get("steps_completed", [])
    progress = int((len(completed_steps) / len(steps)) * 100)
    
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "progress_percent": progress,
        "steps_completed": completed_steps,
        "video_path": job.get("video_path"),
        "cleaned_video_path": job.get("cleaned_video_path"),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
        "completed_at": job.get("completed_at")
    }


@router.post("/batch")
async def batch_generate(request: BatchGenerateRequest, background_tasks: BackgroundTasks):
    """
    Start a batch generation job with optional stitching.
    """
    batch_id = str(uuid.uuid4())[:8]
    
    jobs[batch_id] = {
        "id": batch_id,
        "type": "batch",
        "status": "queued",
        "total_prompts": len(request.prompts),
        "created_at": datetime.now().isoformat()
    }
    
    async def run_batch():
        try:
            pipeline = get_pipeline()
            result = await pipeline.generate_batch(
                prompts=request.prompts,
                stitch_output=request.stitch_output,
                add_captions=request.add_captions,
                schedule_to=request.schedule_to
            )
            jobs[batch_id].update(result)
        except Exception as e:
            jobs[batch_id]["status"] = "failed"
            jobs[batch_id]["error"] = str(e)
    
    background_tasks.add_task(asyncio.create_task, run_batch())
    
    return {
        "batch_id": batch_id,
        "status": "queued",
        "total_prompts": len(request.prompts),
        "message": "Batch generation started."
    }


@router.post("/pipeline")
async def run_full_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Run the complete Sora pipeline:
    Generate → Download → Watermark → Stitch → Caption → Schedule
    """
    pipeline_id = str(uuid.uuid4())[:8]
    
    jobs[pipeline_id] = {
        "id": pipeline_id,
        "type": "pipeline",
        "status": "queued",
        "config": request.dict(),
        "created_at": datetime.now().isoformat()
    }
    
    async def run_pipeline():
        try:
            pipeline = get_pipeline()
            result = await pipeline.generate_batch(
                prompts=request.prompts,
                stitch_output=request.stitch_videos,
                add_captions=request.add_captions,
                schedule_to=request.schedule.get("platform") if request.schedule else None
            )
            jobs[pipeline_id].update(result)
        except Exception as e:
            jobs[pipeline_id]["status"] = "failed"
            jobs[pipeline_id]["error"] = str(e)
    
    background_tasks.add_task(asyncio.create_task, run_pipeline())
    
    return {
        "pipeline_id": pipeline_id,
        "status": "queued",
        "message": "Full pipeline started."
    }


@router.get("/jobs")
async def list_jobs(status: Optional[str] = None, limit: int = 50):
    """List all jobs, optionally filtered by status."""
    result = list(jobs.values())
    
    if status:
        result = [j for j in result if j.get("status") == status]
    
    # Sort by created_at descending
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "jobs": result[:limit],
        "total": len(result)
    }


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from tracking."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    del jobs[job_id]
    return {"message": f"Job {job_id} deleted"}


@router.post("/test")
async def test_sora_connection():
    """Test Sora connection by launching Safari and checking page state."""
    try:
        pipeline = get_pipeline()
        
        # Launch Sora
        launched = await pipeline.controller.launch_sora()
        if not launched:
            return {"status": "failed", "error": "Could not launch Safari with Sora"}
        
        await asyncio.sleep(2)
        
        # Check login
        login_status = await pipeline.controller.check_login_status()
        
        # Get page state
        page_state = await pipeline.controller.get_page_state()
        
        return {
            "status": "success",
            "logged_in": login_status.get("logged_in", False),
            "has_create_ui": login_status.get("has_create_ui", False),
            "page_url": page_state.get("url"),
            "has_prompt_input": page_state.get("has_prompt_input"),
            "has_generate_button": page_state.get("has_generate_button")
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@router.get("/downloads")
async def list_downloads():
    """List downloaded Sora videos."""
    try:
        pipeline = get_pipeline()
        videos = pipeline.downloader.list_downloaded_videos()
        return {"videos": videos, "count": len(videos)}
    except Exception as e:
        return {"error": str(e)}
