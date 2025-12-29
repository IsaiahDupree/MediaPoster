"""
Video Generation Service

Format-agnostic video generation pipeline using Sora for scene generation
and Remotion/Motion Canvas for final rendering.
"""

from .types import (
    TrendItemV1,
    ContentBriefV1,
    StoryIRV1,
    FormatPackV1,
    ShotPlanV1,
    AssetManifestV1,
    RenderPlanRemotionV1,
    BeatType,
    Beat,
    Shot,
    TimelineItem,
)
from .story_ir import make_story_ir
from .shot_plan import make_shot_plan
from .render_plan import make_render_plan
from .format_selector import select_format, get_available_formats

__all__ = [
    # Types
    "TrendItemV1",
    "ContentBriefV1",
    "StoryIRV1",
    "FormatPackV1",
    "ShotPlanV1",
    "AssetManifestV1",
    "RenderPlanRemotionV1",
    "BeatType",
    "Beat",
    "Shot",
    "TimelineItem",
    # Functions
    "make_story_ir",
    "make_shot_plan",
    "make_render_plan",
    "select_format",
    "get_available_formats",
]
