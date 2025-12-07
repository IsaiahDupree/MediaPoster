"""
Viral Video Analysis API Endpoints

New endpoints for the unified schema with word-level and frame-level analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import Optional, List
from pydantic import BaseModel
import uuid
import logging

from database.connection import get_db
from services.video_pipeline import VideoAnalysisPipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/viral-analysis", tags=["viral-analysis"])


@router.get("/videos")
async def list_viral_analysis_videos(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all videos that have been analyzed for viral potential"""
    from sqlalchemy import text
    
    try:
        # Get videos with word-level analysis
        query = text("""
            SELECT DISTINCT 
                v.id,
                v.file_name,
                v.source_uri,
                v.created_at,
                COUNT(vw.word_index) as word_count,
                COUNT(DISTINCT vf.frame_number) as frame_count
            FROM videos v
            LEFT JOIN video_words vw ON v.id = vw.video_id
            LEFT JOIN video_frames vf ON v.id = vf.video_id
            WHERE vw.video_id IS NOT NULL OR vf.video_id IS NOT NULL
            GROUP BY v.id, v.file_name, v.source_uri, v.created_at
            ORDER BY v.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = await db.execute(query, {"limit": limit, "offset": offset})
        rows = list(result.fetchall())
        
        return {
            "total": len(rows),
            "videos": [
                {
                    "video_id": str(row.id),
                    "file_name": row.file_name,
                    "source_uri": row.source_uri,
                    "created_at": str(row.created_at) if row.created_at else None,
                    "word_count": row.word_count or 0,
                    "frame_count": row.frame_count or 0,
                    "analyzed": (row.word_count or 0) > 0 or (row.frame_count or 0) > 0
                }
                for row in rows
            ]
        }
    except Exception as e:
        # If tables don't exist or query fails, return empty list
        logger.warning(f"Error listing viral analysis videos: {e}")
        return {
            "total": 0,
            "videos": []
        }


class AnalysisResponse(BaseModel):
    """Response model for analysis operations"""
    status: str
    video_id: str
    message: Optional[str] = None
    word_count: Optional[int] = None
    frame_count: Optional[int] = None
    duration_seconds: Optional[float] = None


class WordData(BaseModel):
    """Word timeline data"""
    word_index: int
    word: str
    start_s: float
    end_s: float
    is_emphasis: bool
    is_cta_keyword: bool
    is_question: bool
    speech_function: Optional[str]
    sentiment_score: Optional[float]
    emotion: Optional[str]


class FrameData(BaseModel):
    """Frame analysis data"""
    frame_number: int
    timestamp_s: float
    shot_type: Optional[str]
    has_face: bool
    face_count: int
    eye_contact: bool
    has_text: bool
    visual_clutter_score: Optional[float]
    contrast_score: Optional[float]
    motion_score: Optional[float]
    scene_change: bool


@router.post("/videos/{video_id}/analyze", response_model=AnalysisResponse)
async def analyze_video(
    video_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    skip_existing: bool = Query(True, description="Skip if already analyzed"),
    db: AsyncSession = Depends(get_db)
):
    """
    Start complete viral analysis for a video
    
    Analyzes:
    - Word-level transcript with emphasis, CTAs, sentiment
    - Frame-by-frame visual composition
    - Pacing and composition metrics
    
    Returns immediately and runs analysis in background.
    """
    
    # Check if video exists
    result = await db.execute(
        text("SELECT id, file_name, source_uri FROM videos WHERE id = :vid"),
        {"vid": str(video_id)}
    )
    video = result.first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if already analyzed
    if skip_existing:
        check = await db.execute(
            text("SELECT COUNT(*) as count FROM video_words WHERE video_id = :vid"),
            {"vid": str(video_id)}
        )
        word_count = check.scalar()
        
        if word_count > 0:
            return AnalysisResponse(
                status="already_analyzed",
                video_id=str(video_id),
                message=f"Video already has {word_count} words analyzed",
                word_count=word_count
            )
    
    # Start background analysis
    background_tasks.add_task(
        _run_analysis_background,
        video_id=str(video_id),
        skip_existing=skip_existing
    )
    
    return AnalysisResponse(
        status="started",
        video_id=str(video_id),
        message="Analysis started in background"
    )


@router.post("/videos/{video_id}/analyze-sync", response_model=AnalysisResponse)
async def analyze_video_sync(
    video_id: uuid.UUID,
    skip_existing: bool = Query(True, description="Skip if already analyzed"),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze video synchronously (waits for completion)
    
    Use this for testing or when you need immediate results.
    May take 30-60 seconds per video.
    """
    
    pipeline = VideoAnalysisPipeline()
    results = await pipeline.analyze_video_by_id(
        video_id=str(video_id),
        db_session=db,
        skip_existing=skip_existing
    )
    
    if results['status'] == 'error':
        raise HTTPException(status_code=500, detail=results.get('error'))
    
    if results['status'] == 'skipped':
        return AnalysisResponse(
            status="already_analyzed",
            video_id=str(video_id),
            message="Video already analyzed",
            word_count=results.get('existing_word_count')
        )
    
    return AnalysisResponse(
        status="completed",
        video_id=str(video_id),
        word_count=results.get('word_count'),
        frame_count=results.get('frame_count'),
        duration_seconds=results.get('duration_seconds'),
        message="Analysis completed successfully"
    )


@router.get("/videos/{video_id}/words")
async def get_video_words(
    video_id: uuid.UUID,
    start_s: Optional[float] = Query(None, description="Start time in seconds"),
    end_s: Optional[float] = Query(None, description="End time in seconds"),
    limit: int = Query(1000, le=5000, description="Max words to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get word-level timeline for a video
    
    Returns all words with timestamps, emphasis markers, CTAs, etc.
    Optionally filter by time range.
    """
    
    # Build query
    where_clauses = ["video_id = :vid"]
    params = {"vid": str(video_id), "limit": limit}
    
    if start_s is not None:
        where_clauses.append("start_s >= :start_s")
        params["start_s"] = start_s
    
    if end_s is not None:
        where_clauses.append("end_s <= :end_s")
        params["end_s"] = end_s
    
    where_sql = " AND ".join(where_clauses)
    
    query = f"""
        SELECT 
            word_index, word, start_s, end_s,
            is_emphasis, is_cta_keyword, is_question,
            speech_function, sentiment_score, emotion
        FROM video_words
        WHERE {where_sql}
        ORDER BY word_index
        LIMIT :limit
    """
    
    result = await db.execute(text(query), params)
    words = result.fetchall()
    
    if not words:
        raise HTTPException(
            status_code=404, 
            detail="No word data found. Video may not be analyzed yet."
        )
    
    return {
        'video_id': str(video_id),
        'word_count': len(words),
        'time_range': {
            'start_s': words[0].start_s if words else None,
            'end_s': words[-1].end_s if words else None
        },
        'words': [
            {
                'word_index': w.word_index,
                'word': w.word,
                'start_s': float(w.start_s),
                'end_s': float(w.end_s),
                'is_emphasis': w.is_emphasis,
                'is_cta_keyword': w.is_cta_keyword,
                'is_question': w.is_question,
                'speech_function': w.speech_function,
                'sentiment_score': float(w.sentiment_score) if w.sentiment_score else None,
                'emotion': w.emotion
            }
            for w in words
        ]
    }


@router.get("/videos/{video_id}/frames")
async def get_video_frames(
    video_id: uuid.UUID,
    start_s: Optional[float] = Query(None, description="Start time in seconds"),
    end_s: Optional[float] = Query(None, description="End time in seconds"),
    limit: int = Query(200, le=1000, description="Max frames to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get frame-by-frame analysis for a video
    
    Returns all frames with shot types, face detection, composition metrics, etc.
    """
    
    where_clauses = ["video_id = :vid"]
    params = {"vid": str(video_id), "limit": limit}
    
    if start_s is not None:
        where_clauses.append("timestamp_s >= :start_s")
        params["start_s"] = start_s
    
    if end_s is not None:
        where_clauses.append("timestamp_s <= :end_s")
        params["end_s"] = end_s
    
    where_sql = " AND ".join(where_clauses)
    
    query = f"""
        SELECT 
            frame_number, timestamp_s, shot_type, camera_motion,
            has_face, face_count, eye_contact, face_size_ratio,
            has_text, text_area_ratio, visual_clutter_score,
            contrast_score, motion_score, scene_change, color_palette
        FROM video_frames
        WHERE {where_sql}
        ORDER BY timestamp_s
        LIMIT :limit
    """
    
    result = await db.execute(text(query), params)
    frames = result.fetchall()
    
    if not frames:
        raise HTTPException(
            status_code=404,
            detail="No frame data found. Video may not be analyzed yet."
        )
    
    return {
        'video_id': str(video_id),
        'frame_count': len(frames),
        'time_range': {
            'start_s': frames[0].timestamp_s if frames else None,
            'end_s': frames[-1].timestamp_s if frames else None
        },
        'frames': [
            {
                'frame_number': f.frame_number,
                'timestamp_s': float(f.timestamp_s),
                'shot_type': f.shot_type,
                'camera_motion': f.camera_motion,
                'has_face': f.has_face,
                'face_count': f.face_count,
                'eye_contact': f.eye_contact,
                'face_size_ratio': float(f.face_size_ratio) if f.face_size_ratio else None,
                'has_text': f.has_text,
                'text_area_ratio': float(f.text_area_ratio) if f.text_area_ratio else None,
                'visual_clutter_score': float(f.visual_clutter_score) if f.visual_clutter_score else None,
                'contrast_score': float(f.contrast_score) if f.contrast_score else None,
                'motion_score': float(f.motion_score) if f.motion_score else None,
                'scene_change': f.scene_change,
                'color_palette': f.color_palette
            }
            for f in frames
        ]
    }


@router.get("/videos/{video_id}/timeline")
async def get_video_timeline(
    video_id: uuid.UUID,
    timestamp_s: float = Query(..., description="Timestamp to query"),
    window_s: float = Query(2.0, description="Time window around timestamp"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete timeline context at a specific timestamp
    
    Returns:
    - Words spoken in window
    - Frame analysis at timestamp
    - Aggregate metrics
    
    Perfect for timeline viewers and analysis UIs.
    """
    
    start_s = timestamp_s - window_s / 2
    end_s = timestamp_s + window_s / 2
    
    # Get words in window
    words_result = await db.execute(
        text("""
            SELECT word_index, word, start_s, end_s, is_emphasis, speech_function
            FROM video_words
            WHERE video_id = :vid 
              AND start_s <= :end_s 
              AND end_s >= :start_s
            ORDER BY word_index
        """),
        {"vid": str(video_id), "start_s": start_s, "end_s": end_s}
    )
    words = words_result.fetchall()
    
    # Get closest frame
    frame_result = await db.execute(
        text("""
            SELECT 
                frame_number, timestamp_s, shot_type, has_face,
                face_count, eye_contact, has_text, visual_clutter_score
            FROM video_frames
            WHERE video_id = :vid
            ORDER BY ABS(timestamp_s - :ts)
            LIMIT 1
        """),
        {"vid": str(video_id), "ts": timestamp_s}
    )
    frame = frame_result.first()
    
    return {
        'video_id': str(video_id),
        'timestamp_s': timestamp_s,
        'window_s': window_s,
        'words': [
            {
                'word': w.word,
                'start_s': float(w.start_s),
                'end_s': float(w.end_s),
                'is_emphasis': w.is_emphasis,
                'speech_function': w.speech_function
            }
            for w in words
        ],
        'frame': {
            'frame_number': frame.frame_number,
            'timestamp_s': float(frame.timestamp_s),
            'shot_type': frame.shot_type,
            'has_face': frame.has_face,
            'face_count': frame.face_count,
            'eye_contact': frame.eye_contact,
            'has_text': frame.has_text,
            'visual_clutter_score': float(frame.visual_clutter_score) if frame.visual_clutter_score else None
        } if frame else None
    }


@router.get("/videos/{video_id}/metrics")
async def get_video_metrics(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregate metrics for analyzed video
    
    Returns:
    - Pacing metrics (WPM, pauses)
    - Composition metrics (face presence, shot distribution)
    - Emphasis and CTA segment counts
    """
    
    # Word metrics
    word_stats = await db.execute(
        text("""
            SELECT 
                COUNT(*) as total_words,
                MIN(start_s) as first_word_s,
                MAX(end_s) as last_word_s,
                SUM(CASE WHEN is_emphasis THEN 1 ELSE 0 END) as emphasis_words,
                SUM(CASE WHEN is_cta_keyword THEN 1 ELSE 0 END) as cta_words,
                AVG(sentiment_score) as avg_sentiment
            FROM video_words
            WHERE video_id = :vid
        """),
        {"vid": str(video_id)}
    )
    word_data = word_stats.first()
    
    # Frame metrics
    frame_stats = await db.execute(
        text("""
            SELECT 
                COUNT(*) as total_frames,
                SUM(CASE WHEN has_face THEN 1 ELSE 0 END) as frames_with_face,
                SUM(CASE WHEN eye_contact THEN 1 ELSE 0 END) as frames_with_eye_contact,
                SUM(CASE WHEN has_text THEN 1 ELSE 0 END) as frames_with_text,
                AVG(visual_clutter_score) as avg_clutter,
                AVG(contrast_score) as avg_contrast,
                SUM(CASE WHEN scene_change THEN 1 ELSE 0 END) as scene_changes
            FROM video_frames
            WHERE video_id = :vid
        """),
        {"vid": str(video_id)}
    )
    frame_data = frame_stats.first()
    
    # Shot type distribution
    shot_dist = await db.execute(
        text("""
            SELECT shot_type, COUNT(*) as count
            FROM video_frames
            WHERE video_id = :vid AND shot_type IS NOT NULL
            GROUP BY shot_type
            ORDER BY count DESC
        """),
        {"vid": str(video_id)}
    )
    shot_distribution = {row.shot_type: row.count for row in shot_dist.fetchall()}
    
    if not word_data or word_data.total_words == 0:
        raise HTTPException(
            status_code=404,
            detail="No analysis data found for this video"
        )
    
    # Calculate WPM
    duration_s = float(word_data.last_word_s - word_data.first_word_s) if word_data.last_word_s else 0
    wpm = (word_data.total_words / duration_s * 60) if duration_s > 0 else 0
    
    # Calculate percentages
    total_frames = frame_data.total_frames if frame_data else 0
    face_pct = (frame_data.frames_with_face / total_frames * 100) if total_frames > 0 else 0
    eye_contact_pct = (frame_data.frames_with_eye_contact / total_frames * 100) if total_frames > 0 else 0
    text_pct = (frame_data.frames_with_text / total_frames * 100) if total_frames > 0 else 0
    
    return {
        'video_id': str(video_id),
        'pacing': {
            'total_words': word_data.total_words,
            'duration_s': round(duration_s, 2),
            'words_per_minute': round(wpm, 1),
            'emphasis_word_count': word_data.emphasis_words,
            'cta_word_count': word_data.cta_words,
            'avg_sentiment': round(float(word_data.avg_sentiment), 2) if word_data.avg_sentiment else 0
        },
        'composition': {
            'total_frames': total_frames,
            'face_presence_pct': round(face_pct, 1),
            'eye_contact_pct': round(eye_contact_pct, 1),
            'text_presence_pct': round(text_pct, 1),
            'avg_visual_clutter': round(float(frame_data.avg_clutter), 2) if frame_data.avg_clutter else None,
            'avg_contrast': round(float(frame_data.avg_contrast), 2) if frame_data.avg_contrast else None,
            'scene_change_count': frame_data.scene_changes if frame_data else 0
        },
        'shot_distribution': shot_distribution
    }


# Background task helper
async def _run_analysis_background(video_id: str, skip_existing: bool):
    """Run analysis in background"""
    from database.connection import get_db
    
    logger.info(f"Background analysis started for video {video_id}")
    
    try:
        async for session in get_db():
            pipeline = VideoAnalysisPipeline()
            results = await pipeline.analyze_video_by_id(
                video_id=video_id,
                db_session=session,
                skip_existing=skip_existing
            )
            
            if results['status'] == 'success':
                logger.info(f"Background analysis completed for video {video_id}")
            else:
                logger.error(f"Background analysis failed for video {video_id}: {results.get('error')}")
    
    except Exception as e:
        logger.error(f"Background analysis exception for video {video_id}: {e}")
