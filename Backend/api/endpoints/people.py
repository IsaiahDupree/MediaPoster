"""
People API endpoints
Manage people, identities, events, and insights
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Person, Identity, PersonEvent, PersonInsight
from services.people_ingestion import PeopleIngestionService
from services.person_lens import PersonLensComputer
from middleware.workspace_context import get_current_workspace_id

router = APIRouter()


# Pydantic models for API
class PersonResponse(BaseModel):
    id: UUID
    full_name: Optional[str]
    primary_email: Optional[str]
    company: Optional[str]
    role: Optional[str]
    
    class Config:
        from_attributes = True


class PersonInsightResponse(BaseModel):
    person_id: UUID
    interests: List[str]
    tone_preferences: dict
    channel_preferences: dict
    activity_state: str
    warmth_score: float
    last_active_at: Optional[str]
    
    class Config:
        from_attributes = True


class IngestCommentRequest(BaseModel):
    channel: str
    handle: str
    platform_post_id: str
    comment_text: str
    comment_id: str
    traffic_type: str = 'organic'
    user_data: dict = {}


@router.get("/")
async def list_people(
    limit: int = 100,
    offset: int = 0,
):
    """List all people - returns from social accounts and commenters"""
    from sqlalchemy import create_engine, text
    import os
    
    engine = create_engine(os.getenv("DATABASE_URL"))
    people = []
    
    try:
        with engine.connect() as conn:
            # Get people from social_media_accounts (your connected accounts)
            accounts_query = text("""
                SELECT 
                    id::text,
                    COALESCE(display_name, username) as name,
                    username as handle,
                    platform,
                    profile_pic_url as avatar_url,
                    followers_count,
                    engagement_rate as engagement_score,
                    'account' as relationship,
                    last_fetched_at as last_interaction
                FROM social_media_accounts
                WHERE is_active = TRUE
                ORDER BY followers_count DESC
                LIMIT :limit OFFSET :offset
            """)
            
            result = conn.execute(accounts_query, {"limit": limit, "offset": offset})
            for row in result:
                people.append({
                    "id": row[0],
                    "name": row[1] or row[2],
                    "handle": f"@{row[2]}",
                    "platform": row[3],
                    "avatar_url": row[4],
                    "followers_count": row[5] or 0,
                    "engagement_score": float(row[6] or 0),
                    "relationship": row[7],
                    "last_interaction": str(row[8]) if row[8] else None
                })
            
            # Also get people from the people table if any exist
            people_query = text("""
                SELECT 
                    id::text,
                    full_name as name,
                    primary_email as handle,
                    'email' as platform,
                    NULL as avatar_url,
                    0 as followers_count,
                    0 as engagement_score,
                    'contact' as relationship,
                    updated_at as last_interaction
                FROM people
                ORDER BY updated_at DESC
                LIMIT :limit
            """)
            
            try:
                result = conn.execute(people_query, {"limit": limit})
                for row in result:
                    if row[1]:  # Only add if has a name
                        people.append({
                            "id": row[0],
                            "name": row[1],
                            "handle": row[2] or "",
                            "platform": row[3],
                            "avatar_url": row[4],
                            "followers_count": row[5] or 0,
                            "engagement_score": float(row[6] or 0),
                            "relationship": row[7],
                            "last_interaction": str(row[8]) if row[8] else None
                        })
            except:
                pass  # people table might not exist
                
    except Exception as e:
        from loguru import logger
        logger.error(f"Error listing people: {e}")
    
    return {"people": people, "total": len(people)}


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: UUID,
    workspace_id: UUID = Depends(get_current_workspace_id),
    db: AsyncSession = Depends(get_db)
):
    """Get person by ID (must belong to workspace)"""
    result = await db.execute(
        select(Person).where(Person.id == person_id, Person.workspace_id == workspace_id)
    )
    person = result.scalar_one_or_none()
    
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    return person


@router.get("/{person_id}/insights", response_model=PersonInsightResponse)
async def get_person_insights(
    person_id: UUID,
    workspace_id: UUID = Depends(get_current_workspace_id),
    db: AsyncSession = Depends(get_db)
):
    """Get person insights/lens"""
    # Verify person belongs to workspace first
    person_result = await db.execute(
        select(Person).where(Person.id == person_id, Person.workspace_id == workspace_id)
    )
    if not person_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Person not found")
    
    result = await db.execute(
        select(PersonInsight).where(PersonInsight.person_id == person_id)
    )
    insights = result.scalar_one_or_none()
    
    if not insights:
        raise HTTPException(status_code=404, detail="Insights not found")
    
    return insights


@router.post("/{person_id}/recompute-lens")
async def recompute_person_lens(
    person_id: UUID,
    workspace_id: UUID = Depends(get_current_workspace_id),
    db: AsyncSession = Depends(get_db)
):
    """Recompute person lens from events"""
    # Verify person belongs to workspace
    person_result = await db.execute(
        select(Person).where(Person.id == person_id, Person.workspace_id == workspace_id)
    )
    if not person_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Person not found")
    
    computer = PersonLensComputer(db)
    insights = await computer.compute_lens_for_person(person_id)
    
    if not insights:
        raise HTTPException(status_code=404, detail="Person has no events")
    
    return {"status": "success", "person_id": str(person_id)}


@router.post("/ingest/comment")
async def ingest_comment(
    request: IngestCommentRequest,
    workspace_id: UUID = Depends(get_current_workspace_id),
    db: AsyncSession = Depends(get_db)
):
    """Ingest a comment event"""
    service = PeopleIngestionService(db)
    
    # Note: ingestion service should create/link person to workspace_id
    event = await service.ingest_comment(
        channel=request.channel,
        handle=request.handle,
        platform_post_id=request.platform_post_id,
        comment_text=request.comment_text,
        comment_id=request.comment_id,
        traffic_type=request.traffic_type,
        workspace_id=workspace_id,  # Pass workspace_id to service
        **request.user_data
    )
    
    return {
        "status": "success",
        "event_id": str(event.id),
        "person_id": str(event.person_id)
    }


@router.post("/rebuild-all-lenses")
async def rebuild_all_lenses(
    workspace_id: UUID = Depends(get_current_workspace_id),
    db: AsyncSession = Depends(get_db)
):
    """Rebuild lens for all active people in workspace (background job trigger)"""
    computer = PersonLensComputer(db)
    count = await computer.recompute_all_active_people(workspace_id=workspace_id)
    
    return {
        "status": "success",
        "people_updated": count
    }
