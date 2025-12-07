"""
Frame Extraction Service
Extracts key frames and scenes from videos using FFmpeg
"""
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger
import shutil


class FrameExtractor:
    """Extract frames from videos for visual analysis"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize frame extractor
        
        Args:
            output_dir: Directory to save extracted frames
        """
        self.output_dir = output_dir or Path("/tmp/mediaposter/frames")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Frame extractor initialized: {self.output_dir}")
    
    def extract_frames_at_interval(
        self,
        video_path: Path,
        fps: float = 1.0,
        max_frames: Optional[int] = None
    ) -> List[Path]:
        """
        Extract frames at regular intervals
        
        Args:
            video_path: Path to video file
            fps: Frames per second to extract (1 = one frame per second)
            max_frames: Maximum number of frames to extract
            
        Returns:
            List of paths to extracted frame images
        """
        logger.info(f"Extracting frames from {video_path.name} at {fps} fps")
        
        # Create output directory for this video
        video_frames_dir = self.output_dir / video_path.stem
        if video_frames_dir.exists():
            shutil.rmtree(video_frames_dir)
        video_frames_dir.mkdir(parents=True)
        
        output_pattern = str(video_frames_dir / "frame_%04d.jpg")
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vf', f'fps={fps}',
            '-q:v', '2',  # High quality
        ]
        
        if max_frames:
            cmd.extend(['-vframes', str(max_frames)])
        
        cmd.extend(['-y', output_pattern])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")
            
            # Get list of extracted frames
            frames = sorted(video_frames_dir.glob("frame_*.jpg"))
            
            logger.success(f"✓ Extracted {len(frames)} frames")
            return frames
            
        except subprocess.TimeoutExpired:
            logger.error("Frame extraction timed out")
            raise
        except Exception as e:
            logger.error(f"Failed to extract frames: {e}")
            raise
    
    def extract_key_frames(
        self,
        video_path: Path,
        threshold: float = 0.4,
        max_frames: Optional[int] = 30
    ) -> List[Dict]:
        """
        Extract key frames based on scene changes
        
        Args:
            video_path: Path to video file
            threshold: Scene change detection threshold (0.0-1.0)
            max_frames: Maximum number of frames to extract
            
        Returns:
            List of dicts with frame path and timestamp
        """
        logger.info(f"Detecting key frames in {video_path.name}")
        
        # First, detect scene changes
        scenes = self.detect_scenes(video_path, threshold)
        
        if not scenes:
            logger.warning("No scene changes detected, using interval extraction")
            frames = self.extract_frames_at_interval(video_path, fps=0.5, max_frames=max_frames)
            return [{'path': f, 'timestamp': i * 2.0} for i, f in enumerate(frames)]
        
        # Limit to max_frames
        if max_frames and len(scenes) > max_frames:
            # Sample evenly
            step = len(scenes) / max_frames
            scenes = [scenes[int(i * step)] for i in range(max_frames)]
        
        # Extract frame at each scene change
        video_frames_dir = self.output_dir / video_path.stem
        video_frames_dir.mkdir(parents=True, exist_ok=True)
        
        key_frames = []
        for i, scene in enumerate(scenes):
            timestamp = scene['timestamp']
            output_path = video_frames_dir / f"key_frame_{i:04d}.jpg"
            
            if self._extract_frame_at_timestamp(video_path, timestamp, output_path):
                key_frames.append({
                    'path': output_path,
                    'timestamp': timestamp,
                    'score': scene.get('score', 0.0)
                })
        
        logger.success(f"✓ Extracted {len(key_frames)} key frames")
        return key_frames
    
    def detect_scenes(
        self,
        video_path: Path,
        threshold: float = 0.4
    ) -> List[Dict]:
        """
        Detect scene changes in video
        
        Args:
            video_path: Path to video file
            threshold: Scene detection threshold (0.0-1.0, lower = more sensitive)
            
        Returns:
            List of scene change timestamps with scores
        """
        logger.info(f"Detecting scenes in {video_path.name}")
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vf', f'select=gt(scene\\,{threshold}),showinfo',
            '-f', 'null',
            '-'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse scene detection output
            scenes = []
            for line in result.stderr.split('\n'):
                if 'Parsed_showinfo' in line and 'pts_time:' in line:
                    # Extract timestamp
                    try:
                        timestamp_str = line.split('pts_time:')[1].split()[0]
                        timestamp = float(timestamp_str)
                        
                        # Extract scene score if available
                        score = threshold
                        if 'scene:' in line:
                            score_str = line.split('scene:')[1].split()[0]
                            score = float(score_str)
                        
                        scenes.append({
                            'timestamp': timestamp,
                            'score': score
                        })
                    except (IndexError, ValueError):
                        continue
            
            logger.success(f"✓ Detected {len(scenes)} scene changes")
            return scenes
            
        except subprocess.TimeoutExpired:
            logger.error("Scene detection timed out")
            return []
        except Exception as e:
            logger.error(f"Scene detection failed: {e}")
            return []
    
    def _extract_frame_at_timestamp(
        self,
        video_path: Path,
        timestamp: float,
        output_path: Path
    ) -> bool:
        """Extract a single frame at specific timestamp"""
        cmd = [
            'ffmpeg',
            '-ss', str(timestamp),
            '-i', str(video_path),
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            return result.returncode == 0
        except:
            return False
    
    def get_video_duration(self, video_path: Path) -> float:
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
                timeout=30
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data['format']['duration'])
        except:
            pass
        
        return 0.0
    
    def extract_thumbnails(
        self,
        video_path: Path,
        timestamps: List[float]
    ) -> List[Path]:
        """
        Extract frames at specific timestamps (for thumbnails)
        
        Args:
            video_path: Path to video file
            timestamps: List of timestamps in seconds
            
        Returns:
            List of paths to extracted thumbnails
        """
        logger.info(f"Extracting {len(timestamps)} thumbnails")
        
        video_frames_dir = self.output_dir / video_path.stem
        video_frames_dir.mkdir(parents=True, exist_ok=True)
        
        thumbnails = []
        for i, timestamp in enumerate(timestamps):
            output_path = video_frames_dir / f"thumbnail_{i:04d}.jpg"
            
            if self._extract_frame_at_timestamp(video_path, timestamp, output_path):
                thumbnails.append(output_path)
        
        logger.success(f"✓ Extracted {len(thumbnails)} thumbnails")
        return thumbnails
    
    def cleanup(self, video_stem: Optional[str] = None):
        """
        Clean up extracted frames
        
        Args:
            video_stem: Specific video to cleanup, or None for all
        """
        if video_stem:
            video_dir = self.output_dir / video_stem
            if video_dir.exists():
                shutil.rmtree(video_dir)
                logger.info(f"Cleaned up frames for {video_stem}")
        else:
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
                self.output_dir.mkdir(parents=True)
                logger.info("Cleaned up all frames")


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python frame_extractor.py <video_file>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    if not video_path.exists():
        print(f"Video file not found: {video_path}")
        sys.exit(1)
    
    # Test frame extraction
    extractor = FrameExtractor()
    
    print("\n" + "="*60)
    print("FRAME EXTRACTION TEST")
    print("="*60)
    
    # Test 1: Extract frames at interval
    print("\n1. Extracting frames at 1fps...")
    frames = extractor.extract_frames_at_interval(video_path, fps=1.0, max_frames=10)
    print(f"✓ Extracted {len(frames)} frames")
    for i, frame in enumerate(frames[:3]):
        print(f"  Frame {i+1}: {frame.name}")
    
    # Test 2: Detect scenes and extract key frames
    print("\n2. Detecting scenes and extracting key frames...")
    key_frames = extractor.extract_key_frames(video_path, threshold=0.3, max_frames=15)
    print(f"✓ Extracted {len(key_frames)} key frames")
    for i, kf in enumerate(key_frames[:5]):
        print(f"  Key frame {i+1}: {kf['path'].name} at {kf['timestamp']:.2f}s")
    
    # Test 3: Get video duration
    duration = extractor.get_video_duration(video_path)
    print(f"\n3. Video duration: {duration:.1f}s")
    
    print(f"\n✓ All frames saved to: {extractor.output_dir}")
