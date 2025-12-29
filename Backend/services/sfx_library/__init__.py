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
)
from .manifest import (
    load_manifest,
    save_manifest,
    get_sfx_by_id,
    search_sfx_by_tags,
)
from .validator import (
    validate_audio_events,
    validate_and_fix_events,
)
from .context_pack import (
    build_sfx_context_pack,
    build_filtered_context_pack,
    make_sfx_selection_prompt,
)
from .autofix import (
    best_sfx_match,
    tokenize_text,
)

__all__ = [
    # Types
    "SfxItem",
    "SfxManifest", 
    "AudioEvent",
    "AudioEvents",
    "SfxContextPack",
    "FixReport",
    # Manifest
    "load_manifest",
    "save_manifest",
    "get_sfx_by_id",
    "search_sfx_by_tags",
    # Validator
    "validate_audio_events",
    "validate_and_fix_events",
    # Context Pack
    "build_sfx_context_pack",
    "build_filtered_context_pack",
    "make_sfx_selection_prompt",
    # Autofix
    "best_sfx_match",
    "tokenize_text",
]
