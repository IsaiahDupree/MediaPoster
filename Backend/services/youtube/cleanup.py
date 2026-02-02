"""
YTP-022: Temp File Cleanup Service
Manages temporary files created during the YouTube pipeline.
Cleans up downloaded videos, extracted audio, and intermediate files.
"""
import logging
import os
import shutil
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

DEFAULT_TEMP_DIRS = [
    "/tmp/mediaposter/downloads",
    "/tmp/mediaposter/audio",
    "/tmp/mediaposter/transcript_cache",
]


class TempFileCleanup:
    """
    Manages cleanup of temporary files created during pipeline processing.

    Features:
    - Age-based cleanup (files older than N hours)
    - Directory-specific cleanup
    - Size-based cleanup (when total exceeds threshold)
    - Cleanup statistics and reporting
    """

    def __init__(
        self,
        temp_dirs: Optional[List[str]] = None,
        max_age_hours: int = 24,
        max_total_size_mb: int = 5000,
    ):
        self.temp_dirs = [Path(d) for d in (temp_dirs or DEFAULT_TEMP_DIRS)]
        self.max_age_hours = max_age_hours
        self.max_total_size_mb = max_total_size_mb

    def cleanup_old_files(self, max_age_hours: Optional[int] = None) -> Dict[str, Any]:
        """
        Remove files older than the specified age.

        Args:
            max_age_hours: Override default max age

        Returns:
            Dict with cleanup statistics
        """
        age_hours = max_age_hours or self.max_age_hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=age_hours)
        cutoff_timestamp = cutoff.timestamp()

        removed_count = 0
        removed_bytes = 0
        errors = 0

        for temp_dir in self.temp_dirs:
            if not temp_dir.exists():
                continue

            for file_path in temp_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                try:
                    mtime = file_path.stat().st_mtime
                    if mtime < cutoff_timestamp:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        removed_count += 1
                        removed_bytes += size
                except Exception as e:
                    logger.warning("Failed to remove %s: %s", file_path, e)
                    errors += 1

        logger.info(
            "Cleanup complete: removed %d files (%.1f MB), %d errors",
            removed_count,
            removed_bytes / (1024 * 1024),
            errors,
        )

        return {
            "removed_count": removed_count,
            "removed_bytes": removed_bytes,
            "errors": errors,
            "max_age_hours": age_hours,
        }

    def cleanup_directory(self, directory: str) -> Dict[str, Any]:
        """
        Remove all files in a specific directory.

        Args:
            directory: Directory path to clean

        Returns:
            Cleanup statistics
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            return {"removed_count": 0, "removed_bytes": 0}

        removed_count = 0
        removed_bytes = 0

        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    removed_count += 1
                    removed_bytes += size
                except Exception as e:
                    logger.warning("Failed to remove %s: %s", file_path, e)

        return {
            "removed_count": removed_count,
            "removed_bytes": removed_bytes,
            "directory": directory,
        }

    def get_disk_usage(self) -> Dict[str, Any]:
        """
        Get disk usage statistics for all temp directories.

        Returns:
            Dict with usage stats per directory
        """
        usage = {}
        total_bytes = 0

        for temp_dir in self.temp_dirs:
            if not temp_dir.exists():
                usage[str(temp_dir)] = {"files": 0, "bytes": 0}
                continue

            dir_files = 0
            dir_bytes = 0
            for file_path in temp_dir.rglob("*"):
                if file_path.is_file():
                    dir_files += 1
                    dir_bytes += file_path.stat().st_size

            usage[str(temp_dir)] = {
                "files": dir_files,
                "bytes": dir_bytes,
            }
            total_bytes += dir_bytes

        return {
            "directories": usage,
            "total_bytes": total_bytes,
            "total_mb": total_bytes / (1024 * 1024),
            "threshold_mb": self.max_total_size_mb,
            "over_threshold": total_bytes > self.max_total_size_mb * 1024 * 1024,
        }

    def should_cleanup(self) -> bool:
        """Check if cleanup is needed based on disk usage."""
        usage = self.get_disk_usage()
        return usage["over_threshold"]
