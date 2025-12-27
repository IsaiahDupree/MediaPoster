"""
Content Pipeline API Endpoints
Endpoints for CopyPlan and RemotionRenderSpec generation
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
import uuid
import os
import json

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CopyPlanInputModel(BaseModel):
    hook: str = Field(..., description="Main hook/attention grabber")
    topics: List[str] = Field(..., description="Main topics/themes")
    keywords: List[str] = Field(default=[], description="SEO/search keywords")
    audience: List[str] = Field(default=[], description="Target audience segments")
    cta: Optional[Dict[str, str]] = Field(default=None, description="Call to action {type, text}")
    tone: Optional[str] = Field(default=None, description="Content tone")
    pain_points: List[str] = Field(default=[], description="Pain points addressed")
    emotional_drivers: List[str] = Field(default=[], description="Emotional motivations")
    content_type: Optional[str] = Field(default=None, description="Content classification")


class GenerateCopyPlanRequest(BaseModel):
    asset_id: Optional[str] = None
    video_id: Optional[str] = None
    audit_id: Optional[str] = None
    platforms: List[str] = Field(default=["youtube", "instagram", "tiktok"])
    inputs: Optional[CopyPlanInputModel] = None


class GenerateRemotionSpecRequest(BaseModel):
    asset_id: Optional[str] = None
    video_id: Optional[str] = None
    audit_id: Optional[str] = None
    composition_id: str = Field(default="ShortFormV1")
    fps: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    narration_url: Optional[str] = None
    music_url: Optional[str] = None
    caption_style_id: str = Field(default="CaptionStyleA")


class TextConstraintModel(BaseModel):
    platform: str
    surface: str
    field: str
    max_chars: Optional[int] = None
    soft_cap_chars: Optional[int] = None
    target_margin_pct: float = 0.20
    count_rule: str = "graphemes"
    max_hashtags: Optional[int] = None
    max_mentions: Optional[int] = None


# =============================================================================
# PLATFORM CONSTRAINTS ENDPOINTS
# =============================================================================

@router.get("/constraints")
async def get_platform_constraints(
    platform: Optional[str] = None,
    surface: Optional[str] = None
):
    """
    Get platform text constraints.
    Optionally filter by platform and/or surface.
    """
    engine = get_engine()
    
    query = "SELECT * FROM platform_text_constraints WHERE 1=1"
    params = {}
    
    if platform:
        query += " AND platform = :platform"
        params["platform"] = platform
    if surface:
        query += " AND surface = :surface"
        params["surface"] = surface
    
    query += " ORDER BY platform, surface, field"
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            constraints = []
            for row in result:
                constraints.append({
                    "constraint_id": str(row[0]),
                    "platform": row[1],
                    "surface": row[2],
                    "field": row[3],
                    "max_chars": row[4],
                    "soft_cap_chars": row[5],
                    "target_margin_pct": float(row[6]) if row[6] else 0.20,
                    "max_hashtags": row[7],
                    "max_mentions": row[8],
                    "count_rule": row[9],
                    "source_url": row[11],
                    "source_quality": row[12]
                })
            
            return {
                "success": True,
                "constraints": constraints,
                "count": len(constraints)
            }
    except Exception as e:
        logger.error(f"Failed to get constraints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/constraints/{platform}/{surface}")
async def get_platform_surface_constraints(platform: str, surface: str):
    """Get all constraints for a specific platform/surface combination"""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT field, max_chars, soft_cap_chars, target_margin_pct, 
                       count_rule, max_hashtags, max_mentions
                FROM platform_text_constraints
                WHERE platform = :platform AND surface = :surface
            """), {"platform": platform, "surface": surface})
            
            constraints = {}
            for row in result:
                field = row[0]
                target = int(row[1] * (1 - float(row[3]))) if row[1] and row[3] else row[2]
                constraints[field] = {
                    "max_chars": row[1],
                    "soft_cap_chars": row[2],
                    "target_chars": target,
                    "target_margin_pct": float(row[3]) if row[3] else 0.20,
                    "count_rule": row[4],
                    "max_hashtags": row[5],
                    "max_mentions": row[6]
                }
            
            return {
                "success": True,
                "platform": platform,
                "surface": surface,
                "constraints": constraints
            }
    except Exception as e:
        logger.error(f"Failed to get constraints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COPY PLAN ENDPOINTS
# =============================================================================

@router.post("/copy-plan/generate")
async def generate_copy_plan(request: GenerateCopyPlanRequest):
    """
    Generate platform-optimized copy from video analysis or custom inputs.
    """
    try:
        from services.content_pipeline.copy_plan_service import CopyPlanService, CopyPlanInput
        
        service = CopyPlanService()
        
        # Get inputs from request or from video analysis
        if request.inputs:
            inputs = CopyPlanInput(
                hook=request.inputs.hook,
                topics=request.inputs.topics,
                keywords=request.inputs.keywords,
                audience=request.inputs.audience,
                cta=request.inputs.cta,
                tone=request.inputs.tone,
                pain_points=request.inputs.pain_points,
                emotional_drivers=request.inputs.emotional_drivers,
                content_type=request.inputs.content_type
            )
        elif request.video_id:
            # Load from video analysis
            inputs = await _get_inputs_from_video_analysis(request.video_id)
            if not inputs:
                raise HTTPException(status_code=404, detail="Video analysis not found")
        else:
            raise HTTPException(status_code=400, detail="Must provide inputs or video_id")
        
        # Generate copy plan
        plan = await service.generate_copy_plan(
            inputs=inputs,
            platforms=request.platforms,
            asset_id=request.asset_id,
            audit_id=request.audit_id
        )
        
        # Convert to dict for response
        from dataclasses import asdict
        plan_dict = asdict(plan)
        
        return {
            "success": True,
            "copy_plan": plan_dict,
            "platforms_generated": len(plan.variants)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate copy plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/copy-plan/{copy_plan_id}")
async def get_copy_plan(copy_plan_id: str):
    """Get a saved copy plan by ID"""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT copy_plan_id, asset_id, platform, surface, data,
                       title, caption, description, hashtags, model, created_at
                FROM copy_plan
                WHERE copy_plan_id = :id
            """), {"id": copy_plan_id})
            
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Copy plan not found")
            
            return {
                "success": True,
                "copy_plan": {
                    "copy_plan_id": str(row[0]),
                    "asset_id": str(row[1]) if row[1] else None,
                    "platform": row[2],
                    "surface": row[3],
                    "data": row[4],
                    "title": row[5],
                    "caption": row[6],
                    "description": row[7],
                    "hashtags": row[8],
                    "model": row[9],
                    "created_at": row[10].isoformat() if row[10] else None
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get copy plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/copy-plans/by-asset/{asset_id}")
async def get_copy_plans_by_asset(asset_id: str):
    """Get all copy plans for an asset"""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT copy_plan_id, platform, surface, title, caption, 
                       hashtags, model, created_at
                FROM copy_plan
                WHERE asset_id = :asset_id
                ORDER BY created_at DESC
            """), {"asset_id": asset_id})
            
            plans = []
            for row in result:
                plans.append({
                    "copy_plan_id": str(row[0]),
                    "platform": row[1],
                    "surface": row[2],
                    "title": row[3],
                    "caption": row[4],
                    "hashtags": row[5],
                    "model": row[6],
                    "created_at": row[7].isoformat() if row[7] else None
                })
            
            return {
                "success": True,
                "asset_id": asset_id,
                "copy_plans": plans,
                "count": len(plans)
            }
    except Exception as e:
        logger.error(f"Failed to get copy plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# REMOTION RENDER SPEC ENDPOINTS
# =============================================================================

@router.post("/remotion-spec/generate")
async def generate_remotion_spec(request: GenerateRemotionSpecRequest):
    """
    Generate Remotion render spec from video analysis.
    """
    try:
        from services.content_pipeline.remotion_spec_service import RemotionSpecService
        
        service = RemotionSpecService()
        
        # Build spec from video analysis
        if request.video_id:
            spec = service.build_from_video_analysis(
                video_id=request.video_id,
                composition_id=request.composition_id,
                narration_url=request.narration_url,
                music_url=request.music_url,
                caption_style_id=request.caption_style_id
            )
            
            if not spec:
                raise HTTPException(status_code=404, detail="Video analysis not found")
        else:
            raise HTTPException(status_code=400, detail="video_id is required")
        
        # Save if asset_id provided
        render_spec_id = None
        if request.asset_id:
            render_spec_id = await service.save_render_spec(
                spec=spec,
                asset_id=request.asset_id,
                audit_id=request.audit_id
            )
        
        # Convert to dict for response
        from dataclasses import asdict
        spec_dict = asdict(spec)
        
        return {
            "success": True,
            "render_spec_id": render_spec_id,
            "spec": spec_dict,
            "input_props": service.to_remotion_input_props(spec)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate Remotion spec: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/remotion-spec/compositions")
async def get_composition_presets():
    """Get available Remotion composition presets"""
    from services.content_pipeline.remotion_spec_service import RemotionSpecService
    
    service = RemotionSpecService()
    return {
        "success": True,
        "compositions": service.get_composition_presets(),
        "caption_styles": service.get_caption_styles()
    }


@router.get("/remotion-spec/{render_spec_id}")
async def get_remotion_spec(render_spec_id: str):
    """Get a saved Remotion render spec by ID"""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT render_spec_id, asset_id, composition_id, fps, width, height,
                       duration_in_frames, spec, status, output_url, created_at
                FROM remotion_render_spec
                WHERE render_spec_id = :id
            """), {"id": render_spec_id})
            
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Render spec not found")
            
            return {
                "success": True,
                "render_spec": {
                    "render_spec_id": str(row[0]),
                    "asset_id": str(row[1]) if row[1] else None,
                    "composition_id": row[2],
                    "fps": row[3],
                    "width": row[4],
                    "height": row[5],
                    "duration_in_frames": row[6],
                    "spec": row[7],
                    "status": row[8],
                    "output_url": row[9],
                    "created_at": row[10].isoformat() if row[10] else None
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get render spec: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _get_inputs_from_video_analysis(video_id: str):
    """Extract CopyPlanInput from video analysis"""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    detected_hook, topics, tone, pain_points, emotional_drivers,
                    content_type, call_to_action, target_audience, hooks
                FROM video_analysis
                WHERE video_id = :video_id
            """), {"video_id": video_id})
            
            row = result.fetchone()
            if not row:
                return None
            
            from services.content_pipeline.copy_plan_service import CopyPlanInput
            
            # Build CTA dict
            cta = None
            if row[6]:
                cta_data = row[6] if isinstance(row[6], dict) else {}
                if cta_data.get("text"):
                    cta = {"type": cta_data.get("type", "follow"), "text": cta_data["text"]}
            
            return CopyPlanInput(
                hook=row[0] or (row[8][0] if row[8] else ""),
                topics=row[1] or [],
                keywords=(row[1] or [])[:5],
                audience=[row[7].get("demographic", "")] if row[7] and isinstance(row[7], dict) else [],
                cta=cta,
                tone=row[2],
                pain_points=row[3] or [],
                emotional_drivers=row[4] or [],
                content_type=row[5]
            )
    except Exception as e:
        logger.error(f"Failed to get analysis for video {video_id}: {e}")
        return None
