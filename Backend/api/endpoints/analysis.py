"""
AI Analysis API Endpoints - Phase 1
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel
from pathlib import Path
import uuid
import json

from database.connection import get_db
from database.models import OriginalVideo, ProcessingJob
from modules.ai_analysis import ContentAnalyzer

router = APIRouter()


class AnalysisRequest(BaseModel):
    transcribe: bool = True
    analyze_vision: bool = True
    analyze_audio: bool = True
    max_frames: int = 15


class AnalysisResponse(BaseModel):
    job_id: uuid.UUID
    video_id: uuid.UUID
    status: str
    message: str


@router.post("/full-analysis/{video_id}", response_model=AnalysisResponse)
async def start_full_analysis(
    video_id: uuid.UUID,
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start comprehensive AI analysis for a video
    
    Includes:
    - Whisper transcription
    - Frame extraction and GPT-4 Vision analysis
    - Audio characteristic analysis
    """
    from sqlalchemy import select
    
    # Get video from database
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Create processing job
    job = ProcessingJob(
        parent_video_id=video_id,
        job_type="ai_analysis",
        status="queued",
        config_json={
            'transcribe': request.transcribe,
            'analyze_vision': request.analyze_vision,
            'analyze_audio': request.analyze_audio,
            'max_frames': request.max_frames
        }
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Start analysis in background
    background_tasks.add_task(
        run_analysis,
        video_id=video_id,
        job_id=job.job_id,
        video_path=Path(video.file_path),
        config=request.dict()
    )
    
    return AnalysisResponse(
        job_id=job.job_id,
        video_id=video_id,
        status="queued",
        message="Analysis started. Check job status for progress."
    )


@router.post("/transcribe/{video_id}")
async def transcribe_video(
    video_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Transcribe video audio with Whisper"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    job = ProcessingJob(
        parent_video_id=video_id,
        job_type="transcription",
        status="queued"
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    background_tasks.add_task(
        run_transcription_only,
        video_id=video_id,
        job_id=job.job_id,
        video_path=Path(video.file_path)
    )
    
    return {"job_id": str(job.job_id), "status": "queued"}


@router.get("/results")
async def list_analysis_results(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all videos with analysis results"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo)
        .filter(OriginalVideo.analysis_data.isnot(None))
        .limit(limit)
        .offset(offset)
        .order_by(OriginalVideo.created_at.desc())
    )
    videos = list(result.scalars().all())
    
    return {
        "total": len(videos),
        "videos": [
            {
                "video_id": str(v.video_id),
                "video_name": v.file_name,
                "has_analysis": v.analysis_data is not None,
                "analysis_keys": list(v.analysis_data.keys()) if v.analysis_data else []
            }
            for v in videos
        ]
    }


@router.get("/results/{video_id}")
async def get_analysis_results(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get analysis results for a video"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.analysis_data:
        raise HTTPException(status_code=404, detail="No analysis data available")
    
    return {
        "video_id": str(video_id),
        "video_name": video.file_name,
        "analysis": video.analysis_data
    }


@router.get("/transcript/{video_id}")
async def get_transcript(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get transcript for a video"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.analysis_data or 'transcript' not in video.analysis_data:
        raise HTTPException(status_code=404, detail="Transcript not available")
    
    return {
        "video_id": str(video_id),
        "transcript": video.analysis_data['transcript']
    }


# Background task functions
async def run_analysis(
    video_id: uuid.UUID,
    job_id: uuid.UUID,
    video_path: Path,
    config: dict
):
    """Run complete analysis in background"""
    from database.connection import async_session_maker
    from sqlalchemy import select, update
    from datetime import datetime
    
    async with async_session_maker() as session:
        try:
            # Update job status
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="running", started_at=datetime.utcnow())
            )
            await session.commit()
            
            # Run analysis
            analyzer = ContentAnalyzer()
            analysis = analyzer.analyze_video_complete(
                video_path,
                extract_frames=True,
                analyze_vision=config['analyze_vision'],
                transcribe_audio=config['transcribe'],
                analyze_audio=config['analyze_audio'],
                max_frames=config['max_frames']
            )
            
            # Save analysis to video record
            await session.execute(
                update(OriginalVideo)
                .where(OriginalVideo.video_id == video_id)
                .values(analysis_data=analysis)
            )
            
            # Update job status
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
            
        except Exception as e:
            # Update job with error
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(
                    status="failed",
                    error_message=str(e)
                )
            )
            await session.commit()
            raise


async def run_transcription_only(
    video_id: uuid.UUID,
    job_id: uuid.UUID,
    video_path: Path
):
    """Run transcription only"""
    from database.connection import async_session_maker
    from sqlalchemy import update
    from datetime import datetime
    from modules.ai_analysis import WhisperService
    
    async with async_session_maker() as session:
        try:
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="running", started_at=datetime.utcnow())
            )
            await session.commit()
            
            whisper = WhisperService()
            transcript = whisper.transcribe_video(video_path)
            
            # Save to video
            result = await session.execute(
                select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
            )
            video = result.scalar_one()
            
            if video.analysis_data:
                video.analysis_data['transcript'] = transcript
            else:
                video.analysis_data = {'transcript': transcript}
            
            await session.commit()
            
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="completed", completed_at=datetime.utcnow(), progress_percent=100)
            )
            await session.commit()
            
        except Exception as e:
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="failed", error_message=str(e))
            )
            await session.commit()
