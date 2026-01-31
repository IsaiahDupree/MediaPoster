"""
Jobs Router

Handles job status queries, cancellation, and retry.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from ..schemas import (
    JobState,
    JobListResponse,
    JobEventsResponse,
    CancelResponse,
    RetryResponse,
    generate_id
)
from ..storage import job_store, event_store

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobState)
async def get_job(job_id: str):
    """
    Get the current state of a job.
    
    Returns:
        JobState with current status, progress, and result
    """
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return JobState(**job)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    state: Optional[str] = Query(None, description="Filter by state"),
    command: Optional[str] = Query(None, description="Filter by command"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List jobs with optional filters.
    
    Returns:
        JobListResponse with paginated job list
    """
    filters = {}
    if state:
        filters["state"] = state
    if command:
        filters["command"] = command
    if correlation_id:
        filters["correlation_id"] = correlation_id
    
    jobs, total = job_store.list(filters=filters, offset=offset, limit=limit)
    
    return JobListResponse(
        jobs=[JobState(**j) for j in jobs],
        total=total,
        offset=offset,
        limit=limit
    )


@router.get("/jobs/{job_id}/events", response_model=JobEventsResponse)
async def get_job_events(
    job_id: str,
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get events for a specific job.
    
    Returns:
        JobEventsResponse with paginated event list
    """
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    events, total, next_cursor = event_store.list_for_job(
        job_id=job_id,
        cursor=cursor,
        limit=limit
    )
    
    return JobEventsResponse(
        events=events,
        total=total,
        cursor=next_cursor
    )


@router.post("/jobs/{job_id}/cancel", response_model=CancelResponse)
async def cancel_job(job_id: str):
    """
    Cancel a running job.
    
    Only jobs in QUEUED or RUNNING state can be cancelled.
    
    Returns:
        CancelResponse indicating success/failure
    """
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    if job["state"] not in ("QUEUED", "RUNNING"):
        return CancelResponse(
            cancelled=False,
            job_id=job_id,
            message=f"Cannot cancel job in state: {job['state']}"
        )
    
    job_store.update(job_id, {
        "state": "CANCELLED",
        "completed_at": datetime.utcnow()
    })
    
    event_store.emit({
        "event_id": generate_id("evt_"),
        "job_id": job_id,
        "correlation_id": job.get("correlation_id"),
        "type": "job.cancelled",
        "message": "Job cancelled by user",
        "timestamp": datetime.utcnow()
    })
    
    logger.info(f"Job cancelled: {job_id}")
    
    return CancelResponse(
        cancelled=True,
        job_id=job_id,
        message="Job cancelled successfully"
    )


@router.post("/jobs/{job_id}/retry", response_model=RetryResponse)
async def retry_job(job_id: str):
    """
    Retry a failed job.
    
    Creates a new job with the same command and arguments.
    
    Returns:
        RetryResponse with new job ID
    """
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    if job["state"] not in ("FAILED", "CANCELLED"):
        return RetryResponse(
            retried=False,
            job_id=job_id,
            message=f"Cannot retry job in state: {job['state']}"
        )
    
    new_job_id = generate_id("job_")
    new_job = {
        "job_id": new_job_id,
        "command_id": generate_id("cmd_"),
        "correlation_id": job.get("correlation_id"),
        "command": job["command"],
        "args": job["args"],
        "state": "QUEUED",
        "stage": None,
        "percent": 0,
        "result": None,
        "error_code": None,
        "error_message": None,
        "idempotency_key": None,
        "priority": job.get("priority", "normal"),
        "timeout_s": job.get("timeout_s", 3600),
        "created_at": datetime.utcnow(),
        "started_at": None,
        "completed_at": None,
        "updated_at": datetime.utcnow()
    }
    
    job_store.create(new_job)
    
    event_store.emit({
        "event_id": generate_id("evt_"),
        "job_id": new_job_id,
        "correlation_id": job.get("correlation_id"),
        "type": "job.queued",
        "message": f"Job retried from {job_id}",
        "timestamp": datetime.utcnow()
    })
    
    logger.info(f"Job retried: {job_id} -> {new_job_id}")
    
    return RetryResponse(
        retried=True,
        job_id=job_id,
        new_job_id=new_job_id,
        message="Job retry queued"
    )
