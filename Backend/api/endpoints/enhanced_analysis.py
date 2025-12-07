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
