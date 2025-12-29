"""
SFX Library API Endpoints

REST API for managing the SFX library, validating audio events,
and generating AI context packs.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import os
from pathlib import Path

from services.sfx_library import (
    SfxManifest,
    SfxItem,
    AudioEvents,
    SfxContextPack,
    FixReport,
    Beat,
    QATimelineReport,
    load_manifest,
    save_manifest,
    search_sfx_by_tags,
    get_categories,
    get_all_tags,
    validate_audio_events,
    validate_and_fix_events,
    run_qa_gate,
    apply_anti_spam_filter,
    build_sfx_context_pack,
    build_filtered_context_pack,
    make_sfx_selection_prompt,
    get_context_pack_stats,
    best_sfx_match,
    suggest_sfx_for_action,
)


router = APIRouter(prefix="/sfx-library", tags=["SFX Library"])


# Default paths
DEFAULT_MANIFEST_PATH = os.environ.get(
    "SFX_MANIFEST_PATH",
    str(Path(__file__).parent.parent.parent / "assets" / "sfx" / "manifest.json")
)


def get_manifest_path() -> str:
    """Get the manifest path, creating default if needed."""
    return DEFAULT_MANIFEST_PATH


# Request/Response Models

class SearchSfxRequest(BaseModel):
    """Request to search SFX by tags."""
    tags: list[str]
    category: Optional[str] = None
    max_results: int = Field(default=20, ge=1, le=100)


class ValidateEventsRequest(BaseModel):
    """Request to validate audio events."""
    events: AudioEvents
    allow_auto_fix: bool = Field(default=True, alias="allowAutoFix")
    
    class Config:
        populate_by_name = True


class ValidateEventsResponse(BaseModel):
    """Response from event validation."""
    cleaned_events: AudioEvents = Field(alias="cleanedEvents")
    report: FixReport
    
    class Config:
        populate_by_name = True


class ContextPackRequest(BaseModel):
    """Request to generate a context pack."""
    max_items: int = Field(default=500, alias="maxItems", ge=1, le=1000)
    beat_text: Optional[str] = Field(None, alias="beatText")
    custom_rules: Optional[list[str]] = Field(None, alias="customRules")
    
    class Config:
        populate_by_name = True


class ContextPackResponse(BaseModel):
    """Response with context pack and stats."""
    context_pack: SfxContextPack = Field(alias="contextPack")
    stats: dict
    
    class Config:
        populate_by_name = True


class SfxSelectionPromptRequest(BaseModel):
    """Request to generate an SFX selection prompt."""
    beats: list[Beat]
    fps: int = 30
    max_context_items: int = Field(default=80, alias="maxContextItems")
    
    class Config:
        populate_by_name = True


class SfxSelectionPromptResponse(BaseModel):
    """Response with the generated prompt."""
    prompt: str
    estimated_tokens: int = Field(alias="estimatedTokens")
    
    class Config:
        populate_by_name = True


class QAGateRequest(BaseModel):
    """Request to run QA gate."""
    events: AudioEvents
    max_sfx_per_5_seconds: int = Field(default=8, alias="maxSfxPer5Seconds")
    min_gap_frames: int = Field(default=5, alias="minGapFrames")
    max_total_sfx: int = Field(default=50, alias="maxTotalSfx")
    
    class Config:
        populate_by_name = True


class SuggestSfxRequest(BaseModel):
    """Request to suggest SFX for an action."""
    action: str
    max_results: int = Field(default=5, alias="maxResults", ge=1, le=20)
    
    class Config:
        populate_by_name = True


class BestMatchRequest(BaseModel):
    """Request to find best match for unknown ID."""
    requested_id: str = Field(alias="requestedId")
    hint_tags: Optional[list[str]] = Field(None, alias="hintTags")
    hint_category: Optional[str] = Field(None, alias="hintCategory")
    
    class Config:
        populate_by_name = True


# Endpoints

@router.get("/manifest", response_model=SfxManifest)
async def get_manifest():
    """
    Get the full SFX manifest.
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        return SfxManifest(version="1.0", items=[])
    
    try:
        return load_manifest(manifest_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load manifest: {str(e)}")


@router.get("/manifest/stats")
async def get_manifest_stats():
    """
    Get statistics about the SFX manifest.
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        return {
            "total_items": 0,
            "categories": {},
            "tags_count": 0,
        }
    
    manifest = load_manifest(manifest_path)
    categories = get_categories(manifest)
    all_tags = get_all_tags(manifest)
    
    # Count items per category
    category_counts = {}
    for item in manifest.items:
        cat = item.category or "uncategorized"
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    return {
        "total_items": len(manifest.items),
        "categories": category_counts,
        "unique_categories": categories,
        "tags_count": len(all_tags),
        "unique_tags": all_tags[:50],  # Limit for response size
    }


@router.post("/search")
async def search_sfx(request: SearchSfxRequest):
    """
    Search SFX items by tags and optional category.
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        return {"results": []}
    
    manifest = load_manifest(manifest_path)
    results = search_sfx_by_tags(
        manifest=manifest,
        tags=request.tags,
        category=request.category,
        max_results=request.max_results,
    )
    
    return {
        "results": [item.model_dump() for item in results],
        "total": len(results),
    }


@router.post("/validate", response_model=ValidateEventsResponse)
async def validate_events(request: ValidateEventsRequest):
    """
    Validate audio events against the manifest.
    
    Optionally auto-fixes invalid SFX IDs by finding closest matches.
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="SFX manifest not found")
    
    manifest = load_manifest(manifest_path)
    
    cleaned, report = validate_and_fix_events(
        events=request.events,
        manifest=manifest,
        allow_auto_fix=request.allow_auto_fix,
    )
    
    return ValidateEventsResponse(
        cleaned_events=cleaned,
        report=report,
    )


@router.post("/qa-gate", response_model=QATimelineReport)
async def run_qa_gate_endpoint(request: QAGateRequest):
    """
    Run QA gate on audio events timeline.
    
    Checks for:
    - Invalid SFX IDs
    - SFX density (spam)
    - Minimum gaps between SFX
    - Total SFX count
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="SFX manifest not found")
    
    manifest = load_manifest(manifest_path)
    
    report = run_qa_gate(
        events=request.events,
        manifest=manifest,
        max_sfx_per_5_seconds=request.max_sfx_per_5_seconds,
        min_gap_frames=request.min_gap_frames,
        max_total_sfx=request.max_total_sfx,
    )
    
    return report


@router.post("/anti-spam", response_model=AudioEvents)
async def apply_anti_spam(
    events: AudioEvents,
    max_per_window: int = Query(default=3, ge=1, le=10),
    window_frames: int = Query(default=150, ge=30, le=600),
):
    """
    Apply anti-spam filter to remove excess SFX.
    """
    return apply_anti_spam_filter(
        events=events,
        max_per_window=max_per_window,
        window_frames=window_frames,
    )


@router.post("/context-pack", response_model=ContextPackResponse)
async def generate_context_pack(request: ContextPackRequest):
    """
    Generate an AI context pack from the manifest.
    
    If beat_text is provided, generates a filtered pack with relevant SFX only.
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="SFX manifest not found")
    
    manifest = load_manifest(manifest_path)
    
    if request.beat_text:
        context_pack = build_filtered_context_pack(
            manifest=manifest,
            beat_text=request.beat_text,
            max_items=request.max_items,
            rules=request.custom_rules,
        )
    else:
        context_pack = build_sfx_context_pack(
            manifest=manifest,
            max_items=request.max_items,
            rules=request.custom_rules,
        )
    
    stats = get_context_pack_stats(context_pack)
    
    return ContextPackResponse(
        context_pack=context_pack,
        stats=stats,
    )


@router.post("/selection-prompt", response_model=SfxSelectionPromptResponse)
async def generate_selection_prompt(request: SfxSelectionPromptRequest):
    """
    Generate a complete SFX selection prompt for an LLM.
    
    Returns a prompt that includes the context pack and beat information.
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="SFX manifest not found")
    
    manifest = load_manifest(manifest_path)
    
    # Build filtered context pack from beat texts
    beat_texts = " ".join(b.text for b in request.beats)
    context_pack = build_filtered_context_pack(
        manifest=manifest,
        beat_text=beat_texts,
        max_items=request.max_context_items,
    )
    
    # Generate prompt
    prompt = make_sfx_selection_prompt(
        context_pack=context_pack,
        beats=request.beats,
        fps=request.fps,
    )
    
    # Estimate tokens
    estimated_tokens = len(prompt) // 4
    
    return SfxSelectionPromptResponse(
        prompt=prompt,
        estimated_tokens=estimated_tokens,
    )


@router.post("/suggest")
async def suggest_sfx(request: SuggestSfxRequest):
    """
    Suggest SFX for a given action type.
    
    Actions: hook, reveal, transition, punchline, cta, explain
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        return {"suggestions": []}
    
    manifest = load_manifest(manifest_path)
    
    suggestions = suggest_sfx_for_action(
        manifest=manifest,
        action=request.action,
        max_results=request.max_results,
    )
    
    # Enrich with full item data
    enriched = []
    for s in suggestions:
        item = manifest.get_by_id(s["id"])
        if item:
            enriched.append({
                **s,
                "item": item.model_dump(),
            })
    
    return {"suggestions": enriched}


@router.post("/best-match")
async def find_best_match(request: BestMatchRequest):
    """
    Find the best matching SFX for an unknown/hallucinated ID.
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="SFX manifest not found")
    
    manifest = load_manifest(manifest_path)
    
    match = best_sfx_match(
        manifest=manifest,
        requested_id_or_hint=request.requested_id,
        hint_tags=request.hint_tags,
        hint_category=request.hint_category,
    )
    
    if not match:
        return {"match": None}
    
    # Get full item
    item = manifest.get_by_id(match["id"])
    
    return {
        "match": {
            **match,
            "item": item.model_dump() if item else None,
        }
    }


@router.get("/item/{sfx_id}")
async def get_sfx_item(sfx_id: str):
    """
    Get a specific SFX item by ID.
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="SFX manifest not found")
    
    manifest = load_manifest(manifest_path)
    item = manifest.get_by_id(sfx_id)
    
    if not item:
        raise HTTPException(status_code=404, detail=f"SFX not found: {sfx_id}")
    
    return item.model_dump()


@router.get("/categories")
async def list_categories():
    """
    List all unique categories in the manifest.
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        return {"categories": []}
    
    manifest = load_manifest(manifest_path)
    categories = get_categories(manifest)
    
    return {"categories": categories}


@router.get("/tags")
async def list_tags(limit: int = Query(default=100, ge=1, le=500)):
    """
    List all unique tags in the manifest.
    """
    manifest_path = get_manifest_path()
    
    if not os.path.exists(manifest_path):
        return {"tags": []}
    
    manifest = load_manifest(manifest_path)
    all_tags = get_all_tags(manifest)
    
    return {"tags": all_tags[:limit], "total": len(all_tags)}
