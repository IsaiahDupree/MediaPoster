"""
File System Watcher
Monitors directories for new video files (AirDrop, Desktop, etc.)
"""
import os
import time
from pathlib import Path
from typing import List, Callable, Set, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
from loguru import logger


class VideoFileHandler(FileSystemEventHandler):
    """Handler for video file system events"""
    
    def __init__(self, callback: Callable[[Path], None], supported_formats: Set[str]):
        """
        Initialize handler
        
        Args:
            callback: Function to call when new video detected
            supported_formats: Set of supported file extensions (e.g., {'.mp4', '.mov'})
        """
        self.callback = callback
        self.supported_formats = {fmt.lower() for fmt in supported_formats}
        self.processing_files = set()
        self.processed_files = set()
        
    def is_video_file(self, path: Path) -> bool:
        """Check if file is a supported video format"""
        return path.suffix.lower() in self.supported_formats
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        self._handle_new_file(file_path)
    
    def on_moved(self, event):
        """Handle file move events (e.g., AirDrop completion)"""
        if event.is_directory:
            return
        
        dest_path = Path(event.dest_path)
        self._handle_new_file(dest_path)
    
    def _handle_new_file(self, file_path: Path):
        """Process a new file"""
        if not self.is_video_file(file_path):
            return
        
        # Avoid processing same file multiple times
        file_key = str(file_path.absolute())
        if file_key in self.processing_files or file_key in self.processed_files:
            return
        
        self.processing_files.add(file_key)
        logger.info(f"New video file detected: {file_path.name}")
        
        try:
            # Wait for file to be fully written
            if self._wait_for_file_stable(file_path):
                self.callback(file_path)
                self.processed_files.add(file_key)
            else:
                logger.warning(f"File not stable after waiting: {file_path}")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
        finally:
            self.processing_files.discard(file_key)
    
    def _wait_for_file_stable(self, file_path: Path, timeout: int = 30) -> bool:
        """
        Wait for file to be fully written
        Checks if file size stops changing
        
        Args:
            file_path: Path to file
            timeout: Max seconds to wait
            
        Returns:
            True if file is stable
        """
        if not file_path.exists():
            return False
        
        last_size = -1
        stable_count = 0
        checks = 0
        max_checks = timeout * 2  # Check every 0.5 seconds
        
        while checks < max_checks:
            try:
                current_size = file_path.stat().st_size
                
                if current_size == last_size:
                    stable_count += 1
                    # Consider stable after 3 consecutive same-size checks
                    if stable_count >= 3:
                        logger.debug(f"File stable: {file_path.name} ({current_size} bytes)")
                        return True
                else:
                    stable_count = 0
                    last_size = current_size
                
                time.sleep(0.5)
                checks += 1
                
            except OSError:
                # File might be temporarily inaccessible
                time.sleep(0.5)
                checks += 1
        
        return False


class VideoFileWatcher:
    """
    Watches multiple directories for new video files
    Useful for monitoring AirDrop, Desktop, Downloads, etc.
    """
    
    def __init__(self, watch_directories: List[str], supported_formats: Optional[List[str]] = None):
        """
        Initialize file watcher
        
        Args:
            watch_directories: List of directory paths to watch
            supported_formats: List of supported file extensions (default: common video formats)
        """
        if supported_formats is None:
            supported_formats = ['.mp4', '.mov', '.m4v', '.avi', '.mkv', '.mpg', '.mpeg', '.3gp']
        
        self.watch_dirs = [Path(d).expanduser() for d in watch_directories]
        self.supported_formats = set(supported_formats)
        self.observer = None
        self.event_handler = None
        
        logger.info(f"File Watcher initialized for: {', '.join(str(d) for d in self.watch_dirs)}")
    
    def start(self, callback: Callable[[Path], None]):
        """
        Start watching directories
        
        Args:
            callback: Function to call when new video is detected
        """
        if self.observer is not None:
            logger.warning("Watcher already running")
            return
        
        # Create event handler
        self.event_handler = VideoFileHandler(callback, self.supported_formats)
        
        # Create observer
        self.observer = Observer()
        
        # Schedule directories
        for watch_dir in self.watch_dirs:
            if not watch_dir.exists():
                logger.warning(f"Watch directory does not exist: {watch_dir}")
                continue
            
            if not watch_dir.is_dir():
                logger.warning(f"Not a directory: {watch_dir}")
                continue
            
            self.observer.schedule(self.event_handler, str(watch_dir), recursive=False)
            logger.info(f"✓ Watching: {watch_dir}")
        
        # Start observer
        self.observer.start()
        logger.info("File watcher started")
    
    def stop(self):
        """Stop watching directories"""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("File watcher stopped")
    
    def is_running(self) -> bool:
        """Check if watcher is currently running"""
        return self.observer is not None and self.observer.is_alive()
    
    def scan_existing_files(self, callback: Callable[[Path], None], max_age_hours: int = 24):
        """
        Scan watch directories for existing video files
        
        Args:
            callback: Function to call for each video found
            max_age_hours: Only process files modified in last N hours
        """
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        found_count = 0
        
        for watch_dir in self.watch_dirs:
            if not watch_dir.exists():
                continue
            
            logger.info(f"Scanning {watch_dir} for recent videos...")
            
            for file_path in watch_dir.iterdir():
                if not file_path.is_file():
                    continue
                
                if file_path.suffix.lower() not in self.supported_formats:
                    continue
                
                # Check file age
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mod_time < cutoff_time:
                    continue
                
                try:
                    callback(file_path)
                    found_count += 1
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
        
        logger.info(f"Scan complete: found {found_count} recent video files")
        return found_count


class AirDropMonitor:
    """
    Specialized monitor for macOS AirDrop
    AirDrop files typically arrive in ~/Downloads
    """
    
    def __init__(self):
        """Initialize AirDrop monitor"""
        self.downloads_dir = Path.home() / "Downloads"
        self.watcher = VideoFileWatcher([str(self.downloads_dir)])
        
        logger.info(f"AirDrop Monitor initialized (watching {self.downloads_dir})")
    
    def start(self, callback: Callable[[Path], None]):
        """
        Start monitoring for AirDrop videos
        
        Args:
            callback: Function to call when video received via AirDrop
        """
        def airdrop_callback(file_path: Path):
            """Wrapper to add AirDrop context"""
            logger.info(f"Video received via AirDrop: {file_path.name}")
            callback(file_path)
        
        self.watcher.start(airdrop_callback)
        logger.info("AirDrop monitoring started")
    
    def stop(self):
        """Stop AirDrop monitoring"""
        self.watcher.stop()
        logger.info("AirDrop monitoring stopped")
    
    def is_running(self) -> bool:
        """Check if monitoring is active"""
        return self.watcher.is_running()
