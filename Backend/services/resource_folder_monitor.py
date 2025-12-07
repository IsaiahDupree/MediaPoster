"""
Resource Folder Monitor
Monitors the resource folder for new content and triggers scheduler updates
"""
import logging
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import asyncio

logger = logging.getLogger(__name__)


class ResourceFolderHandler(FileSystemEventHandler):
    """Handles file system events in resource folder"""
    
    def __init__(self, on_new_content: Callable[[Path], None]):
        """
        Args:
            on_new_content: Callback when new content is detected
        """
        self.on_new_content = on_new_content
        self.supported_extensions = {
            '.mp4', '.mov', '.avi', '.mkv', '.webm',  # Video
            '.jpg', '.jpeg', '.png', '.heic', '.heif'  # Images
        }
    
    def on_created(self, event: FileSystemEvent):
        """Called when a file is created"""
        if not event.is_directory:
            self._handle_file(event.src_path)
    
    def on_modified(self, event: FileSystemEvent):
        """Called when a file is modified"""
        if not event.is_directory:
            self._handle_file(event.src_path)
    
    def _handle_file(self, file_path: str):
        """Handle a file event"""
        path = Path(file_path)
        
        # Check if it's a supported content file
        if path.suffix.lower() in self.supported_extensions:
            logger.info(f"New content detected: {file_path}")
            try:
                self.on_new_content(path)
            except Exception as e:
                logger.error(f"Error handling new content {file_path}: {e}")


class ResourceFolderMonitor:
    """
    Monitors resource folder for new content
    Triggers scheduler updates when new content is added
    """
    
    def __init__(
        self,
        resource_folder: Path,
        on_new_content: Callable[[Path], None],
        watch_subdirectories: bool = True
    ):
        """
        Args:
            resource_folder: Path to resource folder to monitor
            on_new_content: Callback when new content is detected
            watch_subdirectories: Whether to watch subdirectories
        """
        self.resource_folder = Path(resource_folder)
        self.on_new_content = on_new_content
        self.watch_subdirectories = watch_subdirectories
        self.observer = None
        self.handler = ResourceFolderHandler(on_new_content)
    
    def start(self):
        """Start monitoring the resource folder"""
        if not self.resource_folder.exists():
            logger.warning(f"Resource folder does not exist: {self.resource_folder}")
            self.resource_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created resource folder: {self.resource_folder}")
        
        self.observer = Observer()
        self.observer.schedule(
            self.handler,
            str(self.resource_folder),
            recursive=self.watch_subdirectories
        )
        self.observer.start()
        logger.info(f"Started monitoring resource folder: {self.resource_folder}")
    
    def stop(self):
        """Stop monitoring"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped monitoring resource folder")
    
    def is_running(self) -> bool:
        """Check if monitor is running"""
        return self.observer is not None and self.observer.is_alive()






