"""
Image Capture Integration
Monitors for iPhone USB connections and automatically imports videos
"""
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Dict, Callable
from loguru import logger


class ImageCaptureImporter:
    """
    Handles automatic import of videos from iPhone via USB using Image Capture
    """
    
    def __init__(self, auto_import_dir: Optional[Path] = None):
        """
        Initialize Image Capture importer
        
        Args:
            auto_import_dir: Directory to import videos to (default: ~/Pictures/MediaPoster_Imports)
        """
        if auto_import_dir is None:
            auto_import_dir = Path.home() / "Pictures" / "MediaPoster_Imports"
        
        self.import_dir = auto_import_dir
        self.import_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Image Capture Importer initialized: {self.import_dir}")
    
    def list_connected_devices(self) -> List[Dict[str, str]]:
        """
        List connected iOS devices
        
        Returns:
            List of device info dictionaries
        """
        try:
            # Use system_profiler to list USB devices
            result = subprocess.run(
                ['system_profiler', 'SPUSBDataType', '-json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error("Failed to list USB devices")
                return []
            
            # Parse output to find iOS devices
            # This is simplified - in production, properly parse JSON
            devices = []
            if 'iPhone' in result.stdout or 'iPad' in result.stdout:
                devices.append({
                    'name': 'iPhone',  # Extract from JSON
                    'type': 'iOS Device',
                    'connected': True
                })
            
            return devices
            
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return []
    
    def import_videos_from_device(self, device_name: Optional[str] = None) -> List[Path]:
        """
        Import all videos from connected iPhone
        
        Args:
            device_name: Name of device to import from (default: first found)
            
        Returns:
            List of imported video paths
        """
        devices = self.list_connected_devices()
        
        if not devices:
            logger.warning("No iOS devices connected")
            return []
        
        # Use AppleScript to control Image Capture
        # This provides programmatic access to Image Capture functionality
        script = f'''
        tell application "Image Capture"
            activate
            
            set deviceList to devices
            if (count of deviceList) is 0 then
                return "No devices connected"
            end if
            
            set targetDevice to item 1 of deviceList
            
            -- Get all videos
            set allItems to items of targetDevice
            set videoItems to {{}}
            
            repeat with anItem in allItems
                if type of anItem is "video" then
                    set end of videoItems to anItem
                end if
            end repeat
            
            -- Download videos
            if (count of videoItems) > 0 then
                download videoItems to POSIX file "{self.import_dir}"
                return "Downloaded " & (count of videoItems) & " videos"
            else
                return "No videos found"
            end if
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout for large imports
            )
            
            if result.returncode == 0:
                logger.info(f"Import result: {result.stdout.strip()}")
                
                # List newly imported files
                imported_files = self._get_recent_imports()
                logger.info(f"✓ Imported {len(imported_files)} videos from device")
                return imported_files
            else:
                logger.error(f"Import failed: {result.stderr}")
                return []
                
        except subprocess.TimeoutExpired:
            logger.error("Import timed out")
            return []
        except Exception as e:
            logger.error(f"Error importing videos: {e}")
            return []
    
    def _get_recent_imports(self, max_age_seconds: int = 60) -> List[Path]:
        """Get recently imported files from import directory"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(seconds=max_age_seconds)
        recent_files = []
        
        for file_path in self.import_dir.iterdir():
            if not file_path.is_file():
                continue
            
            # Check if video file
            if file_path.suffix.lower() not in ['.mp4', '.mov', '.m4v', '.avi']:
                continue
            
            # Check modification time
            mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mod_time >= cutoff_time:
                recent_files.append(file_path)
        
        return recent_files
    
    def watch_for_device_connection(self, callback: Callable[[List[Path]], None], poll_interval: int = 5):
        """
        Watch for iPhone connections and auto-import when detected
        
        Args:
            callback: Function to call with list of imported videos
            poll_interval: How often to check for devices (seconds)
        """
        logger.info(f"Watching for iPhone connections (checking every {poll_interval}s)")
        last_device_count = 0
        
        try:
            while True:
                devices = self.list_connected_devices()
                device_count = len(devices)
                
                # New device connected
                if device_count > last_device_count:
                    logger.info("iPhone connected! Starting import...")
                    
                    # Wait a moment for device to fully initialize
                    time.sleep(2)
                    
                    # Import videos
                    imported_files = self.import_videos_from_device()
                    
                    if imported_files:
                        try:
                            callback(imported_files)
                        except Exception as e:
                            logger.error(f"Error in callback: {e}")
                
                last_device_count = device_count
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Device watch stopped by user")
        except Exception as e:
            logger.error(f"Error in watch loop: {e}")
            raise
    
    def import_specific_files(self, file_names: List[str]) -> List[Path]:
        """
        Import specific files from connected device
        
        Args:
            file_names: List of file names to import
            
        Returns:
            List of imported file paths
        """
        # Implementation would use Image Capture scripting
        # to selectively import files
        logger.info(f"Importing {len(file_names)} specific files...")
        # TODO: Implement selective import
        return []
    
    def delete_after_import(self, device_name: Optional[str] = None) -> bool:
        """
        Delete videos from device after successful import
        
        Args:
            device_name: Device to delete from
            
        Returns:
            True if successful
        """
        logger.warning("Auto-delete not implemented - manual deletion recommended for safety")
        return False
