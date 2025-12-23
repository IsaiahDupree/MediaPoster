"""
Clip Extraction Service
=======================
Extracts engaging short-form clips from long-form videos.

Based on SupoClip approach with:
- AI-powered segment analysis
- Face detection for smart cropping
- 9:16 vertical format output
- Optional subtitle generation
"""

from .clip_extractor import (
    ClipExtractor,
    ExtractionConfig,
    TranscriptSegment,
    ExtractedClip,
    CropRegion,
)

__all__ = [
    'ClipExtractor',
    'ExtractionConfig',
    'TranscriptSegment',
    'ExtractedClip',
    'CropRegion',
]
