"""
Video Editor - Core FFmpeg Operations
Handles video cutting, cropping, and format conversion
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger
from datetime import timedelta


class VideoEditor:
    """Core video editing operations using FFmpeg"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize video editor
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir or Path("./clips")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Video editor initialized, output: {self.output_dir}")
    
    def extract_clip(
        self,
        video_path: Path,
        start_time: float,
        duration: float,
        output_path: Optional[Path] = None,
        exact_cut: bool = True
    ) -> Path:
        """
        Extract a clip from video
        
        Args:
            video_path: Source video path
            start_time: Start time in seconds
            duration: Clip duration in seconds
            output_path: Output file path
            exact_cut: Use exact frame cutting (slower but precise)
            
        Returns:
            Path to extracted clip
        """
        if output_path is None:
            output_path = self.output_dir / f"clip_{start_time:.1f}_{duration:.1f}.mp4"
        
        logger.info(f"Extracting clip: {start_time:.1f}s for {duration:.1f}s")
        
        # Build FFmpeg command
        cmd = ['ffmpeg', '-y']
        
        if exact_cut:
            # Precise cutting (slower)
            cmd.extend([
                '-i', str(video_path),
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-strict', 'experimental'
            ])
        else:
            # Fast cutting (seek before input)
            cmd.extend([
                '-ss', str(start_time),
                '-i', str(video_path),
                '-t', str(duration),
                '-c', 'copy'
            ])
        
        cmd.append(str(output_path))
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise Exception(f"Clip extraction failed: {result.stderr}")
            
            logger.success(f"✓ Clip extracted: {output_path}")
            return output_path
            
        except subprocess.TimeoutExpired:
            logger.error("Clip extraction timed out")
            raise
        except Exception as e:
            logger.error(f"Clip extraction failed: {e}")
            raise
    
    def convert_to_vertical(
        self,
        video_path: Path,
        output_path: Optional[Path] = None,
        target_aspect: str = "9:16",
        crop_mode: str = "smart"
    ) -> Path:
        """
        Convert video to vertical format (9:16)
        
        Args:
            video_path: Source video path
            output_path: Output file path
            target_aspect: Target aspect ratio (9:16, 1:1, etc.)
            crop_mode: 'center', 'smart', or 'blur'
            
        Returns:
            Path to converted video
        """
        if output_path is None:
            output_path = self.output_dir / f"{video_path.stem}_vertical.mp4"
        
        logger.info(f"Converting to vertical: {crop_mode} mode")
        
        # Get video dimensions
        width, height = self._get_video_dimensions(video_path)
        
        # Calculate target dimensions (1080x1920 for 9:16)
        target_width = 1080
        target_height = 1920
        
        if crop_mode == "center":
            # Simple center crop
            filters = self._build_center_crop_filter(
                width, height, target_width, target_height
            )
        elif crop_mode == "smart":
            # Smart crop with scaling
            filters = self._build_smart_crop_filter(
                width, height, target_width, target_height
            )
        elif crop_mode == "blur":
            # Blur background with centered content
            filters = self._build_blur_background_filter(
                width, height, target_width, target_height
            )
        else:
            raise ValueError(f"Unknown crop_mode: {crop_mode}")
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', filters,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise Exception(f"Vertical conversion failed: {result.stderr}")
            
            logger.success(f"✓ Converted to vertical: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Vertical conversion failed: {e}")
            raise
    
    def _build_center_crop_filter(
        self,
        src_width: int,
        src_height: int,
        target_width: int,
        target_height: int
    ) -> str:
        """Build center crop filter"""
        # Calculate crop dimensions to match aspect ratio
        target_aspect = target_width / target_height
        src_aspect = src_width / src_height
        
        if src_aspect > target_aspect:
            # Source is wider, crop width
            crop_width = int(src_height * target_aspect)
            crop_height = src_height
            x = (src_width - crop_width) // 2
            y = 0
        else:
            # Source is taller, crop height
            crop_width = src_width
            crop_height = int(src_width / target_aspect)
            x = 0
            y = (src_height - crop_height) // 2
        
        return f"crop={crop_width}:{crop_height}:{x}:{y},scale={target_width}:{target_height}"
    
    def _build_smart_crop_filter(
        self,
        src_width: int,
        src_height: int,
        target_width: int,
        target_height: int
    ) -> str:
        """Build smart crop filter (scales then crops)"""
        target_aspect = target_width / target_height
        src_aspect = src_width / src_height
        
        if src_aspect > target_aspect:
            # Scale to target height, then crop width
            scale_height = target_height
            scale_width = int(src_width * (target_height / src_height))
            crop_x = (scale_width - target_width) // 2
            return f"scale={scale_width}:{scale_height},crop={target_width}:{target_height}:{crop_x}:0"
        else:
            # Scale to target width, then crop height
            scale_width = target_width
            scale_height = int(src_height * (target_width / src_width))
            crop_y = (scale_height - target_height) // 2
            return f"scale={scale_width}:{scale_height},crop={target_width}:{target_height}:0:{crop_y}"
    
    def _build_blur_background_filter(
        self,
        src_width: int,
        src_height: int,
        target_width: int,
        target_height: int
    ) -> str:
        """Build blur background filter (letterbox with blurred bg)"""
        # Scale content to fit vertically
        scale_height = target_height
        scale_width = int(src_width * (target_height / src_height))
        
        if scale_width > target_width:
            # If still too wide, fit to width instead
            scale_width = target_width
            scale_height = int(src_height * (target_width / src_width))
        
        # Complex filter: blur background + overlay centered content
        return (
            f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"boxblur=20:5[bg];"
            f"[0:v]scale={scale_width}:{scale_height}[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
    
    def add_fade_transitions(
        self,
        video_path: Path,
        output_path: Optional[Path] = None,
        fade_in_duration: float = 0.5,
        fade_out_duration: float = 0.5
    ) -> Path:
        """
        Add fade in/out transitions
        
        Args:
            video_path: Source video
            output_path: Output path
            fade_in_duration: Fade in duration (seconds)
            fade_out_duration: Fade out duration (seconds)
            
        Returns:
            Path to video with fades
        """
        if output_path is None:
            output_path = self.output_dir / f"{video_path.stem}_faded.mp4"
        
        # Get video duration
        duration = self._get_video_duration(video_path)
        fade_out_start = duration - fade_out_duration
        
        filter_str = f"fade=t=in:st=0:d={fade_in_duration},fade=t=out:st={fade_out_start}:d={fade_out_duration}"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', filter_str,
            '-c:v', 'libx264',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=300, check=True)
            logger.success(f"✓ Added fade transitions: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to add fades: {e}")
            raise
    
    def adjust_speed(
        self,
        video_path: Path,
        speed_factor: float,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Adjust video playback speed
        
        Args:
            video_path: Source video
            speed_factor: Speed multiplier (0.5 = half speed, 2.0 = double speed)
            output_path: Output path
            
        Returns:
            Path to speed-adjusted video
        """
        if output_path is None:
            output_path = self.output_dir / f"{video_path.stem}_speed{speed_factor}.mp4"
        
        logger.info(f"Adjusting speed: {speed_factor}x")
        
        # Calculate PTS (presentation timestamp) multiplier
        pts_factor = 1.0 / speed_factor
        atempo_factor = speed_factor
        
        # Audio tempo filter (supports 0.5x to 2.0x)
        if 0.5 <= atempo_factor <= 2.0:
            audio_filter = f"atempo={atempo_factor}"
        elif atempo_factor < 0.5:
            # Chain multiple atempo filters
            audio_filter = f"atempo=0.5,atempo={atempo_factor/0.5}"
        else:
            # Chain for > 2x
            audio_filter = f"atempo=2.0,atempo={atempo_factor/2.0}"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-filter_complex',
            f"[0:v]setpts={pts_factor}*PTS[v];[0:a]{audio_filter}[a]",
            '-map', '[v]',
            '-map', '[a]',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=300, check=True)
            logger.success(f"✓ Speed adjusted: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Speed adjustment failed: {e}")
            raise
    
    def concatenate_clips(
        self,
        clip_paths: List[Path],
        output_path: Optional[Path] = None,
        add_transitions: bool = True
    ) -> Path:
        """
        Concatenate multiple clips
        
        Args:
            clip_paths: List of clip paths
            output_path: Output path
            add_transitions: Add cross-fade transitions
            
        Returns:
            Path to concatenated video
        """
        if output_path is None:
            output_path = self.output_dir / "concatenated.mp4"
        
        logger.info(f"Concatenating {len(clip_paths)} clips")
        
        if not add_transitions:
            # Simple concatenation using concat demuxer
            concat_file = self.output_dir / "concat_list.txt"
            with open(concat_file, 'w') as f:
                for clip in clip_paths:
                    f.write(f"file '{clip.absolute()}'\n")
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                str(output_path)
            ]
        else:
            # Complex filter with crossfades
            filter_complex = self._build_crossfade_filter(clip_paths)
            
            cmd = [
                'ffmpeg', '-y'
            ]
            
            # Add all input files
            for clip in clip_paths:
                cmd.extend(['-i', str(clip)])
            
            cmd.extend([
                '-filter_complex', filter_complex,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                str(output_path)
            ])
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=600, check=True)
            logger.success(f"✓ Clips concatenated: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Concatenation failed: {e}")
            raise
    
    def _build_crossfade_filter(
        self,
        clip_paths: List[Path],
        transition_duration: float = 0.5
    ) -> str:
        """Build complex filter for crossfade transitions"""
        if len(clip_paths) < 2:
            return "[0:v]copy[v];[0:a]copy[a]"
        
        # Build xfade filter chain
        filter_parts = []
        
        # Get durations
        durations = [self._get_video_duration(p) for p in clip_paths]
        
        # Build filter
        offset = 0
        for i in range(len(clip_paths) - 1):
            if i == 0:
                filter_parts.append(f"[0:v][1:v]xfade=transition=fade:duration={transition_duration}:offset={durations[0]-transition_duration}[v{i}]")
            else:
                offset += durations[i] - transition_duration
                filter_parts.append(f"[v{i-1}][{i+1}:v]xfade=transition=fade:duration={transition_duration}:offset={offset}[v{i}]")
        
        video_filter = ";".join(filter_parts)
        
        # Audio mixing (simple concat)
        audio_filter = f"{''.join([f'[{i}:a]' for i in range(len(clip_paths))])}concat=n={len(clip_paths)}:v=0:a=1[a]"
        
        return f"{video_filter};{audio_filter}"
    
    def _get_video_dimensions(self, video_path: Path) -> Tuple[int, int]:
        """Get video width and height"""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'json',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            
            data = json.loads(result.stdout)
            stream = data['streams'][0]
            return stream['width'], stream['height']
            
        except Exception as e:
            logger.error(f"Failed to get dimensions: {e}")
            return 1920, 1080  # Default
    
    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds"""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
            
        except Exception as e:
            logger.error(f"Failed to get duration: {e}")
            return 0.0
    
    def optimize_for_social(
        self,
        video_path: Path,
        platform: str = "tiktok",
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Optimize video for specific social platform
        
        Args:
            video_path: Source video
            platform: 'tiktok', 'instagram', 'youtube_shorts'
            output_path: Output path
            
        Returns:
            Optimized video path
        """
        if output_path is None:
            output_path = self.output_dir / f"{video_path.stem}_{platform}.mp4"
        
        logger.info(f"Optimizing for {platform}")
        
        # Platform-specific settings
        settings = {
            'tiktok': {
                'video_bitrate': '5000k',
                'audio_bitrate': '128k',
                'max_size_mb': 287,
                'frame_rate': 30
            },
            'instagram': {
                'video_bitrate': '3500k',
                'audio_bitrate': '128k',
                'max_size_mb': 100,
                'frame_rate': 30
            },
            'youtube_shorts': {
                'video_bitrate': '8000k',
                'audio_bitrate': '192k',
                'max_size_mb': 256,
                'frame_rate': 60
            }
        }
        
        config = settings.get(platform, settings['tiktok'])
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-c:v', 'libx264',
            '-b:v', config['video_bitrate'],
            '-maxrate', config['video_bitrate'],
            '-bufsize', str(int(config['video_bitrate'].rstrip('k')) * 2) + 'k',
            '-r', str(config['frame_rate']),
            '-c:a', 'aac',
            '-b:a', config['audio_bitrate'],
            '-ar', '48000',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=600, check=True)
            logger.success(f"✓ Optimized for {platform}: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            raise


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python video_editor.py <video_file>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    if not video_path.exists():
        print(f"Video not found: {video_path}")
        sys.exit(1)
    
    editor = VideoEditor()
    
    print("\n" + "="*60)
    print("VIDEO EDITOR TEST")
    print("="*60)
    
    # Test clip extraction
    print("\n1. Extracting 30-second clip...")
    clip = editor.extract_clip(video_path, start_time=10.0, duration=30.0)
    print(f"✓ Clip saved: {clip}")
    
    # Test vertical conversion
    print("\n2. Converting to vertical (9:16)...")
    vertical = editor.convert_to_vertical(clip, crop_mode="blur")
    print(f"✓ Vertical video: {vertical}")
    
    # Test optimization
    print("\n3. Optimizing for TikTok...")
    optimized = editor.optimize_for_social(vertical, platform="tiktok")
    print(f"✓ Optimized: {optimized}")
