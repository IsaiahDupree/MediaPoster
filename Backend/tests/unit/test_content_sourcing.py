"""
Unit Tests for Content Sourcing Engine (PIPE-001)
=================================================
Tests for content discovery, hash-based deduplication, and ingestion.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from services.content_sourcing_engine import (
    ContentSourcingEngine,
    ContentFile,
    ContentStatus
)


class TestContentSourcingEngine:
    """Test suite for Content Sourcing Engine"""

    @pytest.fixture
    async def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest.fixture
    def temp_media_dir(self):
        """Create temporary directory with test media files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test video file
            video_path = Path(tmpdir) / "test_video.mp4"
            video_path.write_bytes(b"fake video content")

            # Create test image file
            image_path = Path(tmpdir) / "test_image.jpg"
            image_path.write_bytes(b"fake image content")

            # Create non-media file (should be ignored)
            text_path = Path(tmpdir) / "readme.txt"
            text_path.write_text("This should be ignored")

            yield tmpdir

    @pytest.mark.asyncio
    async def test_compute_file_hash(self, mock_db, temp_media_dir):
        """Test file hash computation"""
        engine = ContentSourcingEngine(mock_db)

        video_path = Path(temp_media_dir) / "test_video.mp4"

        # Compute hash
        hash1 = engine._compute_file_hash(str(video_path))

        # Compute again - should be same
        hash2 = engine._compute_file_hash(str(video_path))

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex is 64 chars

    @pytest.mark.asyncio
    async def test_get_media_type(self, mock_db):
        """Test media type detection"""
        engine = ContentSourcingEngine(mock_db)

        # Videos
        assert engine._get_media_type("video.mp4") == "video"
        assert engine._get_media_type("video.mov") == "video"
        assert engine._get_media_type("VIDEO.MP4") == "video"

        # Images
        assert engine._get_media_type("image.jpg") == "image"
        assert engine._get_media_type("image.png") == "image"
        assert engine._get_media_type("IMAGE.JPEG") == "image"

        # Non-media
        assert engine._get_media_type("document.txt") is None
        assert engine._get_media_type("archive.zip") is None

    @pytest.mark.asyncio
    async def test_scan_directory_discovers_media(self, mock_db, temp_media_dir):
        """Test directory scanning discovers media files"""
        engine = ContentSourcingEngine(mock_db)

        # Mock database query to return empty list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Scan directory
        result = await engine.scan_directory(temp_media_dir, recursive=False)

        # Should discover video and image, ignore txt
        assert result["success"] is True
        assert result["discovered"] == 2
        assert result["duplicates"] == 0
        assert result["total_pending"] == 2

        # Check discovered files
        assert len(engine.discovered_files) == 2

        # Find video and image
        video_file = None
        image_file = None

        for file in engine.discovered_files.values():
            if file.media_type == "video":
                video_file = file
            elif file.media_type == "image":
                image_file = file

        assert video_file is not None
        assert image_file is not None
        assert video_file.status == ContentStatus.PENDING
        assert image_file.status == ContentStatus.PENDING

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, mock_db, temp_media_dir):
        """Test hash-based duplicate detection"""
        engine = ContentSourcingEngine(mock_db)

        video_path = Path(temp_media_dir) / "test_video.mp4"

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # First scan
        result1 = await engine.scan_directory(temp_media_dir)
        assert result1["discovered"] == 2

        # Add to hash index manually (simulate already ingested)
        for file in engine.discovered_files.values():
            engine.hash_index[file.file_hash] = file.file_path

        # Clear discovered files
        engine.discovered_files.clear()

        # Second scan - should detect duplicates
        result2 = await engine.scan_directory(temp_media_dir)
        assert result2["discovered"] == 0
        assert result2["duplicates"] == 2

    @pytest.mark.asyncio
    async def test_ingest_file_creates_video_record(self, mock_db, temp_media_dir):
        """Test file ingestion creates Video record"""
        engine = ContentSourcingEngine(mock_db)

        video_path = Path(temp_media_dir) / "test_video.mp4"
        file_hash = engine._compute_file_hash(str(video_path))

        content_file = ContentFile(
            file_path=str(video_path),
            file_hash=file_hash,
            file_size=video_path.stat().st_size,
            media_type="video",
            mime_type="video/mp4",
            discovered_at=datetime.now(timezone.utc),
            status=ContentStatus.PENDING
        )

        # Mock successful database operations
        mock_video = MagicMock()
        mock_video.id = "test-video-id"
        mock_db.refresh.side_effect = lambda obj: setattr(obj, 'id', 'test-video-id')

        # Ingest file
        success = await engine.ingest_file(content_file)

        assert success is True
        assert content_file.status == ContentStatus.INGESTED
        assert content_file.video_id == "test-video-id"
        assert mock_db.add.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_get_status_returns_metrics(self, mock_db):
        """Test status endpoint returns correct metrics"""
        engine = ContentSourcingEngine(mock_db)

        # Add some discovered files
        engine.discovered_files = {
            "file1": ContentFile(
                file_path="/path/file1.mp4",
                file_hash="hash1",
                file_size=1000,
                media_type="video",
                mime_type="video/mp4",
                discovered_at=datetime.now(timezone.utc),
                status=ContentStatus.PENDING
            ),
            "file2": ContentFile(
                file_path="/path/file2.mp4",
                file_hash="hash2",
                file_size=2000,
                media_type="video",
                mime_type="video/mp4",
                discovered_at=datetime.now(timezone.utc),
                status=ContentStatus.INGESTED
            )
        }

        engine.hash_index = {"hash1": "/path/file1.mp4", "hash2": "/path/file2.mp4"}

        # Mock database count query
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100
        mock_db.execute.return_value = mock_result

        # Get status
        status = await engine.get_status()

        assert status["discovered_files"] == 2
        assert status["hash_index_size"] == 2
        assert status["total_videos_in_db"] == 100
        assert status["status_counts"]["pending"] == 1
        assert status["status_counts"]["ingested"] == 1


@pytest.mark.asyncio
async def test_content_file_to_dict():
    """Test ContentFile serialization"""
    content_file = ContentFile(
        file_path="/path/to/video.mp4",
        file_hash="abc123",
        file_size=1024,
        media_type="video",
        mime_type="video/mp4",
        discovered_at=datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc),
        status=ContentStatus.PENDING,
        video_id="video-123"
    )

    data = content_file.to_dict()

    assert data["file_path"] == "/path/to/video.mp4"
    assert data["file_hash"] == "abc123"
    assert data["file_size"] == 1024
    assert data["media_type"] == "video"
    assert data["status"] == "pending"
    assert data["video_id"] == "video-123"
    assert "discovered_at" in data
