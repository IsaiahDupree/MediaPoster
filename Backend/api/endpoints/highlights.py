"""
Highlight Detection API Endpoints - Phase 2
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
from pathlib import Path
import uuid
import json

from loguru import logger

from database.connection import get_db
from database.models import OriginalVideo, ProcessingJob
from modules.highlight_detection import (
    SceneDetector,
    AudioSignalProcessor,
    TranscriptScanner,
    VisualSalienceDetector,
    HighlightRanker,
    GPTRecommender
)

router = APIRouter()


class HighlightRequest(BaseModel):
    max_highlights: int = 5
    min_duration: float = 10.0
    max_duration: float = 60.0
    min_score: float = 0.4
    use_gpt: bool = True


class HighlightResponse(BaseModel):
    job_id: uuid.UUID
    video_id: uuid.UUID
    status: str
    message: str


@router.post("/detect/{video_id}", response_model=HighlightResponse)
async def detect_highlights(
    video_id: uuid.UUID,
    request: HighlightRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Detect highlights in a video
    
    Analyzes video to identify the best moments for short clips
    """
    from sqlalchemy import select
    
    # Get video from database
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if analysis data exists
    if not video.analysis_data:
        raise HTTPException(
            status_code=400,
            detail="Video must be analyzed first (run AI analysis)"
        )
    
    # Create processing job
    job = ProcessingJob(
        parent_video_id=video_id,
        job_type="highlight_detection",
        status="queued",
        config_json={
            'max_highlights': request.max_highlights,
            'min_duration': request.min_duration,
            'max_duration': request.max_duration,
            'min_score': request.min_score,
            'use_gpt': request.use_gpt
        }
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Start highlight detection in background
    background_tasks.add_task(
        run_highlight_detection,
        video_id=video_id,
        job_id=job.job_id,
        video_path=Path(video.file_path),
        analysis_data=video.analysis_data,
        config=request.dict()
    )
    
    return HighlightResponse(
        job_id=job.job_id,
        video_id=video_id,
        status="queued",
        message="Highlight detection started. Check job status for progress."
    )


@router.get("/results")
async def list_highlights_results(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all videos with highlights detected"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo)
        .filter(
            OriginalVideo.analysis_data.isnot(None),
            OriginalVideo.analysis_data.has_key('highlights')
        )
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
                "has_highlights": v.analysis_data and 'highlights' in v.analysis_data,
                "highlight_count": len(v.analysis_data.get('highlights', {}).get('selected', [])) if v.analysis_data and 'highlights' in v.analysis_data else 0
            }
            for v in videos
        ]
    }


@router.get("/results/{video_id}")
async def get_highlights(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get detected highlights for a video"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.analysis_data or 'highlights' not in video.analysis_data:
        raise HTTPException(status_code=404, detail="No highlights detected yet")
    
    return {
        "video_id": str(video_id),
        "video_name": video.file_name,
        "highlights": video.analysis_data['highlights']
    }


@router.get("/{highlight_id}/reasoning")
async def get_highlight_reasoning(
    video_id: uuid.UUID,
    highlight_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get GPT reasoning for a specific highlight"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    highlights = video.analysis_data.get('highlights', {}).get('selected', [])
    
    if highlight_id < 0 or highlight_id >= len(highlights):
        raise HTTPException(status_code=404, detail="Highlight not found")
    
    highlight = highlights[highlight_id]
    
    return {
        "video_id": str(video_id),
        "highlight_id": highlight_id,
        "highlight": highlight,
        "reasoning": highlight.get('gpt_reasoning', 'No reasoning available')
    }


# Background task functions
async def run_highlight_detection(
    video_id: uuid.UUID,
    job_id: uuid.UUID,
    video_path: Path,
    analysis_data: dict,
    config: dict
):
    """Run highlight detection in background"""
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
            
            logger.info(f"Starting highlight detection for video {video_id}")
            
            # Initialize detectors
            scene_detector = SceneDetector(
                min_scene_duration=config['min_duration'],
                max_scene_duration=config['max_duration']
            )
            audio_processor = AudioSignalProcessor()
            transcript_scanner = TranscriptScanner()
            visual_detector = VisualSalienceDetector()
            ranker = HighlightRanker(
                min_duration=config['min_duration'],
                max_duration=config['max_duration'],
                min_score=config['min_score']
            )
            
            # Step 1: Detect scenes
            logger.info("Step 1/5: Detecting scenes...")
            scenes = scene_detector.detect_scenes(video_path, threshold=0.3)
            
            # Step 2: Audio analysis
            logger.info("Step 2/5: Analyzing audio signals...")
            audio_events = []
            
            volume_spikes = audio_processor.detect_volume_spikes(video_path)
            audio_events.extend(volume_spikes)
            
            energy_curve = audio_processor.calculate_energy_curve(video_path)
            energy_peaks = audio_processor.find_energy_peaks(energy_curve)
            audio_events.extend(energy_peaks)
            
            # Step 3: Transcript analysis
            logger.info("Step 3/5: Scanning transcript...")
            transcript_highlights = {}
            
            if 'transcript' in analysis_data:
                transcript_highlights = transcript_scanner.scan_comprehensive(
                    analysis_data['transcript']
                )
            
            # Step 4: Visual analysis
            logger.info("Step 4/5: Analyzing visuals...")
            visual_highlights = {}
            
            if 'visual_analysis' in analysis_data:
                visual_highlights = visual_detector.analyze_comprehensive(
                    analysis_data['visual_analysis']
                )
            
            # Step 5: Rank highlights
            logger.info("Step 5/5: Ranking highlights...")
            
            # Score scenes
            scored_scenes = scene_detector.score_scenes(
                scenes,
                audio_peaks=audio_events,
                transcript_segments=analysis_data.get('transcript', {}).get('segments', [])
            )
            
            # Rank all highlights
            ranked_highlights = ranker.rank_highlights(
                scored_scenes,
                audio_events=audio_events,
                transcript_highlights=transcript_highlights,
                visual_highlights=visual_highlights
            )
            
            # Select top highlights
            selected_highlights = ranker.select_top_highlights(
                ranked_highlights,
                max_highlights=config['max_highlights']
            )
            
            # Optional: GPT recommendations
            if config['use_gpt'] and selected_highlights:
                logger.info("Getting GPT-4 recommendations...")
                try:
                    gpt = GPTRecommender()
                    video_context = {
                        'duration': analysis_data.get('transcript', {}).get('duration', 0),
                        'content_type': analysis_data.get('insights', {}).get('content_type', 'unknown'),
                        'key_topics': analysis_data.get('insights', {}).get('key_topics', []),
                        'transcript_preview': analysis_data.get('transcript', {}).get('text', '')[:500],
                        'video_name': video_path.stem
                    }
                    
                    selected_highlights = gpt.recommend_highlights(
                        video_context,
                        selected_highlights,
                        target_count=min(3, len(selected_highlights))
                    )
                except Exception as e:
                    logger.warning(f"GPT recommendations failed: {e}")
            
            # Generate report
            report = ranker.generate_highlight_report(
                selected_highlights,
                video_name=video_path.stem
            )
            
            # Save to database
            result = await session.execute(
                select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
            )
            video = result.scalar_one()
            
            if not video.analysis_data:
                video.analysis_data = {}
            
            video.analysis_data['highlights'] = {
                'all_ranked': ranked_highlights[:20],  # Store top 20
                'selected': selected_highlights,
                'report': report,
                'detection_config': config
            }
            
            await session.commit()
            
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
            
            logger.success(f"✓ Highlight detection complete: {len(selected_highlights)} highlights found")
            
        except Exception as e:
            logger.error(f"Highlight detection failed: {e}")
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
