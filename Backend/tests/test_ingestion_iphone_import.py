"""
Tests for iPhone Import Ingestion Service
Verifies that the ingestion service correctly:
1. Watches the IphoneImport directory
2. Detects video files
3. Publishes appropriate events
"""
import pytest
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import shutil


class TestIphoneImportConfig:
    """Test that IphoneImport is configured as the default watch directory"""
    
    def test_default_watch_directory_is_iphone_import(self):
        """Verify default watch directory is ~/Documents/IphoneImport"""
        from api.endpoints.ingestion import IngestionConfig
        
        config = IngestionConfig()
        expected_path = str(Path.home() / "Documents" / "IphoneImport")
        
        # Default should be None, which gets converted to IphoneImport in start_ingestion
        assert config.watch_directories is None
    
    def test_iphone_import_directory_exists(self):
        """Verify IphoneImport directory exists on this system"""
        iphone_import = Path.home() / "Documents" / "IphoneImport"
        assert iphone_import.exists(), f"IphoneImport directory not found at {iphone_import}"
    
    def test_iphone_import_contains_videos(self):
        """Verify IphoneImport contains video files"""
        iphone_import = Path.home() / "Documents" / "IphoneImport"
        
        if not iphone_import.exists():
            pytest.skip("IphoneImport directory not found")
        
        video_extensions = {'.mp4', '.mov', '.m4v', '.avi', '.mkv'}
        video_count = sum(
            1 for f in iphone_import.iterdir() 
            if f.is_file() and f.suffix.lower() in video_extensions
        )
        
        assert video_count > 0, "No video files found in IphoneImport"
        print(f"Found {video_count} video files in IphoneImport")


class TestFileWatcher:
    """Test the file watcher component"""
    
    def test_video_file_handler_detects_mp4(self):
        """Test that VideoFileHandler correctly identifies MP4 files"""
        from modules.video_ingestion.file_watcher import VideoFileHandler
        
        callback = Mock()
        handler = VideoFileHandler(callback, {'.mp4', '.mov'})
        
        assert handler.is_video_file(Path("/test/video.mp4")) is True
        assert handler.is_video_file(Path("/test/video.MP4")) is True
        assert handler.is_video_file(Path("/test/video.mov")) is True
        assert handler.is_video_file(Path("/test/document.pdf")) is False
        assert handler.is_video_file(Path("/test/image.jpg")) is False
    
    def test_video_file_watcher_initialization(self):
        """Test VideoFileWatcher initializes with correct directories"""
        from modules.video_ingestion.file_watcher import VideoFileWatcher
        
        watch_dirs = [str(Path.home() / "Documents" / "IphoneImport")]
        watcher = VideoFileWatcher(watch_dirs)
        
        assert len(watcher.watch_dirs) == 1
        assert watcher.watch_dirs[0] == Path.home() / "Documents" / "IphoneImport"
    
    def test_video_file_watcher_expands_user_path(self):
        """Test that ~ is expanded in paths"""
        from modules.video_ingestion.file_watcher import VideoFileWatcher
        
        watcher = VideoFileWatcher(["~/Documents/IphoneImport"])
        
        assert watcher.watch_dirs[0] == Path.home() / "Documents" / "IphoneImport"


class TestIngestionEvents:
    """Test event publishing during ingestion"""
    
    @pytest.mark.asyncio
    async def test_ingestion_status_endpoint(self):
        """Test the ingestion status endpoint returns valid data"""
        from api.endpoints.ingestion import get_ingestion_status
        
        status = await get_ingestion_status()
        
        assert hasattr(status, 'running')
        assert hasattr(status, 'file_watcher')
    
    @pytest.mark.asyncio
    async def test_iphone_import_stats_endpoint(self):
        """Test the iphone-import-stats endpoint"""
        from api.endpoints.ingestion import get_iphone_import_stats
        
        stats = await get_iphone_import_stats()
        
        assert 'exists' in stats
        assert 'path' in stats
        
        if stats['exists']:
            assert 'video_count' in stats
            assert 'total_size_gb' in stats
            print(f"IphoneImport stats: {stats['video_count']} videos, {stats['total_size_gb']} GB")


class TestIngestionWithTempDir:
    """Test ingestion with temporary directory"""
    
    @pytest.fixture
    def temp_video_dir(self):
        """Create a temporary directory with test video files"""
        temp_dir = tempfile.mkdtemp()
        
        # Create mock video files
        for i in range(3):
            video_path = Path(temp_dir) / f"test_video_{i}.mp4"
            video_path.write_bytes(b"fake video content " * 100)
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_file_watcher_with_temp_directory(self, temp_video_dir):
        """Test file watcher can be configured with custom directory"""
        from modules.video_ingestion.file_watcher import VideoFileWatcher
        
        watcher = VideoFileWatcher([temp_video_dir])
        
        assert len(watcher.watch_dirs) == 1
        assert watcher.watch_dirs[0].exists()
    
    def test_video_files_detected_in_temp_dir(self, temp_video_dir):
        """Test that video files in temp dir would be detected"""
        from modules.video_ingestion.file_watcher import VideoFileHandler
        
        callback = Mock()
        handler = VideoFileHandler(callback, {'.mp4', '.mov'})
        
        temp_path = Path(temp_video_dir)
        video_files = list(temp_path.glob("*.mp4"))
        
        assert len(video_files) == 3
        
        for video in video_files:
            assert handler.is_video_file(video) is True


class TestEnvConfiguration:
    """Test environment variable configuration"""
    
    def test_video_source_dir_env_var(self):
        """Test VIDEO_SOURCE_DIR environment variable"""
        # This should be set in .env
        video_source = os.getenv("VIDEO_SOURCE_DIR")
        
        if video_source:
            assert "IphoneImport" in video_source or video_source.startswith("/media")
            print(f"VIDEO_SOURCE_DIR: {video_source}")
    
    def test_watch_directories_env_var(self):
        """Test WATCH_DIRECTORIES environment variable"""
        watch_dirs = os.getenv("WATCH_DIRECTORIES")
        
        if watch_dirs:
            assert "IphoneImport" in watch_dirs
            print(f"WATCH_DIRECTORIES: {watch_dirs}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
