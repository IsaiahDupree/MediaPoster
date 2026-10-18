"""
Highlight Detection Module - Phase 2
Identifies the best moments in videos for short-form clips
"""
from .scene_detector import SceneDetector
from .audio_signals import AudioSignalProcessor
from .transcript_scanner import TranscriptScanner
from .visual_detector import VisualSalienceDetector
from .highlight_ranker import HighlightRanker
from .gpt_recommender import GPTRecommender

__all__ = [
    "SceneDetector",
    "AudioSignalProcessor",
    "TranscriptScanner",
    "VisualSalienceDetector",
    "HighlightRanker",
    "GPTRecommender",
]
