"""
Template Auto-Forker API Endpoints (AUTO-003)
==============================================
API for managing template auto-forking and A/B testing.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from enum import Enum
from loguru import logger

from services.template_auto_forker import (
    TemplateAutoForker,
    ForkType,
    get_template_auto_forker
)

router = APIRouter()


# =========================================================================
# REQUEST/RESPONSE MODELS
# =========================================================================

class ForkTypeModel(str, Enum):
    """Fork type options"""
    FATE_SHIFT = "fate_shift"
    AWARENESS_SHIFT = "awareness_shift"
    CTA_VARIATION = "cta_variation"
    HOOK_VARIATION = "hook_variation"
    STYLE_VARIATION = "style_variation"


class ForkTemplateRequest(BaseModel):
    """Request to fork a template"""
    template_id: UUID = Field(..., description="Parent template UUID")
    fork_type: ForkTypeModel = Field(..., description="Type of variation to create")
    custom_modifications: Optional[dict] = Field(None, description="Optional custom modifications")


class ForkTemplateResponse(BaseModel):
    """Response after forking a template"""
    success: bool
    fork_id: Optional[UUID] = None
    message: str


class ForkStatusResponse(BaseModel):
    """Status of template auto-forker"""
    is_running: bool
    max_forks_per_template: int
    min_uses_before_fork: int
    fork_cooldown_hours: int
    total_forks_created: int


# =========================================================================
# ENDPOINTS
# =========================================================================

@router.post("/fork", response_model=ForkTemplateResponse)
async def fork_template(request: ForkTemplateRequest):
    """
    Manually fork a template for A/B testing

    Creates a controlled variation of the specified template.
    The fork will be tracked separately in the bandit allocator.

    **Fork Types:**
    - `fate_shift`: Adjust FATE weights (±10% between dimensions)
    - `awareness_shift`: Test at adjacent awareness level
    - `cta_variation`: Change CTA strength (none/soft/direct)
    - `hook_variation`: Test alternative hook patterns
    - `style_variation`: Adjust tone/formality

    **Example:**
    ```json
    {
      "template_id": "123e4567-e89b-12d3-a456-426614174000",
      "fork_type": "fate_shift"
    }
    ```
    """
    try:
        forker = get_template_auto_forker()

        # Convert enum to ForkType
        fork_type = ForkType[request.fork_type.value.upper()]

        fork_id = await forker.fork_template(
            template_id=request.template_id,
            fork_type=fork_type,
            custom_modifications=request.custom_modifications
        )

        if fork_id:
            return ForkTemplateResponse(
                success=True,
                fork_id=fork_id,
                message=f"Successfully forked template {request.template_id}"
            )
        else:
            return ForkTemplateResponse(
                success=False,
                message="Failed to fork template (check cooldown, max forks, or parent existence)"
            )

    except Exception as e:
        logger.error(f"Error forking template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=ForkStatusResponse)
async def get_fork_status():
    """
    Get template auto-forker status

    Returns configuration and activity metrics.
    """
    try:
        forker = get_template_auto_forker()

        # Count total forks created
        total_forks = sum(len(times) for times in forker._fork_history.values())

        return ForkStatusResponse(
            is_running=forker._is_running,
            max_forks_per_template=forker.max_forks_per_template,
            min_uses_before_fork=forker.min_uses_before_fork,
            fork_cooldown_hours=forker.fork_cooldown_hours,
            total_forks_created=total_forks
        )

    except Exception as e:
        logger.error(f"Error getting fork status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/template/{template_id}/forks")
async def get_template_forks(template_id: UUID):
    """
    Get all forks of a specific template

    Returns list of fork UUIDs and their creation times.
    """
    try:
        forker = get_template_auto_forker()

        fork_times = forker._fork_history.get(template_id, [])

        return {
            "template_id": str(template_id),
            "fork_count": len(fork_times),
            "fork_times": [t.isoformat() for t in fork_times],
            "can_fork_now": forker._can_fork(template_id)
        }

    except Exception as e:
        logger.error(f"Error getting template forks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-fork-now")
async def trigger_auto_fork():
    """
    Manually trigger auto-fork check

    Immediately checks for winning templates and creates forks.
    Normally runs every 24 hours automatically.
    """
    try:
        forker = get_template_auto_forker()

        await forker._auto_fork_winners()

        return {
            "success": True,
            "message": "Auto-fork check completed"
        }

    except Exception as e:
        logger.error(f"Error triggering auto-fork: {e}")
        raise HTTPException(status_code=500, detail=str(e))
