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
    Clip,
)
from .story_ir import make_story_ir, validate_story_ir
from .shot_plan import make_shot_plan, estimate_sora_cost
from .render_plan import make_render_plan, validate_render_plan
from .format_selector import select_format, get_available_formats, get_format_by_id
from .sora_runner import (
    SoraRunner,
    run_sora_shot_plan,
    run_sora_shot_plan_sync,
    estimate_generation_cost,
)
from .orchestrator import (
    orchestrate_video_generation,
    orchestrate_video_generation_sync,
    orchestrate_from_dicts,
    preview_orchestration,
    OrchestrationResult,
)

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
    "Clip",
    # Story IR
    "make_story_ir",
    "validate_story_ir",
    # Shot Plan
    "make_shot_plan",
    "estimate_sora_cost",
    # Render Plan
    "make_render_plan",
    "validate_render_plan",
    # Format Selection
    "select_format",
    "get_available_formats",
    "get_format_by_id",
    # Sora Runner
    "SoraRunner",
    "run_sora_shot_plan",
    "run_sora_shot_plan_sync",
    "estimate_generation_cost",
    # Orchestrator
    "orchestrate_video_generation",
    "orchestrate_video_generation_sync",
    "orchestrate_from_dicts",
    "preview_orchestration",
    "OrchestrationResult",
]
