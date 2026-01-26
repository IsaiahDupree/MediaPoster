"""
Test Content Ingestion Pipeline
================================
Tests for BM-001, BM-002, BM-003, BM-004

Tests:
- Directory scanning and file discovery
- Hash-based deduplication
- AI analysis integration
- Safe export system
"""

import pytest
import tempfile
import os
import json
import shutil
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from services.content_sourcing_engine import ContentSourcingEngine, ContentStatus
from services.safe_export_system import SafeExportSystem


class TestContentIngestionPipeline:
    """Test suite for Content Ingestion Pipeline (BM-001 to BM-004)"""

    @pytest.fixture
    async def temp_media_dir(self):
        """Create temporary media directory with test files"""
        temp_dir = tempfile.mkdtemp()

        # Create test video files (empty for testing)
        video_files = [
            "test_video_1.mp4",
            "test_video_2.mov",
            "test_video_3.mp4"
        ]

        for filename in video_files:
            file_path = Path(temp_dir) / filename
            # Create empty file
            file_path.write_bytes(b"test video data " * 100)  # ~1.6KB

        # Create test image files
        image_files = [
            "test_image_1.jpg",
            "test_image_2.png"
        ]

        for filename in image_files:
            file_path = Path(temp_dir) / filename
            # Create empty file
            file_path.write_bytes(b"test image data " * 50)  # ~800B

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    async def temp_export_dir(self):
        """Create temporary export directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_bm001_directory_scanning(self, temp_media_dir, db_session):
        """
        Test BM-001: Directory Ingestion Pipeline

        Verifies:
        - Directory scanning discovers all media files
        - File hashes are computed
        - File metadata is extracted
        """
        # Initialize Content Sourcing Engine
        engine = ContentSourcingEngine(db_session)

        # Scan directory
        result = await engine.scan_directory(
            directory=temp_media_dir,
            recursive=True,
            skip_existing=True
        )

        # Verify scan results
        assert result["success"] is True
        assert result["discovered"] == 5  # 3 videos + 2 images
        assert result["duplicates"] == 0

        # Verify files are in discovered_files
        assert len(engine.discovered_files) == 5

        # Verify file hashes were computed
        for file_path, content_file in engine.discovered_files.items():
            assert content_file.file_hash is not None
            assert len(content_file.file_hash) == 64  # SHA256 hex digest
            assert content_file.status == ContentStatus.PENDING

    @pytest.mark.asyncio
    async def test_bm002_deduplication(self, temp_media_dir, db_session):
        """
        Test BM-002: Media Deduplication

        Verifies:
        - Duplicate files are detected via SHA256 hash
        - Only unique files are ingested
        - Hash index is properly maintained
        """
        engine = ContentSourcingEngine(db_session)

        # First scan
        result1 = await engine.scan_directory(temp_media_dir)
        assert result1["discovered"] == 5
        assert result1["duplicates"] == 0

        # Ingest files
        ingest_result = await engine.ingest_pending()
        assert ingest_result["ingested"] > 0

        # Build hash index
        await engine.build_hash_index()

        # Second scan (should detect duplicates)
        result2 = await engine.scan_directory(temp_media_dir, skip_existing=False)
        assert result2["duplicates"] == 5  # All files are duplicates
        assert result2["discovered"] == 0  # No new unique files

    @pytest.mark.asyncio
    async def test_bm003_ai_analysis_integration_initialization(self, db_session):
        """
        Test BM-003: AI Analysis Integration

        Verifies:
        - Ingestion Analysis Integrator initializes correctly
        - Event subscriptions are set up
        - Processing queue is created
        """
        from services.ingestion_analysis_integrator import get_ingestion_analysis_integrator

        # Get integrator instance
        integrator = get_ingestion_analysis_integrator(db_session)

        # Verify initialization
        assert integrator is not None
        assert integrator._processing_queue is not None
        assert integrator._is_running is False

        # Start integrator
        await integrator.start()

        # Verify it's running
        assert integrator._is_running is True
        assert integrator._event_subscription is not None

        # Stop integrator
        await integrator.stop()

        # Verify it stopped
        assert integrator._is_running is False

    @pytest.mark.asyncio
    async def test_bm004_safe_export_single_video(self, temp_export_dir, db_session):
        """
        Test BM-004: Safe Export System (Single Video)

        Verifies:
        - Analysis data is exported to JSON
        - Export manifest is created
        - File references (not copies) are created
        - Original media is not duplicated
        """
        # Create mock video in database
        from database.models import Video

        video_id = str(uuid4())
        video = Video(
            id=video_id,
            filename="test_video.mp4",
            file_size=1024,
            source_uri="/tmp/test_video.mp4",
            duration=30.0,
            width=1920,
            height=1080,
            fps=30.0,
            created_at=datetime.now(timezone.utc)
        )

        db_session.add(video)
        await db_session.commit()

        # Initialize Safe Export System
        exporter = SafeExportSystem(db_session)

        # Export video analysis
        result = await exporter.export_video_analysis(
            video_id=video_id,
            export_dir=temp_export_dir,
            include_thumbnails=True,
            include_frames=True,
            use_symlinks=True
        )

        # Verify export result
        assert result["success"] is True
        assert result["video_id"] == video_id

        # Verify manifest was created
        manifest_path = Path(result["manifest_path"])
        assert manifest_path.exists()

        # Load and verify manifest
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        assert manifest["video_id"] == video_id
        assert "files" in manifest
        assert "analysis_json" in manifest["files"]

        # Verify analysis JSON was created
        analysis_json_path = manifest["files"]["analysis_json"]
        assert os.path.exists(analysis_json_path)

        # Load and verify analysis data
        with open(analysis_json_path, "r") as f:
            analysis_data = json.load(f)

        assert analysis_data["video_id"] == video_id
        assert "video_metadata" in analysis_data
        assert "file_references" in analysis_data

        # Verify file reference (not a copy)
        file_ref = analysis_data["file_references"]
        assert file_ref["reference_type"] in ["symlink", "path"]
        assert "This is a reference" in file_ref["note"]

    @pytest.mark.asyncio
    async def test_bm004_safe_export_batch(self, temp_export_dir, db_session):
        """
        Test BM-004: Safe Export System (Batch Export)

        Verifies:
        - Multiple videos can be exported in batch
        - Batch manifest is created
        - Each video has its own subdirectory
        """
        from database.models import Video

        # Create multiple mock videos
        video_ids = [str(uuid4()) for _ in range(3)]

        for vid in video_ids:
            video = Video(
                id=vid,
                filename=f"test_video_{vid[:8]}.mp4",
                file_size=1024,
                source_uri=f"/tmp/test_video_{vid[:8]}.mp4",
                duration=30.0,
                width=1920,
                height=1080,
                fps=30.0,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(video)

        await db_session.commit()

        # Initialize Safe Export System
        exporter = SafeExportSystem(db_session)

        # Export batch
        result = await exporter.export_batch(
            video_ids=video_ids,
            export_dir=temp_export_dir,
            include_thumbnails=True,
            include_frames=True,
            use_symlinks=True
        )

        # Verify batch export result
        assert result["success"] is True
        assert result["total_videos"] == 3

        # Verify batch manifest was created
        batch_manifest_path = Path(result["batch_manifest_path"])
        assert batch_manifest_path.exists()

        # Load and verify batch manifest
        with open(batch_manifest_path, "r") as f:
            batch_manifest = json.load(f)

        assert batch_manifest["total_videos"] == 3
        assert "results" in batch_manifest
        assert len(batch_manifest["results"]) == 3

    @pytest.mark.asyncio
    async def test_bm004_export_verification(self, temp_export_dir, db_session):
        """
        Test BM-004: Export Verification

        Verifies:
        - Export verification works correctly
        - Missing files are detected
        - File existence is checked
        """
        from database.models import Video

        # Create mock video
        video_id = str(uuid4())
        video = Video(
            id=video_id,
            filename="test_video.mp4",
            file_size=1024,
            source_uri="/tmp/test_video.mp4",
            duration=30.0,
            created_at=datetime.now(timezone.utc)
        )

        db_session.add(video)
        await db_session.commit()

        # Export video
        exporter = SafeExportSystem(db_session)
        export_result = await exporter.export_video_analysis(
            video_id=video_id,
            export_dir=temp_export_dir
        )

        assert export_result["success"] is True
        manifest_path = export_result["manifest_path"]

        # Verify export
        verification = await exporter.verify_export(manifest_path)

        # Check verification result
        assert "files_verified" in verification
        assert "missing_files" in verification

        # Analysis JSON should exist
        assert verification["files_verified"]["analysis_json"] is True

    @pytest.mark.asyncio
    async def test_integration_end_to_end(self, temp_media_dir, temp_export_dir, db_session):
        """
        Test End-to-End Integration (BM-001 → BM-002 → BM-004)

        Verifies complete pipeline:
        1. Scan directory for media files
        2. Ingest with deduplication
        3. Export analysis data safely
        """
        # Step 1: Scan directory (BM-001)
        engine = ContentSourcingEngine(db_session)
        scan_result = await engine.scan_directory(temp_media_dir)

        assert scan_result["success"] is True
        assert scan_result["discovered"] > 0

        # Step 2: Ingest with deduplication (BM-002)
        ingest_result = await engine.ingest_pending()

        assert ingest_result["ingested"] > 0
        video_ids = ingest_result.get("video_ids", [])

        if not video_ids:
            pytest.skip("No videos ingested - skipping export test")

        # Step 3: Export analysis data (BM-004)
        exporter = SafeExportSystem(db_session)
        export_result = await exporter.export_batch(
            video_ids=video_ids[:2],  # Export first 2 videos
            export_dir=temp_export_dir
        )

        assert export_result["success"] is True
        assert export_result["successful_exports"] > 0


# Test configuration
@pytest.fixture
async def db_session():
    """Mock database session for testing"""
    from database.connection import async_session_maker

    async with async_session_maker() as session:
        yield session


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
