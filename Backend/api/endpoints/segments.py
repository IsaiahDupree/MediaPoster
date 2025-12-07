from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database.connection import get_db
from middleware.workspace_context import get_current_workspace_id
from services.segment_engine import (
    SegmentCreate, 
    SegmentResponse, 
    SegmentInsightResponse,
    compute_segment_insights
)

router = APIRouter()

@router.post("/", response_model=SegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_segment(
    segment: SegmentCreate, 
    workspace_id: UUID = Depends(get_current_workspace_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new audience segment"""
    try:
        # Insert segment
        query = text("""
            INSERT INTO segments (id, workspace_id, name, description, definition, is_dynamic, created_at)
            VALUES (:id, :workspace_id, :name, :description, :definition, :is_dynamic, NOW())
            RETURNING id, created_at
        """)
        
        segment_id = uuid4()
        params = {
            "id": segment_id,
            "workspace_id": workspace_id,
            "name": segment.name,
            "description": segment.description,
            "definition": segment.definition.model_dump_json(),
            "is_dynamic": False # Default for now
        }
        
        result = await db.execute(query, params)
        row = result.fetchone()
        await db.commit()
        
        return SegmentResponse(
            id=row.id,
            created_at=row.created_at,
            updated_at=row.created_at,
            member_count=0,
            **segment.model_dump()
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create segment: {str(e)}")

@router.get("/", response_model=List[SegmentResponse])
async def list_segments(
    workspace_id: UUID = Depends(get_current_workspace_id),
    db: AsyncSession = Depends(get_db)
):
    """List all segments in the current workspace"""
    try:
        query = text("""
            SELECT 
                s.id, 
                s.name, 
                s.description, 
                s.definition, 
                s.created_at,
                COUNT(sm.person_id) as member_count
            FROM segments s
            LEFT JOIN segment_members sm ON s.id = sm.segment_id
            WHERE s.workspace_id = :workspace_id
            GROUP BY s.id
            ORDER BY s.created_at DESC
        """)
        
        result = await db.execute(query, {"workspace_id": workspace_id})
        rows = list(result.fetchall())  # Convert to list immediately
        
        return [
            SegmentResponse(
                id=row.id,
                name=row.name,
                description=row.description,
                definition=row.definition if row.definition else {"operator": "AND", "conditions": []},
                created_at=row.created_at,
                updated_at=row.created_at, # Using created_at as updated_at for now
                member_count=row.member_count
            )
            for row in rows
        ]
    except Exception as e:
        from loguru import logger
        logger.error(f"Error listing segments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list segments: {str(e)}")

@router.get("/{segment_id}", response_model=SegmentResponse)
async def get_segment(
    segment_id: UUID, 
    workspace_id: UUID = Depends(get_current_workspace_id),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific segment (must belong to workspace)"""
    try:
        query = text("""
            SELECT 
                s.id, 
                s.name, 
                s.description, 
                s.definition, 
                s.created_at,
                COUNT(sm.person_id) as member_count
            FROM segments s
            LEFT JOIN segment_members sm ON s.id = sm.segment_id
            WHERE s.id = :segment_id AND s.workspace_id = :workspace_id
            GROUP BY s.id
        """)
        
        result = await db.execute(query, {"segment_id": segment_id, "workspace_id": workspace_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Segment not found")
            
        return SegmentResponse(
            id=row.id,
            name=row.name,
            description=row.description,
            definition=row.definition if row.definition else {"operator": "AND", "conditions": []},
            created_at=row.created_at,
            updated_at=row.created_at,
            member_count=row.member_count
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get segment: {str(e)}")

@router.get("/{segment_id}/insights", response_model=List[SegmentInsightResponse])
async def get_segment_insights(
    segment_id: UUID, 
    workspace_id: UUID = Depends(get_current_workspace_id),
    db: AsyncSession = Depends(get_db)
):
    """Get organic and paid insights for this segment"""
    try:
        # Verify segment belongs to workspace first
        verify_query = text("SELECT 1 FROM segments WHERE id = :segment_id AND workspace_id = :workspace_id")
        verify_result = await db.execute(verify_query, {"segment_id": segment_id, "workspace_id": workspace_id})
        if not verify_result.scalar():
            raise HTTPException(status_code=404, detail="Segment not found")

        # Try to fetch from DB first
        query = text("""
            SELECT * FROM segment_insights 
            WHERE segment_id = :segment_id
        """)
        
        result = await db.execute(query, {"segment_id": segment_id})
        rows = list(result.fetchall())  # Convert to list immediately
        
        if rows:
            return [
                SegmentInsightResponse(
                    segment_id=row.segment_id,
                    traffic_type=row.traffic_type,
                    top_topics=row.top_topics or [],
                    top_platforms=row.top_platforms or {},
                    best_times=row.best_times or {},
                    updated_at=row.updated_at
                )
                for row in rows
            ]
            
        # Fallback to compute/mock if no insights found
        organic = await compute_segment_insights(segment_id, "organic")
        paid = await compute_segment_insights(segment_id, "paid")
        return [organic, paid]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get segment insights: {str(e)}")
