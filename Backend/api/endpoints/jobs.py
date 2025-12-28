"""
Jobs API Endpoints
Manage processing jobs
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import logging

from database.connection import get_db
from database.models import ProcessingJob
from pydantic import BaseModel
from datetime import datetime
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter()


class JobResponse(BaseModel):
    job_id: uuid.UUID
    job_type: str
    status: str
    progress_percent: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List processing jobs"""
    from sqlalchemy import select
    
    query = select(ProcessingJob).limit(limit).order_by(ProcessingJob.created_at.desc())
    
    if status:
        query = query.filter(ProcessingJob.status == status)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get job details"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(ProcessingJob).filter(ProcessingJob.job_id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


# =============================================================================
# BACKGROUND JOBS (New unified job tracking)
# =============================================================================

from services.background_jobs_service import BackgroundJobsService
from fastapi import Query, HTTPException


class BackgroundJobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    progress: float
    input_json: dict | None = None
    output_json: dict | None = None
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    related_id: str | None = None
    related_type: str | None = None


@router.get("/background/list")
async def list_background_jobs(
    job_type: str | None = Query(None, description="Filter by job type"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List background jobs with optional filtering."""
    service = BackgroundJobsService(db)
    return await service.list_jobs(job_type=job_type, status=status, limit=limit, offset=offset)


@router.get("/background/{job_id}", response_model=BackgroundJobResponse)
async def get_background_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single background job by ID."""
    service = BackgroundJobsService(db)
    job = await service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Background job not found")
    
    return job


@router.post("/background/{job_id}/cancel")
async def cancel_background_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending or running background job."""
    service = BackgroundJobsService(db)
    success = await service.cancel_job(job_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled (already completed or not found)")
    
    return {"status": "cancelled", "job_id": job_id}


@router.get("/background/active")
async def list_active_jobs(
    job_type: str | None = Query(None, description="Filter by job type"),
    db: AsyncSession = Depends(get_db),
):
    """List all currently running jobs."""
    service = BackgroundJobsService(db)
    jobs = await service.get_active_jobs(job_type)
    return {"jobs": jobs, "count": len(jobs)}
