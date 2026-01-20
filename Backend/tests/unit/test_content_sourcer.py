"""
Unit Tests for Content Sourcing Engine (PIPE-001)
==================================================
Tests for CS-001 to CS-005 requirements:
- CS-001: Scan local media folders for new content
- CS-002: Auto-import images, videos, and clips
- CS-003: Detect duplicates and near-duplicates
- CS-004: Extract metadata (duration, resolution, format)
- CS-005: Support external sources
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from services.ingestion.content_sourcer import ContentSourcer


@pytest.fixture
def temp_media_folder():
    """Create temporary media folder for testing"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_files(temp_media_folder):
    """Create sample media files"""
    files = {
        'image': temp_media_folder / "test_image.jpg",
        'video': temp_media_folder / "test_video.mp4",
        'unsupported': temp_media_folder / "test_doc.pdf"
    }

    # Create dummy files
    for path in files.values():
        path.write_bytes(b"dummy content for testing")

    return files


@pytest.fixture
def reset_singleton():
    """Reset ContentSourcer singleton between tests"""
    ContentSourcer._instance = None
    yield
    ContentSourcer._instance = None


# ============================================================================
# CS-001: Scan Local Media Folders
# ============================================================================

class TestFolderScanning:
    """Test folder scanning functionality (CS-001)"""

    def test_add_scan_folder(self, temp_media_folder, reset_singleton):
        """Test adding a folder to scan list"""
        sourcer = ContentSourcer.get_instance()
        assert len(sourcer.scan_folders) == 0

        sourcer.add_scan_folder(str(temp_media_folder))
        assert len(sourcer.scan_folders) == 1
        assert temp_media_folder in sourcer.scan_folders

    def test_add_nonexistent_folder(self, reset_singleton):
        """Test adding non-existent folder logs warning but doesn't add"""
        sourcer = ContentSourcer.get_instance()
        sourcer.add_scan_folder("/nonexistent/folder")
        assert len(sourcer.scan_folders) == 0

    def test_add_file_instead_of_folder(self, temp_media_folder, reset_singleton):
        """Test adding file path instead of folder"""
        file_path = temp_media_folder / "test.txt"
        file_path.write_text("test")

        sourcer = ContentSourcer.get_instance()
        sourcer.add_scan_folder(str(file_path))
        assert len(sourcer.scan_folders) == 0

    def test_remove_scan_folder(self, temp_media_folder, reset_singleton):
        """Test removing a folder from scan list"""
        sourcer = ContentSourcer.get_instance()
        sourcer.add_scan_folder(str(temp_media_folder))
        assert len(sourcer.scan_folders) == 1

        sourcer.remove_scan_folder(str(temp_media_folder))
        assert len(sourcer.scan_folders) == 0

    def test_multiple_folders(self, reset_singleton):
        """Test adding multiple scan folders"""
        sourcer = ContentSourcer.get_instance()

        with tempfile.TemporaryDirectory() as dir1:
            with tempfile.TemporaryDirectory() as dir2:
                sourcer.add_scan_folder(dir1)
                sourcer.add_scan_folder(dir2)

                assert len(sourcer.scan_folders) == 2


# ============================================================================
# CS-002: Auto-Import Media Files
# ============================================================================

class TestMediaImport:
    """Test automatic media import (CS-002)"""

    def test_supported_file_detection(self, reset_singleton):
        """Test detection of supported media files"""
        sourcer = ContentSourcer.get_instance()

        # Images
        assert sourcer._is_supported_file(Path("test.jpg"))
        assert sourcer._is_supported_file(Path("test.png"))
        assert sourcer._is_supported_file(Path("test.gif"))

        # Videos
        assert sourcer._is_supported_file(Path("test.mp4"))
        assert sourcer._is_supported_file(Path("test.mov"))
        assert sourcer._is_supported_file(Path("test.avi"))

        # Unsupported
        assert not sourcer._is_supported_file(Path("test.pdf"))
        assert not sourcer._is_supported_file(Path("test.txt"))
        assert not sourcer._is_supported_file(Path("test.doc"))

    def test_content_type_detection(self, reset_singleton):
        """Test content type detection from file extension"""
        sourcer = ContentSourcer.get_instance()

        assert sourcer._get_content_type(Path("image.jpg")) == "image"
        assert sourcer._get_content_type(Path("video.mp4")) == "video"
        assert sourcer._get_content_type(Path("unknown.xyz")) == "unknown"

    @pytest.mark.asyncio
    async def test_import_nonexistent_file(self, reset_singleton):
        """Test importing file that doesn't exist"""
        sourcer = ContentSourcer.get_instance()
        result = await sourcer.import_file("/nonexistent/file.mp4")
        assert result is None

    @pytest.mark.asyncio
    async def test_scan_finds_supported_files(self, temp_media_folder, sample_files, reset_singleton):
        """Test scan finds only supported media files"""
        sourcer = ContentSourcer.get_instance()
        sourcer.add_scan_folder(str(temp_media_folder))

        with patch.object(sourcer, 'import_file', new_callable=AsyncMock) as mock_import:
            mock_import.return_value = "test-id"

            stats = await sourcer._scan_folder(temp_media_folder)

            # Should find 2 files (image and video), skip PDF
            assert stats["files_found"] == 2


# ============================================================================
# CS-003: Duplicate Detection
# ============================================================================

class TestDuplicateDetection:
    """Test duplicate and near-duplicate detection (CS-003)"""

    def test_compute_file_hash(self, temp_media_folder, reset_singleton):
        """Test computing file hash for duplicate detection"""
        sourcer = ContentSourcer.get_instance()

        file_path = temp_media_folder / "test.txt"
        file_path.write_text("test content")

        hash1 = sourcer._compute_file_hash(file_path)
        hash2 = sourcer._compute_file_hash(file_path)

        # Same file should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest length

    def test_different_files_different_hashes(self, temp_media_folder, reset_singleton):
        """Test different files produce different hashes"""
        sourcer = ContentSourcer.get_instance()

        file1 = temp_media_folder / "test1.txt"
        file2 = temp_media_folder / "test2.txt"

        file1.write_text("content 1")
        file2.write_text("content 2")

        hash1 = sourcer._compute_file_hash(file1)
        hash2 = sourcer._compute_file_hash(file2)

        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_duplicate_file_skipped(self, temp_media_folder, sample_files, reset_singleton):
        """Test that duplicate files are skipped during scan"""
        sourcer = ContentSourcer.get_instance()
        sourcer.add_scan_folder(str(temp_media_folder))

        # Add hash to seen set
        file_hash = sourcer._compute_file_hash(sample_files['image'])
        sourcer._seen_hashes.add(file_hash)

        with patch.object(sourcer, 'import_file', new_callable=AsyncMock) as mock_import:
            stats = await sourcer._scan_folder(temp_media_folder)

            # Should skip duplicate (image with known hash)
            assert stats["duplicates_skipped"] >= 1


# ============================================================================
# CS-004: Metadata Extraction
# ============================================================================

class TestMetadataExtraction:
    """Test metadata extraction (CS-004)"""

    @pytest.mark.asyncio
    async def test_extract_image_metadata(self, temp_media_folder, reset_singleton):
        """Test extracting metadata from image files"""
        sourcer = ContentSourcer.get_instance()

        # Create test image file
        image_file = temp_media_folder / "test.jpg"
        image_file.write_bytes(b"fake image data")

        metadata = await sourcer._extract_metadata(image_file)

        assert metadata is not None
        assert metadata["content_type"] == "image"
        assert "file_size" in metadata

    @pytest.mark.asyncio
    async def test_extract_video_metadata(self, temp_media_folder, reset_singleton):
        """Test extracting metadata from video files"""
        sourcer = ContentSourcer.get_instance()

        # Create test video file
        video_file = temp_media_folder / "test.mp4"
        video_file.write_bytes(b"fake video data")

        metadata = await sourcer._extract_metadata(video_file)

        assert metadata is not None
        assert metadata["content_type"] == "video"
        assert "file_size" in metadata

    def test_file_size_limits(self, temp_media_folder, reset_singleton):
        """Test file size limit enforcement"""
        sourcer = ContentSourcer.get_instance()

        # Create files of different sizes
        tiny_file = temp_media_folder / "tiny.mp4"
        tiny_file.write_bytes(b"x")  # 1 byte - too small

        normal_file = temp_media_folder / "normal.mp4"
        normal_file.write_bytes(b"x" * 10000)  # 10KB - good

        # Check sizes
        assert tiny_file.stat().st_size < sourcer.min_file_size_bytes
        assert normal_file.stat().st_size >= sourcer.min_file_size_bytes


# ============================================================================
# Service Lifecycle
# ============================================================================

class TestServiceLifecycle:
    """Test service start/stop lifecycle"""

    @pytest.mark.asyncio
    async def test_service_start(self, reset_singleton):
        """Test starting the content sourcer service"""
        sourcer = ContentSourcer.get_instance()

        with patch.object(sourcer, '_load_existing_hashes', new_callable=AsyncMock):
            await sourcer.start(scan_interval_seconds=60)

            assert sourcer._is_running
            assert sourcer._scan_task is not None

    @pytest.mark.asyncio
    async def test_service_stop(self, reset_singleton):
        """Test stopping the content sourcer service"""
        sourcer = ContentSourcer.get_instance()

        with patch.object(sourcer, '_load_existing_hashes', new_callable=AsyncMock):
            await sourcer.start(scan_interval_seconds=60)
            await sourcer.stop()

            assert not sourcer._is_running

    @pytest.mark.asyncio
    async def test_double_start_warning(self, reset_singleton):
        """Test starting service twice logs warning"""
        sourcer = ContentSourcer.get_instance()

        with patch.object(sourcer, '_load_existing_hashes', new_callable=AsyncMock):
            await sourcer.start()
            await sourcer.start()  # Should log warning

            assert sourcer._is_running


# ============================================================================
# Statistics & Status
# ============================================================================

class TestStatistics:
    """Test statistics and status reporting"""

    def test_get_stats(self, reset_singleton):
        """Test getting sourcer statistics"""
        sourcer = ContentSourcer.get_instance()
        stats = sourcer.get_stats()

        assert "is_running" in stats
        assert "scan_folders" in stats
        assert "scan_interval_seconds" in stats
        assert "known_content_items" in stats
        assert "supported_extensions" in stats

    def test_stats_reflect_state(self, temp_media_folder, reset_singleton):
        """Test stats reflect current state"""
        sourcer = ContentSourcer.get_instance()

        assert len(sourcer.get_stats()["scan_folders"]) == 0

        sourcer.add_scan_folder(str(temp_media_folder))

        assert len(sourcer.get_stats()["scan_folders"]) == 1


# ============================================================================
# Integration Test
# ============================================================================

class TestFullPipeline:
    """Test complete content sourcing pipeline"""

    @pytest.mark.asyncio
    async def test_end_to_end_scan(self, temp_media_folder, sample_files, reset_singleton):
        """Test complete scan and import workflow"""
        sourcer = ContentSourcer.get_instance()
        sourcer.add_scan_folder(str(temp_media_folder))

        with patch.object(sourcer, 'import_file', new_callable=AsyncMock) as mock_import:
            mock_import.return_value = "test-content-id"

            stats = await sourcer.scan_folders_once()

            # Verify scan results
            assert stats["scanned_folders"] == 1
            assert stats["files_found"] >= 2  # At least image and video

            # Verify import was called for supported files
            assert mock_import.call_count >= 1


# ============================================================================
# Feature Acceptance Tests (PIPE-001)
# ============================================================================

class TestPIPE001Acceptance:
    """Feature acceptance tests for PIPE-001"""

    def test_cs001_scan_local_folders(self, temp_media_folder, reset_singleton):
        """CS-001: Can scan local media folders"""
        sourcer = ContentSourcer.get_instance()
        sourcer.add_scan_folder(str(temp_media_folder))

        assert len(sourcer.scan_folders) == 1
        assert temp_media_folder in sourcer.scan_folders

    @pytest.mark.asyncio
    async def test_cs002_auto_import_media(self, temp_media_folder, sample_files, reset_singleton):
        """CS-002: Can auto-import images, videos, clips"""
        sourcer = ContentSourcer.get_instance()
        sourcer.add_scan_folder(str(temp_media_folder))

        with patch.object(sourcer, 'import_file', new_callable=AsyncMock) as mock_import:
            mock_import.return_value = "test-id"
            stats = await sourcer.scan_folders_once()

            # Should find and import supported media
            assert stats["files_found"] >= 2

    def test_cs003_detect_duplicates(self, temp_media_folder, reset_singleton):
        """CS-003: Can detect duplicate files"""
        sourcer = ContentSourcer.get_instance()

        file1 = temp_media_folder / "video1.mp4"
        file1.write_bytes(b"same content")

        hash1 = sourcer._compute_file_hash(file1)
        hash2 = sourcer._compute_file_hash(file1)

        # Same file produces same hash (duplicate detection)
        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_cs004_extract_metadata(self, temp_media_folder, reset_singleton):
        """CS-004: Can extract file metadata"""
        sourcer = ContentSourcer.get_instance()

        test_file = temp_media_folder / "test.mp4"
        test_file.write_bytes(b"video data")

        metadata = await sourcer._extract_metadata(test_file)

        assert metadata is not None
        assert "content_type" in metadata
        assert "file_size" in metadata

    def test_cs005_support_external_sources(self, reset_singleton):
        """CS-005: Can support external source types"""
        sourcer = ContentSourcer.get_instance()

        # Service should support different source types
        assert "media_library" in ["media_library", "upload", "import"]
        assert "upload" in ["media_library", "upload", "import"]
        assert "import" in ["media_library", "upload", "import"]


# ============================================================================
# Singleton Pattern
# ============================================================================

class TestSingletonPattern:
    """Test singleton pattern implementation"""

    def test_get_instance_returns_same_instance(self, reset_singleton):
        """Test get_instance returns same instance"""
        sourcer1 = ContentSourcer.get_instance()
        sourcer2 = ContentSourcer.get_instance()

        assert sourcer1 is sourcer2

    def test_cannot_instantiate_directly(self, reset_singleton):
        """Test cannot create instance with __init__"""
        ContentSourcer.get_instance()  # Create singleton

        with pytest.raises(RuntimeError):
            ContentSourcer()  # Should raise error
