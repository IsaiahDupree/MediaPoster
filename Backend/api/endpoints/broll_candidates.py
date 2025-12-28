"""
B-Roll Candidates API Endpoints
================================
Find, rank, and manage B-roll candidates for video formats.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from loguru import logger
from datetime import datetime

from database.connection import get_db
from services.broll_candidate_service import (
    BrollCandidateService,
    BrollSlotQuery,
    BeatRole,
    get_broll_service,
)

router = APIRouter(prefix="/api/broll", tags=["B-Roll Candidates"])


class BrollSlotQueryRequest(BaseModel):
    """Request to search for B-roll candidates for a slot"""
    slot_id: str
    beat_id: str
    beat_role: str = "other"
    required_concepts: List[str]
    optional_concepts: List[str] = []
    negative_terms: List[str] = []
    people: str = "allowed"  # required, allowed, forbidden
    camera_motion: List[str] = []
    visual_style: str = "any"
    min_duration_sec: float = 2.0
    max_duration_sec: float = 10.0


class GenerateCandidatesRequest(BaseModel):
    """Request to generate B-roll candidates for a format"""
    format_id: str
    slots: List[BrollSlotQueryRequest]
    limit_per_slot: int = 20


class BeatQueryRequest(BaseModel):
    """Request to generate B-roll queries from a beat"""
    beat_role: str
    topic: str
    context: Dict[str, Any] = {}


@router.get("/candidates")
async def list_all_candidates(
    format_id: str = Query(..., description="Format ID to find candidates for"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    beat_filter: Optional[str] = Query(None, description="Filter by beat role"),
    min_score: float = Query(0.0, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all B-roll candidates from user library for a format.
    
    Returns paginated list of candidates with scores and metadata.
    """
    logger.info(f"📥 [API] GET /api/broll/candidates - format={format_id}")
    
    service = get_broll_service(db)
    
    result = await service.find_all_broll_candidates(
        format_id=format_id,
        limit=limit,
        offset=offset,
        beat_filter=beat_filter,
        min_score=min_score,
    )
    
    logger.info(f"✅ [API] Found {len(result['candidates'])} candidates")
    
    return result


@router.post("/generate")
async def generate_candidates(
    request: GenerateCandidatesRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate B-roll candidates for all slots in a format.
    
    This searches the user library and ranks candidates by:
    - Relevance to slot concepts
    - Format constraints (people, camera motion, style)
    - Novelty and brand fit
    """
    logger.info(f"📥 [API] POST /api/broll/generate - format={request.format_id}")
    logger.info(f"   Slots: {len(request.slots)}")
    
    service = get_broll_service(db)
    
    # Convert requests to slot queries
    slots = []
    for slot_req in request.slots:
        try:
            beat_role = BeatRole(slot_req.beat_role)
        except ValueError:
            beat_role = BeatRole.OTHER
        
        slots.append(BrollSlotQuery(
            slot_id=slot_req.slot_id,
            beat_id=slot_req.beat_id,
            beat_role=beat_role,
            required_concepts=slot_req.required_concepts,
            optional_concepts=slot_req.optional_concepts,
            negative_terms=slot_req.negative_terms,
            people=slot_req.people,
            camera_motion=slot_req.camera_motion,
            visual_style=slot_req.visual_style,
            min_duration_sec=slot_req.min_duration_sec,
            max_duration_sec=slot_req.max_duration_sec,
        ))
    
    result = await service.find_candidates_for_format(
        format_id=request.format_id,
        slots=slots,
        limit_per_slot=request.limit_per_slot,
    )
    
    # Convert to response format
    response = {
        "format_id": request.format_id,
        "slots": {},
        "total_candidates": 0,
    }
    
    for slot_id, candidates in result.items():
        response["slots"][slot_id] = {
            "candidates": [c.to_dict() for c in candidates],
            "count": len(candidates),
        }
        response["total_candidates"] += len(candidates)
    
    logger.success(f"✅ [API] Generated {response['total_candidates']} candidates")
    
    return response


@router.post("/beat-queries")
async def generate_beat_queries(
    request: BeatQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate B-roll search queries for a specific beat.
    
    This connects to the Narrative Builder to create story-driven
    B-roll requirements based on the beat role and topic.
    """
    logger.info(f"📥 [API] POST /api/broll/beat-queries")
    logger.info(f"   Beat: {request.beat_role}, Topic: {request.topic}")
    
    service = get_broll_service(db)
    
    try:
        beat_role = BeatRole(request.beat_role)
    except ValueError:
        beat_role = BeatRole.OTHER
    
    query = await service.generate_beat_queries(
        beat_role=beat_role,
        topic=request.topic,
        context=request.context,
    )
    
    return {
        "slot_id": query.slot_id,
        "beat_id": query.beat_id,
        "beat_role": query.beat_role.value,
        "required_concepts": query.required_concepts,
        "optional_concepts": query.optional_concepts,
        "negative_terms": query.negative_terms,
        "query_strings": query.query_strings,
        "constraints": {
            "people": query.people,
            "camera_motion": query.camera_motion,
            "visual_style": query.visual_style,
            "min_duration_sec": query.min_duration_sec,
            "max_duration_sec": query.max_duration_sec,
        },
    }


@router.get("/formats/{format_id}/candidates")
async def get_format_candidates(
    format_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all B-roll candidates for a specific format.
    Includes candidates grouped by beat/slot.
    """
    logger.info(f"📥 [API] GET /api/broll/formats/{format_id}/candidates")
    
    service = get_broll_service(db)
    
    # Get format details
    from sqlalchemy import select, text
    format_query = text("""
        SELECT id, name, definition_json 
        FROM content_formats 
        WHERE id = :format_id
    """)
    result = await db.execute(format_query, {"format_id": format_id})
    format_row = result.fetchone()
    
    if not format_row:
        raise HTTPException(status_code=404, detail=f"Format {format_id} not found")
    
    # Get all candidates
    candidates_result = await service.find_all_broll_candidates(
        format_id=format_id,
        limit=limit,
        offset=offset,
    )
    
    # Extract beats from format definition if available
    beats = []
    if format_row.definition_json:
        defn = format_row.definition_json
        if isinstance(defn, dict):
            # Check for broll slots in definition
            data_sources = defn.get("dataSources", [])
            for ds in data_sources:
                if ds.get("type") == "local_library" and "broll" in ds.get("id", "").lower():
                    beats.append({
                        "id": ds.get("id"),
                        "label": ds.get("id", "").replace("_", " ").title(),
                        "filter": ds.get("filter", {}),
                    })
    
    return {
        "format_id": format_id,
        "format_name": format_row.name,
        "beats": beats,
        "candidates": candidates_result["candidates"],
        "total": candidates_result["total"],
        "offset": offset,
        "limit": limit,
    }


@router.post("/lock-selection")
async def lock_broll_selection(
    format_id: str,
    slot_id: str,
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Lock a B-roll candidate selection for a slot.
    This saves the selection for use in the render pipeline.
    """
    logger.info(f"📥 [API] POST /api/broll/lock-selection")
    logger.info(f"   Format: {format_id}, Slot: {slot_id}, Candidate: {candidate_id}")
    
    # Store selection in database (for now, in-memory)
    # TODO: Create proper selection storage
    
    return {
        "status": "locked",
        "format_id": format_id,
        "slot_id": slot_id,
        "candidate_id": candidate_id,
        "locked_at": datetime.now().isoformat(),
    }
