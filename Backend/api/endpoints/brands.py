"""
Brands API Endpoints (ENTITY-001)
==================================
CRUD API for Brand entities - company/product brands
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
import logging

from database.connection import get_db
from database.models import Brand
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/brands", tags=["Brands"])


# =====================================================
# Pydantic Models
# =====================================================

class BrandVoice(BaseModel):
    """Brand voice configuration"""
    tone: str
    keywords: List[str] = []
    avoid: List[str] = []


class BrandCreate(BaseModel):
    """Create brand request"""
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    brand_voice: Optional[dict] = None  # {tone, keywords, avoid}
    core_values: Optional[List[str]] = None
    target_audience: Optional[str] = None


class BrandUpdate(BaseModel):
    """Update brand request"""
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    brand_voice: Optional[dict] = None
    core_values: Optional[List[str]] = None
    target_audience: Optional[str] = None
    is_active: Optional[bool] = None


class BrandResponse(BaseModel):
    """Brand response"""
    id: UUID
    name: str
    description: Optional[str]
    logo_url: Optional[str]
    website_url: Optional[str]
    brand_voice: Optional[dict]
    core_values: Optional[List[str]]
    target_audience: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# API Endpoints
# =====================================================

@router.post("/", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    brand: BrandCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new brand"""
    try:
        # Create brand entity
        new_brand = Brand(
            name=brand.name,
            description=brand.description,
            logo_url=brand.logo_url,
            website_url=brand.website_url,
            brand_voice=brand.brand_voice,
            core_values=brand.core_values,
            target_audience=brand.target_audience,
            is_active=True
        )

        db.add(new_brand)
        await db.commit()
        await db.refresh(new_brand)

        # Emit BRAND_CREATED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.BRAND_CREATED, {
                "brand_id": str(new_brand.id),
                "brand_name": brand.name,
                "created_at": new_brand.created_at.isoformat()
            })
            logger.info(f"[PubSub] Emitted BRAND_CREATED for {new_brand.id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit BRAND_CREATED: {e}")

        logger.info(f"✓ Created brand: {brand.name} (ID: {new_brand.id})")
        return new_brand

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating brand: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create brand: {str(e)}"
        )


@router.get("/", response_model=List[BrandResponse])
async def get_brands(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all brands (optionally filter by is_active)"""
    try:
        query = select(Brand)

        if is_active is not None:
            query = query.where(Brand.is_active == is_active)

        query = query.order_by(Brand.created_at.desc())

        result = await db.execute(query)
        brands = result.scalars().all()

        logger.info(f"Retrieved {len(brands)} brands")
        return brands

    except Exception as e:
        logger.error(f"Error retrieving brands: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve brands: {str(e)}"
        )


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a single brand by ID"""
    try:
        result = await db.execute(select(Brand).where(Brand.id == brand_id))
        brand = result.scalar_one_or_none()

        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand with ID {brand_id} not found"
            )

        return brand

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving brand {brand_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve brand: {str(e)}"
        )


@router.patch("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: UUID,
    brand_update: BrandUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a brand"""
    try:
        # Get existing brand
        result = await db.execute(select(Brand).where(Brand.id == brand_id))
        brand = result.scalar_one_or_none()

        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand with ID {brand_id} not found"
            )

        # Update fields
        update_data = brand_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(brand, field, value)

        await db.commit()
        await db.refresh(brand)

        # Emit BRAND_UPDATED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.BRAND_UPDATED, {
                "brand_id": str(brand_id),
                "updated_fields": list(update_data.keys()),
                "updated_at": brand.updated_at.isoformat()
            })
            logger.info(f"[PubSub] Emitted BRAND_UPDATED for {brand_id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit BRAND_UPDATED: {e}")

        logger.info(f"✓ Updated brand: {brand.name} (ID: {brand_id})")
        return brand

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating brand {brand_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update brand: {str(e)}"
        )


@router.delete("/{brand_id}")
async def delete_brand(
    brand_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a brand (CASCADE deletes all offers and templates)"""
    try:
        result = await db.execute(select(Brand).where(Brand.id == brand_id))
        brand = result.scalar_one_or_none()

        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand with ID {brand_id} not found"
            )

        brand_name = brand.name

        await db.delete(brand)
        await db.commit()

        # Emit BRAND_DELETED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.BRAND_DELETED, {
                "brand_id": str(brand_id),
                "brand_name": brand_name,
                "deleted_at": datetime.utcnow().isoformat()
            })
            logger.info(f"[PubSub] Emitted BRAND_DELETED for {brand_id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit BRAND_DELETED: {e}")

        logger.info(f"✓ Deleted brand: {brand_name} (ID: {brand_id})")
        return {"message": f"Brand '{brand_name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting brand {brand_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete brand: {str(e)}"
        )
