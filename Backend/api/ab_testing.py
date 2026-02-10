"""
A/B Testing API
================
Endpoints for creating, managing, and analyzing A/B tests.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Query
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/ab-tests", tags=["ab-testing"])


# ─── Models ──────────────────────────────────────────────────────────────────

class CreateTestRequest(BaseModel):
    name: str
    test_type: str  # caption, hook, time, title, hashtag, account
    platform: str
    media_path: Optional[str] = None
    variants: Optional[Dict[str, Dict[str, Any]]] = None
    hypothesis: Optional[str] = None
    auto_schedule: bool = True


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("")
async def create_test(req: CreateTestRequest):
    """Create a new A/B test with variant assignments."""
    from services.ab_testing_service import ABTestingService

    svc = ABTestingService()
    return await svc.create_test(
        name=req.name,
        test_type=req.test_type,
        platform=req.platform,
        media_path=req.media_path,
        variants=req.variants,
        hypothesis=req.hypothesis,
        auto_schedule=req.auto_schedule,
    )


@router.get("")
async def list_tests(
    status: Optional[str] = None,
    platform: Optional[str] = None,
):
    """List all A/B tests."""
    from services.ab_testing_service import ABTestingService

    svc = ABTestingService()
    tests = await svc.list_tests(status=status, platform=platform)
    return {"tests": tests, "total": len(tests)}


@router.get("/learnings")
async def get_learnings(
    platform: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """Browse accumulated A/B test learnings."""
    from services.ab_testing_service import ABTestingService

    svc = ABTestingService()
    learnings = await svc.get_learnings(platform=platform, limit=limit)
    return {"learnings": learnings, "total": len(learnings)}


@router.get("/{test_id}")
async def get_test(test_id: str):
    """Get test details including variants and metrics."""
    from services.ab_testing_service import ABTestingService

    svc = ABTestingService()
    test = await svc.get_test(test_id)
    if not test:
        return {"error": "Test not found"}
    return test


@router.post("/{test_id}/collect")
async def collect_metrics(test_id: str):
    """Force metrics collection for a test."""
    from services.ab_testing_service import ABTestingService

    svc = ABTestingService()
    return await svc.collect_metrics(test_id)


@router.post("/{test_id}/analyze")
async def analyze_test(test_id: str):
    """Run statistical analysis on a test."""
    from services.ab_testing_service import ABTestingService

    svc = ABTestingService()
    return await svc.analyze_test(test_id)


@router.post("/{test_id}/declare")
async def declare_winner(test_id: str):
    """Force declare a winner for a test."""
    from services.ab_testing_service import ABTestingService

    svc = ABTestingService()
    return await svc.declare_winner(test_id)
