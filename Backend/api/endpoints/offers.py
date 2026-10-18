"""
Offers API Endpoints (ENTITY-002)
==================================
CRUD API for Offer entities - products/services/CTAs linked to brands
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import logging

from database.connection import get_db
from database.models import Offer, Brand
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/offers", tags=["Offers"])


# =====================================================
# Pydantic Models
# =====================================================

class OfferCreate(BaseModel):
    """Create offer request"""
    brand_id: UUID
    title: str
    description: Optional[str] = None
    offer_type: Optional[str] = None  # product, service, lead_magnet, content, event
    landing_page_url: Optional[str] = None
    cta_text: Optional[str] = None
    terms: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "USD"
    priority: Optional[int] = 0
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class OfferUpdate(BaseModel):
    """Update offer request"""
    title: Optional[str] = None
    description: Optional[str] = None
    offer_type: Optional[str] = None
    landing_page_url: Optional[str] = None
    cta_text: Optional[str] = None
    terms: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class OfferResponse(BaseModel):
    """Offer response"""
    id: UUID
    brand_id: UUID
    title: str
    description: Optional[str]
    offer_type: Optional[str]
    landing_page_url: Optional[str]
    cta_text: Optional[str]
    terms: Optional[str]
    price: Optional[Decimal]
    currency: str
    is_active: bool
    priority: int
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# API Endpoints
# =====================================================

@router.post("/", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(
    offer: OfferCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new offer"""
    try:
        # Verify brand exists
        result = await db.execute(select(Brand).where(Brand.id == offer.brand_id))
        brand = result.scalar_one_or_none()
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand with ID {offer.brand_id} not found"
            )

        # Create offer entity
        new_offer = Offer(
            brand_id=offer.brand_id,
            title=offer.title,
            description=offer.description,
            offer_type=offer.offer_type,
            landing_page_url=offer.landing_page_url,
            cta_text=offer.cta_text,
            terms=offer.terms,
            price=Decimal(str(offer.price)) if offer.price is not None else None,
            currency=offer.currency,
            priority=offer.priority,
            valid_from=offer.valid_from,
            valid_until=offer.valid_until,
            is_active=True
        )

        db.add(new_offer)
        await db.commit()
        await db.refresh(new_offer)

        # Emit OFFER_CREATED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.OFFER_CREATED, {
                "offer_id": str(new_offer.id),
                "brand_id": str(offer.brand_id),
                "title": offer.title,
                "offer_type": offer.offer_type,
                "created_at": new_offer.created_at.isoformat()
            })
            logger.info(f"[PubSub] Emitted OFFER_CREATED for {new_offer.id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit OFFER_CREATED: {e}")

        logger.info(f"✓ Created offer: {offer.title} (ID: {new_offer.id})")
        return new_offer

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating offer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create offer: {str(e)}"
        )


@router.get("/", response_model=List[OfferResponse])
async def get_offers(
    brand_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    offer_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all offers (optionally filter by brand_id, is_active, offer_type)"""
    try:
        query = select(Offer)

        if brand_id:
            query = query.where(Offer.brand_id == brand_id)
        if is_active is not None:
            query = query.where(Offer.is_active == is_active)
        if offer_type:
            query = query.where(Offer.offer_type == offer_type)

        query = query.order_by(Offer.priority.desc(), Offer.created_at.desc())

        result = await db.execute(query)
        offers = result.scalars().all()

        logger.info(f"Retrieved {len(offers)} offers")
        return offers

    except Exception as e:
        logger.error(f"Error retrieving offers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve offers: {str(e)}"
        )


@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(
    offer_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a single offer by ID"""
    try:
        result = await db.execute(select(Offer).where(Offer.id == offer_id))
        offer = result.scalar_one_or_none()

        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with ID {offer_id} not found"
            )

        return offer

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving offer {offer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve offer: {str(e)}"
        )


@router.patch("/{offer_id}", response_model=OfferResponse)
async def update_offer(
    offer_id: UUID,
    offer_update: OfferUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an offer"""
    try:
        # Get existing offer
        result = await db.execute(select(Offer).where(Offer.id == offer_id))
        offer = result.scalar_one_or_none()

        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with ID {offer_id} not found"
            )

        # Update fields
        update_data = offer_update.dict(exclude_unset=True)

        # Convert price to Decimal if present
        if 'price' in update_data and update_data['price'] is not None:
            update_data['price'] = Decimal(str(update_data['price']))

        for field, value in update_data.items():
            setattr(offer, field, value)

        await db.commit()
        await db.refresh(offer)

        # Emit OFFER_UPDATED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.OFFER_UPDATED, {
                "offer_id": str(offer_id),
                "updated_fields": list(update_data.keys()),
                "updated_at": offer.updated_at.isoformat()
            })
            logger.info(f"[PubSub] Emitted OFFER_UPDATED for {offer_id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit OFFER_UPDATED: {e}")

        logger.info(f"✓ Updated offer: {offer.title} (ID: {offer_id})")
        return offer

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating offer {offer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update offer: {str(e)}"
        )


@router.delete("/{offer_id}")
async def delete_offer(
    offer_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete an offer (CASCADE deletes all touchpoints)"""
    try:
        result = await db.execute(select(Offer).where(Offer.id == offer_id))
        offer = result.scalar_one_or_none()

        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with ID {offer_id} not found"
            )

        offer_title = offer.title

        await db.delete(offer)
        await db.commit()

        # Emit OFFER_DELETED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.OFFER_DELETED, {
                "offer_id": str(offer_id),
                "title": offer_title,
                "deleted_at": datetime.utcnow().isoformat()
            })
            logger.info(f"[PubSub] Emitted OFFER_DELETED for {offer_id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit OFFER_DELETED: {e}")

        logger.info(f"✓ Deleted offer: {offer_title} (ID: {offer_id})")
        return {"message": f"Offer '{offer_title}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting offer {offer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete offer: {str(e)}"
        )
