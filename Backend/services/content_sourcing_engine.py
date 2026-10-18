"""
Content Sourcing Engine (PIPE-001)
==================================
Auto-discover and ingest content from local media folders with deduplication.

Features:
- Monitor local media folders for new content
- Auto-ingest videos and images
- File hash-based deduplication
- Status tracking (pending, ingested, failed)
- Integration with existing iPhone Direct Import
- Watchdog-based file system monitoring

This is the foundation for the automated content pipeline that feeds
into AI analysis, platform matching, and Tinder-style approval.
"""

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import uuid4

from services.event_bus import EventBus, Topics
from database.models import Video


class ContentStatus(str, Enum):
    """Content ingestion status"""
    PENDING = "pending"           # Discovered, not yet ingested
    INGESTING = "ingesting"       # Currently being ingested
    INGESTED = "ingested"         # Successfully ingested
    FAILED = "failed"             # Ingestion failed
    DUPLICATE = "duplicate"       # Duplicate detected
    SKIPPED = "skipped"           # Manually skipped


@dataclass
class ContentFile:
    """Represents a discovered content file"""
    file_path: str
    file_hash: str
    file_size: int
    media_type: str  # 'video', 'image'
    mime_type: str
    discovered_at: datetime
    status: ContentStatus = ContentStatus.PENDING
    error_message: Optional[str] = None
    video_id: Optional[str] = None  # UUID after ingestion
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "media_type": self.media_type,
            "mime_type": self.mime_type,
            "discovered_at": self.discovered_at.isoformat(),
            "status": self.status.value,
            "error_message": self.error_message,
            "video_id": self.video_id,
            "metadata": self.metadata
        }


class ContentSourcingEngine:
    """
    Content Sourcing Engine - Auto-discover and ingest media files

    This service monitors local directories for new media files, generates
    file hashes for deduplication, and coordinates ingestion into the
    MediaPoster database.

    Usage:
        engine = ContentSourcingEngine(db_session)

        # Scan directory for new content
        results = await engine.scan_directory("/path/to/media")

        # Ingest discovered content
        await engine.ingest_pending()

        # Start monitoring (watchdog)
        await engine.start_monitoring(["/path/to/media"])
    """

    # Supported media types
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.flv', '.wmv'}
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}

    def __init__(self, db: AsyncSession):
        """
        Initialize Content Sourcing Engine

        Args:
            db: Database session
        """
        self.db = db
        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("content-sourcing-engine")

        # In-memory cache of discovered files
        self.discovered_files: Dict[str, ContentFile] = {}

        # File hash index for fast duplicate detection
        self.hash_index: Dict[str, str] = {}  # hash -> file_path

        # Monitoring state
        self._is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._watch_dirs: List[str] = []

        logger.info("📁 Content Sourcing Engine initialized")

    async def build_hash_index(self) -> None:
        """
        Build hash index from existing videos in database

        This prevents ingesting duplicates of already-imported content.
        """
        try:
            # Query all videos with source_uri
            stmt = select(Video).where(Video.source_uri.isnot(None))
            result = await self.db.execute(stmt)
            videos = result.scalars().all()

            logger.info(f"Building hash index from {len(videos)} existing videos...")

            hash_count = 0
            for video in videos:
                if video.source_uri and os.path.exists(video.source_uri):
                    try:
                        file_hash = self._compute_file_hash(video.source_uri)
                        self.hash_index[file_hash] = video.source_uri
                        hash_count += 1
                    except Exception as e:
                        logger.debug(f"Error hashing {video.source_uri}: {e}")

            logger.success(f"✓ Hash index built: {hash_count} files indexed")

        except Exception as e:
            logger.error(f"Error building hash index: {e}")

    def _compute_file_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        """
        Compute SHA256 hash of file

        Args:
            file_path: Path to file
            chunk_size: Chunk size for reading (default: 8KB)

        Returns:
            SHA256 hex digest
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _get_media_type(self, file_path: str) -> Optional[str]:
        """
        Determine media type from file extension

        Args:
            file_path: Path to file

        Returns:
            'video', 'image', or None
        """
        ext = Path(file_path).suffix.lower()

        if ext in self.VIDEO_EXTENSIONS:
            return 'video'
        elif ext in self.IMAGE_EXTENSIONS:
            return 'image'
        else:
            return None

    async def scan_directory(
        self,
        directory: str,
        recursive: bool = True,
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Scan directory for media files

        Args:
            directory: Directory path to scan
            recursive: Scan subdirectories (default: True)
            skip_existing: Skip files already in discovered_files (default: True)

        Returns:
            Scan results dictionary
        """
        logger.info(f"📂 Scanning directory: {directory}")

        dir_path = Path(directory)
        if not dir_path.exists():
            logger.error(f"Directory not found: {directory}")
            return {
                "success": False,
                "error": f"Directory not found: {directory}",
                "discovered": 0,
                "duplicates": 0
            }

        # Build hash index if not already built
        if not self.hash_index:
            await self.build_hash_index()

        discovered = 0
        duplicates = 0
        errors = 0

        # Scan files
        pattern = "**/*" if recursive else "*"

        for file_path in dir_path.glob(pattern):
            if not file_path.is_file():
                continue

            # Check media type
            media_type = self._get_media_type(str(file_path))
            if not media_type:
                continue

            try:
                # Skip if already discovered
                file_path_str = str(file_path.resolve())
                if skip_existing and file_path_str in self.discovered_files:
                    continue

                # Compute file hash
                file_hash = self._compute_file_hash(file_path_str)

                # Check for duplicate
                if file_hash in self.hash_index:
                    logger.debug(f"Duplicate detected: {file_path.name}")

                    content_file = ContentFile(
                        file_path=file_path_str,
                        file_hash=file_hash,
                        file_size=file_path.stat().st_size,
                        media_type=media_type,
                        mime_type=mimetypes.guess_type(file_path_str)[0] or "application/octet-stream",
                        discovered_at=datetime.now(timezone.utc),
                        status=ContentStatus.DUPLICATE
                    )
                    self.discovered_files[file_path_str] = content_file
                    duplicates += 1
                    continue

                # Create content file entry
                content_file = ContentFile(
                    file_path=file_path_str,
                    file_hash=file_hash,
                    file_size=file_path.stat().st_size,
                    media_type=media_type,
                    mime_type=mimetypes.guess_type(file_path_str)[0] or "application/octet-stream",
                    discovered_at=datetime.now(timezone.utc),
                    status=ContentStatus.PENDING
                )

                self.discovered_files[file_path_str] = content_file
                discovered += 1

                logger.debug(f"Discovered: {file_path.name} ({content_file.file_size / (1024*1024):.1f} MB)")

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                errors += 1

        result = {
            "success": True,
            "directory": directory,
            "discovered": discovered,
            "duplicates": duplicates,
            "errors": errors,
            "total_pending": len([f for f in self.discovered_files.values() if f.status == ContentStatus.PENDING])
        }

        logger.success(
            f"✓ Scan complete: {discovered} new, {duplicates} duplicates, {errors} errors"
        )

        # Emit event
        await self.event_bus.publish(
            Topics.CONTENT_DISCOVERED,
            {
                "directory": directory,
                "discovered": discovered,
                "duplicates": duplicates,
                "total_pending": result["total_pending"]
            }
        )

        return result

    async def ingest_file(self, content_file: ContentFile) -> bool:
        """
        Ingest a single content file into database

        Args:
            content_file: ContentFile to ingest

        Returns:
            True if ingestion successful
        """
        try:
            content_file.status = ContentStatus.INGESTING

            # Create Video record
            video_id = str(uuid4())
            video = Video(
                id=video_id,
                user_id=uuid4(),  # TODO: Get from context or config
                source_type="local",
                source_uri=content_file.file_path,
                file_name=Path(content_file.file_path).name,
                title=Path(content_file.file_path).stem,
                file_size=content_file.file_size,
                curation_status="pending"
            )

            self.db.add(video)
            await self.db.commit()
            await self.db.refresh(video)

            # Update content file
            content_file.status = ContentStatus.INGESTED
            content_file.video_id = video_id

            # Add to hash index
            self.hash_index[content_file.file_hash] = content_file.file_path

            logger.info(f"✓ Ingested: {Path(content_file.file_path).name} → {video_id}")

            # Emit event
            await self.event_bus.publish(
                Topics.CONTENT_INGESTED,
                {
                    "video_id": video_id,
                    "file_path": content_file.file_path,
                    "file_hash": content_file.file_hash,
                    "media_type": content_file.media_type,
                    "file_size": content_file.file_size
                }
            )

            return True

        except Exception as e:
            logger.error(f"Error ingesting {content_file.file_path}: {e}")
            content_file.status = ContentStatus.FAILED
            content_file.error_message = str(e)
            await self.db.rollback()
            return False

    async def ingest_pending(
        self,
        max_files: Optional[int] = None,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Ingest all pending content files

        Args:
            max_files: Maximum files to ingest (None = all)
            batch_size: Number of files to commit per batch

        Returns:
            Ingestion results
        """
        pending_files = [
            f for f in self.discovered_files.values()
            if f.status == ContentStatus.PENDING
        ]

        if not pending_files:
            logger.info("No pending files to ingest")
            return {
                "success": True,
                "ingested": 0,
                "failed": 0,
                "total_pending": 0
            }

        logger.info(f"🔄 Ingesting {len(pending_files)} pending files...")

        # Limit if max_files specified
        if max_files:
            pending_files = pending_files[:max_files]

        ingested = 0
        failed = 0

        # Process in batches
        for i in range(0, len(pending_files), batch_size):
            batch = pending_files[i:i+batch_size]

            for content_file in batch:
                success = await self.ingest_file(content_file)
                if success:
                    ingested += 1
                else:
                    failed += 1

            # Small delay between batches
            await asyncio.sleep(0.1)

        result = {
            "success": True,
            "ingested": ingested,
            "failed": failed,
            "total_pending": len([f for f in self.discovered_files.values() if f.status == ContentStatus.PENDING])
        }

        logger.success(f"✓ Ingestion complete: {ingested} ingested, {failed} failed")

        return result

    async def get_status(self) -> Dict[str, Any]:
        """
        Get current status of content sourcing engine

        Returns:
            Status dictionary
        """
        # Count by status
        status_counts = {}
        for content_file in self.discovered_files.values():
            status = content_file.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count total videos in database
        try:
            stmt = select(func.count(Video.id))
            result = await self.db.execute(stmt)
            total_videos = result.scalar()
        except Exception:
            total_videos = 0

        return {
            "is_monitoring": self._is_monitoring,
            "watch_directories": self._watch_dirs,
            "discovered_files": len(self.discovered_files),
            "hash_index_size": len(self.hash_index),
            "status_counts": status_counts,
            "total_videos_in_db": total_videos
        }

    async def start_monitoring(self, directories: List[str]) -> None:
        """
        Start monitoring directories for new files (using polling)

        Note: This is a simple polling-based implementation. For production,
        consider using watchdog library for real-time file system events.

        Args:
            directories: List of directories to monitor
        """
        if self._is_monitoring:
            logger.warning("Already monitoring directories")
            return

        self._is_monitoring = True
        self._watch_dirs = directories

        logger.info(f"👀 Starting directory monitoring: {directories}")

        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitoring_loop())

        logger.success("✓ Directory monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop monitoring directories"""
        if not self._is_monitoring:
            return

        self._is_monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Directory monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """
        Background loop for monitoring directories

        Polls directories every 60 seconds for new files.
        """
        logger.info("🔍 Monitoring loop started")

        while self._is_monitoring:
            try:
                # Scan all watch directories
                for directory in self._watch_dirs:
                    try:
                        await self.scan_directory(directory, recursive=True, skip_existing=True)
                    except Exception as e:
                        logger.error(f"Error scanning {directory}: {e}")

                # Auto-ingest pending files
                pending_count = len([
                    f for f in self.discovered_files.values()
                    if f.status == ContentStatus.PENDING
                ])

                if pending_count > 0:
                    logger.info(f"Auto-ingesting {pending_count} pending files...")
                    await self.ingest_pending()

                # Sleep for 60 seconds
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)

        logger.info("🛑 Monitoring loop stopped")

    def clear_discovered(self, status_filter: Optional[ContentStatus] = None) -> int:
        """
        Clear discovered files from memory

        Args:
            status_filter: Only clear files with this status (None = all)

        Returns:
            Number of files cleared
        """
        if status_filter:
            to_remove = [
                path for path, f in self.discovered_files.items()
                if f.status == status_filter
            ]
            for path in to_remove:
                del self.discovered_files[path]
            count = len(to_remove)
        else:
            count = len(self.discovered_files)
            self.discovered_files.clear()

        logger.info(f"Cleared {count} discovered files")
        return count
