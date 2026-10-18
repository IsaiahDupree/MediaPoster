"""
Visual Salience Detector
Identifies visually interesting moments from frame analysis
"""
from typing import List, Dict, Optional
from loguru import logger
import re


class VisualSalienceDetector:
    """Detect visually salient moments for highlights"""
    
    # Keywords indicating visual interest
    VISUAL_INTEREST_KEYWORDS = {
        'action': ['moving', 'jumping', 'running', 'dancing', 'action', 'dynamic'],
        'emotion': ['smiling', 'laughing', 'surprised', 'excited', 'emotional', 'expressive'],
        'unusual': ['unusual', 'unexpected', 'surprising', 'strange', 'unique', 'rare'],
        'text': ['text', 'words', 'caption', 'overlay', 'title', 'graphic'],
        'people': ['person', 'people', 'face', 'crowd', 'audience', 'group'],
        'contrast': ['bright', 'colorful', 'contrast', 'vivid', 'bold', 'striking']
    }
    
    def __init__(self):
        """Initialize visual salience detector"""
        logger.info("Visual salience detector initialized")
    
    def analyze_frame_descriptions(
        self,
        visual_analysis: List[Dict]
    ) -> List[Dict]:
        """
        Analyze GPT-4 Vision frame descriptions for salient moments
        
        Args:
            visual_analysis: Frame analysis results from Phase 1
            
        Returns:
            Visually salient moments with scores
        """
        logger.info(f"Analyzing {len(visual_analysis)} frame descriptions")
        
        salient_frames = []
        
        for frame_data in visual_analysis:
            description = frame_data.get('description', '').lower()
            timestamp = frame_data.get('timestamp', 0)
            
            if not description:
                continue
            
            # Score based on keywords
            scores = self._score_description(description)
            total_score = sum(scores.values())
            
            if total_score > 0:
                salient_frames.append({
                    'timestamp': timestamp,
                    'description': frame_data.get('description', ''),
                    'salience_score': min(total_score, 1.0),
                    'categories': {k: v for k, v in scores.items() if v > 0},
                    'type': 'visual_salience'
                })
        
        # Sort by salience
        salient_frames.sort(key=lambda x: x['salience_score'], reverse=True)
        
        logger.success(f"✓ Found {len(salient_frames)} visually salient frames")
        return salient_frames
    
    def _score_description(self, description: str) -> Dict[str, float]:
        """Score description text for visual interest"""
        scores = {}
        
        for category, keywords in self.VISUAL_INTEREST_KEYWORDS.items():
            category_score = 0.0
            for keyword in keywords:
                if keyword in description:
                    category_score += 0.2
            
            scores[category] = min(category_score, 0.5)  # Cap per category
        
        return scores
    
    def detect_on_screen_text(
        self,
        visual_analysis: List[Dict]
    ) -> List[Dict]:
        """
        Identify frames with on-screen text
        
        Args:
            visual_analysis: Frame analysis results
            
        Returns:
            Frames with detected text
        """
        logger.info("Detecting on-screen text")
        
        text_frames = []
        
        for frame_data in visual_analysis:
            description = frame_data.get('description', '').lower()
            timestamp = frame_data.get('timestamp', 0)
            
            # Look for text indicators
            text_indicators = [
                'text', 'caption', 'subtitle', 'title', 'words',
                'overlay', 'graphic', 'label', 'sign', 'banner'
            ]
            
            found_indicators = [ind for ind in text_indicators if ind in description]
            
            if found_indicators:
                text_frames.append({
                    'timestamp': timestamp,
                    'description': frame_data.get('description', ''),
                    'indicators': found_indicators,
                    'confidence': min(len(found_indicators) * 0.3, 1.0),
                    'type': 'on_screen_text'
                })
        
        logger.success(f"✓ Found {len(text_frames)} frames with text")
        return text_frames
    
    def detect_faces_emotions(
        self,
        visual_analysis: List[Dict]
    ) -> List[Dict]:
        """
        Identify frames with expressive faces/emotions
        
        Args:
            visual_analysis: Frame analysis results
            
        Returns:
            Frames with emotional expressions
        """
        logger.info("Detecting facial expressions")
        
        emotion_frames = []
        
        emotion_keywords = [
            'smiling', 'laughing', 'surprised', 'shocked', 'excited',
            'happy', 'sad', 'angry', 'confused', 'amazed', 'expressive',
            'emotional', 'reaction', 'expression'
        ]
        
        for frame_data in visual_analysis:
            description = frame_data.get('description', '').lower()
            timestamp = frame_data.get('timestamp', 0)
            
            found_emotions = [kw for kw in emotion_keywords if kw in description]
            
            if found_emotions:
                emotion_frames.append({
                    'timestamp': timestamp,
                    'description': frame_data.get('description', ''),
                    'emotions': found_emotions,
                    'intensity': min(len(found_emotions) * 0.25, 1.0),
                    'type': 'facial_emotion'
                })
        
        logger.success(f"✓ Found {len(emotion_frames)} emotional frames")
        return emotion_frames
    
    def detect_action_moments(
        self,
        visual_analysis: List[Dict]
    ) -> List[Dict]:
        """
        Identify frames with action/movement
        
        Args:
            visual_analysis: Frame analysis results
            
        Returns:
            Action-filled frames
        """
        logger.info("Detecting action moments")
        
        action_frames = []
        
        action_keywords = [
            'moving', 'jumping', 'running', 'dancing', 'walking',
            'gesture', 'gesturing', 'pointing', 'waving', 'action',
            'dynamic', 'active', 'motion', 'movement'
        ]
        
        for frame_data in visual_analysis:
            description = frame_data.get('description', '').lower()
            timestamp = frame_data.get('timestamp', 0)
            
            found_actions = [kw for kw in action_keywords if kw in description]
            
            if found_actions:
                action_frames.append({
                    'timestamp': timestamp,
                    'description': frame_data.get('description', ''),
                    'actions': found_actions,
                    'energy': min(len(found_actions) * 0.3, 1.0),
                    'type': 'action_moment'
                })
        
        logger.success(f"✓ Found {len(action_frames)} action frames")
        return action_frames
    
    def detect_visual_contrasts(
        self,
        visual_analysis: List[Dict]
    ) -> List[Dict]:
        """
        Identify visually striking moments (colors, contrast)
        
        Args:
            visual_analysis: Frame analysis results
            
        Returns:
            Visually striking frames
        """
        logger.info("Detecting visual contrasts")
        
        contrast_frames = []
        
        contrast_keywords = [
            'bright', 'colorful', 'vivid', 'bold', 'striking',
            'contrast', 'dramatic', 'vibrant', 'saturated', 'intense'
        ]
        
        for frame_data in visual_analysis:
            description = frame_data.get('description', '').lower()
            timestamp = frame_data.get('timestamp', 0)
            
            found_contrasts = [kw for kw in contrast_keywords if kw in description]
            
            if found_contrasts:
                contrast_frames.append({
                    'timestamp': timestamp,
                    'description': frame_data.get('description', ''),
                    'qualities': found_contrasts,
                    'visual_impact': min(len(found_contrasts) * 0.3, 1.0),
                    'type': 'visual_contrast'
                })
        
        logger.success(f"✓ Found {len(contrast_frames)} high-contrast frames")
        return contrast_frames
    
    def analyze_comprehensive(
        self,
        visual_analysis: List[Dict]
    ) -> Dict:
        """
        Run all visual analyses
        
        Args:
            visual_analysis: Frame analysis results from Phase 1
            
        Returns:
            Comprehensive visual analysis
        """
        logger.info("Running comprehensive visual analysis")
        
        results = {
            'salient_frames': self.analyze_frame_descriptions(visual_analysis),
            'text_frames': self.detect_on_screen_text(visual_analysis),
            'emotion_frames': self.detect_faces_emotions(visual_analysis),
            'action_frames': self.detect_action_moments(visual_analysis),
            'contrast_frames': self.detect_visual_contrasts(visual_analysis)
        }
        
        total = sum(len(v) for v in results.values())
        logger.success(f"✓ Comprehensive visual analysis complete: {total} interesting frames")
        
        return results
    
    def score_timestamp_by_visuals(
        self,
        timestamp: float,
        visual_highlights: Dict,
        window: float = 2.0
    ) -> float:
        """
        Score a timestamp based on visual analysis
        
        Args:
            timestamp: Timestamp to score
            visual_highlights: Results from analyze_comprehensive
            window: Time window for proximity
            
        Returns:
            Visual score (0-1)
        """
        score = 0.0
        
        for highlight_type, highlights in visual_highlights.items():
            for highlight in highlights:
                h_ts = highlight['timestamp']
                distance = abs(timestamp - h_ts)
                
                if distance <= window:
                    proximity = 1.0 - (distance / window)
                    
                    # Weight by type
                    weight = {
                        'salient_frames': 0.3,
                        'emotion_frames': 0.25,
                        'action_frames': 0.2,
                        'text_frames': 0.15,
                        'contrast_frames': 0.1
                    }.get(highlight_type, 0.1)
                    
                    # Get highlight score
                    h_score = highlight.get('salience_score', 
                              highlight.get('intensity',
                              highlight.get('energy',
                              highlight.get('confidence', 0.5))))
                    
                    score += proximity * weight * h_score
        
        return min(score, 1.0)


# Example usage and testing
if __name__ == "__main__":
    import sys
    import json
    from pathlib import Path
    
    if len(sys.argv) < 2:
        print("Usage: python visual_detector.py <analysis_json>")
        print("  (analysis JSON should contain 'visual_analysis' from Phase 1)")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    
    with open(input_path) as f:
        analysis = json.load(f)
    
    if 'visual_analysis' not in analysis:
        print("Error: JSON must contain 'visual_analysis' field")
        sys.exit(1)
    
    # Test visual detection
    detector = VisualSalienceDetector()
    
    print("\n" + "="*60)
    print("VISUAL SALIENCE ANALYSIS")
    print("="*60)
    
    # Run comprehensive analysis
    results = detector.analyze_comprehensive(analysis['visual_analysis'])
    
    # Display results
    for analysis_type, items in results.items():
        if items:
            print(f"\n{analysis_type.upper()}: {len(items)} found")
            for i, item in enumerate(items[:3]):
                print(f"  {i+1}. [{item['timestamp']:.1f}s]")
                print(f"      {item['description'][:80]}...")
                if 'salience_score' in item:
                    print(f"      Score: {item['salience_score']:.2f}")
