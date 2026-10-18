"""
Safe Export System (BM-004)
============================
Export analysis data, thumbnails, and references without duplicating media files.

This service:
1. Exports analysis data (JSON)
2. Exports thumbnails and derived assets
3. Creates file references (not copies) to original media
4. Maintains directory structure
5. Generates export manifest

Key principle: NEVER duplicate original media files - only export references.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from database.models import Video, AnalyzedVideo, VideoFrame


class SafeExportSystem:
    """
    Safe Export System - Export analysis data without duplicating media

    This service exports:
    - Analysis data (JSON files)
    - Thumbnails and derived assets
    - File references to original media (symlinks or path references)
    - Export manifest with all metadata

    It NEVER duplicates original media files.

    Usage:
        exporter = SafeExportSystem(db_session)

        # Export single video analysis
        result = await exporter.export_video_analysis(
            video_id="abc-123",
            export_dir="/exports/batch-001"
        )

        # Export multiple videos
        result = await exporter.export_batch(
            video_ids=["abc-123", "def-456"],
            export_dir="/exports/batch-001"
        )
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize Safe Export System

        Args:
            db: Database session
        """
        self.db = db
        logger.info("📦 Safe Export System initialized")

    async def export_video_analysis(
        self,
        video_id: str,
        export_dir: str,
        include_thumbnails: bool = True,
        include_frames: bool = True,
        use_symlinks: bool = True
    ) -> Dict[str, Any]:
        """
        Export analysis data for a single video

        Args:
            video_id: Video UUID
            export_dir: Export directory path
            include_thumbnails: Include thumbnail images
            include_frames: Include extracted frame images
            use_symlinks: Use symlinks instead of copying files

        Returns:
            Export result dictionary
        """
        try:
            logger.info(f"📤 Exporting analysis for video: {video_id}")

            # Create export directory
            export_path = Path(export_dir)
            export_path.mkdir(parents=True, exist_ok=True)

            # Get video record
            video_uuid = UUID(video_id) if isinstance(video_id, str) else video_id
            stmt = select(Video).where(Video.id == video_uuid)
            result = await self.db.execute(stmt)
            video = result.scalar_one_or_none()

            if not video:
                logger.error(f"Video not found: {video_id}")
                return {
                    "success": False,
                    "error": f"Video not found: {video_id}"
                }

            # Get analyzed video record
            stmt = select(AnalyzedVideo).where(AnalyzedVideo.id == video_uuid)
            result = await self.db.execute(stmt)
            analyzed_video = result.scalar_one_or_none()

            # Build export data
            export_data = {
                "video_id": str(video.id),
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "video_metadata": self._extract_video_metadata(video),
                "analysis_data": self._extract_analysis_data(analyzed_video) if analyzed_video else None,
                "file_references": self._create_file_references(video, use_symlinks)
            }

            # Export analysis JSON
            json_path = export_path / f"{video_id}_analysis.json"
            with open(json_path, "w") as f:
                json.dump(export_data, f, indent=2, default=str)

            logger.info(f"✓ Exported analysis JSON: {json_path}")

            # Export thumbnails if requested
            thumbnail_paths = []
            if include_thumbnails and video.thumbnail_path:
                thumbnail_path = await self._export_thumbnail(
                    video.thumbnail_path,
                    export_path,
                    video_id,
                    use_symlinks
                )
                if thumbnail_path:
                    thumbnail_paths.append(thumbnail_path)

            # Export frames if requested
            frame_paths = []
            if include_frames and analyzed_video:
                frame_paths = await self._export_frames(
                    video_uuid,
                    export_path,
                    video_id,
                    use_symlinks
                )

            # Create export manifest
            manifest = {
                "video_id": video_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "export_dir": str(export_path),
                "files": {
                    "analysis_json": str(json_path),
                    "thumbnails": [str(p) for p in thumbnail_paths],
                    "frames": [str(p) for p in frame_paths],
                    "original_media": video.source_uri if video.source_uri else None
                },
                "export_settings": {
                    "include_thumbnails": include_thumbnails,
                    "include_frames": include_frames,
                    "use_symlinks": use_symlinks
                }
            }

            # Write manifest
            manifest_path = export_path / f"{video_id}_manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2, default=str)

            logger.success(f"✓ Export complete: {video_id}")

            return {
                "success": True,
                "video_id": video_id,
                "export_dir": str(export_path),
                "manifest_path": str(manifest_path),
                "files_exported": {
                    "analysis_json": 1,
                    "thumbnails": len(thumbnail_paths),
                    "frames": len(frame_paths)
                }
            }

        except Exception as e:
            logger.error(f"Error exporting video analysis: {e}")
            return {
                "success": False,
                "video_id": video_id,
                "error": str(e)
            }

    async def export_batch(
        self,
        video_ids: List[str],
        export_dir: str,
        include_thumbnails: bool = True,
        include_frames: bool = True,
        use_symlinks: bool = True
    ) -> Dict[str, Any]:
        """
        Export analysis data for multiple videos

        Args:
            video_ids: List of video UUIDs
            export_dir: Export directory path
            include_thumbnails: Include thumbnail images
            include_frames: Include extracted frame images
            use_symlinks: Use symlinks instead of copying files

        Returns:
            Batch export result dictionary
        """
        logger.info(f"📦 Starting batch export for {len(video_ids)} videos")

        # Create batch export directory
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)

        # Export each video
        results = []
        for video_id in video_ids:
            video_export_dir = export_path / video_id
            result = await self.export_video_analysis(
                video_id=video_id,
                export_dir=str(video_export_dir),
                include_thumbnails=include_thumbnails,
                include_frames=include_frames,
                use_symlinks=use_symlinks
            )
            results.append(result)

        # Create batch manifest
        batch_manifest = {
            "batch_exported_at": datetime.now(timezone.utc).isoformat(),
            "export_dir": str(export_path),
            "total_videos": len(video_ids),
            "successful_exports": sum(1 for r in results if r.get("success")),
            "failed_exports": sum(1 for r in results if not r.get("success")),
            "results": results
        }

        # Write batch manifest
        batch_manifest_path = export_path / "batch_manifest.json"
        with open(batch_manifest_path, "w") as f:
            json.dump(batch_manifest, f, indent=2, default=str)

        logger.success(f"✓ Batch export complete: {batch_manifest['successful_exports']}/{len(video_ids)} successful")

        return {
            "success": True,
            "batch_manifest_path": str(batch_manifest_path),
            "total_videos": len(video_ids),
            "successful_exports": batch_manifest["successful_exports"],
            "failed_exports": batch_manifest["failed_exports"]
        }

    def _extract_video_metadata(self, video: Video) -> Dict[str, Any]:
        """Extract video metadata for export"""
        return {
            "id": str(video.id),
            "filename": video.filename,
            "file_size": video.file_size,
            "duration": float(video.duration) if video.duration else None,
            "width": video.width,
            "height": video.height,
            "fps": float(video.fps) if video.fps else None,
            "source_uri": video.source_uri,
            "created_at": video.created_at.isoformat() if video.created_at else None,
            "uploaded_at": video.uploaded_at.isoformat() if video.uploaded_at else None
        }

    def _extract_analysis_data(self, analyzed_video: AnalyzedVideo) -> Dict[str, Any]:
        """Extract analysis data for export"""
        if not analyzed_video:
            return None

        return {
            "id": str(analyzed_video.id),
            "title": analyzed_video.title,
            "description": analyzed_video.description,
            "tags": analyzed_video.tags,
            "quality_score": float(analyzed_video.quality_score) if analyzed_video.quality_score else None,
            "engagement_potential": float(analyzed_video.engagement_potential) if analyzed_video.engagement_potential else None,
            "analyzed_at": analyzed_video.analyzed_at.isoformat() if analyzed_video.analyzed_at else None,
            "metadata": analyzed_video.metadata
        }

    def _create_file_references(
        self,
        video: Video,
        use_symlinks: bool
    ) -> Dict[str, Any]:
        """
        Create file references to original media

        Args:
            video: Video record
            use_symlinks: Whether to create symlinks

        Returns:
            File reference data
        """
        return {
            "original_path": video.source_uri,
            "reference_type": "symlink" if use_symlinks else "path",
            "exists": os.path.exists(video.source_uri) if video.source_uri else False,
            "note": "This is a reference to the original file - no copy was made"
        }

    async def _export_thumbnail(
        self,
        thumbnail_path: str,
        export_dir: Path,
        video_id: str,
        use_symlinks: bool
    ) -> Optional[Path]:
        """
        Export thumbnail to export directory

        Args:
            thumbnail_path: Source thumbnail path
            export_dir: Export directory
            video_id: Video UUID
            use_symlinks: Use symlinks instead of copying

        Returns:
            Exported thumbnail path or None
        """
        try:
            if not os.path.exists(thumbnail_path):
                logger.warning(f"Thumbnail not found: {thumbnail_path}")
                return None

            # Create thumbnails subdirectory
            thumbs_dir = export_dir / "thumbnails"
            thumbs_dir.mkdir(exist_ok=True)

            # Determine file extension
            ext = Path(thumbnail_path).suffix
            dest_path = thumbs_dir / f"{video_id}_thumbnail{ext}"

            # Create symlink or copy
            if use_symlinks:
                if dest_path.exists():
                    dest_path.unlink()
                dest_path.symlink_to(Path(thumbnail_path).resolve())
                logger.info(f"✓ Created thumbnail symlink: {dest_path}")
            else:
                shutil.copy2(thumbnail_path, dest_path)
                logger.info(f"✓ Copied thumbnail: {dest_path}")

            return dest_path

        except Exception as e:
            logger.error(f"Error exporting thumbnail: {e}")
            return None

    async def _export_frames(
        self,
        video_id: UUID,
        export_dir: Path,
        video_id_str: str,
        use_symlinks: bool
    ) -> List[Path]:
        """
        Export extracted frames to export directory

        Args:
            video_id: Video UUID
            export_dir: Export directory
            video_id_str: Video UUID as string
            use_symlinks: Use symlinks instead of copying

        Returns:
            List of exported frame paths
        """
        try:
            # Get frames from database
            stmt = select(VideoFrame).where(VideoFrame.video_id == video_id)
            result = await self.db.execute(stmt)
            frames = result.scalars().all()

            if not frames:
                logger.info(f"No frames found for video: {video_id}")
                return []

            # Create frames subdirectory
            frames_dir = export_dir / "frames"
            frames_dir.mkdir(exist_ok=True)

            exported_paths = []

            for i, frame in enumerate(frames):
                if not frame.frame_path or not os.path.exists(frame.frame_path):
                    continue

                # Determine file extension
                ext = Path(frame.frame_path).suffix
                dest_path = frames_dir / f"{video_id_str}_frame_{i:04d}{ext}"

                # Create symlink or copy
                if use_symlinks:
                    if dest_path.exists():
                        dest_path.unlink()
                    dest_path.symlink_to(Path(frame.frame_path).resolve())
                else:
                    shutil.copy2(frame.frame_path, dest_path)

                exported_paths.append(dest_path)

            logger.info(f"✓ Exported {len(exported_paths)} frames")
            return exported_paths

        except Exception as e:
            logger.error(f"Error exporting frames: {e}")
            return []

    async def verify_export(self, manifest_path: str) -> Dict[str, Any]:
        """
        Verify an export using its manifest

        Args:
            manifest_path: Path to export manifest JSON

        Returns:
            Verification result dictionary
        """
        try:
            # Load manifest
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            # Verify each file
            verification = {
                "manifest_valid": True,
                "files_verified": {},
                "missing_files": []
            }

            # Check analysis JSON
            analysis_json = manifest["files"].get("analysis_json")
            if analysis_json:
                verification["files_verified"]["analysis_json"] = os.path.exists(analysis_json)
                if not os.path.exists(analysis_json):
                    verification["missing_files"].append(analysis_json)

            # Check thumbnails
            thumbnails = manifest["files"].get("thumbnails", [])
            for thumb_path in thumbnails:
                exists = os.path.exists(thumb_path)
                verification["files_verified"][thumb_path] = exists
                if not exists:
                    verification["missing_files"].append(thumb_path)

            # Check frames
            frames = manifest["files"].get("frames", [])
            for frame_path in frames:
                exists = os.path.exists(frame_path)
                verification["files_verified"][frame_path] = exists
                if not exists:
                    verification["missing_files"].append(frame_path)

            # Check original media reference
            original_media = manifest["files"].get("original_media")
            if original_media:
                verification["files_verified"]["original_media"] = os.path.exists(original_media)
                if not os.path.exists(original_media):
                    verification["missing_files"].append(original_media)

            # Overall success
            verification["success"] = len(verification["missing_files"]) == 0

            return verification

        except Exception as e:
            logger.error(f"Error verifying export: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_exporter_instance: Optional[SafeExportSystem] = None


def get_safe_export_system(db: AsyncSession) -> SafeExportSystem:
    """
    Get singleton instance of Safe Export System

    Args:
        db: Database session

    Returns:
        SafeExportSystem instance
    """
    global _exporter_instance
    if _exporter_instance is None:
        _exporter_instance = SafeExportSystem(db)
    return _exporter_instance
