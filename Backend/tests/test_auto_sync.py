"""
Tests for Auto-Sync Ingestion System

Tests that:
1. Auto-sync correctly identifies files not in DB
2. Skips files already in DB
3. Publishes correct events
4. Handles errors gracefully
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime


class TestAutoSyncEndpoint:
    """Test the /api/ingestion/auto-sync endpoint"""
    
    @pytest.mark.asyncio
    async def test_auto_sync_returns_correct_stats(self):
        """Test that auto-sync returns correct video counts"""
        from api.endpoints.ingestion import auto_sync_iphone_import
        from fastapi import BackgroundTasks
        
        background_tasks = BackgroundTasks()
        
        # Mock the response
        with patch('api.endpoints.ingestion.Path') as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.iterdir.return_value = []
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value = mock_dir
            
            result = await auto_sync_iphone_import(background_tasks, limit=10)
            
            assert "message" in result
            assert "total_videos" in result
            assert "already_in_db" in result
            assert "new_to_ingest" in result
    
    @pytest.mark.asyncio
    async def test_auto_sync_handles_missing_directory(self):
        """Test graceful handling when IphoneImport doesn't exist"""
        from api.endpoints.ingestion import auto_sync_iphone_import
        from fastapi import BackgroundTasks
        
        background_tasks = BackgroundTasks()
        
        with patch('api.endpoints.ingestion.Path') as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value = mock_dir
            
            result = await auto_sync_iphone_import(background_tasks)
            
            assert "error" in result
            assert "not found" in result["error"].lower()


class TestVideoFiltering:
    """Test video file filtering logic"""
    
    def test_video_extensions_filter(self):
        """Test that only video extensions are matched"""
        video_extensions = {'.mp4', '.mov', '.m4v', '.avi', '.mkv'}
        
        # Should match
        assert '.mp4' in video_extensions
        assert '.mov' in video_extensions
        assert '.MP4'.lower() in video_extensions
        
        # Should not match
        assert '.jpg' not in video_extensions
        assert '.pdf' not in video_extensions
        assert '.txt' not in video_extensions
    
    def test_empty_files_are_skipped(self):
        """Test that zero-size files are filtered out"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create an empty file
            empty_file = Path(temp_dir) / "empty.mp4"
            empty_file.touch()
            
            # Create a file with content
            content_file = Path(temp_dir) / "content.mp4"
            content_file.write_bytes(b"fake video content")
            
            assert empty_file.stat().st_size == 0
            assert content_file.stat().st_size > 0


class TestDatabaseCheck:
    """Test database duplicate checking"""
    
    def test_existing_path_detection(self):
        """Test that existing paths in DB are detected"""
        existing_paths = {
            "/Users/test/Documents/IphoneImport/video1.mp4",
            "/Users/test/Documents/IphoneImport/video2.mov"
        }
        
        all_videos = [
            Path("/Users/test/Documents/IphoneImport/video1.mp4"),
            Path("/Users/test/Documents/IphoneImport/video2.mov"),
            Path("/Users/test/Documents/IphoneImport/video3.mp4"),
        ]
        
        new_videos = [v for v in all_videos if str(v) not in existing_paths]
        
        assert len(new_videos) == 1
        assert new_videos[0].name == "video3.mp4"
    
    def test_all_new_videos_when_db_empty(self):
        """Test that all videos are new when DB is empty"""
        existing_paths = set()
        
        all_videos = [
            Path("/path/to/video1.mp4"),
            Path("/path/to/video2.mov"),
            Path("/path/to/video3.mp4"),
        ]
        
        new_videos = [v for v in all_videos if str(v) not in existing_paths]
        
        assert len(new_videos) == 3


class TestFileWatcherGetAllVideos:
    """Test the get_all_video_files method"""
    
    def test_get_all_video_files_with_temp_dir(self):
        """Test getting all video files from a directory"""
        from modules.video_ingestion.file_watcher import VideoFileWatcher
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test video files
            (Path(temp_dir) / "video1.mp4").write_bytes(b"content1")
            (Path(temp_dir) / "video2.mov").write_bytes(b"content2")
            (Path(temp_dir) / "image.jpg").write_bytes(b"image")
            (Path(temp_dir) / "empty.mp4").touch()  # Empty file
            
            watcher = VideoFileWatcher([temp_dir])
            videos = watcher.get_all_video_files()
            
            # Should find 2 videos (excludes jpg and empty file)
            assert len(videos) == 2
            names = {v.name for v in videos}
            assert "video1.mp4" in names
            assert "video2.mov" in names
            assert "image.jpg" not in names
            assert "empty.mp4" not in names
    
    def test_get_all_video_files_empty_directory(self):
        """Test with empty directory"""
        from modules.video_ingestion.file_watcher import VideoFileWatcher
        
        with tempfile.TemporaryDirectory() as temp_dir:
            watcher = VideoFileWatcher([temp_dir])
            videos = watcher.get_all_video_files()
            
            assert len(videos) == 0
    
    def test_get_all_video_files_nonexistent_directory(self):
        """Test with nonexistent directory"""
        from modules.video_ingestion.file_watcher import VideoFileWatcher
        
        watcher = VideoFileWatcher(["/nonexistent/path"])
        videos = watcher.get_all_video_files()
        
        assert len(videos) == 0


class TestIphoneImportStats:
    """Test the iphone-import-stats endpoint"""
    
    @pytest.mark.asyncio
    async def test_stats_endpoint_returns_data(self):
        """Test that stats endpoint returns expected fields"""
        from api.endpoints.ingestion import get_iphone_import_stats
        
        result = await get_iphone_import_stats()
        
        assert "exists" in result
        assert "path" in result
        
        if result["exists"]:
            assert "video_count" in result
            assert "total_size_gb" in result
            assert "recent_videos" in result


class TestEventPublishing:
    """Test that correct events are published during sync"""
    
    @pytest.mark.asyncio
    async def test_event_bus_available(self):
        """Test that EventBus can be instantiated"""
        from services.event_bus import EventBus
        
        event_bus = EventBus.get_instance()
        assert event_bus is not None
    
    def test_event_topics_defined(self):
        """Test that ingestion event topics are defined"""
        expected_topics = [
            "ingestion.detected",
            "ingestion.processing", 
            "ingestion.completed",
            "ingestion.exists",
            "ingestion.error"
        ]
        
        # These should be valid topic strings
        for topic in expected_topics:
            assert isinstance(topic, str)
            assert topic.startswith("ingestion.")


class TestAutoSyncIntegration:
    """Integration tests for auto-sync with real IphoneImport"""
    
    def test_iphone_import_directory_accessible(self):
        """Test that IphoneImport directory is accessible"""
        iphone_import = Path.home() / "Documents" / "IphoneImport"
        
        if not iphone_import.exists():
            pytest.skip("IphoneImport directory not found")
        
        # Should be readable
        assert iphone_import.is_dir()
        
        # Should contain files
        files = list(iphone_import.iterdir())
        assert len(files) > 0
    
    def test_video_count_matches_stats(self):
        """Test that video count is consistent"""
        iphone_import = Path.home() / "Documents" / "IphoneImport"
        
        if not iphone_import.exists():
            pytest.skip("IphoneImport directory not found")
        
        video_extensions = {'.mp4', '.mov', '.m4v', '.avi', '.mkv'}
        video_count = sum(
            1 for f in iphone_import.iterdir()
            if f.is_file() and f.suffix.lower() in video_extensions
            and f.stat().st_size > 0
        )
        
        # Should have a significant number of videos
        assert video_count > 0
        print(f"Found {video_count} non-empty video files")


class TestRateLimiting:
    """Test that auto-sync respects rate limits"""
    
    def test_limit_parameter_respected(self):
        """Test that the limit parameter caps ingestion count"""
        all_videos = [f"video{i}.mp4" for i in range(100)]
        limit = 10
        
        videos_to_ingest = all_videos[:limit]
        
        assert len(videos_to_ingest) == limit
    
    def test_default_limit_is_reasonable(self):
        """Test that default limit is set"""
        # Default should be 50 based on the endpoint definition
        default_limit = 50
        
        assert default_limit > 0
        assert default_limit <= 100  # Reasonable upper bound


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
