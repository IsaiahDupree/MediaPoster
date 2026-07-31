"""
Script Generation API
======================
Turns a topic (typically the output of /api/recommend/next-content) into a
full, copy-pasteable production packet: hook, main points, proof/demo, CTA,
full spoken script, and a shot-by-shot visual plan.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Brand
from services.script_generation import ScriptGenerationUnavailable, get_script_generation_service

router = APIRouter(prefix="/api/scripts", tags=["Script Generation"])


class ScriptRequest(BaseModel):
    topic: str
    angle: Optional[str] = None
    format: Optional[str] = None
    platform: Optional[str] = None
    hook: Optional[str] = None
    reasoning: Optional[str] = None
    brand_id: Optional[UUID] = None
    target_audience: Optional[str] = None
    available_minutes: Optional[int] = None


@router.post("/generate")
async def generate_script(req: ScriptRequest, db: AsyncSession = Depends(get_db)):
    """
    Generate a full script from a topic. Field names match
    recommend_next_content's recommendation object (topic/angle/format/
    platform/hook/reasoning), so its output can be passed straight through.
    brand_id resolves voice/audience/available_minutes the same way
    recommend_next_content does; explicit fields on this request still win.
    """
    brand_voice = None
    target_audience = req.target_audience
    resolved_available_minutes = req.available_minutes

    if req.brand_id is not None:
        result = await db.execute(select(Brand).where(Brand.id == req.brand_id))
        brand = result.scalar_one_or_none()
        if not brand:
            raise HTTPException(status_code=404, detail=f"Brand {req.brand_id} not found")
        brand_voice = brand.brand_voice
        target_audience = target_audience or brand.target_audience
        resolved_available_minutes = (
            resolved_available_minutes if resolved_available_minutes is not None
            else brand.available_minutes_per_day
        )

    service = get_script_generation_service()
    try:
        return await service.generate_script(
            topic=req.topic,
            angle=req.angle,
            content_format=req.format,
            platform=req.platform,
            hook=req.hook,
            reasoning=req.reasoning,
            brand_voice=brand_voice,
            target_audience=target_audience,
            available_minutes=resolved_available_minutes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ScriptGenerationUnavailable as e:
        raise HTTPException(status_code=503, detail=f"script generation unavailable: {e}")
