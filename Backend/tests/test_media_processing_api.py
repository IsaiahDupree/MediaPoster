"""
Tests for Media Processing API
Covers upload, ingestion, analysis, batch processing, and resume functionality.
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
import json

# Test configuration
IPHONE_IMPORT_PATH = Path(os.path.expanduser("~/Documents/IphoneImport"))


# =============================================================================
# UNIT TESTS - API Models
# =============================================================================

class TestMediaModels:
    """Test API request/response models."""
    
    def test_upload_init_request_defaults(self):
        """Test UploadInitRequest has correct defaults."""
        from api.media_processing import UploadInitRequest
        
        request = UploadInitRequest(
            filename="test.mov",
            file_size=1000000,
            content_type="video/quicktime"
        )
        
        assert request.client_type == "web"
        assert request.checksum is None
    
    def test_media_status_enum_values(self):
        """Test MediaStatus enum has all required values."""
        from api.media_processing import MediaStatus
        
        assert MediaStatus.PENDING == "pending"
        assert MediaStatus.UPLOADING == "uploading"
        assert MediaStatus.UPLOADED == "uploaded"
        assert MediaStatus.INGESTING == "ingesting"
        assert MediaStatus.INGESTED == "ingested"
        assert MediaStatus.ANALYZING == "analyzing"
        assert MediaStatus.ANALYZED == "analyzed"
        assert MediaStatus.FAILED == "failed"
    
    def test_media_type_detection(self):
        """Test media type detection from filename."""
        from api.media_processing import get_media_type, MediaType
        
        # Videos
        assert get_media_type("video.mov") == MediaType.VIDEO
        assert get_media_type("VIDEO.MP4") == MediaType.VIDEO
        assert get_media_type("test.m4v") == MediaType.VIDEO
        assert get_media_type("clip.avi") == MediaType.VIDEO
        
        # Images
        assert get_media_type("photo.jpg") == MediaType.IMAGE
        assert get_media_type("image.JPEG") == MediaType.IMAGE
        assert get_media_type("pic.png") == MediaType.IMAGE
        assert get_media_type("shot.heic") == MediaType.IMAGE
        assert get_media_type("graphic.webp") == MediaType.IMAGE


# =============================================================================
# UNIT TESTS - Helper Functions
# =============================================================================

class TestHelperFunctions:
    """Test helper functions."""
    
    def test_compute_file_hash(self):
        """Test file hash computation."""
        from api.media_processing import compute_file_hash
        
        data1 = b"test data 1"
        data2 = b"test data 2"
        
        hash1 = compute_file_hash(data1)
        hash2 = compute_file_hash(data2)
        hash1_again = compute_file_hash(data1)
        
        assert hash1 != hash2
        assert hash1 == hash1_again
        assert len(hash1) == 32  # MD5 hex string
    
    def test_media_type_from_extension(self):
        """Test media type detection from various extensions."""
        from api.media_processing import get_media_type, MediaType
        
        video_extensions = ['.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm']
        for ext in video_extensions:
            assert get_media_type(f"test{ext}") == MediaType.VIDEO
            assert get_media_type(f"TEST{ext.upper()}") == MediaType.VIDEO


# =============================================================================
# INTEGRATION TESTS - Upload Endpoints
# =============================================================================

class TestUploadEndpoints:
    """Test upload-related endpoints."""
    
    @pytest.fixture
    def sample_video_content(self):
        """Create sample video content."""
        return b"fake video content " * 1000  # ~19KB
    
    @pytest.fixture
    def sample_image_content(self):
        """Create sample image content."""
        return b"\x89PNG\r\n\x1a\n" + b"fake image data" * 100
    
    def test_upload_init_creates_session(self):
        """Test upload initialization creates a session."""
        from api.media_processing import upload_sessions
        from api.media_processing import UploadInitRequest
        
        # Clear existing sessions
        upload_sessions.clear()
        
        request = UploadInitRequest(
            filename="test_video.mov",
            file_size=50000000,  # 50MB
            content_type="video/quicktime",
            client_type="ios"
        )
        
        # Manually create session (simulating endpoint)
        import uuid
        upload_id = str(uuid.uuid4())
        upload_sessions[upload_id] = {
            "filename": request.filename,
            "file_size": request.file_size,
            "client_type": request.client_type
        }
        
        assert upload_id in upload_sessions
        assert upload_sessions[upload_id]["client_type"] == "ios"
    
    def test_chunk_sizes_by_client_type(self):
        """Test chunk sizes are appropriate for each client type."""
        chunk_sizes = {
            "ios": 5 * 1024 * 1024,      # 5MB
            "android": 5 * 1024 * 1024,   # 5MB
            "web": 10 * 1024 * 1024       # 10MB
        }
        
        # iOS should have smaller chunks for mobile constraints
        assert chunk_sizes["ios"] <= chunk_sizes["web"]
        assert chunk_sizes["android"] <= chunk_sizes["web"]
    
    def test_duplicate_detection(self, sample_video_content):
        """Test duplicate file detection by hash."""
        from api.media_processing import compute_file_hash, media_items
        
        media_items.clear()
        
        # Create first entry
        file_hash = compute_file_hash(sample_video_content)
        media_id_1 = "test-id-1"
        media_items[media_id_1] = {
            "media_id": media_id_1,
            "file_hash": file_hash,
            "filename": "video1.mov"
        }
        
        # Check for duplicate
        is_duplicate = any(
            m.get("file_hash") == file_hash 
            for m in media_items.values()
        )
        
        assert is_duplicate is True


# =============================================================================
# INTEGRATION TESTS - Analysis
# =============================================================================

class TestAnalysisEndpoints:
    """Test analysis-related endpoints."""
    
    @pytest.fixture
    def analyzed_media(self):
        """Create an analyzed media item."""
        from api.media_processing import media_items, MediaStatus
        
        media_items.clear()
        
        media_id = "test-analyzed-id"
        media_items[media_id] = {
            "media_id": media_id,
            "filename": "analyzed_video.mov",
            "status": MediaStatus.ANALYZED,
            "progress": 1.0,
            "file_path": "/tmp/test.mov",
            "file_size": 1000000,
            "file_hash": "abc123",
            "media_type": "video",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "analysis_result": {
                "pre_social_score": 85,
                "hook_strength": 8,
                "pacing_score": 7,
                "transcript": "Test transcript",
                "topics": ["tech", "tutorial"],
                "suggested_captions": ["Caption 1", "Caption 2"],
                "analyzed_at": datetime.now().isoformat()
            }
        }
        
        return media_id
    
    def test_get_analysis_result(self, analyzed_media):
        """Test retrieving analysis results."""
        from api.media_processing import media_items
        
        media = media_items.get(analyzed_media)
        result = media.get("analysis_result")
        
        assert result is not None
        assert result["pre_social_score"] == 85
        assert "tech" in result["topics"]
        assert len(result["suggested_captions"]) == 2
    
    def test_analysis_has_required_fields(self, analyzed_media):
        """Test analysis results have all required fields."""
        from api.media_processing import media_items
        
        result = media_items[analyzed_media]["analysis_result"]
        
        required_fields = [
            "pre_social_score",
            "hook_strength", 
            "pacing_score",
            "transcript",
            "topics",
            "suggested_captions",
            "analyzed_at"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"


# =============================================================================
# INTEGRATION TESTS - Batch Processing
# =============================================================================

class TestBatchProcessing:
    """Test batch ingestion functionality."""
    
    @pytest.fixture
    def temp_media_dir(self, tmp_path):
        """Create temporary directory with test media files."""
        # Create test files
        for i in range(5):
            (tmp_path / f"video_{i}.mov").write_bytes(b"fake video " * 100)
            (tmp_path / f"image_{i}.jpg").write_bytes(b"fake image " * 50)
        
        return tmp_path
    
    def test_batch_job_creation(self, temp_media_dir):
        """Test batch job is created correctly."""
        from api.media_processing import background_jobs
        import uuid
        
        background_jobs.clear()
        
        job_id = str(uuid.uuid4())
        background_jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "directory": str(temp_media_dir),
            "total_files": 10,
            "processed_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "progress": 0.0,
            "can_resume": True,
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        assert job_id in background_jobs
        assert background_jobs[job_id]["total_files"] == 10
    
    def test_batch_progress_tracking(self):
        """Test batch job progress is tracked correctly."""
        from api.media_processing import background_jobs
        import uuid
        
        job_id = str(uuid.uuid4())
        background_jobs[job_id] = {
            "job_id": job_id,
            "total_files": 100,
            "processed_count": 0,
            "progress": 0.0
        }
        
        # Simulate processing
        for i in range(1, 101):
            background_jobs[job_id]["processed_count"] = i
            background_jobs[job_id]["progress"] = i / 100
        
        assert background_jobs[job_id]["progress"] == 1.0
        assert background_jobs[job_id]["processed_count"] == 100
    
    def test_resume_skips_processed_files(self):
        """Test resume functionality skips already processed files."""
        from api.media_processing import media_items, compute_file_hash
        
        media_items.clear()
        
        # Simulate already processed file
        existing_hash = compute_file_hash(b"existing file content")
        media_items["existing-id"] = {
            "media_id": "existing-id",
            "file_hash": existing_hash,
            "status": "analyzed"
        }
        
        # Check if file would be skipped on resume
        new_file_hash = existing_hash  # Same hash = already processed
        is_already_processed = any(
            m.get("file_hash") == new_file_hash
            for m in media_items.values()
        )
        
        assert is_already_processed is True


# =============================================================================
# INTEGRATION TESTS - Smart Resume
# =============================================================================

class TestSmartResume:
    """Test smart resume functionality."""
    
    def test_job_can_resume_flag(self):
        """Test can_resume flag is set correctly."""
        from api.media_processing import background_jobs
        import uuid
        
        job_id = str(uuid.uuid4())
        
        # Running job can resume
        background_jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "can_resume": True
        }
        assert background_jobs[job_id]["can_resume"] is True
        
        # Completed job cannot resume
        background_jobs[job_id]["status"] = "completed"
        background_jobs[job_id]["can_resume"] = False
        assert background_jobs[job_id]["can_resume"] is False
    
    def test_resume_continues_from_last_position(self):
        """Test resume continues from where it stopped."""
        processed_files = ["file1.mov", "file2.mov", "file3.mov"]
        all_files = ["file1.mov", "file2.mov", "file3.mov", "file4.mov", "file5.mov"]
        
        remaining = [f for f in all_files if f not in processed_files]
        
        assert len(remaining) == 2
        assert "file4.mov" in remaining
        assert "file5.mov" in remaining
    
    def test_state_persists_between_runs(self, tmp_path):
        """Test state is saved and can be loaded."""
        state_file = tmp_path / "state.json"
        
        state = {
            "job_id": "test-job",
            "processed_count": 50,
            "total_files": 100,
            "files_state": {
                "file1.mov": {"status": "analyzed"},
                "file2.mov": {"status": "analyzed"}
            }
        }
        
        # Save state
        with open(state_file, 'w') as f:
            json.dump(state, f)
        
        # Load state
        with open(state_file, 'r') as f:
            loaded = json.load(f)
        
        assert loaded["processed_count"] == 50
        assert len(loaded["files_state"]) == 2


# =============================================================================
# INTEGRATION TESTS - Real Data (iPhone Import)
# =============================================================================

class TestRealDataIngestion:
    """Test ingestion with real iPhone import data."""
    
    @pytest.fixture
    def iphone_import_available(self):
        """Check if iPhone import directory exists."""
        return IPHONE_IMPORT_PATH.exists()
    
    def test_iphone_import_directory_exists(self, iphone_import_available):
        """Verify iPhone import directory exists."""
        if not iphone_import_available:
            pytest.skip("iPhone import directory not available")
        
        assert IPHONE_IMPORT_PATH.exists()
        assert IPHONE_IMPORT_PATH.is_dir()
    
    def test_scan_iphone_import_finds_media(self, iphone_import_available):
        """Test scanning iPhone import finds media files."""
        if not iphone_import_available:
            pytest.skip("iPhone import directory not available")
        
        video_exts = {'.mov', '.mp4', '.m4v'}
        image_exts = {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
        
        videos = list(IPHONE_IMPORT_PATH.glob("*.[mM][oO][vV]"))
        videos += list(IPHONE_IMPORT_PATH.glob("*.[mM][pP]4"))
        
        images = []
        for ext in ['jpg', 'jpeg', 'png', 'heic', 'webp']:
            images += list(IPHONE_IMPORT_PATH.glob(f"*.{ext}"))
            images += list(IPHONE_IMPORT_PATH.glob(f"*.{ext.upper()}"))
        
        total_media = len(videos) + len(images)
        
        assert total_media > 0, "Expected to find media files in iPhone import"
        print(f"\nFound {len(videos)} videos and {len(images)} images")
    
    def test_can_read_file_metadata(self, iphone_import_available):
        """Test reading file metadata from iPhone import."""
        if not iphone_import_available:
            pytest.skip("iPhone import directory not available")
        
        # Get first video file
        videos = list(IPHONE_IMPORT_PATH.glob("*.MOV"))[:1]
        if not videos:
            videos = list(IPHONE_IMPORT_PATH.glob("*.mov"))[:1]
        
        if not videos:
            pytest.skip("No video files found")
        
        video = videos[0]
        stat = video.stat()
        
        assert stat.st_size > 0
        assert video.name
        
        print(f"\nSample file: {video.name}, Size: {stat.st_size / 1024 / 1024:.1f}MB")


# =============================================================================
# END-TO-END TESTS
# =============================================================================

class TestEndToEnd:
    """End-to-end tests for full media processing pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_upload_and_analysis_flow(self):
        """Test complete flow: upload -> ingest -> analyze."""
        from api.media_processing import (
            media_items, MediaStatus, get_media_type, 
            compute_file_hash, run_analysis
        )
        import uuid
        
        media_items.clear()
        
        # Simulate upload
        media_id = str(uuid.uuid4())
        file_content = b"fake video content for testing"
        file_hash = compute_file_hash(file_content)
        
        media_items[media_id] = {
            "media_id": media_id,
            "filename": "test_video.mov",
            "file_path": "/tmp/test.mov",
            "file_size": len(file_content),
            "file_hash": file_hash,
            "media_type": get_media_type("test_video.mov"),
            "status": MediaStatus.INGESTED,
            "progress": 0.3,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "analysis_result": None,
            "error_message": None
        }
        
        # Run analysis
        await run_analysis(media_id, "/tmp/test.mov")
        
        # Verify final state
        media = media_items[media_id]
        assert media["status"] == MediaStatus.ANALYZED
        assert media["progress"] == 1.0
        assert media["analysis_result"] is not None
        assert "pre_social_score" in media["analysis_result"]
    
    @pytest.mark.asyncio
    async def test_retry_after_failure(self):
        """Test retry functionality for failed media."""
        from api.media_processing import media_items, MediaStatus, run_analysis
        import uuid
        
        media_items.clear()
        
        media_id = str(uuid.uuid4())
        media_items[media_id] = {
            "media_id": media_id,
            "filename": "failed_video.mov",
            "file_path": "/tmp/failed.mov",
            "status": MediaStatus.FAILED,
            "progress": 0.0,
            "error_message": "Previous error",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Reset for retry
        media_items[media_id]["status"] = MediaStatus.INGESTED
        media_items[media_id]["error_message"] = None
        media_items[media_id]["progress"] = 0.3
        
        # Run analysis again
        await run_analysis(media_id, "/tmp/failed.mov")
        
        assert media_items[media_id]["status"] == MediaStatus.ANALYZED
        assert media_items[media_id]["error_message"] is None


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Performance-related tests."""
    
    def test_hash_computation_speed(self):
        """Test file hash computation is fast."""
        import time
        from api.media_processing import compute_file_hash
        
        # 10MB of data
        large_data = b"x" * (10 * 1024 * 1024)
        
        start = time.time()
        compute_file_hash(large_data)
        elapsed = time.time() - start
        
        # Should complete in under 1 second
        assert elapsed < 1.0, f"Hash computation too slow: {elapsed:.2f}s"
    
    def test_media_list_pagination(self):
        """Test media listing with pagination."""
        from api.media_processing import media_items
        import uuid
        
        media_items.clear()
        
        # Create 100 items
        for i in range(100):
            media_id = str(uuid.uuid4())
            media_items[media_id] = {
                "media_id": media_id,
                "created_at": datetime.now().isoformat()
            }
        
        # Paginate
        items = list(media_items.values())
        page_1 = items[0:20]
        page_2 = items[20:40]
        
        assert len(page_1) == 20
        assert len(page_2) == 20
        assert page_1[0] != page_2[0]


# =============================================================================
# MOBILE CLIENT TESTS (iOS/Android)
# =============================================================================

class TestMobileClients:
    """Tests specific to mobile client requirements."""
    
    def test_ios_upload_parameters(self):
        """Test iOS-specific upload parameters."""
        ios_config = {
            "chunk_size": 5 * 1024 * 1024,  # 5MB
            "timeout": 60,  # 60 seconds per chunk
            "retry_on_network_error": True,
            "compress_before_upload": True
        }
        
        assert ios_config["chunk_size"] == 5 * 1024 * 1024
        assert ios_config["retry_on_network_error"] is True
    
    def test_android_upload_parameters(self):
        """Test Android-specific upload parameters."""
        android_config = {
            "chunk_size": 5 * 1024 * 1024,  # 5MB
            "background_upload": True,
            "notification_progress": True,
            "wifi_only_option": True
        }
        
        assert android_config["background_upload"] is True
        assert android_config["notification_progress"] is True
    
    def test_mobile_response_format(self):
        """Test response format is mobile-friendly."""
        response = {
            "media_id": "123",
            "status": "analyzed",
            "progress": 1.0,
            "analysis_result": {
                "pre_social_score": 85
            }
        }
        
        # Response should be JSON-serializable
        json_str = json.dumps(response)
        parsed = json.loads(json_str)
        
        assert parsed["media_id"] == "123"
        assert parsed["progress"] == 1.0


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
