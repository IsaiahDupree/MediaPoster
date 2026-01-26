"""
Content Repurposing API
=======================
API endpoints for the content repurposing engine.

Features:
- Upload/import videos
- Process videos for highlights
- List and manage clips
- Export/download clips

PRD: docs/PRD_CONTENT_REPURPOSING_ENGINE.md
"""

import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, BackgroundTasks
from pydantic import BaseModel, Field
from loguru import logger

from services.repurpose import RepurposePipeline


router = APIRouter(prefix="/api/repurpose", tags=["Content Repurposing"])


# Singleton pipeline instance
_pipeline_instance = None


def get_pipeline() -> RepurposePipeline:
    """Get or create pipeline instance"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = RepurposePipeline()
    return _pipeline_instance


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ProcessVideoRequest(BaseModel):
    """Request to process a video"""
    video_path: str = Field(..., description="Path to video file on server")
    user_id: str = Field(..., description="User UUID")
    title: str = Field(..., description="Video title")
    source_type: str = Field("upload", description="Source type: upload, youtube, podcast_rss, twitch_vod")
    source_url: Optional[str] = Field(None, description="Original URL if applicable")
    auto_extract: bool = Field(True, description="Automatically extract clips after analysis")


class SourceResponse(BaseModel):
    """Repurpose source info"""
    id: str
    title: str
    status: str
    clips_generated: int
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None


class ClipResponse(BaseModel):
    """Detected clip info"""
    id: str
    start: float
    end: float
    title: str
    virality_score: int
    hook_score: int
    emotion_score: int
    status: str


class SourceDetailResponse(SourceResponse):
    """Source with clips"""
    clips: List[ClipResponse] = []


class ProcessResultResponse(BaseModel):
    """Result from video processing"""
    source_id: str
    status: str
    highlights_count: int
    clips_extracted: int
    error: Optional[str] = None


class ApproveClipRequest(BaseModel):
    """Request to approve a clip"""
    approved: bool = Field(True, description="Approve or reject")


class RenderClipRequest(BaseModel):
    """Request to render a clip"""
    aspect_ratios: List[str] = Field(["9:16"], description="Aspect ratios to render: 9:16, 1:1, 16:9, 4:5")
    platforms: List[str] = Field(["tiktok"], description="Target platforms: tiktok, reels, shorts, twitter, instagram")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/process", response_model=ProcessResultResponse)
async def process_video(
    request: ProcessVideoRequest,
    background_tasks: BackgroundTasks
):
    """
    Process a video to detect highlights

    This endpoint:
    1. Transcribes video with Whisper
    2. Analyzes for emotional peaks and highlights
    3. Generates virality scores
    4. Optionally extracts clips

    Returns immediately with source_id. Check status with GET /sources/{id}
    """
    try:
        pipeline = get_pipeline()

        # Validate video file exists
        if not os.path.exists(request.video_path):
            raise HTTPException(status_code=404, detail="Video file not found")

        # Process in background
        result = await pipeline.process_video(
            video_path=request.video_path,
            user_id=request.user_id,
            title=request.title,
            source_type=request.source_type,
            source_url=request.source_url,
            auto_extract=request.auto_extract
        )

        return ProcessResultResponse(**result)

    except Exception as e:
        logger.error(f"Process video failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/{source_id}", response_model=SourceDetailResponse)
async def get_source_status(source_id: str):
    """
    Get repurpose source status and clips

    Returns:
        - Source metadata
        - Processing status
        - List of detected clips with scores
    """
    try:
        pipeline = get_pipeline()
        result = await pipeline.get_source_status(source_id)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return SourceDetailResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get source failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clips/{clip_id}/approve")
async def approve_clip(clip_id: str, request: ApproveClipRequest):
    """
    Approve or reject a detected clip

    Approved clips can be rendered and exported.
    """
    try:
        pipeline = get_pipeline()

        with pipeline.SessionLocal() as session:
            from sqlalchemy import text
            session.execute(text("""
                UPDATE repurpose_clips
                SET is_approved = :approved, status = :status, updated_at = NOW()
                WHERE id = :id
            """), {
                "id": clip_id,
                "approved": request.approved,
                "status": "approved" if request.approved else "rejected"
            })
            session.commit()

        return {"success": True, "clip_id": clip_id, "approved": request.approved}

    except Exception as e:
        logger.error(f"Approve clip failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clips/{clip_id}/render")
async def render_clip(clip_id: str, request: RenderClipRequest):
    """
    Render clip in specified aspect ratios

    Generates video files optimized for each platform.
    """
    try:
        pipeline = get_pipeline()

        # Get clip info
        with pipeline.SessionLocal() as session:
            from sqlalchemy import text
            result = session.execute(text("""
                SELECT c.start_time, c.end_time, s.file_path
                FROM repurpose_clips c
                JOIN repurpose_sources s ON c.source_id = s.id
                WHERE c.id = :clip_id
            """), {"clip_id": clip_id})

            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Clip not found")

            start_time, end_time, source_path = row

        # Render for each aspect ratio/platform
        from services.repurpose.clip_extractor import ClipConfig
        renders = []

        for aspect_ratio in request.aspect_ratios:
            for platform in request.platforms:
                config = ClipConfig(
                    start_time=start_time,
                    end_time=end_time,
                    aspect_ratio=aspect_ratio,
                    target_platform=platform
                )

                render_result = await pipeline.extractor.extract_clip(source_path, config)

                if render_result.success:
                    # Save render record
                    render_id = await pipeline._save_render(
                        clip_id=clip_id,
                        aspect_ratio=aspect_ratio,
                        target_platform=platform,
                        file_path=render_result.output_path,
                        file_size=render_result.file_size_bytes,
                        status="completed"
                    )
                    renders.append({
                        "render_id": str(render_id),
                        "aspect_ratio": aspect_ratio,
                        "platform": platform,
                        "file_path": render_result.output_path,
                        "file_size_bytes": render_result.file_size_bytes
                    })
                else:
                    logger.warning(f"Render failed: {render_result.error_message}")

        return {
            "success": True,
            "clip_id": clip_id,
            "renders": renders
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Render clip failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def list_sources(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List repurpose sources

    Returns list of videos being repurposed.
    """
    try:
        pipeline = get_pipeline()

        with pipeline.SessionLocal() as session:
            from sqlalchemy import text

            query = """
                SELECT id, title, status, clips_generated, duration_seconds, created_at
                FROM repurpose_sources
                WHERE 1=1
            """
            params = {}

            if user_id:
                query += " AND user_id = :user_id"
                params["user_id"] = user_id

            if status:
                query += " AND status = :status"
                params["status"] = status

            query += " ORDER BY created_at DESC LIMIT :limit"
            params["limit"] = limit

            result = session.execute(text(query), params)

            sources = [
                {
                    "id": str(row[0]),
                    "title": row[1],
                    "status": row[2],
                    "clips_generated": row[3],
                    "duration_seconds": row[4],
                    "created_at": row[5].isoformat() if row[5] else None
                }
                for row in result.fetchall()
            ]

        return {"sources": sources, "count": len(sources)}

    except Exception as e:
        logger.error(f"List sources failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clips")
async def list_clips(
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    min_virality: int = Query(0, ge=0, le=100, description="Minimum virality score"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List detected clips

    Returns clips sorted by virality score.
    """
    try:
        pipeline = get_pipeline()

        with pipeline.SessionLocal() as session:
            from sqlalchemy import text

            query = """
                SELECT id, source_id, start_time, end_time, title,
                       virality_score, hook_score, emotion_score, status
                FROM repurpose_clips
                WHERE virality_score >= :min_virality
            """
            params = {"min_virality": min_virality}

            if source_id:
                query += " AND source_id = :source_id"
                params["source_id"] = source_id

            query += " ORDER BY virality_score DESC LIMIT :limit"
            params["limit"] = limit

            result = session.execute(text(query), params)

            clips = [
                {
                    "id": str(row[0]),
                    "source_id": str(row[1]),
                    "start": row[2],
                    "end": row[3],
                    "title": row[4],
                    "virality_score": row[5],
                    "hook_score": row[6],
                    "emotion_score": row[7],
                    "status": row[8]
                }
                for row in result.fetchall()
            ]

        return {"clips": clips, "count": len(clips)}

    except Exception as e:
        logger.error(f"List clips failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    """
    Delete a repurpose source

    Cascade deletes clips and renders.
    """
    try:
        pipeline = get_pipeline()

        with pipeline.SessionLocal() as session:
            from sqlalchemy import text
            result = session.execute(text("""
                DELETE FROM repurpose_sources
                WHERE id = :id
                RETURNING id
            """), {"id": source_id})
            deleted = result.fetchone()
            session.commit()

            if not deleted:
                raise HTTPException(status_code=404, detail="Source not found")

        return {"success": True, "deleted_id": source_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete source failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
