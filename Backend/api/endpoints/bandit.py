"""
Bandit Allocator API Endpoints (AUTO-002)
==========================================
REST API for Thompson Sampling-based template allocation.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, UUID4
from typing import Optional, Dict, Any, List
from uuid import UUID

from services.bandit_allocator import get_bandit_allocator, BanditAllocator
from loguru import logger


router = APIRouter(prefix="/api/bandit", tags=["Bandit Allocation"])


class ComputeAllocationsRequest(BaseModel):
    """Request to compute allocations"""
    awareness_level: Optional[str] = Field(None, description="Filter by awareness level")
    brand_id: Optional[UUID4] = Field(None, description="Filter by brand ID")
    force_refresh: bool = Field(False, description="Force cache refresh")


class AllocationsResponse(BaseModel):
    """Response with allocation results"""
    success: bool
    allocations: Dict[str, float]
    stats: List[Dict[str, Any]]
    cached: Optional[bool] = None
    cache_age_seconds: Optional[float] = None
    message: Optional[str] = None


class TemplateAllocationResponse(BaseModel):
    """Response for single template allocation"""
    success: bool
    template_id: str
    allocation: float
    message: Optional[str] = None


@router.post("/compute", response_model=AllocationsResponse)
async def compute_allocations(
    request: ComputeAllocationsRequest,
    allocator: BanditAllocator = Depends(get_bandit_allocator)
):
    """
    Compute Thompson Sampling allocations for templates

    This endpoint implements the 70/20/10 bandit allocation strategy:
    - 70% → Top performers (winners)
    - 20% → Promising but under-tested
    - 10% → New experiments

    **Thompson Sampling Algorithm:**
    1. Track wins/losses for each template (based on reward threshold)
    2. Model each template as Beta(wins + 1, losses + 1) distribution
    3. Sample theta from each Beta distribution
    4. Sort templates by sampled theta values
    5. Assign allocation buckets and compute probabilities

    **Example:**
    ```bash
    curl -X POST http://localhost:5555/api/bandit/compute \\
      -H "Content-Type: application/json" \\
      -d '{"awareness_level": "problem_aware", "force_refresh": true}'
    ```
    """
    try:
        result = await allocator.compute_allocations(
            awareness_level=request.awareness_level,
            brand_id=request.brand_id,
            force_refresh=request.force_refresh
        )

        return AllocationsResponse(
            success=True,
            allocations=result.get("allocations", {}),
            stats=result.get("stats", []),
            cached=result.get("cached", False),
            cache_age_seconds=result.get("cache_age_seconds"),
            message=f"Computed allocations for {len(result.get('stats', []))} templates"
        )

    except Exception as e:
        logger.error(f"Error computing allocations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allocations", response_model=AllocationsResponse)
async def get_allocations(
    awareness_level: Optional[str] = Query(None, description="Filter by awareness level"),
    brand_id: Optional[UUID] = Query(None, description="Filter by brand ID"),
    force_refresh: bool = Query(False, description="Force cache refresh"),
    allocator: BanditAllocator = Depends(get_bandit_allocator)
):
    """
    Get current template allocations (cached or recomputed)

    Returns the cached allocations if available and valid (< 1 hour old).
    Use `force_refresh=true` to recompute fresh allocations.

    **Example:**
    ```bash
    curl http://localhost:5555/api/bandit/allocations?awareness_level=problem_aware
    ```
    """
    try:
        result = await allocator.compute_allocations(
            awareness_level=awareness_level,
            brand_id=brand_id,
            force_refresh=force_refresh
        )

        return AllocationsResponse(
            success=True,
            allocations=result.get("allocations", {}),
            stats=result.get("stats", []),
            cached=result.get("cached", False),
            cache_age_seconds=result.get("cache_age_seconds"),
            message="Allocations retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Error getting allocations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allocation/{template_id}", response_model=TemplateAllocationResponse)
async def get_template_allocation(
    template_id: UUID,
    allocator: BanditAllocator = Depends(get_bandit_allocator)
):
    """
    Get allocation probability for a specific template

    Returns the Thompson Sampling allocation probability for a single template.
    This represents the percentage of slots that should use this template.

    **Example:**
    ```bash
    curl http://localhost:5555/api/bandit/allocation/550e8400-e29b-41d4-a716-446655440000
    ```
    """
    try:
        allocation = await allocator.get_template_allocation(template_id)

        return TemplateAllocationResponse(
            success=True,
            template_id=str(template_id),
            allocation=allocation,
            message=f"Allocation: {allocation:.2%}"
        )

    except Exception as e:
        logger.error(f"Error getting template allocation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_bandit_status(
    allocator: BanditAllocator = Depends(get_bandit_allocator)
):
    """
    Get bandit allocator service status

    Returns configuration, cache status, and service health.

    **Example:**
    ```bash
    curl http://localhost:5555/api/bandit/status
    ```
    """
    try:
        cache_valid = allocator._is_cache_valid()
        cache_age = 0.0

        if allocator._cache_timestamp:
            from datetime import datetime, timezone
            cache_age = (
                datetime.now(timezone.utc) - allocator._cache_timestamp
            ).total_seconds()

        return {
            "success": True,
            "status": "running" if allocator._is_running else "stopped",
            "config": {
                "winner_weight": allocator.winner_weight,
                "promising_weight": allocator.promising_weight,
                "experiment_weight": allocator.experiment_weight,
                "reward_threshold": allocator.reward_threshold,
                "min_uses_for_confidence": allocator.min_uses_for_confidence,
                "min_allocation": allocator.min_allocation,
                "max_allocation": allocator.max_allocation
            },
            "cache": {
                "valid": cache_valid,
                "age_seconds": cache_age,
                "ttl_seconds": allocator._cache_ttl_seconds,
                "entries": len(allocator._allocation_cache)
            },
            "message": "Bandit allocator service operational"
        }

    except Exception as e:
        logger.error(f"Error getting bandit status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
