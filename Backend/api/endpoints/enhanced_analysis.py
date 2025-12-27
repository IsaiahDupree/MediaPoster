"""
Enhanced Analysis API Endpoints
Comprehensive API for video analysis, segment management, and performance correlation
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid

from database.connection import get_db
from services.content_analysis_orchestrator import ContentAnalysisOrchestrator
from services.segment_editor import SegmentEditor
from services.performance_correlator import PerformanceCorrelator
from services.event_bus import EventBus, Topics
from database.models import VideoSegment, AnalyzedVideo

router = APIRouter()


@router.get("/videos")
def list_enhanced_analysis_videos(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List all videos with enhanced analysis"""
    from sqlalchemy import select, func
    
    try:
        result = db.execute(
            select(AnalyzedVideo)
            .limit(limit)
            .offset(offset)
            .order_by(AnalyzedVideo.created_at.desc())
        )
        videos = list(result.scalars().all())
        
        return {
            "total": len(videos),
            "videos": [
                {
                    "video_id": str(v.id),
                    "title": v.content_item.title if v.content_item else None,
                    "has_segments": v.segments is not None and len(v.segments) > 0,
                    "segment_count": len(v.segments) if v.segments else 0,
                    "created_at": str(v.created_at) if v.created_at else None
                }
                for v in videos
            ]
        }
    except Exception as e:
        # If table doesn't exist or query fails, return empty list
        return {
            "total": 0,
            "videos": []
        }


# ==================== Request Models ====================

class SegmentCreateRequest(BaseModel):
    video_id: str
    start_time: float
    end_time: float
    segment_type: str
    psychology_tags: Optional[Dict] = None
    cta_keywords: Optional[List[str]] = None
    edit_reason: Optional[str] = None


class SegmentUpdateRequest(BaseModel):
    segment_type: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    psychology_tags: Optional[Dict] = None
    edit_reason: Optional[str] = None


class SegmentSplitRequest(BaseModel):
    split_time: float
    edit_reason: Optional[str] = None


class SegmentMergeRequest(BaseModel):
    segment_ids: List[str]
    merged_type: Optional[str] = None
    edit_reason: Optional[str] = None


# ==================== Video Analysis Endpoints ====================

@router.post("/videos/{video_id}/analyze")
async def analyze_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    force_reanalyze: bool = False,
    include_performance: bool = False,
    db: Session = Depends(get_db)
):
    """Trigger full video analysis"""
    orchestrator = ContentAnalysisOrchestrator(db)
    
    # In a real app, we'd fetch the video path from DB
    # For now, just a placeholder response
    return {"message": "Analysis started", "video_id": video_id}


@router.get("/videos/{video_id}/validate")
def validate_analysis(
    video_id: str,
    db: Session = Depends(get_db)
):
    """Validate segment data for a video"""
    editor = SegmentEditor(db)
    result = editor.validate_segments(video_id)
    return result


@router.get("/videos/{video_id}/export")
def export_analysis(
    video_id: str,
    db: Session = Depends(get_db)
):
    """Export analysis data as JSON"""
    orchestrator = ContentAnalysisOrchestrator(db)
    try:
        return orchestrator.export_analysis(video_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Segment Management Endpoints ====================

@router.post("/segments")
def create_segment(
    request: SegmentCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new manual segment"""
    editor = SegmentEditor(db)
    try:
        segment = editor.create_segment(
            video_id=request.video_id,
            start_time=request.start_time,
            end_time=request.end_time,
            segment_type=request.segment_type,
            psychology_tags=request.psychology_tags,
            cta_keywords=request.cta_keywords,
            edited_by=None, # Auth user ID would go here
            edit_reason=request.edit_reason
        )
        return {"segment_id": str(segment.id), "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/segments/{segment_id}")
def update_segment(
    segment_id: str,
    request: SegmentUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update an existing segment"""
    editor = SegmentEditor(db)
    try:
        segment = editor.update_segment(
            segment_id=segment_id,
            edited_by=None, # Auth user ID
            edit_reason=request.edit_reason,
            **request.dict(exclude_unset=True, exclude={"edit_reason"})
        )
        return {"segment_id": str(segment.id), "status": "updated"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/segments/{segment_id}")
def delete_segment(
    segment_id: str,
    edit_reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Delete a segment"""
    editor = SegmentEditor(db)
    success = editor.delete_segment(
        segment_id=segment_id,
        edited_by=None, # Auth user ID
        edit_reason=edit_reason
    )
    if not success:
        raise HTTPException(status_code=404, detail="Segment not found")
    return {"message": "Segment deleted"}


@router.post("/segments/{segment_id}/split")
def split_segment(
    segment_id: str,
    request: SegmentSplitRequest,
    db: Session = Depends(get_db)
):
    """Split a segment into two"""
    editor = SegmentEditor(db)
    try:
        seg1, seg2 = editor.split_segment(
            segment_id=segment_id,
            split_time=request.split_time,
            edited_by=None, # Auth user ID
            edit_reason=request.edit_reason
        )
        return {
            "message": "Segment split successfully",
            "segments": [str(seg1.id), str(seg2.id)]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/segments/merge")
def merge_segments(
    request: SegmentMergeRequest,
    db: Session = Depends(get_db)
):
    """Merge multiple segments"""
    editor = SegmentEditor(db)
    try:
        merged = editor.merge_segments(
            segment_ids=request.segment_ids,
            merged_type=request.merged_type,
            edited_by=None, # Auth user ID
            edit_reason=request.edit_reason
        )
        return {"segment_id": str(merged.id), "status": "merged"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Performance Endpoints ====================

@router.get("/segments/{segment_id}/performance")
def get_segment_performance(
    segment_id: str,
    db: Session = Depends(get_db)
):
    """Get performance metrics for a segment"""
    # This would query SegmentPerformance table
    # Placeholder implementation
    return {"segment_id": segment_id, "metrics": "Not implemented yet"}


@router.get("/patterns/top-performing")
def get_top_patterns(
    pattern_type: str = Query("hook", enum=["hook", "emotion", "duration"]),
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get top performing patterns"""
    correlator = PerformanceCorrelator(db)
    return correlator.find_top_performing_patterns(pattern_type, limit)


@router.post("/predict")
def predict_performance(
    segment_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Predict performance for a potential segment"""
    correlator = PerformanceCorrelator(db)
    return correlator.predict_segment_performance(segment_data)


# ==================== Enhanced Vision Analysis Endpoints ====================

class StructuredAnalysisRequest(BaseModel):
    """Request for structured frame analysis"""
    frame_paths: List[str]
    timestamps: List[float]
    analyze_every_nth: int = 3
    include_motion_detection: bool = True
    include_scene_detection: bool = True


class TemplateMatchRequest(BaseModel):
    """Request to match content to templates"""
    content_type: str
    tone: str
    topics: List[str] = []
    duration_sec: float = 30


@router.post("/vision/analyze-structured")
async def analyze_frames_structured(
    request: StructuredAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Perform structured visual analysis on video frames.
    
    Extracts:
    - Color palette (primary, secondary, accent, mood)
    - Lighting (type, direction, quality, exposure)
    - Camera info (shot_type, angle, depth_of_field)
    - Scene elements (setting, subjects, objects, text)
    - Viral indicators (hook_potential, pattern_interrupts)
    - Camera motion sequences
    - Scene boundaries
    """
    try:
        from services.enhanced_vision_analyzer import EnhancedVisionAnalyzer
        from pathlib import Path
        
        analyzer = EnhancedVisionAnalyzer()
        
        frame_paths = [Path(p) for p in request.frame_paths]
        
        # Run full analysis
        results = await analyzer.full_video_analysis(
            frame_paths=frame_paths,
            timestamps=request.timestamps,
            analyze_every_nth=request.analyze_every_nth
        )
        
        return {
            "success": True,
            "frame_analyses_count": len(results.get("frame_analyses", [])),
            "scene_boundaries_count": len(results.get("scene_boundaries", [])),
            "camera_motions_count": len(results.get("camera_motions", [])),
            "overall_style": results.get("overall_style", {}),
            "dominant_colors": results.get("dominant_colors", []),
            "summary": results.get("analysis_summary", ""),
            "full_results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vision/detect-scenes")
async def detect_scene_boundaries(
    frame_paths: List[str],
    timestamps: List[float],
    threshold: float = 30.0
):
    """
    Detect scene boundaries/cuts in a video.
    
    Uses OpenCV for fast detection, AI for boundary classification.
    Returns timestamps where scene changes occur.
    """
    try:
        from services.enhanced_vision_analyzer import EnhancedVisionAnalyzer
        from pathlib import Path
        
        analyzer = EnhancedVisionAnalyzer()
        
        boundaries = await analyzer.detect_scene_boundaries(
            frame_paths=[Path(p) for p in frame_paths],
            timestamps=timestamps,
            threshold=threshold
        )
        
        return {
            "success": True,
            "scene_count": len(boundaries) + 1,
            "boundaries": [
                {
                    "timestamp": b.timestamp,
                    "frame_index": b.frame_index,
                    "boundary_type": b.boundary_type,
                    "confidence": b.confidence,
                    "visual_change_score": b.visual_change_score
                }
                for b in boundaries
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vision/detect-motion")
async def detect_camera_motion(
    frame_paths: List[str],
    timestamps: List[float]
):
    """
    Detect camera motion sequences (pan, tilt, zoom, etc).
    
    Uses OpenCV optical flow for motion detection.
    Returns motion sequences with type, direction, and timing.
    """
    try:
        from services.enhanced_vision_analyzer import EnhancedVisionAnalyzer
        from pathlib import Path
        
        analyzer = EnhancedVisionAnalyzer()
        
        motions = await analyzer.detect_camera_motion_sequence(
            frame_paths=[Path(p) for p in frame_paths],
            timestamps=timestamps
        )
        
        return {
            "success": True,
            "motion_sequences": [
                {
                    "start_time": m.start_time,
                    "end_time": m.end_time,
                    "motion_type": m.motion_type,
                    "direction": m.direction,
                    "confidence": m.confidence,
                    "speed": m.speed
                }
                for m in motions
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Template Library Endpoints ====================

@router.get("/templates")
async def list_templates(
    category: Optional[str] = None,
    limit: int = 20
):
    """
    List available video templates.
    
    Templates are reusable formats extracted from high-performing videos.
    """
    try:
        from services.template_library import TemplateLibrary
        
        library = TemplateLibrary()
        templates = await library.list_templates(category=category, limit=limit)
        
        return {
            "success": True,
            "templates": templates,
            "count": len(templates)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template with full beat sheet"""
    try:
        from services.template_library import TemplateLibrary
        
        library = TemplateLibrary()
        template = await library.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "success": True,
            "template": template
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/match")
async def match_content_to_templates(request: TemplateMatchRequest):
    """
    Find best matching templates for given content.
    
    Analyzes content characteristics and suggests templates
    that would work well for the content type.
    """
    try:
        from services.template_library import TemplateLibrary
        
        library = TemplateLibrary()
        
        content_analysis = {
            "content_type": request.content_type,
            "tone": request.tone,
            "topics": request.topics,
            "transcription_duration_sec": request.duration_sec
        }
        
        matches = await library.match_content_to_template(content_analysis)
        
        return {
            "success": True,
            "matches": [
                {
                    "template_id": m.template_id,
                    "template_name": m.template_name,
                    "match_score": m.match_score,
                    "reasons": m.match_reasons,
                    "suggested_modifications": m.suggested_modifications
                }
                for m in matches
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/auto-populate")
async def auto_populate_templates(
    min_engagement_rate: float = 0.05,
    limit: int = 10,
    background_tasks: BackgroundTasks = None
):
    """
    Auto-generate templates from top-performing analyzed videos.
    
    Scans video_analysis table for high-performing content
    and creates reusable templates from their patterns.
    """
    try:
        from services.template_library import TemplateLibrary
        
        library = TemplateLibrary()
        created = await library.auto_populate_from_top_videos(
            min_engagement_rate=min_engagement_rate,
            limit=limit
        )
        
        return {
            "success": True,
            "templates_created": created,
            "message": f"Created {created} templates from high-performing videos"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/create-from-video")
async def create_template_from_video(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    Create a template from a specific video's analysis.
    
    Extracts the video's beat sheet, style, and patterns
    into a reusable template.
    """
    try:
        from services.template_library import TemplateLibrary
        from sqlalchemy import text
        
        library = TemplateLibrary()
        
        # Fetch video analysis
        result = db.execute(text("""
            SELECT id, beat_sheet, visual_analysis, hooks, tone, pacing,
                   music_suggestion, transcription_duration_sec, pillar_tags,
                   format_tags, content_type, call_to_action, pre_social_score
            FROM video_analysis
            WHERE id = :video_id
        """), {"video_id": video_id})
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video analysis not found")
        
        analysis_data = {
            "beat_sheet": row[1] or [],
            "visual_analysis": row[2] or {},
            "hooks": row[3] or [],
            "tone": row[4] or "",
            "pacing": row[5] or "",
            "music_suggestion": row[6] or {},
            "transcription_duration_sec": row[7] or 30,
            "pillar_tags": row[8] or [],
            "format_tags": row[9] or [],
            "content_type": row[10] or "",
            "call_to_action": row[11] or {}
        }
        
        performance = {
            "engagement_rate": (row[12] or 0) / 100,
            "views": 0,
            "completion_rate": 0
        }
        
        template = await library.create_template_from_video(
            video_id=str(row[0]),
            analysis_data=analysis_data,
            performance_metrics=performance
        )
        
        template_id = await library.save_template(template)
        
        return {
            "success": True,
            "template_id": template_id,
            "template_name": template.name,
            "category": template.category
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
