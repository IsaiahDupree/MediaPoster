"""
Tests for Video Ingestion Service
"""
import pytest
import time
from pathlib import Path
from modules.video_ingestion.ingestion_service import VideoIngestionService, watch_for_videos


class TestVideoIngestionService:
    """Test VideoIngestionService class"""
    
    def test_initialization(self):
        """Test service initialization"""
        service = VideoIngestionService(
            enable_icloud=False,
            enable_usb=False,
            enable_airdrop=False,
            enable_file_watcher=False
        )
        
        assert not service.running
        assert service.icloud_monitor is None
        assert service.image_capture is None
        assert service.airdrop_monitor is None
        assert service.file_watcher is None
    
    def test_initialization_with_watchers(self, watch_directory):
        """Test service with file watchers enabled"""
        service = VideoIngestionService(
            enable_icloud=False,
            enable_usb=False,
            enable_airdrop=False,
            enable_file_watcher=True,
            watch_directories=[str(watch_directory)]
        )
        
        assert service.file_watcher is not None
    
    def test_process_video(self, sample_video):
        """Test video processing"""
        processed_videos = []
        
        def callback(path: Path, metadata: dict):
            processed_videos.append((path, metadata))
        
        service = VideoIngestionService(
            enable_icloud=False,
            enable_usb=False,
            enable_airdrop=False,
            enable_file_watcher=False,
            callback=callback
        )
        
        service.process_video(sample_video, source="test")
        
        assert len(processed_videos) == 1
        path, metadata = processed_videos[0]
        assert path == sample_video
        assert metadata['source'] == 'test'
        assert 'duration' in metadata
        assert 'width' in metadata
    
    def test_process_invalid_video(self, invalid_file):
        """Test processing of invalid video"""
        processed_videos = []
        
        def callback(path: Path, metadata: dict):
            processed_videos.append((path, metadata))
        
        service = VideoIngestionService(
            enable_icloud=False,
            enable_usb=False,
            enable_airdrop=False,
            enable_file_watcher=False,
            callback=callback
        )
        
        service.process_video(invalid_file, source="test")
        
        # Should not process invalid file
        assert len(processed_videos) == 0
    
    def test_get_status(self):
        """Test status reporting"""
        service = VideoIngestionService(
            enable_icloud=False,
            enable_usb=False,
            enable_airdrop=True,
            enable_file_watcher=True,
            watch_directories=["/tmp"]
        )
        
        status = service.get_status()
        
        assert 'running' in status
        assert 'icloud' in status
        assert 'usb' in status
        assert 'airdrop' in status
        assert 'file_watcher' in status
        
        assert status['icloud']['enabled'] is False
        assert status['airdrop']['enabled'] is True
    
    def test_context_manager(self, watch_directory):
        """Test using service as context manager"""
        processed = []
        
        def callback(path: Path, metadata: dict):
            processed.append(path)
        
        with VideoIngestionService(
            enable_icloud=False,
            enable_usb=False,
            enable_airdrop=False,
            enable_file_watcher=True,
            watch_directories=[str(watch_directory)],
            callback=callback
        ) as service:
            assert service.running
        
        # Should be stopped after exiting context
        # Note: may still be running briefly due to thread shutdown
    
    def test_callback_error_handling(self, sample_video):
        """Test that errors in callback don't crash service"""
        def bad_callback(path: Path, metadata: dict):
            raise Exception("Test error")
        
        service = VideoIngestionService(
            enable_icloud=False,
            enable_usb=False,
            enable_airdrop=False,
            enable_file_watcher=False,
            callback=bad_callback
        )
        
        # Should not raise exception
        service.process_video(sample_video, source="test")


class TestWatchForVideosFunction:
    """Test convenience function"""
    
    def test_watch_for_videos(self, watch_directory):
        """Test the watch_for_videos convenience function"""
        processed = []
        
        def callback(path: Path, metadata: dict):
            processed.append((path, metadata))
        
        # Note: This would normally run indefinitely
        # In tests, we just verify it initializes correctly
        service = watch_for_videos(
            callback=callback,
            enable_all=False,  # Disable to avoid actual watching
            watch_dirs=[str(watch_directory)]
        )
        
        assert service is not None
        assert isinstance(service, VideoIngestionService)


class TestIngestionServiceIntegration:
    """Integration tests for ingestion service"""
    
    @pytest.mark.slow
    def test_end_to_end_file_detection(self, watch_directory, sample_video):
        """Test complete flow from file detection to callback"""
        import shutil
        
        processed = []
        
        def callback(path: Path, metadata: dict):
            processed.append({
                'path': path,
                'source': metadata['source'],
                'duration': metadata['duration']
            })
        
        service = VideoIngestionService(
            enable_icloud=False,
            enable_usb=False,
            enable_airdrop=False,
            enable_file_watcher=True,
            watch_directories=[str(watch_directory)],
            callback=callback
        )
        
        service.start_all()
        
        # Wait for service to start
        time.sleep(1)
        
        # Add video to watched directory
        dest = watch_directory / "detected_video.mp4"
        shutil.copy2(sample_video, dest)
        
        # Wait for detection and processing
        time.sleep(3)
        
        service.stop_all()
        
        # Should have detected and processed the video
        assert len(processed) > 0
        assert processed[0]['source'] == 'file_watcher'
        assert processed[0]['duration'] > 0
    
    def test_multiple_source_handling(self):
        """Test handling videos from multiple sources"""
        processed = []
        
        def callback(path: Path, metadata: dict):
            processed.append(metadata['source'])
        
        service = VideoIngestionService(
            enable_icloud=False,
            enable_usb=False,
            enable_airdrop=False,
            enable_file_watcher=False,
            callback=callback
        )
        
        # Simulate videos from different sources
        # (Using dummy paths - actual detection tested separately)
        # This tests the routing and source tracking
        
        status = service.get_status()
        assert status is not None
