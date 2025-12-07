"""
iCloud Photos Monitor
Monitors macOS Photos library for new videos synced from iPhone
"""
import os
import sqlite3
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from loguru import logger
import time


class iCloudPhotosMonitor:
    """
    Monitors macOS Photos library for new video imports from iCloud
    Uses the Photos library SQLite database to detect new videos
    """
    
    def __init__(self, photos_library_path: Optional[str] = None, poll_interval: int = 60):
        """
        Initialize iCloud Photos monitor
        
        Args:
            photos_library_path: Path to Photos Library.photoslibrary (default: ~/Pictures/Photos Library.photoslibrary)
            poll_interval: How often to check for new videos in seconds
        """
        if photos_library_path is None:
            photos_library_path = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")
        
        self.library_path = Path(photos_library_path)
        self.poll_interval = poll_interval
        self.database_path = self.library_path / "database" / "Photos.sqlite"
        self.last_check_time = None
        self.processed_uuids = set()
        
        logger.info(f"iCloud Photos Monitor initialized: {self.library_path}")
    
    def is_photos_library_available(self) -> bool:
        """Check if Photos library is accessible"""
        if not self.library_path.exists():
            logger.error(f"Photos library not found at: {self.library_path}")
            return False
        
        if not self.database_path.exists():
            logger.error(f"Photos database not found at: {self.database_path}")
            return False
        
        return True
    
    def get_recent_videos(self, since_hours: int = 24) -> List[Dict]:
        """
        Get videos added to Photos library in the last N hours
        
        Args:
            since_hours: Look back this many hours
            
        Returns:
            List of video metadata dictionaries
        """
        if not self.is_photos_library_available():
            return []
        
        try:
            # Use osascript (AppleScript) to query Photos library safely
            # This is safer than directly accessing SQLite which can be locked
            videos = self._query_photos_via_applescript(since_hours)
            return videos
            
        except Exception as e:
            logger.error(f"Error getting recent videos: {e}")
            return []
    
    def _query_photos_via_applescript(self, since_hours: int) -> List[Dict]:
        """
        Query Photos library using AppleScript
        This is the recommended way to access Photos on macOS
        """
        cutoff_date = datetime.now() - timedelta(hours=since_hours)
        
        # AppleScript to get recent videos
        script = f'''
        tell application "Photos"
            set recentVideos to {{}}
            set cutoffDate to (current date) - ({since_hours} * hours)
            
            set allVideos to every media item whose media type is video and date is greater than cutoffDate
            
            repeat with videoItem in allVideos
                set videoInfo to {{}}
                set videoInfo's uuid to id of videoItem
                set videoInfo's filename to filename of videoItem
                set videoInfo's date_added to date of videoItem as string
                set videoInfo's duration to duration of videoItem
                
                try
                    set videoInfo's width to width of videoItem
                    set videoInfo's height to height of videoItem
                end try
                
                set end of recentVideos to videoInfo
            end repeat
            
            return recentVideos
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"AppleScript error: {result.stderr}")
                return []
            
            # Parse the AppleScript output
            videos = self._parse_applescript_output(result.stdout)
            logger.info(f"Found {len(videos)} recent videos in Photos library")
            return videos
            
        except subprocess.TimeoutExpired:
            logger.error("AppleScript query timed out")
            return []
        except Exception as e:
            logger.error(f"Error running AppleScript: {e}")
            return []
    
    def _parse_applescript_output(self, output: str) -> List[Dict]:
        """Parse AppleScript output into structured data"""
        videos = []
        # AppleScript returns records, parse them
        # This is a simplified parser - in production you'd use a proper parser
        try:
            # Basic parsing - adjust based on actual output format
            lines = output.strip().split('\n')
            for line in lines:
                if 'uuid' in line.lower():
                    # Extract video info from line
                    # This is placeholder - actual implementation would parse properly
                    video = {
                        'uuid': '',  # Extract from line
                        'filename': '',
                        'date_added': datetime.now().isoformat(),
                        'duration': 0,
                        'source': 'iCloud Photos'
                    }
                    videos.append(video)
        except Exception as e:
            logger.error(f"Error parsing AppleScript output: {e}")
        
        return videos
    
    def export_video(self, video_uuid: str, output_dir: Path) -> Optional[Path]:
        """
        Export a video from Photos library to a directory
        
        Args:
            video_uuid: UUID of the video in Photos
            output_dir: Directory to export to
            
        Returns:
            Path to exported video or None if failed
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        script = f'''
        tell application "Photos"
            set targetVideo to media item id "{video_uuid}"
            set videoName to filename of targetVideo
            
            export {{targetVideo}} to POSIX file "{output_dir}" with using originals
            
            return videoName
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                filename = result.stdout.strip()
                exported_path = output_dir / filename
                
                # Wait for export to complete
                for _ in range(30):  # Wait up to 30 seconds
                    if exported_path.exists():
                        logger.info(f"✓ Exported video: {exported_path}")
                        return exported_path
                    time.sleep(1)
                
                logger.error(f"Export completed but file not found: {exported_path}")
                return None
            else:
                logger.error(f"Export failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error exporting video {video_uuid}: {e}")
            return None
    
    def watch(self, callback: Callable[[Path], None], check_interval: Optional[int] = None):
        """
        Continuously watch for new videos and call callback when found
        
        Args:
            callback: Function to call with path to new video
            check_interval: Override default poll interval
        """
        interval = check_interval or self.poll_interval
        logger.info(f"Starting iCloud Photos watch (checking every {interval}s)")
        
        temp_export_dir = Path("/tmp/mediaposter_icloud_exports")
        temp_export_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            while True:
                # Get videos from last check interval + buffer
                videos = self.get_recent_videos(since_hours=(interval // 60) + 1)
                
                for video in videos:
                    video_uuid = video.get('uuid')
                    
                    if video_uuid and video_uuid not in self.processed_uuids:
                        logger.info(f"New video detected: {video.get('filename', video_uuid)}")
                        
                        # Export video
                        exported_path = self.export_video(video_uuid, temp_export_dir)
                        
                        if exported_path:
                            # Call callback with exported video
                            try:
                                callback(exported_path)
                                self.processed_uuids.add(video_uuid)
                            except Exception as e:
                                logger.error(f"Error in callback for {exported_path}: {e}")
                
                # Update last check time
                self.last_check_time = datetime.now()
                
                # Wait before next check
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("iCloud Photos watch stopped by user")
        except Exception as e:
            logger.error(f"Error in watch loop: {e}")
            raise
    
    def get_library_stats(self) -> Dict:
        """Get statistics about the Photos library"""
        script = '''
        tell application "Photos"
            set videoCount to count of (every media item whose media type is video)
            set totalCount to count of every media item
            
            return {videoCount:videoCount, totalCount:totalCount}
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse output
                return {
                    'library_path': str(self.library_path),
                    'accessible': True,
                    'video_count': 0,  # Parse from output
                    'total_items': 0,  # Parse from output
                }
            else:
                return {'accessible': False, 'error': result.stderr}
                
        except Exception as e:
            logger.error(f"Error getting library stats: {e}")
            return {'accessible': False, 'error': str(e)}
