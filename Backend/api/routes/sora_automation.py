"""
Sora Automation API - Control Safari browser automation for video generation
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

router = APIRouter(prefix="/api/sora", tags=["sora"])

# Storage paths
SORA_DIR = Path("/Users/isaiahdupree/Documents/CompetitorResearch/sora_downloads")
SORA_DIR.mkdir(parents=True, exist_ok=True)
JOBS_FILE = SORA_DIR / "jobs.json"
SCHEDULE_FILE = SORA_DIR / "schedule.json"


class SoraPrompt(BaseModel):
    prompt: str
    duration: int = 5
    aspect_ratio: str = "9:16"
    scheduled_at: Optional[str] = None


class ScheduleConfig(BaseModel):
    enabled: bool
    interval_minutes: int = 60
    max_daily_generations: int = 10


def load_jobs() -> List[dict]:
    """Load jobs from file"""
    if JOBS_FILE.exists():
        with open(JOBS_FILE) as f:
            return json.load(f)
    return []


def save_jobs(jobs: List[dict]):
    """Save jobs to file"""
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def load_schedule() -> List[dict]:
    """Load schedule from file"""
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE) as f:
            return json.load(f)
    return []


def save_schedule(schedule: List[dict]):
    """Save schedule to file"""
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedule, f, indent=2)


@router.get("/jobs")
async def list_jobs():
    """List all Sora generation jobs"""
    jobs = load_jobs()
    
    # Also include format jobs
    formats_jobs_file = Path("/Users/isaiahdupree/Documents/CompetitorResearch/formats/jobs.json")
    if formats_jobs_file.exists():
        with open(formats_jobs_file) as f:
            format_jobs = json.load(f)
            jobs.extend(format_jobs)
    
    # Sort by created_at descending
    jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"jobs": jobs}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a specific job"""
    jobs = load_jobs()
    
    for job in jobs:
        if job.get("id") == job_id:
            return job
    
    raise HTTPException(status_code=404, detail="Job not found")


@router.post("/generate")
async def create_generation(prompt_data: SoraPrompt, background_tasks: BackgroundTasks):
    """Create a new Sora generation job"""
    job_id = f"sora_{int(datetime.now().timestamp())}"
    
    job = {
        "id": job_id,
        "prompt": prompt_data.prompt,
        "duration": prompt_data.duration,
        "aspect_ratio": prompt_data.aspect_ratio,
        "status": "pending",
        "scheduled_at": prompt_data.scheduled_at or datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
        "video_path": None,
        "error": None
    }
    
    jobs = load_jobs()
    jobs.append(job)
    save_jobs(jobs)
    
    # If not scheduled for future, trigger immediately
    if not prompt_data.scheduled_at:
        background_tasks.add_task(run_sora_generation, job_id)
    
    return {"success": True, "job": job}


@router.post("/automate/{job_id}")
async def trigger_automation(job_id: str, background_tasks: BackgroundTasks):
    """Trigger Safari automation for a specific job"""
    jobs = load_jobs()
    
    # Also check format jobs
    formats_jobs_file = Path("/Users/isaiahdupree/Documents/CompetitorResearch/formats/jobs.json")
    if formats_jobs_file.exists():
        with open(formats_jobs_file) as f:
            format_jobs = json.load(f)
            jobs.extend(format_jobs)
    
    job = None
    for j in jobs:
        if j.get("id") == job_id:
            job = j
            break
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("status") not in ["pending", "failed"]:
        raise HTTPException(status_code=400, detail=f"Job status is {job.get('status')}, cannot re-run")
    
    # Update status
    job["status"] = "generating"
    save_jobs([j for j in jobs if j.get("id") != job_id] + [job])
    
    # Trigger automation in background
    background_tasks.add_task(run_sora_generation, job_id)
    
    return {"success": True, "message": f"Automation triggered for job {job_id}"}


async def run_sora_generation(job_id: str):
    """Background task to run Sora browser automation"""
    try:
        from automation.sora_browser_automation import SoraBrowserAutomation
        
        jobs = load_jobs()
        job = None
        for j in jobs:
            if j.get("id") == job_id:
                job = j
                break
        
        if not job:
            return
        
        automation = SoraBrowserAutomation()
        
        # If this is a format job, we need to generate the prompt first
        if "format_id" in job:
            from services.ai_video_pipeline.pipeline import VideoPipeline, PipelineConfig
            
            config = PipelineConfig(
                style=job["format_id"],
                character_description="Isaiah, a charismatic Black man in his late 20s with a warm smile, wearing a casual hoodie and gold chain",
                video_generator="sora"
            )
            
            pipeline = VideoPipeline(config)
            video = await pipeline.create_video(
                location=job["location"],
                theme=job.get("theme"),
                duration=30
            )
            
            # Get first scene prompt
            if video.script and video.script.scenes:
                prompt = video.script.scenes[0].sora_prompt
            else:
                prompt = job.get("prompt", "")
        else:
            prompt = job.get("prompt", "")
        
        # Run generation
        result = await automation.generate_video(
            prompt=prompt,
            duration=job.get("duration", 5),
            aspect_ratio=job.get("aspect_ratio", "9:16"),
            job_id=job_id
        )
        
        # Update job status
        job["status"] = result.status
        job["video_path"] = result.video_path
        job["error"] = result.error
        job["completed_at"] = datetime.now().isoformat()
        
        # Save updated jobs
        jobs = [j for j in load_jobs() if j.get("id") != job_id]
        jobs.append(job)
        save_jobs(jobs)
        
    except Exception as e:
        # Update job with error
        jobs = load_jobs()
        for j in jobs:
            if j.get("id") == job_id:
                j["status"] = "failed"
                j["error"] = str(e)
        save_jobs(jobs)


@router.get("/schedule")
async def get_schedule():
    """Get scheduled generation jobs"""
    schedule = load_schedule()
    return {"schedule": schedule}


@router.post("/schedule")
async def add_to_schedule(prompt_data: SoraPrompt):
    """Add a job to the schedule"""
    if not prompt_data.scheduled_at:
        raise HTTPException(status_code=400, detail="scheduled_at is required")
    
    job_id = f"scheduled_{int(datetime.now().timestamp())}"
    
    scheduled_job = {
        "id": job_id,
        "prompt": prompt_data.prompt,
        "duration": prompt_data.duration,
        "aspect_ratio": prompt_data.aspect_ratio,
        "scheduled_at": prompt_data.scheduled_at,
        "status": "scheduled",
        "created_at": datetime.now().isoformat()
    }
    
    schedule = load_schedule()
    schedule.append(scheduled_job)
    save_schedule(schedule)
    
    return {"success": True, "job": scheduled_job}


@router.delete("/schedule/{job_id}")
async def remove_from_schedule(job_id: str):
    """Remove a job from the schedule"""
    schedule = load_schedule()
    schedule = [j for j in schedule if j.get("id") != job_id]
    save_schedule(schedule)
    
    return {"success": True}


@router.post("/scheduler/start")
async def start_scheduler(background_tasks: BackgroundTasks):
    """Start the background scheduler"""
    background_tasks.add_task(run_scheduler_loop)
    return {"success": True, "message": "Scheduler started"}


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the background scheduler"""
    # Set a flag file to stop the scheduler
    stop_file = SORA_DIR / ".scheduler_stop"
    stop_file.touch()
    return {"success": True, "message": "Scheduler stop requested"}


async def run_scheduler_loop():
    """Background scheduler loop"""
    stop_file = SORA_DIR / ".scheduler_stop"
    stop_file.unlink(missing_ok=True)
    
    while not stop_file.exists():
        schedule = load_schedule()
        now = datetime.now()
        
        for job in schedule:
            if job.get("status") != "scheduled":
                continue
            
            scheduled_time = datetime.fromisoformat(job["scheduled_at"])
            if scheduled_time <= now:
                # Time to run this job
                job["status"] = "pending"
                save_schedule(schedule)
                
                # Create a regular job and trigger it
                jobs = load_jobs()
                jobs.append({
                    "id": job["id"],
                    "prompt": job["prompt"],
                    "duration": job["duration"],
                    "aspect_ratio": job["aspect_ratio"],
                    "status": "pending",
                    "created_at": datetime.now().isoformat()
                })
                save_jobs(jobs)
                
                # Trigger generation
                await run_sora_generation(job["id"])
        
        await asyncio.sleep(60)  # Check every minute
