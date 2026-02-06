"""
Hook Library API Endpoints
Manage curated hooks extracted from competitor content analysis.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from services.hook_library_service import get_hook_library_service, SavedHook

router = APIRouter(prefix="/api/hooks", tags=["Hook Library"])


class AddHookRequest(BaseModel):
    """Request to add a hook to the library"""
    hook_text: str
    hook_type: str
    source_account: Optional[str] = None
    source_views: Optional[int] = None
    source_likes: Optional[int] = None
    source_comments: Optional[int] = None
    notes: Optional[str] = None
    tags: List[str] = []


class GenerateVariationsRequest(BaseModel):
    """Request to generate hook variations"""
    hook_text: str
    niche: str = "personal branding"
    count: int = 5


@router.get("/health")
async def health_check():
    """Health check for hook library service"""
    service = get_hook_library_service()
    hooks = service.get_hooks(limit=0)
    return {
        "status": "healthy",
        "service": "hook-library",
        "total_hooks": len(service._hooks),
    }


@router.get("")
async def list_hooks(
    hook_type: Optional[str] = Query(None, description="Filter by hook type"),
    source_account: Optional[str] = Query(None, description="Filter by source competitor"),
    favorites_only: bool = Query(False, description="Only show favorites"),
    sort_by: str = Query("performance_score", description="Sort by: performance_score, created_at, times_used"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    List hooks from the library with optional filtering.
    
    Sort options:
    - performance_score: Highest performing hooks first
    - created_at: Most recently added first
    - times_used: Most used hooks first
    """
    service = get_hook_library_service()
    hooks = service.get_hooks(
        hook_type=hook_type,
        source_account=source_account,
        favorites_only=favorites_only,
        limit=limit,
        sort_by=sort_by,
    )
    return {
        "count": len(hooks),
        "hooks": hooks,
    }


@router.get("/by-type")
async def get_hooks_by_type():
    """Get all hooks grouped by type (question, bold_statement, etc.)"""
    service = get_hook_library_service()
    grouped = service.get_hooks_by_type()
    return {
        "types": list(grouped.keys()),
        "hooks_by_type": {
            k: {"count": len(v), "hooks": v[:10]}
            for k, v in grouped.items()
        },
        "total": sum(len(v) for v in grouped.values()),
    }


@router.post("")
async def add_hook(request: AddHookRequest):
    """Add a new hook to the library"""
    service = get_hook_library_service()

    hook = SavedHook(
        hook_text=request.hook_text,
        hook_type=request.hook_type,
        source_account=request.source_account,
        source_views=request.source_views,
        source_likes=request.source_likes,
        source_comments=request.source_comments,
        notes=request.notes,
        tags=request.tags,
    )

    result = service.add_hook(hook)
    return {"status": "added", "hook": result}


@router.post("/{hook_id}/favorite")
async def toggle_favorite(hook_id: str):
    """Toggle favorite status of a hook"""
    service = get_hook_library_service()
    result = service.toggle_favorite(hook_id)
    if not result:
        raise HTTPException(status_code=404, detail="Hook not found")
    return {"status": "toggled", "hook": result}


@router.post("/{hook_id}/used")
async def mark_hook_used(hook_id: str):
    """Increment usage count when a hook is used in content"""
    service = get_hook_library_service()
    result = service.increment_usage(hook_id)
    if not result:
        raise HTTPException(status_code=404, detail="Hook not found")
    return {"status": "updated", "hook": result}


@router.delete("/{hook_id}")
async def delete_hook(hook_id: str):
    """Delete a hook from the library"""
    service = get_hook_library_service()
    deleted = service.delete_hook(hook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Hook not found")
    return {"status": "deleted", "hook_id": hook_id}


@router.post("/generate-variations")
async def generate_variations(request: GenerateVariationsRequest):
    """
    Generate AI-powered variations of a hook.
    Returns multiple unique variations adapted for different sub-topics.
    """
    service = get_hook_library_service()

    variations = await service.generate_variations(
        hook_text=request.hook_text,
        niche=request.niche,
        count=request.count,
    )

    if not variations:
        raise HTTPException(status_code=500, detail="Failed to generate variations")

    return {
        "original": request.hook_text,
        "niche": request.niche,
        "variations": variations,
    }


@router.post("/extract/{username}")
async def extract_hooks_from_competitor(username: str):
    """Extract hooks from a competitor's analysis and add to library"""
    service = get_hook_library_service()
    hooks = service.extract_hooks_from_analysis(username)

    if not hooks:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis found for @{username}. Run /api/competitors/accounts/{username}/analyze first.",
        )

    return {
        "status": "extracted",
        "username": username,
        "hooks_added": len(hooks),
        "hooks": hooks,
    }


@router.get("/scored")
async def get_scored_hooks():
    """
    Get all hooks scored and tiered by engagement + usage metrics.
    
    Tiers:
    - S: score >= 1000 (top performers)
    - A: score >= 500
    - B: score >= 100
    - C: score < 100 (new/untested)
    """
    service = get_hook_library_service()
    scored = service.score_hooks()
    tiers = {}
    for h in scored:
        t = h.get("tier", "C")
        tiers.setdefault(t, 0)
        tiers[t] += 1
    return {
        "total": len(scored),
        "tier_breakdown": tiers,
        "hooks": scored,
    }


@router.post("/{hook_id}/ab-test")
async def generate_ab_test(hook_id: str, niche: str = "personal branding"):
    """
    Generate an AI-powered A/B test plan for a specific hook.
    Returns: original hook, variant, hypothesis, rationale, and test parameters.
    """
    service = get_hook_library_service()
    result = await service.generate_ab_test(hook_id=hook_id, niche=niche)
    if result.get("error") == "Hook not found":
        raise HTTPException(status_code=404, detail="Hook not found")
    return result


@router.post("/auto-populate")
async def auto_populate_hooks():
    """
    Scan all competitor analysis data and populate the hook library.
    Extracts hooks from every analyzed competitor account.
    """
    service = get_hook_library_service()
    result = await service.auto_populate_from_all_competitors()
    return result
