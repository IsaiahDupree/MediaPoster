"""
Video Validator
Validates video files and extracts metadata
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger


class VideoValidator:
    """Validates and extracts metadata from video files"""
    
    SUPPORTED_FORMATS = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.mpg', '.mpeg', '.3gp'}
    
    def __init__(self, min_duration: int = 10, max_duration: int = 3600, max_size_mb: int = 500):
        """
        Initialize video validator
        
        Args:
            min_duration: Minimum video duration in seconds
            max_duration: Maximum video duration in seconds
            max_size_mb: Maximum file size in MB
        """
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.max_size_bytes = max_size_mb * 1024 * 1024
        
    def is_video_file(self, file_path: Path) -> bool:
        """Check if file is a supported video format"""
        return file_path.suffix.lower() in self.SUPPORTED_FORMATS
    
    def validate(self, file_path: Path) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate a video file
        
        Returns:
            (is_valid, error_message, metadata)
        """
        if not file_path.exists():
            return False, f"File does not exist: {file_path}", None
        
        if not self.is_video_file(file_path):
            return False, f"Unsupported format: {file_path.suffix}", None
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > self.max_size_bytes:
            return False, f"File too large: {file_size / (1024*1024):.2f}MB > {self.max_size_bytes / (1024*1024):.2f}MB", None
        
        if file_size == 0:
            return False, "File is empty", None
        
        # Extract metadata using ffprobe
        metadata = self.extract_metadata(file_path)
        if not metadata:
            return False, "Failed to extract video metadata", None
        
        # Validate duration
        duration = metadata.get('duration', 0)
        if duration < self.min_duration:
            return False, f"Video too short: {duration}s < {self.min_duration}s", None
        
        if duration > self.max_duration:
            return False, f"Video too long: {duration}s > {self.max_duration}s", None
        
        # Check if video has valid streams
        if not metadata.get('has_video'):
            return False, "No valid video stream found", None
        
        logger.info(f"✓ Video validated: {file_path.name} ({duration:.1f}s, {file_size/(1024*1024):.2f}MB)")
        return True, None, metadata
    
    def extract_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Extract video metadata using ffprobe
        
        Returns:
            Dictionary with video metadata or None if extraction fails
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"ffprobe failed for {file_path}: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            
            # Extract key information
            format_info = data.get('format', {})
            streams = data.get('streams', [])
            
            # Find video and audio streams
            video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
            audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)
            
            if not video_stream:
                return None
            
            metadata = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'file_size_bytes': file_path.stat().st_size,
                'duration': float(format_info.get('duration', 0)),
                'format_name': format_info.get('format_name', ''),
                'bit_rate': int(format_info.get('bit_rate', 0)),
                
                # Video stream info
                'has_video': True,
                'video_codec': video_stream.get('codec_name', ''),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'fps': self._parse_fps(video_stream.get('r_frame_rate', '0/1')),
                'aspect_ratio': f"{video_stream.get('width', 0)}:{video_stream.get('height', 0)}",
                
                # Audio stream info
                'has_audio': audio_stream is not None,
                'audio_codec': audio_stream.get('codec_name', '') if audio_stream else None,
                'sample_rate': int(audio_stream.get('sample_rate', 0)) if audio_stream else None,
                
                # File timestamps
                'created_at': datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            }
            
            # Try to extract creation date from metadata
            tags = format_info.get('tags', {})
            if 'creation_time' in tags:
                metadata['recording_date'] = tags['creation_time']
            
            return metadata
            
        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe timeout for {file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffprobe output for {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            return None
    
    def _parse_fps(self, fps_str: str) -> float:
        """Parse FPS string like '30000/1001' to float"""
        try:
            if '/' in fps_str:
                num, denom = fps_str.split('/')
                return float(num) / float(denom)
            return float(fps_str)
        except:
            return 0.0
    
    def get_video_thumbnail(self, file_path: Path, output_path: Path, time_offset: float = 1.0) -> bool:
        """
        Extract a thumbnail from the video
        
        Args:
            file_path: Path to video file
            output_path: Path to save thumbnail
            time_offset: Time in seconds to extract frame
            
        Returns:
            True if successful
        """
        try:
            cmd = [
                'ffmpeg',
                '-ss', str(time_offset),
                '-i', str(file_path),
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode == 0 and output_path.exists():
                logger.debug(f"Thumbnail created: {output_path}")
                return True
            else:
                logger.error(f"Failed to create thumbnail: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            return False
