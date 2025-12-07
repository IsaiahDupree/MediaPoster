"""
Clip Generation API Endpoints - Phase 3
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
from pathlib import Path
import uuid

from loguru import logger

from database.connection import get_db
from database.models import OriginalVideo, Clip, ProcessingJob
from modules.clip_generation import ClipAssembler

router = APIRouter()


class ClipRequest(BaseModel):
    template: str = 'viral_basic'
    platforms: List[str] = ['tiktok']
    use_highlights: bool = True
    manual_times: Optional[List[dict]] = None


class ClipResponse(BaseModel):
    job_id: uuid.UUID
    video_id: uuid.UUID
    status: str
    message: str


@router.get("/")
async def list_all_clips(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List all clips"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Clip).limit(limit)
    )
    clips = result.scalars().all()
    
    return {
        "clips": [
            {
                "clip_id": str(c.clip_id),
                "parent_video_id": str(c.parent_video_id),
                "duration": c.clip_duration_seconds,
                "status": c.clip_status
            }
            for c in clips
        ]
    }


@router.post("/generate/{video_id}", response_model=ClipResponse)
async def generate_clips(
    video_id: uuid.UUID,
    request: ClipRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Generate clips from video"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if request.use_highlights:
        if not video.analysis_data or 'highlights' not in video.analysis_data:
            raise HTTPException(
                status_code=400,
                detail="Highlights required"
            )
    elif not request.manual_times:
        raise HTTPException(
            status_code=400,
            detail="Provide manual_times or use_highlights"
        )
    
    job = ProcessingJob(
        parent_video_id=video_id,
        job_type="clip_generation",
        status="queued",
        config_json={
            'template': request.template,
            'platforms': request.platforms,
            'use_highlights': request.use_highlights,
            'manual_times': request.manual_times
        }
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    background_tasks.add_task(
        run_clip_generation,
        video_id=video_id,
        job_id=job.job_id,
        video_path=Path(video.file_path),
        analysis_data=video.analysis_data,
        config=request.dict()
    )
    
    return ClipResponse(
        job_id=job.job_id,
        video_id=video_id,
        status="queued",
        message="Clip generation started"
    )


@router.get("/list/{video_id}")
async def list_clips(video_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get clips for video"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Clip).filter(Clip.parent_video_id == video_id)
    )
    clips = result.scalars().all()
    
    return {
        "video_id": str(video_id),
        "clips": [
            {
                "clip_id": str(c.clip_id),
                "file_path": c.file_path,
                "duration": c.duration,
                "platform": c.target_platform
            }
            for c in clips
        ]
    }


@router.get("/{clip_id}/stream")
async def stream_clip(
    clip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Stream a generated clip"""
    from sqlalchemy import select
    from fastapi.responses import FileResponse
    
    result = await db.execute(
        select(Clip).filter(Clip.clip_id == clip_id)
    )
    clip = result.scalar_one_or_none()
    
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    path = Path(clip.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Clip file not found")
        
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"clip_{clip_id}.mp4"
    )


async def run_clip_generation(
    video_id: uuid.UUID,
    job_id: uuid.UUID,
    video_path: Path,
    analysis_data: dict,
    config: dict
):
    """Background clip generation"""
    from database.connection import async_session_maker
    from sqlalchemy import update
    from datetime import datetime
    
    async with async_session_maker() as session:
        try:
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="running", started_at=datetime.utcnow())
            )
            await session.commit()
            
            logger.info(f"Starting clip generation for {video_id}")
            
            assembler = ClipAssembler()
            
            if config['use_highlights']:
                highlights = analysis_data['highlights']['selected']
            else:
                highlights = config['manual_times']
            
            transcript = analysis_data.get('transcript')
            video_context = {
                'content_type': analysis_data.get('insights', {}).get('content_type', 'video'),
                'key_topics': analysis_data.get('insights', {}).get('key_topics', []),
                'video_name': video_path.stem
            }
            
            clips_meta = assembler.create_clips_batch(
                video_path,
                highlights,
                transcript,
                video_context,
                template=config['template'],
                platforms=config['platforms']
            )
            
            for clip_meta in clips_meta:
                clip = Clip(
                    parent_video_id=video_id,
                    file_path=clip_meta['clip_path'],
                    duration=clip_meta['duration'],
                    target_platform=clip_meta['platform'],
                    metadata_json=clip_meta
                )
                session.add(clip)
            
            await session.commit()
            
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(
                    status="completed",
                    completed_at=datetime.utcnow(),
                    progress_percent=100
                )
            )
            await session.commit()
            
            logger.success(f"Clip generation complete: {len(clips_meta)} clips")
            
        except Exception as e:
            logger.error(f"Clip generation failed: {e}")
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="failed", error_message=str(e))
            )
            await session.commit()
            raise
