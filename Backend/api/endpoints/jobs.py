"""
Jobs API Endpoints
Manage processing jobs
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from database.connection import get_db
from database.models import ProcessingJob
from pydantic import BaseModel
from datetime import datetime

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
