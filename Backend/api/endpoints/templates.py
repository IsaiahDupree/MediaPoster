"""
Content Templates API
====================
CRUD API for content generation templates with FATE weights and awareness levels.

Endpoints:
- GET /api/templates - List templates with filtering
- GET /api/templates/{id} - Get specific template
- POST /api/templates - Create new template
- PUT /api/templates/{id} - Update template
- DELETE /api/templates/{id} - Delete template
- POST /api/templates/{id}/fork - Fork a winning template
- POST /api/templates/render - Render template with variables

TPL-007: Template CRUD API
TPL-008: Template Forking
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from loguru import logger

from database.connection import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from database.models import ContentTemplate, Brand
from services.template_validator import TemplateValidator, AwarenessLevel, CTAStrength


router = APIRouter(prefix="/api/templates", tags=["Templates"])


class FATEWeights(BaseModel):
    """FATE weights model"""
    F: float = Field(..., ge=0.0, le=1.0, description="Focus weight (0-1)")
    A: float = Field(..., ge=0.0, le=1.0, description="Authority weight (0-1)")
    T: float = Field(..., ge=0.0, le=1.0, description="Tribe weight (0-1)")
    E: float = Field(..., ge=0.0, le=1.0, description="Emotion weight (0-1)")

    @validator('E')
    def weights_sum_to_one(cls, v, values):
        """Validate FATE weights sum to ~1.0"""
        total = values.get('F', 0) + values.get('A', 0) + values.get('T', 0) + v
        if abs(total - 1.0) > 0.02:
            raise ValueError(f"FATE weights must sum to 1.0 (got {total})")
        return v


class CreateTemplateRequest(BaseModel):
    """Request to create a new template"""
    brand_id: Optional[UUID] = Field(None, description="Brand ID (optional)")
    name: str = Field(..., min_length=1, max_length=200, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    template_type: str = Field(default="post", description="Template type (post, email, dm, ad, story)")

    prompt_text: str = Field(..., min_length=1, description="AI prompt with {variable} placeholders")

    fate_weights: FATEWeights = Field(..., description="FATE weights (must sum to 1.0)")
    awareness_level: str = Field(..., description="Awareness level (unaware, problem_aware, solution_aware, product_aware, most_aware)")
    cta_strength: str = Field(default="soft", description="CTA strength (none, soft, direct)")
    cta_template: Optional[str] = Field(None, description="Optional CTA template")

    is_active: bool = Field(default=True, description="Whether template is active")


class UpdateTemplateRequest(BaseModel):
    """Request to update a template"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    template_type: Optional[str] = None
    prompt_text: Optional[str] = None
    fate_weights: Optional[FATEWeights] = None
    awareness_level: Optional[str] = None
    cta_strength: Optional[str] = None
    cta_template: Optional[str] = None
    is_active: Optional[bool] = None


class ForkTemplateRequest(BaseModel):
    """Request to fork a template"""
    new_name: str = Field(..., min_length=1, max_length=200, description="Name for forked template")
    modifications: Optional[str] = Field(None, description="Description of modifications made")


class RenderTemplateRequest(BaseModel):
    """Request to render a template with variables"""
    template_id: UUID = Field(..., description="Template ID to render")
    variables: Dict[str, Any] = Field(..., description="Variable values to substitute")


class TemplateResponse(BaseModel):
    """Template response model"""
    id: UUID
    brand_id: Optional[UUID]
    name: str
    description: Optional[str]
    template_type: str
    prompt_text: str
    required_variables: List[str]
    fate_weights: Dict[str, float]
    awareness_level: str
    cta_strength: str
    cta_template: Optional[str]
    usage_count: int
    avg_reward_score: float
    performance_label: Optional[str]
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/")
async def list_templates(
    brand_id: Optional[UUID] = Query(None, description="Filter by brand ID"),
    awareness_level: Optional[str] = Query(None, description="Filter by awareness level"),
    template_type: Optional[str] = Query(None, description="Filter by template type"),
    performance_label: Optional[str] = Query(None, description="Filter by performance label"),
    is_active: bool = Query(True, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
):
    """
    List content templates with filtering

    Returns list of templates matching filters, ordered by performance.
    """
    try:
        # Build query
        query = select(ContentTemplate)

        filters = [ContentTemplate.is_active == is_active]

        if brand_id:
            filters.append(ContentTemplate.brand_id == brand_id)
        if awareness_level:
            filters.append(ContentTemplate.awareness_level == awareness_level)
        if template_type:
            filters.append(ContentTemplate.template_type == template_type)
        if performance_label:
            filters.append(ContentTemplate.performance_label == performance_label)

        query = query.where(and_(*filters))
        query = query.order_by(ContentTemplate.avg_reward_score.desc())
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        templates = result.scalars().all()

        return {
            "success": True,
            "data": [
                {
                    "id": str(t.id),
                    "brand_id": str(t.brand_id) if t.brand_id else None,
                    "name": t.name,
                    "description": t.description,
                    "template_type": t.template_type,
                    "prompt_text": t.prompt_text,
                    "required_variables": t.required_variables or [],
                    "fate_weights": {
                        "F": t.fate_focus,
                        "A": t.fate_authority,
                        "T": t.fate_tribe,
                        "E": t.fate_emotion
                    },
                    "awareness_level": t.awareness_level,
                    "cta_strength": t.cta_strength,
                    "cta_template": t.cta_template,
                    "usage_count": t.usage_count,
                    "avg_reward_score": t.avg_reward_score,
                    "performance_label": t.performance_label,
                    "is_active": t.is_active,
                    "created_by": t.created_by,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None
                }
                for t in templates
            ],
            "count": len(templates),
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}")
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific template by ID"""
    try:
        query = select(ContentTemplate).where(ContentTemplate.id == template_id)
        result = await db.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

        return {
            "success": True,
            "data": {
                "id": str(template.id),
                "brand_id": str(template.brand_id) if template.brand_id else None,
                "name": template.name,
                "description": template.description,
                "template_type": template.template_type,
                "prompt_text": template.prompt_text,
                "required_variables": template.required_variables or [],
                "fate_weights": {
                    "F": template.fate_focus,
                    "A": template.fate_authority,
                    "T": template.fate_tribe,
                    "E": template.fate_emotion
                },
                "awareness_level": template.awareness_level,
                "cta_strength": template.cta_strength,
                "cta_template": template.cta_template,
                "usage_count": template.usage_count,
                "avg_reward_score": template.avg_reward_score,
                "performance_label": template.performance_label,
                "is_active": template.is_active,
                "created_by": template.created_by,
                "created_at": template.created_at.isoformat() if template.created_at else None,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_template(
    request: CreateTemplateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new content template

    Validates template structure and FATE weights before creation.
    """
    try:
        # Validate template
        validator = TemplateValidator.get_instance()

        template_dict = {
            "prompt_text": request.prompt_text,
            "fate_weights": {
                "F": request.fate_weights.F,
                "A": request.fate_weights.A,
                "T": request.fate_weights.T,
                "E": request.fate_weights.E
            },
            "awareness_level": request.awareness_level,
            "cta_strength": request.cta_strength
        }

        validation_result = validator.validate_template(template_dict)

        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Template validation failed",
                    "errors": validation_result["errors"],
                    "warnings": validation_result["warnings"]
                }
            )

        # Extract required variables
        required_vars = list(validator.extract_variables(request.prompt_text))

        # Create template
        new_template = ContentTemplate(
            brand_id=request.brand_id,
            name=request.name,
            description=request.description,
            template_type=request.template_type,
            prompt_text=request.prompt_text,
            required_variables=required_vars,
            fate_focus=request.fate_weights.F,
            fate_authority=request.fate_weights.A,
            fate_tribe=request.fate_weights.T,
            fate_emotion=request.fate_weights.E,
            awareness_level=request.awareness_level,
            cta_strength=request.cta_strength,
            cta_template=request.cta_template,
            is_active=request.is_active,
            created_by="api"
        )

        db.add(new_template)
        await db.commit()
        await db.refresh(new_template)

        logger.info(f"Created template: {new_template.name} (ID: {new_template.id})")

        return {
            "success": True,
            "message": "Template created successfully",
            "data": {
                "id": str(new_template.id),
                "name": new_template.name,
                "awareness_level": new_template.awareness_level,
                "required_variables": new_template.required_variables
            },
            "warnings": validation_result.get("warnings", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}")
async def update_template(
    template_id: UUID,
    request: UpdateTemplateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing template"""
    try:
        # Get existing template
        query = select(ContentTemplate).where(ContentTemplate.id == template_id)
        result = await db.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

        # Update fields
        update_data = {}

        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.template_type is not None:
            update_data["template_type"] = request.template_type
        if request.prompt_text is not None:
            update_data["prompt_text"] = request.prompt_text
            # Re-extract variables
            validator = TemplateValidator.get_instance()
            update_data["required_variables"] = list(validator.extract_variables(request.prompt_text))
        if request.fate_weights is not None:
            update_data["fate_focus"] = request.fate_weights.F
            update_data["fate_authority"] = request.fate_weights.A
            update_data["fate_tribe"] = request.fate_weights.T
            update_data["fate_emotion"] = request.fate_weights.E
        if request.awareness_level is not None:
            update_data["awareness_level"] = request.awareness_level
        if request.cta_strength is not None:
            update_data["cta_strength"] = request.cta_strength
        if request.cta_template is not None:
            update_data["cta_template"] = request.cta_template
        if request.is_active is not None:
            update_data["is_active"] = request.is_active

        if update_data:
            stmt = (
                update(ContentTemplate)
                .where(ContentTemplate.id == template_id)
                .values(**update_data)
            )
            await db.execute(stmt)
            await db.commit()

            # Refresh
            await db.refresh(template)

            logger.info(f"Updated template: {template.name} (ID: {template_id})")

        return {
            "success": True,
            "message": "Template updated successfully",
            "data": {
                "id": str(template.id),
                "name": template.name,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}")
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a template"""
    try:
        # Check template exists
        query = select(ContentTemplate).where(ContentTemplate.id == template_id)
        result = await db.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

        # Soft delete (set is_active = False) instead of hard delete
        stmt = (
            update(ContentTemplate)
            .where(ContentTemplate.id == template_id)
            .values(is_active=False)
        )
        await db.execute(stmt)
        await db.commit()

        logger.info(f"Deleted template: {template.name} (ID: {template_id})")

        return {
            "success": True,
            "message": "Template deleted successfully",
            "data": {
                "id": str(template_id)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/fork")
async def fork_template(
    template_id: UUID,
    request: ForkTemplateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Fork a winning template (TPL-008)

    Creates a copy of the template with a new name, preserving the original.
    Use this to create variations of high-performing templates.
    """
    try:
        # Get original template
        query = select(ContentTemplate).where(ContentTemplate.id == template_id)
        result = await db.execute(query)
        original = result.scalar_one_or_none()

        if not original:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

        # Create forked template
        forked = ContentTemplate(
            brand_id=original.brand_id,
            name=request.new_name,
            description=f"Forked from '{original.name}'. {request.modifications or ''}",
            template_type=original.template_type,
            prompt_text=original.prompt_text,
            required_variables=original.required_variables,
            fate_focus=original.fate_focus,
            fate_authority=original.fate_authority,
            fate_tribe=original.fate_tribe,
            fate_emotion=original.fate_emotion,
            awareness_level=original.awareness_level,
            cta_strength=original.cta_strength,
            cta_template=original.cta_template,
            is_active=True,
            created_by=f"fork_of_{template_id}"
        )

        db.add(forked)
        await db.commit()
        await db.refresh(forked)

        logger.info(f"Forked template: {original.name} → {forked.name} (ID: {forked.id})")

        return {
            "success": True,
            "message": "Template forked successfully",
            "data": {
                "original_id": str(template_id),
                "forked_id": str(forked.id),
                "forked_name": forked.name
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error forking template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/render")
async def render_template(
    request: RenderTemplateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Render a template with variable substitution (TPL-006)

    Substitutes {variable} placeholders with provided values.
    """
    try:
        # Get template
        query = select(ContentTemplate).where(ContentTemplate.id == request.template_id)
        result = await db.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail=f"Template {request.template_id} not found")

        # Check for missing variables
        validator = TemplateValidator.get_instance()
        missing_vars = validator.get_missing_variables(template.prompt_text, request.variables)

        if missing_vars:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Missing required variables",
                    "missing_variables": missing_vars,
                    "required_variables": template.required_variables
                }
            )

        # Render template
        rendered_text = template.prompt_text
        for var_name, var_value in request.variables.items():
            placeholder = f"{{{var_name}}}"
            rendered_text = rendered_text.replace(placeholder, str(var_value))

        return {
            "success": True,
            "data": {
                "template_id": str(template.id),
                "template_name": template.name,
                "original_text": template.prompt_text,
                "rendered_text": rendered_text,
                "variables_used": request.variables,
                "fate_weights": {
                    "F": template.fate_focus,
                    "A": template.fate_authority,
                    "T": template.fate_tribe,
                    "E": template.fate_emotion
                },
                "awareness_level": template.awareness_level,
                "cta_strength": template.cta_strength
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/overview")
async def get_template_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get overview statistics about templates"""
    try:
        from sqlalchemy import func

        # Count templates by awareness level
        query = select(
            ContentTemplate.awareness_level,
            func.count(ContentTemplate.id).label('count')
        ).where(ContentTemplate.is_active == True).group_by(ContentTemplate.awareness_level)

        result = await db.execute(query)
        awareness_counts = {row[0]: row[1] for row in result}

        # Count by performance label
        query = select(
            ContentTemplate.performance_label,
            func.count(ContentTemplate.id).label('count')
        ).where(ContentTemplate.is_active == True).group_by(ContentTemplate.performance_label)

        result = await db.execute(query)
        performance_counts = {row[0]: row[1] for row in result}

        # Total templates
        query = select(func.count(ContentTemplate.id)).where(ContentTemplate.is_active == True)
        result = await db.execute(query)
        total_templates = result.scalar()

        return {
            "success": True,
            "data": {
                "total_templates": total_templates,
                "by_awareness_level": awareness_counts,
                "by_performance": performance_counts
            }
        }

    except Exception as e:
        logger.error(f"Error getting template stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
