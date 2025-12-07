"""
Tests for File Watcher
"""
import pytest
import time
import shutil
from pathlib import Path
from modules.video_ingestion.file_watcher import VideoFileWatcher, AirDropMonitor


class TestVideoFileWatcher:
    """Test VideoFileWatcher class"""
    
    def test_initialization(self, watch_directory):
        """Test watcher initialization"""
        watcher = VideoFileWatcher([str(watch_directory)])
        
        assert not watcher.is_running()
        assert len(watcher.watch_dirs) == 1
    
    def test_start_and_stop(self, watch_directory):
        """Test starting and stopping the watcher"""
        detected_files = []
        
        def callback(path: Path):
            detected_files.append(path)
        
        watcher = VideoFileWatcher([str(watch_directory)])
        watcher.start(callback)
        
        assert watcher.is_running()
        
        watcher.stop()
        
        assert not watcher.is_running()
    
    def test_detect_new_video(self, watch_directory, sample_video):
        """Test detection of new video file"""
        detected_files = []
        
        def callback(path: Path):
            detected_files.append(path)
        
        watcher = VideoFileWatcher([str(watch_directory)])
        watcher.start(callback)
        
        # Give watcher time to start
        time.sleep(0.5)
        
        # Copy video to watched directory
        dest_path = watch_directory / "new_video.mp4"
        shutil.copy2(sample_video, dest_path)
        
        # Wait for detection
        time.sleep(2)
        
        watcher.stop()
        
        # Should have detected the file
        assert len(detected_files) > 0
        assert any(str(dest_path) in str(f) for f in detected_files)
    
    def test_ignore_non_video_files(self, watch_directory, invalid_file):
        """Test that non-video files are ignored"""
        detected_files = []
        
        def callback(path: Path):
            detected_files.append(path)
        
        watcher = VideoFileWatcher([str(watch_directory)])
        watcher.start(callback)
        
        time.sleep(0.5)
        
        # Copy non-video file
        dest_path = watch_directory / "document.txt"
        shutil.copy2(invalid_file, dest_path)
        
        time.sleep(2)
        
        watcher.stop()
        
        # Should not detect non-video file
        assert len(detected_files) == 0
    
    def test_scan_existing_files(self, watch_directory, sample_video):
        """Test scanning for existing files"""
        # Copy video to directory
        dest_path = watch_directory / "existing_video.mp4"
        shutil.copy2(sample_video, dest_path)
        
        detected_files = []
        
        def callback(path: Path):
            detected_files.append(path)
        
        watcher = VideoFileWatcher([str(watch_directory)])
        count = watcher.scan_existing_files(callback, max_age_hours=24)
        
        assert count > 0
        assert len(detected_files) > 0
        assert any(str(dest_path) in str(f) for f in detected_files)
    
    def test_multiple_directories(self, temp_dir):
        """Test watching multiple directories"""
        dir1 = temp_dir / "watch1"
        dir2 = temp_dir / "watch2"
        dir1.mkdir()
        dir2.mkdir()
        
        watcher = VideoFileWatcher([str(dir1), str(dir2)])
        
        detected_files = []
        watcher.start(lambda p: detected_files.append(p))
        
        assert watcher.is_running()
        
        watcher.stop()


class TestAirDropMonitor:
    """Test AirDropMonitor class"""
    
    def test_initialization(self):
        """Test AirDrop monitor initialization"""
        monitor = AirDropMonitor()
        
        assert monitor.downloads_dir.exists()
        assert not monitor.is_running()
    
    def test_start_and_stop(self):
        """Test starting and stopping AirDrop monitor"""
        monitor = AirDropMonitor()
        
        def callback(path: Path):
            pass
        
        monitor.start(callback)
        assert monitor.is_running()
        
        monitor.stop()
        assert not monitor.is_running()


class TestFileWatcherIntegration:
    """Integration tests for file watcher"""
    
    def test_concurrent_file_additions(self, watch_directory, sample_video):
        """Test handling of multiple files added simultaneously"""
        detected_files = []
        
        def callback(path: Path):
            detected_files.append(path)
        
        watcher = VideoFileWatcher([str(watch_directory)])
        watcher.start(callback)
        
        time.sleep(0.5)
        
        # Add multiple files
        for i in range(3):
            dest = watch_directory / f"video_{i}.mp4"
            shutil.copy2(sample_video, dest)
        
        # Wait for all to be detected
        time.sleep(3)
        
        watcher.stop()
        
        # Should detect all files
        assert len(detected_files) >= 3
    
    def test_file_stability_check(self, watch_directory, sample_video):
        """Test that watcher waits for file to be fully written"""
        detected_files = []
        
        def callback(path: Path):
            # Check that file is readable and complete
            assert path.exists()
            assert path.stat().st_size > 0
            detected_files.append(path)
        
        watcher = VideoFileWatcher([str(watch_directory)])
        watcher.start(callback)
        
        time.sleep(0.5)
        
        # Simulate gradual file write by copying in chunks
        dest = watch_directory / "copying.mp4"
        
        # Start with partial file
        with open(sample_video, 'rb') as src:
            data = src.read()
            mid_point = len(data) // 2
            
            with open(dest, 'wb') as dst:
                # Write first half
                dst.write(data[:mid_point])
                dst.flush()
                time.sleep(0.5)
                
                # Write second half
                dst.write(data[mid_point:])
                dst.flush()
        
        # Wait for detection
        time.sleep(3)
        
        watcher.stop()
        
        # Should have detected file after it was stable
        assert len(detected_files) > 0
