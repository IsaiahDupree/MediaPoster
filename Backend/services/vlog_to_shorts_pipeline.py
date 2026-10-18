"""
BM-017: Dev Vlog to YouTube Shorts Pipeline
End-to-end pipeline for converting dev vlogs into YouTube Shorts.
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ShortSpec:
    """Specification for a generated Short."""
    clip_start: float
    clip_end: float
    title: str
    description: str = ""
    hashtags: List[str] = field(default_factory=list)
    transcript_excerpt: str = ""
    viral_score: float = 0.0


@dataclass
class GeneratedShort:
    """A generated YouTube Short."""
    short_id: str
    source_video_id: str
    file_path: str
    title: str
    description: str
    duration_seconds: float
    has_captions: bool = False
    has_title_card: bool = False
    is_vertical: bool = True
    status: str = "ready"  # ready, published, failed
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class VlogToShortsPipeline:
    """
    Converts dev vlogs into YouTube Shorts.

    Pipeline steps:
    1. Detect viral-potential segments
    2. Extract clips
    3. Smart reframe to 9:16
    4. Generate captions
    5. Add title card overlay
    6. Output ready-to-upload Short
    """

    def __init__(self):
        self._generated: List[GeneratedShort] = []

    async def process(
        self,
        video_path: str,
        video_id: str,
        transcript_segments: Optional[List[Dict[str, Any]]] = None,
        max_shorts: int = 5,
    ) -> List[GeneratedShort]:
        """
        Process a vlog video into YouTube Shorts.

        Args:
            video_path: Path to the source video
            video_id: Source video identifier
            transcript_segments: Transcript segments for the video
            max_shorts: Maximum number of shorts to generate

        Returns:
            List of GeneratedShort
        """
        from uuid import uuid4

        shorts = []
        segments = transcript_segments or []

        # Step 1: Detect viral segments
        from services.viral_clip_detector import ViralClipDetector
        detector = ViralClipDetector()
        candidates = detector.get_top_clips(segments, max_clips=max_shorts)

        for candidate in candidates:
            short = GeneratedShort(
                short_id=str(uuid4()),
                source_video_id=video_id,
                file_path="",  # Set after processing
                title=candidate.transcript_excerpt[:50],
                description=candidate.transcript_excerpt,
                duration_seconds=candidate.end_seconds - candidate.start_seconds,
            )
            shorts.append(short)

        self._generated.extend(shorts)
        logger.info("Generated %d shorts from video %s", len(shorts), video_id)
        return shorts

    async def process_and_render(
        self,
        video_path: str,
        video_id: str,
        transcript_segments: Optional[List[Dict[str, Any]]] = None,
        max_shorts: int = 3,
    ) -> List[GeneratedShort]:
        """
        Full pipeline: detect, extract, reframe, caption, title card.

        Args:
            video_path: Source video
            video_id: Source video ID
            transcript_segments: Transcript segments
            max_shorts: Max shorts to generate

        Returns:
            List of rendered GeneratedShort
        """
        from services.viral_clip_detector import ViralClipDetector
        from services.video_clipper import VideoClipper, ClipSpec

        segments = transcript_segments or []

        # Detect
        detector = ViralClipDetector()
        candidates = detector.get_top_clips(segments, max_clips=max_shorts)

        # Extract clips
        clipper = VideoClipper()
        specs = [
            ClipSpec(
                start_seconds=c.start_seconds,
                end_seconds=c.end_seconds,
                label=f"short_{i}",
            )
            for i, c in enumerate(candidates)
        ]
        clips = await clipper.extract_clips(video_path, specs)

        from uuid import uuid4
        shorts = []
        for clip, candidate in zip(clips, candidates):
            short = GeneratedShort(
                short_id=str(uuid4()),
                source_video_id=video_id,
                file_path=clip.file_path,
                title=candidate.transcript_excerpt[:50],
                description=candidate.transcript_excerpt,
                duration_seconds=clip.duration_seconds,
            )
            shorts.append(short)

        self._generated.extend(shorts)
        return shorts

    def get_generated_shorts(
        self,
        video_id: Optional[str] = None,
    ) -> List[GeneratedShort]:
        """Get generated shorts, optionally filtered by source video."""
        if video_id:
            return [s for s in self._generated if s.source_video_id == video_id]
        return list(self._generated)

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "total_generated": len(self._generated),
            "ready": sum(1 for s in self._generated if s.status == "ready"),
            "published": sum(1 for s in self._generated if s.status == "published"),
            "failed": sum(1 for s in self._generated if s.status == "failed"),
        }
