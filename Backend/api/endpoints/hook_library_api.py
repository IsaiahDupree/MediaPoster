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


@router.post("/{hook_id}/track-usage")
async def track_hook_usage(hook_id: str, platform: str = "instagram", post_url: str = "", notes: str = ""):
    """
    Record that a hook was used in a post. Tracks which hooks you've actually posted.
    """
    service = get_hook_library_service()
    hooks = service.get_all_hooks()
    hook = next((h for h in hooks if h.get("id") == hook_id), None)
    if not hook:
        raise HTTPException(status_code=404, detail="Hook not found")

    from datetime import datetime
    usage_entry = {
        "id": f"usage_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "hook_id": hook_id,
        "hook_text": hook.get("hook", ""),
        "platform": platform,
        "post_url": post_url,
        "notes": notes,
        "used_at": datetime.now().isoformat(),
        "results": None,
    }

    # Load or create usage log
    usage_path = service.storage_path.parent / "hook_usage_log.json"
    usage_log = []
    if usage_path.exists():
        try:
            import json
            with open(usage_path) as f:
                usage_log = json.load(f)
        except Exception:
            usage_log = []

    usage_log.append(usage_entry)

    import json
    with open(usage_path, "w") as f:
        json.dump(usage_log, f, indent=2)

    # Increment hook usage count
    hook["usage_count"] = hook.get("usage_count", 0) + 1
    service._save_hooks(hooks)

    return {"status": "tracked", "usage": usage_entry}


@router.patch("/{hook_id}/track-results")
async def track_hook_results(
    hook_id: str,
    usage_id: str = "",
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    saves: int = 0,
    watch_through_rate: float = 0.0,
):
    """
    Record performance results for a hook that was used.
    Updates the usage log entry with actual engagement metrics.
    """
    service = get_hook_library_service()
    usage_path = service.storage_path.parent / "hook_usage_log.json"

    if not usage_path.exists():
        raise HTTPException(status_code=404, detail="No usage log found")

    import json
    with open(usage_path) as f:
        usage_log = json.load(f)

    # Find usage entry
    target = None
    if usage_id:
        target = next((u for u in usage_log if u.get("id") == usage_id), None)
    else:
        # Find latest usage of this hook
        for u in reversed(usage_log):
            if u.get("hook_id") == hook_id:
                target = u
                break

    if not target:
        raise HTTPException(status_code=404, detail="Usage entry not found")

    from datetime import datetime
    target["results"] = {
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "watch_through_rate": watch_through_rate,
        "engagement_rate": round((likes + comments + shares + saves) / max(views, 1) * 100, 2),
        "recorded_at": datetime.now().isoformat(),
    }

    with open(usage_path, "w") as f:
        json.dump(usage_log, f, indent=2)

    return {"status": "results_recorded", "usage": target}


@router.get("/effectiveness")
async def get_hook_effectiveness():
    """
    Get hook effectiveness report: which hooks performed best when actually used.
    Returns hooks sorted by engagement rate with full performance data.
    """
    service = get_hook_library_service()
    usage_path = service.storage_path.parent / "hook_usage_log.json"

    if not usage_path.exists():
        return {"total_uses": 0, "with_results": 0, "hooks": []}

    import json
    with open(usage_path) as f:
        usage_log = json.load(f)

    # Group by hook_id
    hook_perf: dict = {}
    for entry in usage_log:
        hid = entry.get("hook_id", "")
        if hid not in hook_perf:
            hook_perf[hid] = {
                "hook_id": hid,
                "hook_text": entry.get("hook_text", ""),
                "times_used": 0,
                "times_with_results": 0,
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "total_saves": 0,
                "avg_engagement_rate": 0,
                "best_platform": "",
                "usages": [],
            }
        hook_perf[hid]["times_used"] += 1
        hook_perf[hid]["usages"].append(entry)

        if entry.get("results"):
            r = entry["results"]
            hook_perf[hid]["times_with_results"] += 1
            hook_perf[hid]["total_views"] += r.get("views", 0)
            hook_perf[hid]["total_likes"] += r.get("likes", 0)
            hook_perf[hid]["total_comments"] += r.get("comments", 0)
            hook_perf[hid]["total_shares"] += r.get("shares", 0)
            hook_perf[hid]["total_saves"] += r.get("saves", 0)

    # Calculate averages
    for hid, perf in hook_perf.items():
        if perf["total_views"] > 0:
            total_eng = perf["total_likes"] + perf["total_comments"] + perf["total_shares"] + perf["total_saves"]
            perf["avg_engagement_rate"] = round(total_eng / perf["total_views"] * 100, 2)
        # Remove full usages from summary (too verbose)
        perf.pop("usages", None)

    sorted_hooks = sorted(hook_perf.values(), key=lambda h: h["avg_engagement_rate"], reverse=True)
    total_with_results = sum(1 for h in sorted_hooks if h["times_with_results"] > 0)

    return {
        "total_uses": len(usage_log),
        "unique_hooks_used": len(hook_perf),
        "with_results": total_with_results,
        "hooks": sorted_hooks,
    }


@router.post("/auto-populate")
async def auto_populate_hooks():
    """
    Scan all competitor analysis data and populate the hook library.
    Extracts hooks from every analyzed competitor account.
    """
    service = get_hook_library_service()
    result = await service.auto_populate_from_all_competitors()
    return result
