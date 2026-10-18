"""
Analysis Pre-Validation Endpoint
=================================
Validates videos before analysis to identify potential failures ahead of time.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pathlib import Path
import os
from loguru import logger
from datetime import datetime

from database.connection import get_db
from database.models import Video, VideoAnalysis
from api.media_processing_db import map_host_to_container_path

router = APIRouter(prefix="/api/analysis-validation", tags=["Analysis Validation"])


class ValidationResult:
    """Result of validating a single video"""
    def __init__(self, video_id: str, filename: str):
        self.video_id = video_id
        self.filename = filename
        self.valid = True
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.file_path: Optional[str] = None
        self.file_exists = False
        self.file_size: Optional[int] = None
        self.file_readable = False
        self.container_path: Optional[str] = None
        self.container_exists = False
        
    def add_issue(self, issue: str):
        """Add a critical issue that will cause analysis to fail"""
        self.issues.append(issue)
        self.valid = False
        
    def add_warning(self, warning: str):
        """Add a warning that might cause issues but won't necessarily fail"""
        self.warnings.append(warning)
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "filename": self.filename,
            "valid": self.valid,
            "issues": self.issues,
            "warnings": self.warnings,
            "file_path": self.file_path,
            "file_exists": self.file_exists,
            "file_size": self.file_size,
            "file_readable": self.file_readable,
            "container_path": self.container_path,
            "container_exists": self.container_exists
        }


async def validate_video_file(video: Video) -> ValidationResult:
    """
    Validate a single video file for analysis readiness.
    Checks file existence, permissions, format, size, etc.
    """
    result = ValidationResult(str(video.id), video.file_name or "unknown")
    
    # Check source URI
    if not video.source_uri:
        result.add_issue("No source_uri - cannot locate video file")
        return result
    
    # Expand user path
    file_path = os.path.expanduser(video.source_uri)
    result.file_path = file_path
    
    # Check file existence (host path)
    if os.path.exists(file_path):
        result.file_exists = True
        result.file_size = os.path.getsize(file_path)
        
        # Check file readability
        if os.access(file_path, os.R_OK):
            result.file_readable = True
        else:
            result.add_issue(f"File exists but is not readable: {file_path}")
    else:
        result.add_issue(f"File does not exist: {file_path}")
    
    # Check container path (Docker)
    container_path = map_host_to_container_path(file_path)
    result.container_path = container_path
    
    if container_path and os.path.exists(container_path):
        result.container_exists = True
        if not os.access(container_path, os.R_OK):
            result.add_warning(f"Container path exists but may not be readable: {container_path}")
    elif container_path:
        result.add_warning(f"Container path does not exist (may be OK if using host path): {container_path}")
    
    # Check file extension
    VIDEO_EXTENSIONS = {'.mov', '.mp4', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv', '.3gp'}
    ext = Path(file_path).suffix.lower()
    if ext not in VIDEO_EXTENSIONS:
        result.add_issue(f"Invalid file extension: {ext} (not a video file)")
    
    # Check file size
    if result.file_size is not None:
        if result.file_size == 0:
            result.add_issue("File size is 0 bytes - file is empty")
        elif result.file_size < 1024:  # Less than 1KB
            result.add_warning(f"File size is very small ({result.file_size} bytes) - may be corrupted")
        elif result.file_size > 10 * 1024 * 1024 * 1024:  # More than 10GB
            result.add_warning(f"File size is very large ({result.file_size / (1024**3):.2f} GB) - may cause timeout")
    
    # Check if already analyzed
    # (This is informational, not a blocker)
    
    return result


async def validate_system_resources() -> Dict[str, Any]:
    """
    Validate system resources needed for analysis.
    Checks API keys, database connectivity, etc.
    """
    issues = []
    warnings = []
    
    # Check OpenAI API key
    from config import settings
    if not settings.openai_api_key:
        issues.append("OpenAI API key not configured - analysis will use fallback mode")
    elif len(settings.openai_api_key) < 20:
        warnings.append("OpenAI API key appears invalid (too short)")
    
    # Check database connectivity (basic check)
    try:
        from database.connection import async_session_maker
        async with async_session_maker() as db:
            await db.execute(select(1))
    except Exception as e:
        issues.append(f"Database connectivity issue: {str(e)}")
    
    # Check temp directory
    temp_dir = "/tmp/mediaposter"
    if not os.path.exists(temp_dir):
        try:
            os.makedirs(temp_dir, exist_ok=True)
        except Exception as e:
            warnings.append(f"Cannot create temp directory: {str(e)}")
    
    # Check disk space (if possible)
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024**3)
        if free_gb < 1:
            warnings.append(f"Low disk space: {free_gb:.2f} GB free")
    except Exception:
        pass  # Can't check disk space on all systems
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }


@router.get("/pre-check")
async def pre_check_analysis(
    limit: int = Query(default=100, le=500, description="Number of videos to validate"),
    include_analyzed: bool = Query(default=False, description="Include already analyzed videos"),
    db: AsyncSession = Depends(get_db)
):
    """
    Pre-validate videos before starting analysis.
    Returns a report of potential issues that would cause analysis to fail.
    """
    logger.info(f"[Validation] Starting pre-check for up to {limit} videos")
    
    # Get videos to validate
    query = select(Video).where(
        Video.source_uri.isnot(None),
        Video.source_uri != ''
    )
    
    if not include_analyzed:
        # Only videos without analysis
        subquery = select(VideoAnalysis.video_id).distinct()
        query = query.where(~Video.id.in_(subquery))
    
    query = query.order_by(Video.created_at.desc()).limit(limit)
    result = await db.execute(query)
    videos = result.scalars().all()
    
    logger.info(f"[Validation] Found {len(videos)} videos to validate")
    
    # Validate each video
    validation_results = []
    for video in videos:
        result = await validate_video_file(video)
        validation_results.append(result.to_dict())
    
    # Validate system resources
    system_validation = await validate_system_resources()
    
    # Summary statistics
    valid_count = sum(1 for r in validation_results if r["valid"])
    invalid_count = len(validation_results) - valid_count
    total_issues = sum(len(r["issues"]) for r in validation_results)
    total_warnings = sum(len(r["warnings"]) for r in validation_results)
    
    # Group by issue type
    issue_types: Dict[str, int] = {}
    for result in validation_results:
        for issue in result["issues"]:
            issue_type = issue.split(":")[0] if ":" in issue else issue.split(" - ")[0]
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
    
    return {
        "summary": {
            "total_videos": len(validation_results),
            "valid_videos": valid_count,
            "invalid_videos": invalid_count,
            "total_issues": total_issues,
            "total_warnings": total_warnings,
            "validation_timestamp": datetime.now().isoformat()
        },
        "system_validation": system_validation,
        "issue_breakdown": issue_types,
        "videos": validation_results,
        "recommendations": _generate_recommendations(validation_results, system_validation)
    }


@router.get("/pre-check/{video_id}")
async def pre_check_single_video(
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Pre-validate a single video before analysis.
    """
    from uuid import UUID
    
    try:
        video_uuid = UUID(video_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid video ID format: {video_id}")
    
    result = await db.execute(select(Video).where(Video.id == video_uuid))
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")
    
    validation_result = await validate_video_file(video)
    system_validation = await validate_system_resources()
    
    return {
        "video": validation_result.to_dict(),
        "system_validation": system_validation,
        "ready_for_analysis": validation_result.valid and system_validation["valid"]
    }


def _generate_recommendations(
    validation_results: List[Dict[str, Any]],
    system_validation: Dict[str, Any]
) -> List[str]:
    """Generate actionable recommendations based on validation results."""
    recommendations = []
    
    # Count issue types
    file_not_found = sum(1 for r in validation_results if any("does not exist" in issue for issue in r["issues"]))
    file_not_readable = sum(1 for r in validation_results if any("not readable" in issue for issue in r["issues"]))
    invalid_extension = sum(1 for r in validation_results if any("Invalid file extension" in issue for issue in r["issues"]))
    empty_file = sum(1 for r in validation_results if any("0 bytes" in issue for issue in r["issues"]))
    
    if file_not_found > 0:
        recommendations.append(
            f"⚠️  {file_not_found} video(s) have missing files. Check file paths and ensure files are accessible."
        )
    
    if file_not_readable > 0:
        recommendations.append(
            f"⚠️  {file_not_readable} video(s) have permission issues. Check file permissions (chmod +r)."
        )
    
    if invalid_extension > 0:
        recommendations.append(
            f"⚠️  {invalid_extension} file(s) have invalid extensions. These may be images or unsupported formats."
        )
    
    if empty_file > 0:
        recommendations.append(
            f"⚠️  {empty_file} file(s) are empty (0 bytes). These files are corrupted or incomplete."
        )
    
    if system_validation["issues"]:
        recommendations.append(
            f"⚠️  System issues detected: {', '.join(system_validation['issues'])}"
        )
    
    if not recommendations:
        recommendations.append("✅ All videos appear ready for analysis!")
    
    return recommendations

