"""
SFX Library Service

AI-addressable sound effects library with manifest validation,
context pack generation for LLMs, and auto-fix capabilities.
"""

from .types import (
    SfxItem,
    SfxManifest,
    AudioEvent,
    AudioEvents,
    SfxContextPack,
    FixReport,
    Beat,
    QATimelineReport,
)
from .manifest import (
    load_manifest,
    save_manifest,
    get_sfx_by_id,
    search_sfx_by_tags,
    get_categories,
    get_all_tags,
)
from .validator import (
    validate_audio_events,
    validate_and_fix_events,
    run_qa_gate,
    apply_anti_spam_filter,
)
from .context_pack import (
    build_sfx_context_pack,
    build_filtered_context_pack,
    make_sfx_selection_prompt,
    get_context_pack_stats,
)
from .autofix import (
    best_sfx_match,
    tokenize_text,
    suggest_sfx_for_action,
)
from .beat_extractor import (
    extract_beats_from_script,
    extract_beats_with_markers,
    ExtractedBeat,
    BeatExtractionResult,
)
from .audio_utils import (
    merge_audio_events,
    clamp_events_to_duration,
    snap_sfx_to_beats,
    thin_sfx_events,
    finalize_audio_events,
    get_sfx_density_stats,
)
from .cue_sheet import (
    CueSheet,
    SfxCue,
    audio_events_to_cue_sheet,
    beats_to_cue_sheet,
    save_cue_sheet,
    load_cue_sheet,
    validate_cue_sheet,
)
from .audio_mixer import (
    mix_audio_bus,
    mix_audio_bus_sync,
    mix_tracks,
    get_audio_duration,
    normalize_audio,
)

__all__ = [
    # Types
    "SfxItem",
    "SfxManifest", 
    "AudioEvent",
    "AudioEvents",
    "SfxContextPack",
    "FixReport",
    "Beat",
    "QATimelineReport",
    "ExtractedBeat",
    "BeatExtractionResult",
    # Manifest
    "load_manifest",
    "save_manifest",
    "get_sfx_by_id",
    "search_sfx_by_tags",
    "get_categories",
    "get_all_tags",
    # Validator
    "validate_audio_events",
    "validate_and_fix_events",
    "run_qa_gate",
    "apply_anti_spam_filter",
    # Context Pack
    "build_sfx_context_pack",
    "build_filtered_context_pack",
    "make_sfx_selection_prompt",
    "get_context_pack_stats",
    # Autofix
    "best_sfx_match",
    "tokenize_text",
    "suggest_sfx_for_action",
    # Beat Extractor
    "extract_beats_from_script",
    "extract_beats_with_markers",
    # Audio Utils
    "merge_audio_events",
    "clamp_events_to_duration",
    "snap_sfx_to_beats",
    "thin_sfx_events",
    "finalize_audio_events",
    "get_sfx_density_stats",
    # Cue Sheet
    "CueSheet",
    "SfxCue",
    "audio_events_to_cue_sheet",
    "beats_to_cue_sheet",
    "save_cue_sheet",
    "load_cue_sheet",
    "validate_cue_sheet",
    # Audio Mixer
    "mix_audio_bus",
    "mix_audio_bus_sync",
    "mix_tracks",
    "get_audio_duration",
    "normalize_audio",
]
