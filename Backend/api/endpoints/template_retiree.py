"""
Template Retiree API Endpoints (AUTO-004)
==========================================
API for managing template retirement and lifecycle.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from loguru import logger

from services.template_retiree import (
    TemplateRetiree,
    RetirementCandidate,
    get_template_retiree
)

router = APIRouter()


# =========================================================================
# RESPONSE MODELS
# =========================================================================

class RetirementCandidateResponse(BaseModel):
    """Retirement candidate information"""
    template_id: str
    template_name: str
    allocation: float
    usage_count: int
    created_at: str
    consecutive_low_cycles: int


class RetireTemplateRequest(BaseModel):
    """Request to retire a template"""
    template_id: UUID = Field(..., description="Template UUID to retire")
    reason: Optional[str] = Field(None, description="Retirement reason")


class RetireTemplateResponse(BaseModel):
    """Response after retiring a template"""
    success: bool
    message: str


class RetireStatusResponse(BaseModel):
    """Status of template retiree"""
    is_running: bool
    allocation_threshold: float
    min_uses_for_retirement: int
    grace_period_days: int
    consecutive_cycles_required: int
    tracked_templates: int


# =========================================================================
# ENDPOINTS
# =========================================================================

@router.get("/candidates", response_model=List[RetirementCandidateResponse])
async def get_retirement_candidates():
    """
    Get templates that are candidates for retirement

    Returns templates with:
    - Allocation < 5% for 3+ consecutive cycles
    - At least 50 uses
    - Out of 30-day grace period

    **Example Response:**
    ```json
    [
      {
        "template_id": "123e4567-e89b-12d3-a456-426614174000",
        "template_name": "Old Hook Template",
        "allocation": 0.02,
        "usage_count": 75,
        "created_at": "2025-12-01T00:00:00Z",
        "consecutive_low_cycles": 4
      }
    ]
    ```
    """
    try:
        retiree = get_template_retiree()

        candidates = await retiree.get_retirement_candidates()

        return [
            RetirementCandidateResponse(
                template_id=str(c.template_id),
                template_name=c.template_name,
                allocation=c.allocation,
                usage_count=c.usage_count,
                created_at=c.created_at.isoformat() if c.created_at else "",
                consecutive_low_cycles=c.consecutive_low_cycles
            )
            for c in candidates
        ]

    except Exception as e:
        logger.error(f"Error getting retirement candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retire", response_model=RetireTemplateResponse)
async def retire_template(request: RetireTemplateRequest):
    """
    Manually retire a template

    Deactivates the template (sets is_active = False).
    Retired templates are preserved for analysis but won't be used for new content.

    **Example:**
    ```json
    {
      "template_id": "123e4567-e89b-12d3-a456-426614174000",
      "reason": "Consistently low performance"
    }
    ```
    """
    try:
        retiree = get_template_retiree()

        success = await retiree.retire_template(
            template_id=request.template_id,
            reason=request.reason
        )

        if success:
            return RetireTemplateResponse(
                success=True,
                message=f"Successfully retired template {request.template_id}"
            )
        else:
            return RetireTemplateResponse(
                success=False,
                message="Failed to retire template (check if template exists and is active)"
            )

    except Exception as e:
        logger.error(f"Error retiring template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=RetireStatusResponse)
async def get_retiree_status():
    """
    Get template retiree status

    Returns configuration and tracking metrics.
    """
    try:
        retiree = get_template_retiree()

        return RetireStatusResponse(
            is_running=retiree._is_running,
            allocation_threshold=retiree.allocation_threshold,
            min_uses_for_retirement=retiree.min_uses_for_retirement,
            grace_period_days=retiree.grace_period_days,
            consecutive_cycles_required=retiree.consecutive_cycles_required,
            tracked_templates=len(retiree._low_allocation_history)
        )

    except Exception as e:
        logger.error(f"Error getting retiree status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-now")
async def trigger_retirement_check():
    """
    Manually trigger retirement check

    Immediately checks for retirement candidates and retires eligible templates.
    Normally runs every 24 hours automatically.
    """
    try:
        retiree = get_template_retiree()

        await retiree._check_and_retire()

        return {
            "success": True,
            "message": "Retirement check completed"
        }

    except Exception as e:
        logger.error(f"Error triggering retirement check: {e}")
        raise HTTPException(status_code=500, detail=str(e))
