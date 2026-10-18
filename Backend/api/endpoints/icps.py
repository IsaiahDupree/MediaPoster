"""
ICPs API Endpoints (ENTITY-003)
================================
CRUD API for ICP (Ideal Customer Profile) entities - target audience personas
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
from database.models import ICP
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/icps", tags=["ICPs"])


# =====================================================
# Pydantic Models
# =====================================================

class ICPCreate(BaseModel):
    """Create ICP request"""
    name: str
    description: Optional[str] = None
    age_range: Optional[str] = None  # e.g., "25-34", "35-44"
    location: Optional[List[str]] = None
    job_titles: Optional[List[str]] = None
    company_size: Optional[str] = None  # e.g., "1-10", "11-50"
    pain_points: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    objections: Optional[List[str]] = None
    default_awareness_level: Optional[str] = "problem_aware"  # unaware, problem_aware, solution_aware, product_aware, most_aware


class ICPUpdate(BaseModel):
    """Update ICP request"""
    name: Optional[str] = None
    description: Optional[str] = None
    age_range: Optional[str] = None
    location: Optional[List[str]] = None
    job_titles: Optional[List[str]] = None
    company_size: Optional[str] = None
    pain_points: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    objections: Optional[List[str]] = None
    default_awareness_level: Optional[str] = None
    is_active: Optional[bool] = None


class ICPResponse(BaseModel):
    """ICP response"""
    id: UUID
    name: str
    description: Optional[str]
    age_range: Optional[str]
    location: Optional[List[str]]
    job_titles: Optional[List[str]]
    company_size: Optional[str]
    pain_points: Optional[List[str]]
    goals: Optional[List[str]]
    interests: Optional[List[str]]
    objections: Optional[List[str]]
    default_awareness_level: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# API Endpoints
# =====================================================

@router.post("/", response_model=ICPResponse, status_code=status.HTTP_201_CREATED)
async def create_icp(
    icp: ICPCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new ICP (Ideal Customer Profile)"""
    try:
        # Create ICP entity
        new_icp = ICP(
            name=icp.name,
            description=icp.description,
            age_range=icp.age_range,
            location=icp.location,
            job_titles=icp.job_titles,
            company_size=icp.company_size,
            pain_points=icp.pain_points,
            goals=icp.goals,
            interests=icp.interests,
            objections=icp.objections,
            default_awareness_level=icp.default_awareness_level,
            is_active=True
        )

        db.add(new_icp)
        await db.commit()
        await db.refresh(new_icp)

        # Emit ICP_CREATED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.ICP_CREATED, {
                "icp_id": str(new_icp.id),
                "name": icp.name,
                "awareness_level": icp.default_awareness_level,
                "created_at": new_icp.created_at.isoformat()
            })
            logger.info(f"[PubSub] Emitted ICP_CREATED for {new_icp.id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit ICP_CREATED: {e}")

        logger.info(f"✓ Created ICP: {icp.name} (ID: {new_icp.id})")
        return new_icp

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating ICP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ICP: {str(e)}"
        )


@router.get("/", response_model=List[ICPResponse])
async def get_icps(
    is_active: Optional[bool] = None,
    awareness_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all ICPs (optionally filter by is_active, awareness_level)"""
    try:
        query = select(ICP)

        if is_active is not None:
            query = query.where(ICP.is_active == is_active)
        if awareness_level:
            query = query.where(ICP.default_awareness_level == awareness_level)

        query = query.order_by(ICP.created_at.desc())

        result = await db.execute(query)
        icps = result.scalars().all()

        logger.info(f"Retrieved {len(icps)} ICPs")
        return icps

    except Exception as e:
        logger.error(f"Error retrieving ICPs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ICPs: {str(e)}"
        )


@router.get("/{icp_id}", response_model=ICPResponse)
async def get_icp(
    icp_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a single ICP by ID"""
    try:
        result = await db.execute(select(ICP).where(ICP.id == icp_id))
        icp = result.scalar_one_or_none()

        if not icp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ICP with ID {icp_id} not found"
            )

        return icp

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving ICP {icp_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ICP: {str(e)}"
        )


@router.patch("/{icp_id}", response_model=ICPResponse)
async def update_icp(
    icp_id: UUID,
    icp_update: ICPUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an ICP"""
    try:
        # Get existing ICP
        result = await db.execute(select(ICP).where(ICP.id == icp_id))
        icp = result.scalar_one_or_none()

        if not icp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ICP with ID {icp_id} not found"
            )

        # Update fields
        update_data = icp_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(icp, field, value)

        await db.commit()
        await db.refresh(icp)

        # Emit ICP_UPDATED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.ICP_UPDATED, {
                "icp_id": str(icp_id),
                "updated_fields": list(update_data.keys()),
                "updated_at": icp.updated_at.isoformat()
            })
            logger.info(f"[PubSub] Emitted ICP_UPDATED for {icp_id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit ICP_UPDATED: {e}")

        logger.info(f"✓ Updated ICP: {icp.name} (ID: {icp_id})")
        return icp

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating ICP {icp_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update ICP: {str(e)}"
        )


@router.delete("/{icp_id}")
async def delete_icp(
    icp_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete an ICP (CASCADE deletes all touchpoints)"""
    try:
        result = await db.execute(select(ICP).where(ICP.id == icp_id))
        icp = result.scalar_one_or_none()

        if not icp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ICP with ID {icp_id} not found"
            )

        icp_name = icp.name

        await db.delete(icp)
        await db.commit()

        # Emit ICP_DELETED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.ICP_DELETED, {
                "icp_id": str(icp_id),
                "name": icp_name,
                "deleted_at": datetime.utcnow().isoformat()
            })
            logger.info(f"[PubSub] Emitted ICP_DELETED for {icp_id}")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit ICP_DELETED: {e}")

        logger.info(f"✓ Deleted ICP: {icp_name} (ID: {icp_id})")
        return {"message": f"ICP '{icp_name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting ICP {icp_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete ICP: {str(e)}"
        )
