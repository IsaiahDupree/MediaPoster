"""
Scene Detection and Scoring
Identifies distinct scenes and rates them for highlight potential
"""
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from loguru import logger
import statistics


class SceneDetector:
    """Detect and score video scenes for highlight potential"""
    
    def __init__(self, min_scene_duration: float = 2.0, max_scene_duration: float = 60.0):
        """
        Initialize scene detector
        
        Args:
            min_scene_duration: Minimum scene length in seconds
            max_scene_duration: Maximum scene length for highlights
        """
        self.min_scene_duration = min_scene_duration
        self.max_scene_duration = max_scene_duration
        
        logger.info(f"Scene detector initialized (min: {min_scene_duration}s, max: {max_scene_duration}s)")
    
    def detect_scenes(
        self,
        video_path: Path,
        threshold: float = 0.3,
        min_change_frames: int = 5
    ) -> List[Dict]:
        """
        Detect scene changes in video
        
        Args:
            video_path: Path to video file
            threshold: Scene change sensitivity (0.0-1.0, lower = more sensitive)
            min_change_frames: Minimum frames between scene changes
            
        Returns:
            List of scenes with timestamps and metadata
        """
        logger.info(f"Detecting scenes in {video_path.name}")
        
        # Get video duration first
        duration = self._get_duration(video_path)
        
        # Detect scene changes with FFmpeg
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
            
            # Parse scene changes
            scene_changes = []
            for line in result.stderr.split('\n'):
                if 'Parsed_showinfo' in line and 'pts_time:' in line:
                    try:
                        timestamp_str = line.split('pts_time:')[1].split()[0]
                        timestamp = float(timestamp_str)
                        
                        # Extract scene score if available
                        score = threshold
                        if 'scene:' in line:
                            score_str = line.split('scene:')[1].split()[0]
                            score = float(score_str)
                        
                        scene_changes.append({
                            'timestamp': timestamp,
                            'score': score
                        })
                    except (IndexError, ValueError):
                        continue
            
            # Convert scene changes to scenes with durations
            scenes = self._build_scenes_from_changes(scene_changes, duration)
            
            logger.success(f"✓ Detected {len(scenes)} scenes")
            return scenes
            
        except subprocess.TimeoutExpired:
            logger.error("Scene detection timed out")
            return []
        except Exception as e:
            logger.error(f"Scene detection failed: {e}")
            return []
    
    def _build_scenes_from_changes(
        self,
        scene_changes: List[Dict],
        duration: float
    ) -> List[Dict]:
        """Build scene objects from change timestamps"""
        if not scene_changes:
            # No scene changes = single scene
            return [{
                'start': 0.0,
                'end': duration,
                'duration': duration,
                'scene_id': 0,
                'change_score': 0.0
            }]
        
        scenes = []
        
        # First scene (start to first change)
        scenes.append({
            'start': 0.0,
            'end': scene_changes[0]['timestamp'],
            'duration': scene_changes[0]['timestamp'],
            'scene_id': 0,
            'change_score': scene_changes[0]['score']
        })
        
        # Middle scenes
        for i in range(len(scene_changes) - 1):
            start = scene_changes[i]['timestamp']
            end = scene_changes[i + 1]['timestamp']
            duration_val = end - start
            
            scenes.append({
                'start': start,
                'end': end,
                'duration': duration_val,
                'scene_id': i + 1,
                'change_score': scene_changes[i + 1]['score']
            })
        
        # Last scene (last change to end)
        if scene_changes:
            last_change = scene_changes[-1]['timestamp']
            scenes.append({
                'start': last_change,
                'end': duration,
                'duration': duration - last_change,
                'scene_id': len(scene_changes),
                'change_score': 0.0
            })
        
        return scenes
    
    def score_scenes(
        self,
        scenes: List[Dict],
        audio_peaks: Optional[List[Dict]] = None,
        transcript_segments: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Score scenes for highlight potential
        
        Args:
            scenes: List of detected scenes
            audio_peaks: Audio peak timestamps
            transcript_segments: Transcript segments with text
            
        Returns:
            Scenes with added highlight_score
        """
        logger.info(f"Scoring {len(scenes)} scenes for highlight potential")
        
        for scene in scenes:
            score = 0.0
            factors = []
            
            # 1. Duration score (prefer 10-30 second scenes)
            duration_score = self._score_duration(scene['duration'])
            score += duration_score * 0.3
            factors.append(f"duration:{duration_score:.2f}")
            
            # 2. Scene change intensity (higher = more dynamic)
            change_score = min(scene['change_score'] / 0.5, 1.0)  # Normalize
            score += change_score * 0.2
            factors.append(f"change:{change_score:.2f}")
            
            # 3. Audio activity (peaks in this scene)
            if audio_peaks:
                audio_score = self._score_audio_activity(scene, audio_peaks)
                score += audio_score * 0.3
                factors.append(f"audio:{audio_score:.2f}")
            
            # 4. Speech density (transcript coverage)
            if transcript_segments:
                speech_score = self._score_speech_density(scene, transcript_segments)
                score += speech_score * 0.2
                factors.append(f"speech:{speech_score:.2f}")
            
            scene['highlight_score'] = min(score, 1.0)  # Cap at 1.0
            scene['score_factors'] = factors
        
        # Sort by score
        scenes.sort(key=lambda x: x['highlight_score'], reverse=True)
        
        logger.success(f"✓ Scene scoring complete")
        return scenes
    
    def _score_duration(self, duration: float) -> float:
        """Score based on ideal duration (10-30 seconds)"""
        if duration < self.min_scene_duration:
            return 0.0
        elif duration > self.max_scene_duration:
            return 0.3
        elif 10 <= duration <= 30:
            return 1.0
        elif duration < 10:
            return duration / 10.0
        else:
            return max(0.3, 1.0 - (duration - 30) / 60.0)
    
    def _score_audio_activity(
        self,
        scene: Dict,
        audio_peaks: List[Dict]
    ) -> float:
        """Score based on audio peaks in scene"""
        peaks_in_scene = [
            p for p in audio_peaks
            if scene['start'] <= p['timestamp'] <= scene['end']
        ]
        
        if not peaks_in_scene:
            return 0.0
        
        # More peaks = more energy = better highlight
        peak_density = len(peaks_in_scene) / scene['duration']
        
        # Ideal: 0.5-1.5 peaks per second
        if 0.5 <= peak_density <= 1.5:
            return 1.0
        elif peak_density > 1.5:
            return 0.8  # Too chaotic
        else:
            return min(peak_density / 0.5, 1.0)
    
    def _score_speech_density(
        self,
        scene: Dict,
        transcript_segments: List[Dict]
    ) -> float:
        """Score based on speech coverage in scene"""
        segments_in_scene = [
            seg for seg in transcript_segments
            if scene['start'] <= seg.get('start', 0) <= scene['end']
        ]
        
        if not segments_in_scene:
            return 0.0
        
        # Calculate speech coverage
        total_speech_duration = sum(
            seg.get('end', seg.get('start', 0)) - seg.get('start', 0)
            for seg in segments_in_scene
        )
        
        speech_ratio = total_speech_duration / scene['duration']
        
        # Ideal: 70-90% speech coverage
        if 0.7 <= speech_ratio <= 0.9:
            return 1.0
        elif speech_ratio > 0.9:
            return 0.9  # Too dense
        else:
            return speech_ratio / 0.7
    
    def find_best_scenes(
        self,
        scenes: List[Dict],
        min_score: float = 0.5,
        max_scenes: int = 10
    ) -> List[Dict]:
        """
        Filter to best scenes for highlights
        
        Args:
            scenes: Scored scenes
            min_score: Minimum highlight score
            max_scenes: Maximum scenes to return
            
        Returns:
            Top scenes for highlights
        """
        # Filter by minimum score
        good_scenes = [s for s in scenes if s['highlight_score'] >= min_score]
        
        # Sort by score and limit
        good_scenes.sort(key=lambda x: x['highlight_score'], reverse=True)
        
        logger.info(f"Found {len(good_scenes)} scenes above {min_score} threshold")
        
        return good_scenes[:max_scenes]
    
    def merge_short_scenes(
        self,
        scenes: List[Dict],
        min_duration: float = 5.0
    ) -> List[Dict]:
        """
        Merge very short scenes with neighbors
        
        Args:
            scenes: List of scenes
            min_duration: Minimum scene duration
            
        Returns:
            Merged scenes
        """
        if not scenes:
            return []
        
        merged = []
        current = scenes[0].copy()
        
        for next_scene in scenes[1:]:
            if current['duration'] < min_duration:
                # Merge with next
                current['end'] = next_scene['end']
                current['duration'] = current['end'] - current['start']
                current['change_score'] = max(current['change_score'], next_scene['change_score'])
            else:
                merged.append(current)
                current = next_scene.copy()
        
        # Add last scene
        merged.append(current)
        
        logger.info(f"Merged scenes: {len(scenes)} → {len(merged)}")
        return merged
    
    def _get_duration(self, video_path: Path) -> float:
        """Get video duration"""
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


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python scene_detector.py <video_file>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    if not video_path.exists():
        print(f"Video file not found: {video_path}")
        sys.exit(1)
    
    # Test scene detection
    detector = SceneDetector()
    
    print("\n" + "="*60)
    print("SCENE DETECTION TEST")
    print("="*60)
    
    # Detect scenes
    scenes = detector.detect_scenes(video_path, threshold=0.3)
    
    print(f"\n✓ Detected {len(scenes)} scenes")
    print("\nTop 10 scenes:")
    for i, scene in enumerate(scenes[:10]):
        print(f"\n  Scene {i+1}:")
        print(f"    Time: {scene['start']:.1f}s - {scene['end']:.1f}s ({scene['duration']:.1f}s)")
        print(f"    Change score: {scene['change_score']:.3f}")
    
    # Score scenes
    scored_scenes = detector.score_scenes(scenes)
    
    print("\n" + "="*60)
    print("TOP SCENES FOR HIGHLIGHTS")
    print("="*60)
    
    for i, scene in enumerate(scored_scenes[:5]):
        print(f"\n  #{i+1} - Score: {scene['highlight_score']:.2f}")
        print(f"    Time: {scene['start']:.1f}s - {scene['end']:.1f}s ({scene['duration']:.1f}s)")
        print(f"    Factors: {', '.join(scene.get('score_factors', []))}")
