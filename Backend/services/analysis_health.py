"""
Analysis Health Service
Detects failed, incomplete, or stale analysis and manages re-analysis
"""
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# File extensions that are videos (can be transcribed)
VIDEO_EXTENSIONS = {'.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm', '.3gp', '.wmv', '.flv'}

# File extensions that are images (cannot be transcribed)
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.heic', '.heif', '.gif', '.bmp', '.webp', '.tiff', '.raw'}


@dataclass
class AnalysisHealthStatus:
    """Health status of a video's analysis"""
    video_id: str
    filename: str
    file_extension: str
    is_video: bool
    is_image: bool
    has_transcript: bool
    has_visual_analysis: bool
    has_audio_analysis: bool
    has_ai_score: bool
    analysis_status: str  # 'complete', 'incomplete', 'failed', 'not_started', 'not_applicable'
    missing_components: List[str]
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "filename": self.filename,
            "file_extension": self.file_extension,
            "is_video": self.is_video,
            "is_image": self.is_image,
            "has_transcript": self.has_transcript,
            "has_visual_analysis": self.has_visual_analysis,
            "has_audio_analysis": self.has_audio_analysis,
            "has_ai_score": self.has_ai_score,
            "analysis_status": self.analysis_status,
            "missing_components": self.missing_components,
            "recommendation": self.recommendation,
        }


class AnalysisHealthService:
    """Service to check and manage analysis health"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _get_extension(self, filename: str) -> str:
        """Get lowercase file extension"""
        if not filename:
            return ""
        parts = filename.rsplit('.', 1)
        return f".{parts[-1].lower()}" if len(parts) > 1 else ""
    
    def _is_video_file(self, filename: str) -> bool:
        """Check if file is a video based on extension"""
        ext = self._get_extension(filename)
        return ext in VIDEO_EXTENSIONS
    
    def _is_image_file(self, filename: str) -> bool:
        """Check if file is an image based on extension"""
        ext = self._get_extension(filename)
        return ext in IMAGE_EXTENSIONS
    
    async def check_video_health(self, video_id: str) -> Optional[AnalysisHealthStatus]:
        """Check analysis health for a single video"""
        query = text("""
            SELECT 
                v.id,
                v.file_name,
                va.transcript,
                va.visual_analysis,
                va.audio_analysis,
                va.ai_virality_score,
                va.curation_status
            FROM videos v
            LEFT JOIN video_analysis va ON v.id = va.video_id
            WHERE v.id = CAST(:video_id AS uuid)
        """)
        
        result = await self.db.execute(query, {"video_id": video_id})
        row = result.fetchone()
        
        if not row:
            return None
        
        return self._build_health_status(row)
    
    def _build_health_status(self, row) -> AnalysisHealthStatus:
        """Build health status from database row"""
        video_id = str(row[0])
        filename = row[1] or ""
        transcript = row[2]
        visual_analysis = row[3]
        audio_analysis = row[4]
        ai_score = row[5]
        
        ext = self._get_extension(filename)
        is_video = self._is_video_file(filename)
        is_image = self._is_image_file(filename)
        
        has_transcript = bool(transcript and len(str(transcript)) > 10)
        has_visual = bool(visual_analysis)
        has_audio = bool(audio_analysis)
        has_score = ai_score is not None and ai_score > 0
        
        missing = []
        
        if is_image:
            # Images don't need transcription
            analysis_status = "not_applicable"
            recommendation = "skip_image"
        elif is_video:
            # Check what's missing for videos
            if not has_transcript:
                missing.append("transcript")
            if not has_visual:
                missing.append("visual_analysis")
            if not has_audio:
                missing.append("audio_analysis")
            if not has_score:
                missing.append("ai_score")
            
            if not missing:
                analysis_status = "complete"
                recommendation = "none"
            elif len(missing) == 4:
                analysis_status = "not_started"
                recommendation = "run_full_analysis"
            else:
                analysis_status = "incomplete"
                recommendation = "resume_analysis"
        else:
            # Unknown file type
            analysis_status = "unknown"
            recommendation = "review_manually"
            missing.append("unknown_file_type")
        
        return AnalysisHealthStatus(
            video_id=video_id,
            filename=filename,
            file_extension=ext,
            is_video=is_video,
            is_image=is_image,
            has_transcript=has_transcript,
            has_visual_analysis=has_visual,
            has_audio_analysis=has_audio,
            has_ai_score=has_score,
            analysis_status=analysis_status,
            missing_components=missing,
            recommendation=recommendation,
        )
    
    async def scan_all_health(self, limit: int = 1000) -> Dict[str, Any]:
        """Scan all videos and categorize by analysis health"""
        query = text("""
            SELECT 
                v.id,
                v.file_name,
                va.transcript,
                va.visual_analysis,
                va.audio_analysis,
                va.ai_virality_score,
                va.curation_status
            FROM videos v
            LEFT JOIN video_analysis va ON v.id = va.video_id
            ORDER BY v.created_at DESC
            LIMIT :limit
        """)
        
        result = await self.db.execute(query, {"limit": limit})
        rows = result.fetchall()
        
        categories = {
            "complete": [],
            "incomplete": [],
            "not_started": [],
            "not_applicable": [],  # Images
            "unknown": [],
        }
        
        for row in rows:
            status = self._build_health_status(row)
            categories[status.analysis_status].append(status.to_dict())
        
        return {
            "total_scanned": len(rows),
            "summary": {
                "complete": len(categories["complete"]),
                "incomplete": len(categories["incomplete"]),
                "not_started": len(categories["not_started"]),
                "images_skipped": len(categories["not_applicable"]),
                "unknown": len(categories["unknown"]),
            },
            "incomplete_videos": categories["incomplete"][:50],
            "not_started_videos": categories["not_started"][:50],
        }
    
    async def mark_for_reanalysis(self, video_ids: List[str]) -> Dict[str, Any]:
        """Mark videos for re-analysis by clearing their analysis data"""
        marked = []
        errors = []
        
        for video_id in video_ids:
            try:
                # Update curation_status to trigger re-analysis
                await self.db.execute(
                    text("""
                        UPDATE video_analysis 
                        SET curation_status = 'needs_reanalysis'
                        WHERE video_id = CAST(:video_id AS uuid)
                    """),
                    {"video_id": video_id}
                )
                marked.append(video_id)
            except Exception as e:
                errors.append({"video_id": video_id, "error": str(e)})
        
        await self.db.commit()
        
        return {
            "marked_count": len(marked),
            "video_ids": marked,
            "errors": errors,
        }
    
    async def get_videos_needing_reanalysis(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get videos marked for re-analysis"""
        query = text("""
            SELECT v.id, v.file_name, v.duration_sec
            FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE va.curation_status = 'needs_reanalysis'
            LIMIT :limit
        """)
        
        result = await self.db.execute(query, {"limit": limit})
        rows = result.fetchall()
        
        return [
            {"id": str(row[0]), "filename": row[1], "duration_sec": row[2]}
            for row in rows
        ]
    
    async def clear_analysis_for_retry(self, video_id: str) -> bool:
        """Clear analysis data for a video to allow fresh re-analysis"""
        try:
            await self.db.execute(
                text("""
                    UPDATE video_analysis 
                    SET 
                        transcript = NULL,
                        visual_analysis = NULL,
                        audio_analysis = NULL,
                        ai_virality_score = NULL,
                        curation_status = 'needs_reanalysis'
                    WHERE video_id = CAST(:video_id AS uuid)
                """),
                {"video_id": video_id}
            )
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to clear analysis for {video_id}: {e}")
            return False
    
    async def mark_images_as_skipped(self) -> Dict[str, Any]:
        """Mark all image files as 'image_skipped' to exclude from analysis"""
        # Get all image files
        image_patterns = [f"%.{ext.strip('.')}" for ext in IMAGE_EXTENSIONS]
        
        marked = 0
        for pattern in image_patterns:
            result = await self.db.execute(
                text("""
                    UPDATE video_analysis va
                    SET curation_status = 'image_skipped'
                    FROM videos v
                    WHERE va.video_id = v.id
                      AND LOWER(v.file_name) LIKE :pattern
                      AND (va.curation_status IS NULL OR va.curation_status NOT IN ('approved', 'rejected', 'image_skipped'))
                """),
                {"pattern": pattern}
            )
            marked += result.rowcount
        
        await self.db.commit()
        
        return {
            "marked_as_skipped": marked,
            "message": f"Marked {marked} image files as 'image_skipped'"
        }
