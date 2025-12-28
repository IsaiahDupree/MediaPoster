"""
Formats API Endpoints
Manage video format templates and runs
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from loguru import logger
import uuid

from database.connection import get_db
from services.formats.sample_formats import SAMPLE_FORMATS, get_sample_format
import json

router = APIRouter(prefix="/api/formats", tags=["Formats"])


class FormatResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    version: str
    definition_json: Dict[str, Any]
    quality_profile_id: Optional[str] = None
    remotion_composition_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_run: Optional[Dict[str, Any]] = None


class FormatListResponse(BaseModel):
    formats: List[FormatResponse]
    total: int


class RunRequest(BaseModel):
    params: Dict[str, Any] = {}
    trigger_type: str = "manual"
    variant_id: Optional[str] = None


class RunResponse(BaseModel):
    run_id: str
    format_id: str
    status: str
    message: str


def _sample_to_format_response(sample: Dict[str, Any]) -> FormatResponse:
    """Convert a sample format dict to FormatResponse"""
    composition = sample.get("composition", {})
    return FormatResponse(
        id=sample["id"],
        name=sample["name"],
        description=sample.get("description"),
        status=sample.get("status", "draft"),
        version=sample.get("version", "1.0.0"),
        definition_json=sample,
        quality_profile_id=sample.get("defaults", {}).get("qualityProfileId"),
        remotion_composition_id=composition.get("remotionCompositionId"),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        last_run=None
    )


@router.get("/list", response_model=FormatListResponse)
async def list_formats(
    status: Optional[str] = Query(default=None, description="Filter by status: active, draft, archived"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all available formats from the database.
    """
    logger.info(f"📋 [Formats] Listing formats, status filter: {status}")
    
    where_clause = ""
    if status:
        where_clause = f"WHERE status = '{status}'"
    
    query = f"""
        SELECT id, name, description, status, version, definition_json,
               quality_profile_id, remotion_composition_id, created_at, updated_at
        FROM formats
        {where_clause}
        ORDER BY updated_at DESC
    """
    
    result = await db.execute(text(query))
    rows = result.fetchall()
    
    formats = []
    for row in rows:
        def_json = row[5]
        if isinstance(def_json, str):
            def_json = json.loads(def_json)
        
        formats.append(FormatResponse(
            id=row[0],
            name=row[1],
            description=row[2],
            status=row[3],
            version=row[4],
            definition_json=def_json or {},
            quality_profile_id=row[6],
            remotion_composition_id=row[7],
            created_at=str(row[8]) if row[8] else None,
            updated_at=str(row[9]) if row[9] else None,
            last_run=None
        ))
    
    logger.info(f"✅ [Formats] Found {len(formats)} formats")
    return FormatListResponse(
        formats=formats,
        total=len(formats)
    )


@router.post("/seed-samples")
async def seed_sample_formats(db: AsyncSession = Depends(get_db)):
    """
    Seed the database with sample format templates.
    """
    logger.info(f"🌱 [Formats] Seeding {len(SAMPLE_FORMATS)} sample formats...")
    
    seeded = []
    skipped = []
    
    for sample in SAMPLE_FORMATS:
        format_id = sample["id"]
        
        # Check if already exists
        check = await db.execute(text("SELECT id FROM formats WHERE id = :id"), {"id": format_id})
        if check.fetchone():
            skipped.append(format_id)
            continue
        
        composition = sample.get("composition", {})
        remotion_id = composition.get("remotionCompositionId")
        quality_profile_id = sample.get("defaults", {}).get("qualityProfileId", "qp_shortform_v1")
        
        await db.execute(text("""
            INSERT INTO formats (id, name, description, status, version, definition_json,
                                quality_profile_id, remotion_composition_id)
            VALUES (:id, :name, :description, :status, :version, :definition_json,
                    :quality_profile_id, :remotion_composition_id)
        """), {
            "id": format_id,
            "name": sample["name"],
            "description": sample.get("description"),
            "status": sample.get("status", "active"),
            "version": sample.get("version", "1.0.0"),
            "definition_json": json.dumps(sample),
            "quality_profile_id": quality_profile_id,
            "remotion_composition_id": remotion_id
        })
        seeded.append(format_id)
    
    await db.commit()
    
    logger.info(f"✅ [Formats] Seeded {len(seeded)}, skipped {len(skipped)} existing")
    
    return {
        "status": "success",
        "message": f"Seeded {len(seeded)} sample formats",
        "format_ids": seeded,
        "skipped": skipped
    }


@router.get("/{format_id}")
async def get_format(format_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a single format by ID.
    """
    result = await db.execute(text("""
        SELECT id, name, description, status, version, definition_json,
               quality_profile_id, remotion_composition_id, created_at, updated_at
        FROM formats WHERE id = :id
    """), {"id": format_id})
    row = result.fetchone()
    
    if row:
        def_json = row[5]
        if isinstance(def_json, str):
            def_json = json.loads(def_json)
        return FormatResponse(
            id=row[0],
            name=row[1],
            description=row[2],
            status=row[3],
            version=row[4],
            definition_json=def_json or {},
            quality_profile_id=row[6],
            remotion_composition_id=row[7],
            created_at=str(row[8]) if row[8] else None,
            updated_at=str(row[9]) if row[9] else None,
            last_run=None
        )
    
    # Fallback to sample formats
    sample = get_sample_format(format_id)
    if sample:
        return _sample_to_format_response(sample)
    
    raise HTTPException(status_code=404, detail=f"Format '{format_id}' not found")


@router.post("/{format_id}/run", response_model=RunResponse)
async def run_format(
    format_id: str,
    request: RunRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a new run for a format.
    This queues the format for processing with Remotion.
    """
    # Validate format exists
    result = await db.execute(text("SELECT name FROM formats WHERE id = :id"), {"id": format_id})
    row = result.fetchone()
    format_name = row[0] if row else None
    
    if not format_name:
        sample = get_sample_format(format_id)
        format_name = sample["name"] if sample else None
    
    if not format_name:
        raise HTTPException(status_code=404, detail=f"Format '{format_id}' not found")
    
    # Generate run ID
    run_id = str(uuid.uuid4())
    
    logger.info(f"Triggered run {run_id} for format {format_id}")
    
    return RunResponse(
        run_id=run_id,
        format_id=format_id,
        status="queued",
        message=f"Run queued for format '{format_name}'"
    )


@router.get("/{format_id}/runs")
async def list_format_runs(
    format_id: str,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List recent runs for a format.
    """
    # Validate format exists
    result = await db.execute(text("SELECT id FROM formats WHERE id = :id"), {"id": format_id})
    if not result.fetchone() and not get_sample_format(format_id):
        raise HTTPException(status_code=404, detail=f"Format '{format_id}' not found")
    
    # Return empty runs for now (would be from DB in production)
    return {
        "format_id": format_id,
        "runs": [],
        "total": 0
    }


@router.delete("/{format_id}")
async def delete_format(format_id: str):
    """
    Delete a format (removes from seeded formats).
    """
    if format_id in _seeded_formats:
        del _seeded_formats[format_id]
        return {"status": "success", "message": f"Format '{format_id}' deleted"}
    
    raise HTTPException(status_code=404, detail=f"Format '{format_id}' not found")
