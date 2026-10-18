"""
BM-013: Viral Clip Detection
Detects potentially viral segments in videos based on audio/visual/engagement signals.
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ViralCandidate:
    """A segment identified as having viral potential."""
    start_seconds: float
    end_seconds: float
    score: float  # 0-1 viral potential score
    reasons: List[str] = field(default_factory=list)
    transcript_excerpt: str = ""


class ViralClipDetector:
    """
    Detects viral-potential segments in videos.

    Scoring signals:
    - High energy audio transitions
    - Dense text in transcript (high information density)
    - Emotional language patterns
    - Hook patterns (questions, surprising statements)
    """

    def __init__(self, min_score: float = 0.5, min_duration: float = 15):
        self.min_score = min_score
        self.min_duration = min_duration

    def detect(
        self,
        transcript_segments: List[Dict[str, Any]],
        video_duration: float = 0,
    ) -> List[ViralCandidate]:
        """
        Analyze transcript segments for viral potential.

        Args:
            transcript_segments: List of {start, end, text} segments
            video_duration: Total video duration in seconds

        Returns:
            List of ViralCandidate sorted by score
        """
        candidates = []

        for i, seg in enumerate(transcript_segments):
            text = seg.get("text", "")
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            duration = end - start

            if duration < self.min_duration:
                continue

            score = 0.0
            reasons = []

            # Score based on text patterns
            if "?" in text:
                score += 0.2
                reasons.append("contains_question")

            hook_words = ["secret", "never", "always", "mistake", "hack", "tip", "truth", "believe"]
            if any(w in text.lower() for w in hook_words):
                score += 0.3
                reasons.append("hook_language")

            # Text density (words per second)
            words = len(text.split())
            if duration > 0:
                density = words / duration
                if density > 2.5:
                    score += 0.2
                    reasons.append("high_density")

            # Strong opening segment
            if start < 30:
                score += 0.15
                reasons.append("opening_segment")

            # Emotional language
            emotion_words = ["amazing", "incredible", "love", "hate", "worst", "best", "insane", "crazy"]
            if any(w in text.lower() for w in emotion_words):
                score += 0.15
                reasons.append("emotional_language")

            if score >= self.min_score:
                candidates.append(ViralCandidate(
                    start_seconds=start,
                    end_seconds=end,
                    score=min(score, 1.0),
                    reasons=reasons,
                    transcript_excerpt=text[:200],
                ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    def get_top_clips(
        self,
        transcript_segments: List[Dict[str, Any]],
        max_clips: int = 5,
    ) -> List[ViralCandidate]:
        """Get the top N viral candidates."""
        all_candidates = self.detect(transcript_segments)
        return all_candidates[:max_clips]
