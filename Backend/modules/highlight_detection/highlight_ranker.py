"""
Highlight Ranker
Combines all signals to rank and identify the best highlight moments
"""
from typing import List, Dict, Optional
from loguru import logger
from pathlib import Path
import json


class HighlightRanker:
    """Rank video moments for highlight potential using multi-signal analysis"""
    
    def __init__(
        self,
        min_duration: float = 10.0,
        max_duration: float = 60.0,
        min_score: float = 0.4
    ):
        """
        Initialize highlight ranker
        
        Args:
            min_duration: Minimum highlight duration
            max_duration: Maximum highlight duration
            min_score: Minimum score threshold
        """
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.min_score = min_score
        
        logger.info(f"Highlight ranker initialized (duration: {min_duration}-{max_duration}s, min_score: {min_score})")
    
    def rank_highlights(
        self,
        scenes: List[Dict],
        audio_events: Optional[List[Dict]] = None,
        transcript_highlights: Optional[Dict] = None,
        visual_highlights: Optional[Dict] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        Rank all scenes/moments for highlight potential
        
        Args:
            scenes: Detected scenes with basic scores
            audio_events: Audio signal events
            transcript_highlights: Transcript analysis results
            visual_highlights: Visual analysis results
            weights: Custom weights for each signal type
            
        Returns:
            Ranked highlights with composite scores
        """
        logger.info(f"Ranking {len(scenes)} candidate highlights")
        
        # Default weights
        if weights is None:
            weights = {
                'scene': 0.2,
                'audio': 0.3,
                'transcript': 0.3,
                'visual': 0.2
            }
        
        ranked = []
        
        for scene in scenes:
            # Skip scenes outside duration bounds
            if scene['duration'] < self.min_duration or scene['duration'] > self.max_duration:
                continue
            
            # Calculate composite score
            scores = {}
            
            # 1. Scene score (duration, change intensity)
            scores['scene'] = scene.get('highlight_score', 0.5)
            
            # 2. Audio score
            if audio_events:
                scores['audio'] = self._score_by_audio(scene, audio_events)
            else:
                scores['audio'] = 0.5
            
            # 3. Transcript score
            if transcript_highlights:
                scores['transcript'] = self._score_by_transcript(scene, transcript_highlights)
            else:
                scores['transcript'] = 0.5
            
            # 4. Visual score
            if visual_highlights:
                scores['visual'] = self._score_by_visuals(scene, visual_highlights)
            else:
                scores['visual'] = 0.5
            
            # Calculate weighted composite score
            composite_score = sum(
                scores[signal_type] * weights[signal_type]
                for signal_type in weights.keys()
                if signal_type in scores
            )
            
            # Only include if above threshold
            if composite_score >= self.min_score:
                ranked.append({
                    'start': scene['start'],
                    'end': scene['end'],
                    'duration': scene['duration'],
                    'composite_score': composite_score,
                    'signal_scores': scores,
                    'scene_id': scene.get('scene_id', 0),
                    'metadata': {
                        'has_audio_peaks': scores['audio'] > 0.6,
                        'has_transcript_hooks': scores['transcript'] > 0.6,
                        'has_visual_interest': scores['visual'] > 0.6
                    }
                })
        
        # Sort by composite score
        ranked.sort(key=lambda x: x['composite_score'], reverse=True)
        
        logger.success(f"✓ Ranked {len(ranked)} highlights above threshold")
        return ranked
    
    def _score_by_audio(self, scene: Dict, audio_events: List[Dict]) -> float:
        """Score scene based on audio events"""
        score = 0.0
        scene_start = scene['start']
        scene_end = scene['end']
        
        # Count events in this scene
        events_in_scene = [
            e for e in audio_events
            if scene_start <= e['timestamp'] <= scene_end
        ]
        
        if not events_in_scene:
            return 0.0
        
        # Score based on event types and intensity
        for event in events_in_scene:
            event_type = event.get('type', '')
            
            if event_type == 'volume_spike':
                intensity = event.get('relative_intensity', 1.0)
                score += min(intensity * 0.3, 0.5)
            elif event_type == 'energy_peak':
                prominence = event.get('prominence', 0.5)
                score += prominence * 0.4
            elif event_type == 'emphasized_speech':
                score += 0.3
            elif event_type == 'tempo_change':
                score += 0.2
        
        return min(score, 1.0)
    
    def _score_by_transcript(self, scene: Dict, transcript_highlights: Dict) -> float:
        """Score scene based on transcript analysis"""
        score = 0.0
        scene_start = scene['start']
        scene_end = scene['end']
        
        # Check each highlight type
        for highlight_type, highlights in transcript_highlights.items():
            for highlight in highlights:
                h_ts = highlight['timestamp']
                
                if scene_start <= h_ts <= scene_end:
                    # Weight by type
                    type_weights = {
                        'hooks': 0.4,
                        'punchlines': 0.3,
                        'questions': 0.2,
                        'emphasis': 0.15,
                        'story_beats': 0.1,
                        'key_phrases': 0.1
                    }
                    
                    weight = type_weights.get(highlight_type, 0.1)
                    h_score = highlight.get('score', 0.5)
                    score += weight * h_score
        
        return min(score, 1.0)
    
    def _score_by_visuals(self, scene: Dict, visual_highlights: Dict) -> float:
        """Score scene based on visual analysis"""
        score = 0.0
        scene_start = scene['start']
        scene_end = scene['end']
        
        # Check each visual type
        for visual_type, highlights in visual_highlights.items():
            for highlight in highlights:
                h_ts = highlight['timestamp']
                
                if scene_start <= h_ts <= scene_end:
                    # Weight by type
                    type_weights = {
                        'salient_frames': 0.3,
                        'emotion_frames': 0.25,
                        'action_frames': 0.2,
                        'text_frames': 0.15,
                        'contrast_frames': 0.1
                    }
                    
                    weight = type_weights.get(visual_type, 0.1)
                    
                    # Get score from highlight
                    h_score = highlight.get('salience_score',
                              highlight.get('intensity',
                              highlight.get('energy',
                              highlight.get('confidence', 0.5))))
                    
                    score += weight * h_score
        
        return min(score, 1.0)
    
    def select_top_highlights(
        self,
        ranked_highlights: List[Dict],
        max_highlights: int = 5,
        min_gap: float = 10.0
    ) -> List[Dict]:
        """
        Select top N non-overlapping highlights
        
        Args:
            ranked_highlights: Ranked highlights
            max_highlights: Maximum number to select
            min_gap: Minimum time gap between highlights (seconds)
            
        Returns:
            Top selected highlights
        """
        logger.info(f"Selecting top {max_highlights} highlights")
        
        if not ranked_highlights:
            return []
        
        selected = []
        
        for highlight in ranked_highlights:
            # Check if this overlaps with any selected highlight
            overlaps = False
            for sel in selected:
                # Check for overlap or proximity
                if (highlight['start'] <= sel['end'] + min_gap and
                    highlight['end'] >= sel['start'] - min_gap):
                    overlaps = True
                    break
            
            if not overlaps:
                selected.append(highlight)
            
            if len(selected) >= max_highlights:
                break
        
        logger.success(f"✓ Selected {len(selected)} top highlights")
        return selected
    
    def generate_highlight_report(
        self,
        highlights: List[Dict],
        video_name: str = "video"
    ) -> Dict:
        """
        Generate a detailed report for selected highlights
        
        Args:
            highlights: Selected highlights
            video_name: Name of video
            
        Returns:
            Report dictionary
        """
        report = {
            'video_name': video_name,
            'num_highlights': len(highlights),
            'highlights': []
        }
        
        for i, h in enumerate(highlights, 1):
            report['highlights'].append({
                'rank': i,
                'start': h['start'],
                'end': h['end'],
                'duration': h['duration'],
                'score': h['composite_score'],
                'signals': h['signal_scores'],
                'strengths': self._identify_strengths(h),
                'suggested_clip_name': f"{video_name}_highlight_{i}"
            })
        
        return report
    
    def _identify_strengths(self, highlight: Dict) -> List[str]:
        """Identify what makes this highlight good"""
        strengths = []
        scores = highlight['signal_scores']
        metadata = highlight.get('metadata', {})
        
        if scores.get('audio', 0) > 0.7:
            strengths.append("Strong audio energy")
        if scores.get('transcript', 0) > 0.7:
            strengths.append("Engaging dialogue")
        if scores.get('visual', 0) > 0.7:
            strengths.append("Visually interesting")
        if metadata.get('has_audio_peaks'):
            strengths.append("Exciting moments")
        if metadata.get('has_transcript_hooks'):
            strengths.append("Hook phrases")
        if metadata.get('has_visual_interest'):
            strengths.append("Dynamic visuals")
        
        if 10 <= highlight['duration'] <= 30:
            strengths.append("Perfect clip length")
        
        return strengths if strengths else ["Good overall balance"]
    
    def save_highlights(
        self,
        highlights: List[Dict],
        output_path: Path
    ):
        """
        Save highlights to JSON file
        
        Args:
            highlights: Highlighted moments
            output_path: Where to save
        """
        with open(output_path, 'w') as f:
            json.dump(highlights, f, indent=2, default=str)
        
        logger.success(f"✓ Highlights saved to {output_path}")


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    print("\n" + "="*60)
    print("HIGHLIGHT RANKER TEST")
    print("="*60)
    print("\nThis module combines signals from all other detectors.")
    print("To test, first run:")
    print("  1. Scene detection")
    print("  2. Audio signal processing")
    print("  3. Transcript scanning")
    print("  4. Visual detection")
    print("\nThen pass all results to the ranker.")
    print("\nFor end-to-end testing, use test_phase2.py")
