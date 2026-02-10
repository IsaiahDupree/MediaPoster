"""
Caption Variants API
====================
Endpoints for AI-powered per-platform caption rewriting.
"""

import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/caption-variants", tags=["caption-variants"])


# ─── Models ──────────────────────────────────────────────────────────────────

class GenerateVariantsRequest(BaseModel):
    caption: str
    platforms: Optional[List[str]] = None
    context: Optional[str] = None
    hashtags: Optional[List[str]] = None


class GenerateSingleRequest(BaseModel):
    caption: str
    platform: str
    context: Optional[str] = None
    hashtags: Optional[List[str]] = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_variants(req: GenerateVariantsRequest):
    """Generate caption variants for multiple platforms."""
    from services.caption_variants_service import CaptionVariantsService

    service = CaptionVariantsService()
    variants = await service.generate_variants(
        base_caption=req.caption,
        platforms=req.platforms,
        context=req.context,
        hashtags=req.hashtags,
    )
    return {
        "success": True,
        "base_caption": req.caption,
        "variants": variants,
        "platform_count": len(variants),
    }


@router.post("/generate-single")
async def generate_single(req: GenerateSingleRequest):
    """Generate a caption variant for a single platform."""
    from services.caption_variants_service import CaptionVariantsService

    service = CaptionVariantsService()
    variant = await service.generate_single(
        base_caption=req.caption,
        platform=req.platform,
        context=req.context,
        hashtags=req.hashtags,
    )
    return {
        "success": True,
        "platform": req.platform,
        "original": req.caption,
        "variant": variant,
    }


@router.get("/platforms")
async def get_platforms():
    """List supported platforms with tone descriptions."""
    from services.caption_variants_service import CaptionVariantsService, PLATFORM_TONES

    platforms = []
    for name, info in PLATFORM_TONES.items():
        platforms.append({
            "name": name,
            "tone": info["tone"],
            "max_length": info["max_length"],
            "max_hashtags": info["max_hashtags"],
        })
    return {"platforms": platforms, "enabled": os.getenv("ENABLE_AI_CAPTION_VARIANTS", "true").lower() == "true"}
