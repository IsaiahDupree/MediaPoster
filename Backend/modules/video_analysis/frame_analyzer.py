"""
Frame Sampling & Visual Analysis
Uses OpenCV for frame extraction and optional cloud vision APIs for analysis
"""
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from loguru import logger
import os
import cv2
import numpy as np
from pathlib import Path


@dataclass
class FrameData:
    """Single frame with metadata"""
    frame_number: int
    time_s: float
    frame_path: str
    width: int
    height: int


@dataclass
class FrameAnalysis:
    """Visual analysis results for a frame"""
    frame_data: FrameData
    
    # Visual classification
    shot_type: str  # close_up, medium, wide, screen_record
    camera_motion: str  # static, slight, aggressive
    presence: str  # face, full_body, hands, no_human
    
    # Detected elements
    objects: List[str]
    text_on_screen: str
    
    # Pattern interrupts
    is_pattern_interrupt: bool
    is_hook_frame: bool
    has_meme_element: bool
    
    # Visual metrics
    brightness_level: str  # dark, normal, bright
    color_temperature: str  # warm, neutral, cool
    visual_clutter_score: float  # 0-1
    
    # Face detection
    face_detected: bool
    face_expression: Optional[str]
    eye_contact: bool
    
    # Raw data
    vision_analysis: Dict[str, Any]


class FrameAnalyzer:
    """Sample and analyze video frames"""
    
    def __init__(self, output_dir: str = "frames"):
        """
        Initialize frame analyzer
        
        Args:
            output_dir: Directory to save sampled frames
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load face detector (Haar Cascade - simple, fast)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        logger.info(f"Frame Analyzer initialized (output: {self.output_dir})")
    
    def sample_frames(
        self, 
        video_path: str, 
        interval: float = 0.5,
        video_id: Optional[str] = None
    ) -> List[FrameData]:
        """
        Sample frames from video at regular intervals
        
        Args:
            video_path: Path to video file
            interval: Seconds between samples
            video_id: Optional video ID for file naming
            
        Returns:
            List of FrameData
        """
        logger.info(f"Sampling frames from {video_path} (interval: {interval}s)")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Could not open video: {video_path}")
            return []
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        logger.info(f"Video: {fps:.2f} FPS, {total_frames} frames, {duration:.2f}s")
        
        frames = []
        frame_interval = int(fps * interval)  # Frames between samples
        
        frame_number = 0
        sampled_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Sample at intervals
            if frame_number % frame_interval == 0:
                time_s = frame_number / fps
                
                # Save frame
                frame_filename = f"{video_id or 'video'}_{sampled_count:04d}_{time_s:.2f}s.jpg"
                frame_path = self.output_dir / frame_filename
                
                cv2.imwrite(str(frame_path), frame)
                
                height, width = frame.shape[:2]
                
                frame_data = FrameData(
                    frame_number=frame_number,
                    time_s=time_s,
                    frame_path=str(frame_path),
                    width=width,
                    height=height
                )
                
                frames.append(frame_data)
                sampled_count += 1
            
            frame_number += 1
        
        cap.release()
        
        logger.success(f"Sampled {len(frames)} frames")
        return frames
    
    def analyze_frame(self, frame_path: str) -> FrameAnalysis:
        """
        Analyze a single frame
        
        Args:
            frame_path: Path to frame image
            
        Returns:
            FrameAnalysis with visual features
        """
        # Load frame
        frame = cv2.imread(frame_path)
        if frame is None:
            logger.error(f"Could not load frame: {frame_path}")
            return None
        
        # Basic measurements
        height, width = frame.shape[:2]
        
        # Brightness analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        avg_brightness = np.mean(gray)
        brightness_level = self._classify_brightness(avg_brightness)
        
        # Color temperature
        color_temp = self._analyze_color_temperature(frame)
        
        # Visual clutter
        clutter_score = self._calculate_clutter(gray)
        
        # Face detection
        face_detected, face_count, face_data = self._detect_faces(gray)
        
        # Shot type estimation (very simple heuristic)
        shot_type = self._estimate_shot_type(face_detected, face_data, height, width)
        
        # Pattern interrupt detection (compare with previous frame if available)
        # TODO: Implement frame delta analysis
        is_pattern_interrupt = False
        
        # Create analysis result
        analysis = FrameAnalysis(
            frame_data=FrameData(
                frame_number=0,  # Will be set by caller
                time_s=0.0,  # Will be set by caller
                frame_path=frame_path,
                width=width,
                height=height
            ),
            shot_type=shot_type,
            camera_motion="static",  # TODO: motion detection
            presence="face" if face_detected else "no_human",
            objects=[],  # TODO: object detection
            text_on_screen="",  # TODO: OCR
            is_pattern_interrupt=is_pattern_interrupt,
            is_hook_frame=face_detected and clutter_score < 0.4,  # Simple heuristic
            has_meme_element=False,  # TODO: meme detection
            brightness_level=brightness_level,
            color_temperature=color_temp,
            visual_clutter_score=clutter_score,
            face_detected=face_detected,
            face_expression=None,  # TODO: expression recognition
            eye_contact=False,  # TODO: gaze detection
            vision_analysis={
                'avg_brightness': float(avg_brightness),
                'face_count': face_count,
                'face_data': face_data
            }
        )
        
        return analysis
    
    def detect_pattern_interrupts(
        self, 
        frames: List[FrameData],
        threshold: float = 30.0
    ) -> List[Dict[str, Any]]:
        """
        Detect visual pattern interrupts (big changes between frames)
        
        Args:
            frames: List of frame data
            threshold: Change threshold (0-100)
            
        Returns:
            List of pattern interrupt events
        """
        if len(frames) < 2:
            return []
        
        interrupts = []
        
        for i in range(1, len(frames)):
            prev_frame = cv2.imread(frames[i-1].frame_path)
            curr_frame = cv2.imread(frames[i].frame_path)
            
            if prev_frame is None or curr_frame is None:
                continue
            
            # Resize to same dimensions if needed
            if prev_frame.shape != curr_frame.shape:
                curr_frame = cv2.resize(curr_frame, (prev_frame.shape[1], prev_frame.shape[0]))
            
            # Calculate frame difference
            diff = cv2.absdiff(prev_frame, curr_frame)
            mean_diff = np.mean(diff)
            
            if mean_diff > threshold:
                interrupts.append({
                    'frame_number': frames[i].frame_number,
                    'time_s': frames[i].time_s,
                    'change_magnitude': float(mean_diff),
                    'type': 'visual_change'
                })
        
        logger.info(f"Detected {len(interrupts)} pattern interrupts")
        return interrupts
    
    def _classify_brightness(self, avg_brightness: float) -> str:
        """Classify brightness level"""
        if avg_brightness < 85:
            return "dark"
        elif avg_brightness < 170:
            return "normal"
        else:
            return "bright"
    
    def _analyze_color_temperature(self, frame: np.ndarray) -> str:
        """Analyze color temperature (warm/cool)"""
        # Simple heuristic: compare blue vs red channels
        b, g, r = cv2.split(frame)
        
        avg_blue = np.mean(b)
        avg_red = np.mean(r)
        
        ratio = avg_blue / (avg_red + 1)  # Avoid division by zero
        
        if ratio > 1.1:
            return "cool"
        elif ratio < 0.9:
            return "warm"
        else:
            return "neutral"
    
    def _calculate_clutter(self, gray_frame: np.ndarray) -> float:
        """
        Calculate visual clutter score (0-1, higher = more cluttered)
        Uses edge density as proxy
        """
        # Detect edges
        edges = cv2.Canny(gray_frame, 50, 150)
        
        # Calculate ratio of edge pixels to total pixels
        edge_density = np.count_nonzero(edges) / edges.size
        
        # Normalize to 0-1 (assuming max clutter at ~30% edges)
        clutter_score = min(edge_density / 0.3, 1.0)
        
        return clutter_score
    
    def _detect_faces(self, gray_frame: np.ndarray) -> Tuple[bool, int, List[Dict]]:
        """
        Detect faces in frame
        
        Returns:
            (face_detected, face_count, face_data)
        """
        faces = self.face_cascade.detectMultiScale(
            gray_frame,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        face_data = []
        for (x, y, w, h) in faces:
            face_data.append({
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h),
                'center_x': int(x + w/2),
                'center_y': int(y + h/2)
            })
        
        return len(faces) > 0, len(faces), face_data
    
    def _estimate_shot_type(
        self, 
        face_detected: bool, 
        face_data: List[Dict],
        frame_height: int,
        frame_width: int
    ) -> str:
        """
        Estimate shot type based on face size/position
        Very simple heuristic
        """
        if not face_detected or not face_data:
            return "wide_or_screen"  # No face = likely screen record or wide shot
        
        # Use largest face
        largest_face = max(face_data, key=lambda f: f['width'] * f['height'])
        
        face_area = largest_face['width'] * largest_face['height']
        frame_area = frame_height * frame_width
        face_ratio = face_area / frame_area
        
        if face_ratio > 0.15:  # Face takes up > 15% of frame
            return "close_up"
        elif face_ratio > 0.05:  # 5-15%
            return "medium"
        else:
            return "wide"


# Example usage
if __name__ == '__main__':
    import sys
    
    logger.info("Frame Analyzer Test")
    
    # Test video path
    test_video = sys.argv[1] if len(sys.argv) > 1 else "test_video.mp4"
    
    if not os.path.exists(test_video):
        logger.error(f"Test video not found: {test_video}")
        logger.info("Usage: python frame_analyzer.py <video_path>")
        sys.exit(1)
    
    analyzer = FrameAnalyzer(output_dir="test_frames")
    
    # Sample frames
    logger.info(f"\nSampling frames from {test_video}...")
    frames = analyzer.sample_frames(test_video, interval=1.0, video_id="test")
    
    if not frames:
        logger.error("No frames sampled")
        sys.exit(1)
    
    # Analyze first few frames
    logger.info(f"\nAnalyzing first 5 frames...")
    for frame in frames[:5]:
        analysis = analyzer.analyze_frame(frame.frame_path)
        
        if analysis:
            logger.info(f"\nFrame at {frame.time_s:.2f}s:")
            logger.info(f"  Shot type: {analysis.shot_type}")
            logger.info(f"  Brightness: {analysis.brightness_level}")
            logger.info(f"  Color temp: {analysis.color_temperature}")
            logger.info(f"  Visual clutter: {analysis.visual_clutter_score:.2f}")
            logger.info(f"  Face detected: {analysis.face_detected}")
    
    # Pattern interrupts
    logger.info(f"\nDetecting pattern interrupts...")
    interrupts = analyzer.detect_pattern_interrupts(frames, threshold=25.0)
    
    logger.info(f"\nFound {len(interrupts)} pattern interrupts:")
    for interrupt in interrupts[:3]:
        logger.info(f"  {interrupt['time_s']:.2f}s: change magnitude {interrupt['change_magnitude']:.1f}")
    
    logger.success(f"\nTest complete! Frames saved to test_frames/")
