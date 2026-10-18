"""
Content Variations API (PIPE-008)
==================================
Manage content reusability through title/description variations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from database.connection import get_db
from services.content_variations import (
    ContentReusabilityService,
    VariationType,
    get_content_reusability_service
)

router = APIRouter(prefix="/api/content-variations", tags=["Content Variations"])


# ==================== Request/Response Models ====================

class CreateVariationRequest(BaseModel):
    """Request to create a variation"""
    content_id: str
    variation_type: str  # "title", "description", "caption", "hashtags", "cta"
    text: str
    metadata: Optional[Dict[str, Any]] = None


class GenerateVariationsRequest(BaseModel):
    """Request to generate multiple variations"""
    content_id: str
    base_title: str
    base_description: str
    num_variations: int = 5


class MarkUsedRequest(BaseModel):
    """Request to mark variation as used"""
    variation_id: str
    performance_score: Optional[float] = None


class VariationResponse(BaseModel):
    """Variation response"""
    variation_id: str
    content_id: str
    variation_type: str
    text: str
    created_at: str
    last_used_at: Optional[str]
    usage_count: int
    performance_score: float


# ==================== Endpoints ====================

@router.post("/create")
async def create_variation(
    request: CreateVariationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new content variation

    Use this to manually add variations for a content piece.
    """
    try:
        service = get_content_reusability_service(db)

        # Parse variation type
        try:
            var_type = VariationType(request.variation_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid variation_type. Must be one of: {[t.value for t in VariationType]}"
            )

        variation = await service.create_variation(
            content_id=request.content_id,
            variation_type=var_type,
            text=request.text,
            metadata=request.metadata
        )

        return {
            "success": True,
            "variation_id": variation.variation_id,
            "variation": VariationResponse(
                variation_id=variation.variation_id,
                content_id=variation.content_id,
                variation_type=variation.variation_type.value,
                text=variation.text,
                created_at=variation.created_at.isoformat(),
                last_used_at=variation.last_used_at.isoformat() if variation.last_used_at else None,
                usage_count=variation.usage_count,
                performance_score=variation.performance_score
            )
        }

    except Exception as e:
        logger.error(f"Error creating variation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{content_id}")
async def get_variations(
    content_id: str,
    variation_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all variations for a content piece

    Optionally filter by variation type.
    """
    try:
        service = get_content_reusability_service(db)

        # Parse variation type if provided
        var_type = None
        if variation_type:
            try:
                var_type = VariationType(variation_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid variation_type. Must be one of: {[t.value for t in VariationType]}"
                )

        variations = await service.get_variations(content_id, var_type)

        return {
            "content_id": content_id,
            "count": len(variations),
            "variations": [
                VariationResponse(
                    variation_id=v.variation_id,
                    content_id=v.content_id,
                    variation_type=v.variation_type.value,
                    text=v.text,
                    created_at=v.created_at.isoformat(),
                    last_used_at=v.last_used_at.isoformat() if v.last_used_at else None,
                    usage_count=v.usage_count,
                    performance_score=v.performance_score
                )
                for v in variations
            ]
        }

    except Exception as e:
        logger.error(f"Error getting variations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{content_id}/next")
async def get_next_variation(
    content_id: str,
    variation_type: str,
    min_reuse_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the next unused variation for a content piece

    Prioritizes never-used variations, then least-recently-used.
    """
    try:
        service = get_content_reusability_service(db)

        try:
            var_type = VariationType(variation_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid variation_type. Must be one of: {[t.value for t in VariationType]}"
            )

        variation = await service.get_next_unused_variation(
            content_id=content_id,
            variation_type=var_type,
            min_reuse_days=min_reuse_days
        )

        if not variation:
            return {
                "available": False,
                "message": f"All variations used within last {min_reuse_days} days"
            }

        return {
            "available": True,
            "variation": VariationResponse(
                variation_id=variation.variation_id,
                content_id=variation.content_id,
                variation_type=variation.variation_type.value,
                text=variation.text,
                created_at=variation.created_at.isoformat(),
                last_used_at=variation.last_used_at.isoformat() if variation.last_used_at else None,
                usage_count=variation.usage_count,
                performance_score=variation.performance_score
            )
        }

    except Exception as e:
        logger.error(f"Error getting next variation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-used")
async def mark_used(
    request: MarkUsedRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a variation as used

    Call this after using a variation in a post to track usage.
    """
    try:
        service = get_content_reusability_service(db)

        await service.mark_variation_used(
            variation_id=request.variation_id,
            performance_score=request.performance_score
        )

        return {
            "success": True,
            "message": "Variation marked as used"
        }

    except Exception as e:
        logger.error(f"Error marking variation as used: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_variations(
    request: GenerateVariationsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate multiple variations using AI

    Creates num_variations different titles and descriptions
    for the content piece.
    """
    try:
        service = get_content_reusability_service(db)

        variation_set = await service.generate_variations(
            content_id=request.content_id,
            base_title=request.base_title,
            base_description=request.base_description,
            num_variations=request.num_variations
        )

        return {
            "success": True,
            "content_id": variation_set.content_id,
            "titles_generated": len(variation_set.titles),
            "descriptions_generated": len(variation_set.descriptions),
            "total_variations": len(variation_set.titles) + len(variation_set.descriptions)
        }

    except Exception as e:
        logger.error(f"Error generating variations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{content_id}/stats")
async def get_stats(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get usage statistics for a content piece's variations

    Returns metrics about variation usage, performance, and reusability.
    """
    try:
        service = get_content_reusability_service(db)

        stats = await service.get_variation_stats(content_id)

        return {
            "content_id": content_id,
            **stats
        }

    except Exception as e:
        logger.error(f"Error getting variation stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{content_id}/suggest-repost")
async def suggest_repost_timing(
    content_id: str,
    min_reuse_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Suggest when content can be reposted with a new variation

    Returns suggested repost date, or indicates if can repost now.
    """
    try:
        service = get_content_reusability_service(db)

        suggested_date = await service.suggest_repost_timing(
            content_id=content_id,
            min_reuse_days=min_reuse_days
        )

        if suggested_date is None:
            return {
                "can_repost_now": True,
                "message": "Unused variations available - can repost now!"
            }

        return {
            "can_repost_now": False,
            "suggested_date": suggested_date.isoformat(),
            "days_until_repost": (suggested_date - datetime.now(suggested_date.tzinfo)).days,
            "message": f"All variations used recently. Suggest reposting on {suggested_date.date()}"
        }

    except Exception as e:
        logger.error(f"Error suggesting repost timing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-generate")
async def bulk_generate(
    content_ids: List[str],
    num_variations: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate variations for multiple content pieces

    Useful for batch processing newly uploaded content.
    """
    try:
        service = get_content_reusability_service(db)

        results = await service.bulk_create_variations(
            content_ids=content_ids,
            num_variations=num_variations
        )

        return {
            "success": True,
            "processed": len(content_ids),
            "succeeded": len(results),
            "failed": len(content_ids) - len(results),
            "total_variations": sum(
                len(vs.titles) + len(vs.descriptions)
                for vs in results.values()
            )
        }

    except Exception as e:
        logger.error(f"Error bulk generating variations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
