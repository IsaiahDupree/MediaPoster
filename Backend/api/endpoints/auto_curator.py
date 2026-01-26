"""
Auto-Curator API Endpoints
==========================
API for automatic content curation based on rules and thresholds.

Endpoints:
- POST /api/curator/curate - Curate content based on analysis
- GET /api/curator/rules - List all curation rules
- POST /api/curator/rules - Add a new curation rule
- PUT /api/curator/rules/{rule_id} - Update a curation rule
- DELETE /api/curator/rules/{rule_id} - Remove a curation rule
- GET /api/curator/stats - Get curation statistics
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from loguru import logger

from services.auto_curator import (
    get_auto_curator,
    CurationRule,
    CurationDecision
)

router = APIRouter(prefix="/api/curator", tags=["Auto-Curator"])


class CurateRequest(BaseModel):
    """Request to curate content"""
    content_analysis: Dict[str, Any] = Field(..., description="Content analysis with scores")
    platform: Optional[str] = Field(None, description="Target platform")


class CurationRuleRequest(BaseModel):
    """Request to create/update a curation rule"""
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    conditions: Dict[str, Any] = Field(..., description="Rule conditions")
    decision: str = Field(..., description="Decision: approve, reject, or manual_review")
    priority: int = Field(0, description="Rule priority (higher = evaluated first)")
    enabled: bool = Field(True, description="Whether rule is enabled")


@router.post("/curate")
async def curate_content(request: CurateRequest):
    """
    Curate content based on analysis

    Applies curation rules to content analysis and returns a decision.

    Args:
        content_analysis: Content analysis with scores (sentiment, quality, etc.)
        platform: Target platform (optional)

    Returns:
        Curation decision with confidence and reasoning
    """
    try:
        curator = get_auto_curator()

        result = curator.curate(
            content_analysis=request.content_analysis,
            platform=request.platform
        )

        return {
            "success": True,
            "data": {
                "decision": result.decision.value,
                "confidence": result.confidence,
                "matched_rules": result.matched_rules,
                "reasons": result.reasons,
                "scores": result.scores,
                "processing_time_ms": result.processing_time_ms
            }
        }

    except Exception as e:
        logger.error(f"Error curating content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules")
async def list_rules():
    """
    List all curation rules

    Returns rules sorted by priority (highest first).

    Returns:
        List of curation rules
    """
    try:
        curator = get_auto_curator()
        rules = curator.list_rules()

        return {
            "success": True,
            "data": {
                "rules": [
                    {
                        "rule_id": r.rule_id,
                        "name": r.name,
                        "description": r.description,
                        "conditions": r.conditions,
                        "decision": r.decision.value,
                        "priority": r.priority,
                        "enabled": r.enabled
                    }
                    for r in rules
                ],
                "count": len(rules)
            }
        }

    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules")
async def create_rule(request: CurationRuleRequest):
    """
    Create a new curation rule

    Args:
        rule: Rule configuration

    Returns:
        Created rule
    """
    try:
        # Validate decision
        try:
            decision = CurationDecision(request.decision)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision: {request.decision}. "
                       f"Must be: approve, reject, or manual_review"
            )

        curator = get_auto_curator()

        # Create rule
        rule = CurationRule(
            rule_id=request.rule_id,
            name=request.name,
            description=request.description,
            conditions=request.conditions,
            decision=decision,
            priority=request.priority,
            enabled=request.enabled
        )

        curator.add_rule(rule)

        return {
            "success": True,
            "message": "Rule created",
            "data": {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "decision": rule.decision.value,
                "priority": rule.priority
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, request: CurationRuleRequest):
    """
    Update an existing curation rule

    Args:
        rule_id: Rule ID to update
        request: New rule configuration

    Returns:
        Updated rule
    """
    try:
        # Validate decision
        try:
            decision = CurationDecision(request.decision)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision: {request.decision}"
            )

        curator = get_auto_curator()

        # Check if rule exists
        existing_rule = curator.get_rule(rule_id)
        if not existing_rule:
            raise HTTPException(
                status_code=404,
                detail=f"Rule not found: {rule_id}"
            )

        # Update rule
        rule = CurationRule(
            rule_id=request.rule_id,
            name=request.name,
            description=request.description,
            conditions=request.conditions,
            decision=decision,
            priority=request.priority,
            enabled=request.enabled
        )

        curator.add_rule(rule)

        return {
            "success": True,
            "message": "Rule updated",
            "data": {
                "rule_id": rule.rule_id,
                "name": rule.name
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """
    Delete a curation rule

    Args:
        rule_id: Rule ID to delete

    Returns:
        Success message
    """
    try:
        curator = get_auto_curator()

        removed = curator.remove_rule(rule_id)

        if not removed:
            raise HTTPException(
                status_code=404,
                detail=f"Rule not found: {rule_id}"
            )

        return {
            "success": True,
            "message": "Rule deleted",
            "data": {
                "rule_id": rule_id
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_curator_stats():
    """
    Get auto-curator statistics

    Returns statistics about configured rules.

    Returns:
        Curator statistics
    """
    try:
        curator = get_auto_curator()
        stats = curator.get_stats()

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        logger.error(f"Error getting curator stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def curator_health():
    """
    Health check for auto-curator

    Returns:
        Health status
    """
    try:
        curator = get_auto_curator()
        stats = curator.get_stats()

        return {
            "success": True,
            "data": {
                "status": "operational",
                "rules_configured": stats["total_rules"]
            }
        }

    except Exception as e:
        logger.error(f"Error checking curator health: {e}")
        return {
            "success": False,
            "error": str(e)
        }
