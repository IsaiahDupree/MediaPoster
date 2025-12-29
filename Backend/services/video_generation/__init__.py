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
from .voice_engine import (
    VoiceStrategy,
    NarratorConfig,
    BeatSpeechBudget,
    SpeechBudgetResult,
    plan_speech_budget,
    build_voice_policy,
    generate_tts_audio,
    enforce_perspective,
)
from .shot_types import (
    ShotType,
    ShotV2,
    AssetClipV2,
    build_sora_prompt,
    determine_shot_type,
    get_postprocess_hints,
)
from .postprocess import (
    chroma_key_to_alpha,
    extract_audio,
    mute_video,
    mix_audio_tracks,
    get_video_duration,
    get_video_info,
    postprocess_sora_clip,
)
from .render_plan_v2 import (
    RenderPlanRemotionV2,
    LayerV2,
    Transform2D,
    OverlayRules,
    make_render_plan_v2,
    validate_render_plan_v2,
)
from .validator import (
    ValidationResult,
    validate_story_ir as validate_ir,
    validate_shot_plan,
    validate_assets,
    validate_pipeline,
    validate_pre_sora,
)
from .auto_shot_planner import (
    BeatShotPolicy,
    PlannedShot,
    ShotPlanEntry,
    plan_shots_for_beat,
    make_auto_shot_plan,
    get_shots_by_beat,
    estimate_auto_plan_cost,
)
from .full_pipeline import (
    PipelineConfig,
    PipelineResult,
    run_full_pipeline,
    run_full_pipeline_sync,
    preview_pipeline,
)
from .shot_budgeter import (
    ShotBudget,
    BudgetPlan,
    apply_shot_budget,
    make_budgeted_shot_plan,
    estimate_budget_savings,
)
from .plate_manager import (
    PlateVariantPlan,
    PlateUsage,
    RiskReport,
    match_plate_to_beat,
    build_beat_bg_bindings,
    inject_variety,
    detect_plate_anti_patterns,
    fix_anti_patterns,
)
from .media_probe import (
    MediaTiming,
    MediaInfo,
    probe_duration_seconds,
    probe_duration_seconds_sync,
    probe_media_info,
    seconds_to_frames,
    get_media_timing,
    attach_timing_to_clips,
    build_plate_frames_map,
)
from .audio_ducking import (
    DuckingPolicy,
    NarrationCue,
    DEFAULT_DUCKING,
    bg_volume_at_frame,
    generate_volume_keyframes,
    beats_to_narration_cues,
    story_ir_to_narration_cues,
    calculate_ducking_for_render_plan,
    apply_ducking_to_layers,
)
from .char_variety import (
    CharPlacement,
    CharVarietyConfig,
    assign_char_presets_round_robin,
    detect_char_boredom,
    fix_char_placement_boredom,
    create_dramatic_switch_placements,
    merge_char_placements_with_budget,
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
    # Voice Engine
    "VoiceStrategy",
    "NarratorConfig",
    "BeatSpeechBudget",
    "SpeechBudgetResult",
    "plan_speech_budget",
    "build_voice_policy",
    "generate_tts_audio",
    "enforce_perspective",
    # Shot Types
    "ShotType",
    "ShotV2",
    "AssetClipV2",
    "build_sora_prompt",
    "determine_shot_type",
    "get_postprocess_hints",
    # Postprocess
    "chroma_key_to_alpha",
    "extract_audio",
    "mute_video",
    "mix_audio_tracks",
    "get_video_duration",
    "get_video_info",
    "postprocess_sora_clip",
    # Render Plan V2
    "RenderPlanRemotionV2",
    "LayerV2",
    "Transform2D",
    "OverlayRules",
    "make_render_plan_v2",
    "validate_render_plan_v2",
    # Validator
    "ValidationResult",
    "validate_ir",
    "validate_shot_plan",
    "validate_assets",
    "validate_pipeline",
    "validate_pre_sora",
    # Auto Shot Planner
    "BeatShotPolicy",
    "PlannedShot",
    "ShotPlanEntry",
    "plan_shots_for_beat",
    "make_auto_shot_plan",
    "get_shots_by_beat",
    "estimate_auto_plan_cost",
    # Full Pipeline
    "PipelineConfig",
    "PipelineResult",
    "run_full_pipeline",
    "run_full_pipeline_sync",
    "preview_pipeline",
    # Shot Budgeter
    "ShotBudget",
    "BudgetPlan",
    "apply_shot_budget",
    "make_budgeted_shot_plan",
    "estimate_budget_savings",
    # Plate Manager
    "PlateVariantPlan",
    "PlateUsage",
    "RiskReport",
    "match_plate_to_beat",
    "build_beat_bg_bindings",
    "inject_variety",
    "detect_plate_anti_patterns",
    "fix_anti_patterns",
    # Media Probe
    "MediaTiming",
    "MediaInfo",
    "probe_duration_seconds",
    "probe_duration_seconds_sync",
    "probe_media_info",
    "seconds_to_frames",
    "get_media_timing",
    "attach_timing_to_clips",
    "build_plate_frames_map",
    # Audio Ducking
    "DuckingPolicy",
    "NarrationCue",
    "DEFAULT_DUCKING",
    "bg_volume_at_frame",
    "generate_volume_keyframes",
    "beats_to_narration_cues",
    "story_ir_to_narration_cues",
    "calculate_ducking_for_render_plan",
    "apply_ducking_to_layers",
    # Character Variety
    "CharPlacement",
    "CharVarietyConfig",
    "assign_char_presets_round_robin",
    "detect_char_boredom",
    "fix_char_placement_boredom",
    "create_dramatic_switch_placements",
    "merge_char_placements_with_budget",
]
