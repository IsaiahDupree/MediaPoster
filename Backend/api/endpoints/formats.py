"""
Formats API Endpoints
CRUD operations for video formats and run management
"""
import os
import logging
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


def get_engine():
    return create_engine(DATABASE_URL)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class FormatCreate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str = "draft"
    version: str = "1.0.0"
    definition_json: Dict[str, Any]
    quality_profile_id: Optional[str] = "qp_shortform_v1"


class FormatUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    version: Optional[str] = None
    definition_json: Optional[Dict[str, Any]] = None
    quality_profile_id: Optional[str] = None


class RunCreate(BaseModel):
    params: Dict[str, Any] = {}
    trigger_type: str = "manual"
    triggered_by: Optional[str] = None
    variant_id: Optional[str] = None


class FormatResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    version: str
    definition_json: Dict[str, Any]
    quality_profile_id: Optional[str]
    remotion_composition_id: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    last_run: Optional[Dict[str, Any]] = None


class RunResponse(BaseModel):
    id: str
    format_id: str
    status: str
    trigger_type: str
    triggered_by: Optional[str]
    params_json: Dict[str, Any]
    resolved_inputs_json: Optional[Dict[str, Any]]
    render_props_json: Optional[Dict[str, Any]]
    variant_id: Optional[str]
    error_json: Optional[Dict[str, Any]]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str
    artifacts: Optional[List[Dict[str, Any]]] = None


# =============================================================================
# FORMAT CRUD ENDPOINTS
# =============================================================================

@router.get("/list")
async def list_formats(
    status: Optional[str] = Query(None, description="Filter by status: draft, active, archived"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List all formats for the sidebar.
    Returns formats with their last run status.
    """
    engine = get_engine()
    
    where_clause = "WHERE 1=1"
    params = {"limit": limit}
    
    if status:
        where_clause += " AND f.status = :status"
        params["status"] = status
    
    query = f"""
        SELECT 
            f.id, f.name, f.description, f.status, f.version,
            f.definition_json, f.quality_profile_id, f.remotion_composition_id,
            f.created_at, f.updated_at,
            lr.id as last_run_id, lr.status as last_run_status, 
            lr.created_at as last_run_at
        FROM formats f
        LEFT JOIN LATERAL (
            SELECT id, status, created_at
            FROM format_runs
            WHERE format_id = f.id
            ORDER BY created_at DESC
            LIMIT 1
        ) lr ON true
        {where_clause}
        ORDER BY f.updated_at DESC
        LIMIT :limit
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = result.fetchall()
    
    formats = []
    for row in rows:
        formats.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "status": row[3],
            "version": row[4],
            "definition_json": row[5] if isinstance(row[5], dict) else json.loads(row[5]) if row[5] else {},
            "quality_profile_id": row[6],
            "remotion_composition_id": row[7],
            "created_at": str(row[8]) if row[8] else None,
            "updated_at": str(row[9]) if row[9] else None,
            "last_run": {
                "id": str(row[10]),
                "status": row[11],
                "created_at": str(row[12])
            } if row[10] else None
        })
    
    return {"formats": formats, "total": len(formats)}


@router.get("/{format_id}")
async def get_format(format_id: str):
    """Get a single format with full definition."""
    engine = get_engine()
    
    query = """
        SELECT 
            id, name, description, status, version,
            definition_json, quality_profile_id, remotion_composition_id,
            created_at, updated_at
        FROM formats
        WHERE id = :format_id
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query), {"format_id": format_id})
        row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Format not found: {format_id}")
    
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "status": row[3],
        "version": row[4],
        "definition_json": row[5] if isinstance(row[5], dict) else json.loads(row[5]) if row[5] else {},
        "quality_profile_id": row[6],
        "remotion_composition_id": row[7],
        "created_at": str(row[8]) if row[8] else None,
        "updated_at": str(row[9]) if row[9] else None
    }


@router.post("/create")
async def create_format(format_data: FormatCreate):
    """Create a new format."""
    engine = get_engine()
    
    definition = format_data.definition_json
    remotion_id = definition.get("composition", {}).get("remotionCompositionId")
    
    with engine.connect() as conn:
        # Check if format already exists
        existing = conn.execute(
            text("SELECT id FROM formats WHERE id = :id"),
            {"id": format_data.id}
        ).fetchone()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Format already exists: {format_data.id}")
        
        conn.execute(text("""
            INSERT INTO formats (id, name, description, status, version, definition_json, 
                                quality_profile_id, remotion_composition_id)
            VALUES (:id, :name, :description, :status, :version, :definition_json,
                    :quality_profile_id, :remotion_composition_id)
        """), {
            "id": format_data.id,
            "name": format_data.name,
            "description": format_data.description,
            "status": format_data.status,
            "version": format_data.version,
            "definition_json": json.dumps(definition),
            "quality_profile_id": format_data.quality_profile_id,
            "remotion_composition_id": remotion_id
        })
        conn.commit()
    
    return {"id": format_data.id, "message": "Format created successfully"}


@router.put("/{format_id}")
async def update_format(format_id: str, format_data: FormatUpdate):
    """Update an existing format."""
    engine = get_engine()
    
    updates = []
    params = {"format_id": format_id}
    
    if format_data.name is not None:
        updates.append("name = :name")
        params["name"] = format_data.name
    
    if format_data.description is not None:
        updates.append("description = :description")
        params["description"] = format_data.description
    
    if format_data.status is not None:
        updates.append("status = :status")
        params["status"] = format_data.status
    
    if format_data.version is not None:
        updates.append("version = :version")
        params["version"] = format_data.version
    
    if format_data.definition_json is not None:
        updates.append("definition_json = :definition_json")
        params["definition_json"] = json.dumps(format_data.definition_json)
        
        remotion_id = format_data.definition_json.get("composition", {}).get("remotionCompositionId")
        if remotion_id:
            updates.append("remotion_composition_id = :remotion_composition_id")
            params["remotion_composition_id"] = remotion_id
    
    if format_data.quality_profile_id is not None:
        updates.append("quality_profile_id = :quality_profile_id")
        params["quality_profile_id"] = format_data.quality_profile_id
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = NOW()")
    
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            UPDATE formats SET {', '.join(updates)}
            WHERE id = :format_id
        """), params)
        conn.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Format not found: {format_id}")
    
    return {"id": format_id, "message": "Format updated successfully"}


@router.delete("/{format_id}")
async def delete_format(format_id: str):
    """Delete a format (sets status to archived)."""
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            UPDATE formats SET status = 'archived', updated_at = NOW()
            WHERE id = :format_id
        """), {"format_id": format_id})
        conn.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Format not found: {format_id}")
    
    return {"id": format_id, "message": "Format archived successfully"}


# =============================================================================
# RUN ENDPOINTS
# =============================================================================

@router.post("/{format_id}/run")
async def trigger_run(
    format_id: str,
    run_data: RunCreate,
    background_tasks: BackgroundTasks
):
    """
    Trigger a new format run.
    Creates a run record and enqueues the compilation job.
    """
    engine = get_engine()
    run_id = str(uuid.uuid4())
    
    with engine.connect() as conn:
        # Verify format exists
        format_row = conn.execute(
            text("SELECT id, definition_json FROM formats WHERE id = :id"),
            {"id": format_id}
        ).fetchone()
        
        if not format_row:
            raise HTTPException(status_code=404, detail=f"Format not found: {format_id}")
        
        # Create run record
        conn.execute(text("""
            INSERT INTO format_runs (id, format_id, status, trigger_type, triggered_by, 
                                     params_json, variant_id)
            VALUES (:id, :format_id, 'queued', :trigger_type, :triggered_by, 
                    :params_json, :variant_id)
        """), {
            "id": run_id,
            "format_id": format_id,
            "trigger_type": run_data.trigger_type,
            "triggered_by": run_data.triggered_by,
            "params_json": json.dumps(run_data.params),
            "variant_id": run_data.variant_id
        })
        conn.commit()
    
    # Enqueue the run job (for now, run in background)
    background_tasks.add_task(execute_format_run, run_id, format_id, run_data.params)
    
    return {"run_id": run_id, "status": "queued", "message": "Run triggered successfully"}


@router.get("/{format_id}/runs")
async def list_runs(
    format_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """List runs for a format."""
    engine = get_engine()
    
    where_clause = "WHERE format_id = :format_id"
    params = {"format_id": format_id, "limit": limit}
    
    if status:
        where_clause += " AND status = :status"
        params["status"] = status
    
    query = f"""
        SELECT id, format_id, status, trigger_type, triggered_by,
               params_json, variant_id, error_json,
               started_at, completed_at, created_at, updated_at
        FROM format_runs
        {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = result.fetchall()
    
    runs = []
    for row in rows:
        runs.append({
            "id": str(row[0]),
            "format_id": row[1],
            "status": row[2],
            "trigger_type": row[3],
            "triggered_by": row[4],
            "params_json": row[5] if isinstance(row[5], dict) else json.loads(row[5]) if row[5] else {},
            "variant_id": row[6],
            "error_json": row[7] if isinstance(row[7], dict) else json.loads(row[7]) if row[7] else None,
            "started_at": str(row[8]) if row[8] else None,
            "completed_at": str(row[9]) if row[9] else None,
            "created_at": str(row[10]),
            "updated_at": str(row[11])
        })
    
    return {"runs": runs, "total": len(runs)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get a specific run with artifacts."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get run
        run_row = conn.execute(text("""
            SELECT id, format_id, status, trigger_type, triggered_by,
                   params_json, resolved_inputs_json, render_props_json,
                   variant_id, error_json,
                   started_at, completed_at, created_at, updated_at
            FROM format_runs
            WHERE id = :run_id
        """), {"run_id": run_id}).fetchone()
        
        if not run_row:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        
        # Get artifacts
        artifacts = conn.execute(text("""
            SELECT id, kind, url, file_path, file_size_bytes, duration_sec, meta, created_at
            FROM run_artifacts
            WHERE run_id = :run_id
            ORDER BY created_at
        """), {"run_id": run_id}).fetchall()
    
    artifact_list = [
        {
            "id": str(a[0]),
            "kind": a[1],
            "url": a[2],
            "file_path": a[3],
            "file_size_bytes": a[4],
            "duration_sec": float(a[5]) if a[5] else None,
            "meta": a[6] if isinstance(a[6], dict) else json.loads(a[6]) if a[6] else {},
            "created_at": str(a[7])
        }
        for a in artifacts
    ]
    
    def parse_json(val):
        if val is None:
            return None
        if isinstance(val, dict):
            return val
        try:
            return json.loads(val)
        except:
            return None
    
    return {
        "id": str(run_row[0]),
        "format_id": run_row[1],
        "status": run_row[2],
        "trigger_type": run_row[3],
        "triggered_by": run_row[4],
        "params_json": parse_json(run_row[5]) or {},
        "resolved_inputs_json": parse_json(run_row[6]),
        "render_props_json": parse_json(run_row[7]),
        "variant_id": run_row[8],
        "error_json": parse_json(run_row[9]),
        "started_at": str(run_row[10]) if run_row[10] else None,
        "completed_at": str(run_row[11]) if run_row[11] else None,
        "created_at": str(run_row[12]),
        "updated_at": str(run_row[13]),
        "artifacts": artifact_list
    }


@router.get("/runs/{run_id}/artifacts")
async def get_run_artifacts(run_id: str, kind: Optional[str] = Query(None)):
    """Get artifacts for a run."""
    engine = get_engine()
    
    where_clause = "WHERE run_id = :run_id"
    params = {"run_id": run_id}
    
    if kind:
        where_clause += " AND kind = :kind"
        params["kind"] = kind
    
    with engine.connect() as conn:
        artifacts = conn.execute(text(f"""
            SELECT id, kind, url, file_path, file_size_bytes, duration_sec, meta, created_at
            FROM run_artifacts
            {where_clause}
            ORDER BY created_at
        """), params).fetchall()
    
    return {
        "artifacts": [
            {
                "id": str(a[0]),
                "kind": a[1],
                "url": a[2],
                "file_path": a[3],
                "file_size_bytes": a[4],
                "duration_sec": float(a[5]) if a[5] else None,
                "meta": a[6] if isinstance(a[6], dict) else json.loads(a[6]) if a[6] else {},
                "created_at": str(a[7])
            }
            for a in artifacts
        ]
    }


# =============================================================================
# QUALITY PROFILES ENDPOINTS
# =============================================================================

@router.post("/seed-samples")
async def seed_sample_formats():
    """Seed the database with sample format definitions."""
    from services.formats.sample_formats import list_sample_formats
    
    engine = get_engine()
    samples = list_sample_formats()
    created = []
    skipped = []
    
    with engine.connect() as conn:
        for fmt in samples:
            existing = conn.execute(
                text("SELECT id FROM formats WHERE id = :id"),
                {"id": fmt["id"]}
            ).fetchone()
            
            if existing:
                skipped.append(fmt["id"])
                continue
            
            remotion_id = fmt.get("composition", {}).get("remotionCompositionId")
            quality_profile_id = fmt.get("defaults", {}).get("qualityProfileId", "qp_shortform_v1")
            
            conn.execute(text("""
                INSERT INTO formats (id, name, description, status, version, definition_json, 
                                    quality_profile_id, remotion_composition_id)
                VALUES (:id, :name, :description, :status, :version, :definition_json,
                        :quality_profile_id, :remotion_composition_id)
            """), {
                "id": fmt["id"],
                "name": fmt["name"],
                "description": fmt.get("description"),
                "status": fmt.get("status", "draft"),
                "version": fmt.get("version", "1.0.0"),
                "definition_json": json.dumps(fmt),
                "quality_profile_id": quality_profile_id,
                "remotion_composition_id": remotion_id
            })
            created.append(fmt["id"])
        
        conn.commit()
    
    return {
        "created": created,
        "skipped": skipped,
        "message": f"Seeded {len(created)} formats, skipped {len(skipped)} existing"
    }


@router.get("/quality-profiles/list")
async def list_quality_profiles():
    """List all quality profiles."""
    engine = get_engine()
    
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, name, description, gates_json, is_default, created_at
            FROM quality_profiles
            ORDER BY is_default DESC, name
        """)).fetchall()
    
    return {
        "profiles": [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "gates_json": row[3] if isinstance(row[3], list) else json.loads(row[3]) if row[3] else [],
                "is_default": row[4],
                "created_at": str(row[5]) if row[5] else None
            }
            for row in rows
        ]
    }


# =============================================================================
# RUN WORKER (Background Task)
# =============================================================================

async def execute_format_run(run_id: str, format_id: str, params: Dict):
    """
    Execute a format run in the background.
    This is the main worker function that compiles and renders the format.
    """
    from services.formats.compiler import compile_run
    from services.formats.quality_gates import run_quality_gates
    
    engine = get_engine()
    
    try:
        # Update status to running
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE format_runs 
                SET status = 'running', started_at = NOW(), updated_at = NOW()
                WHERE id = :run_id
            """), {"run_id": run_id})
            conn.commit()
            
            # Load format definition
            format_row = conn.execute(text("""
                SELECT definition_json, quality_profile_id FROM formats WHERE id = :format_id
            """), {"format_id": format_id}).fetchone()
            
            if not format_row:
                raise ValueError(f"Format not found: {format_id}")
            
            format_def = format_row[0] if isinstance(format_row[0], dict) else json.loads(format_row[0])
            quality_profile_id = format_row[1] or "qp_shortform_v1"
            
            # Load quality profile
            profile_row = conn.execute(text("""
                SELECT id, name, gates_json FROM quality_profiles WHERE id = :id
            """), {"id": quality_profile_id}).fetchone()
            
            quality_profile = {
                "id": profile_row[0],
                "name": profile_row[1],
                "gates_json": profile_row[2] if isinstance(profile_row[2], list) else json.loads(profile_row[2]) if profile_row[2] else []
            } if profile_row else {"id": "default", "name": "Default", "gates_json": []}
        
        # Compile the run
        logger.info(f"[FormatRun] Compiling run {run_id} for format {format_id}")
        compile_result = await compile_run(
            format_def=format_def,
            run_id=run_id,
            params=params,
            supabase_client=None,  # TODO: Pass actual client
            libraries={}  # TODO: Load libraries
        )
        
        # Store resolved inputs and render props
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE format_runs 
                SET resolved_inputs_json = :resolved, render_props_json = :props, updated_at = NOW()
                WHERE id = :run_id
            """), {
                "run_id": run_id,
                "resolved": json.dumps(compile_result.resolved_inputs),
                "props": compile_result.render_props.model_dump_json()
            })
            conn.commit()
        
        # Run pre-render quality gates
        pre_gates = await run_quality_gates(
            phase="pre",
            format_def=format_def,
            quality_profile=quality_profile,
            render_props=compile_result.render_props.model_dump(),
            video_config=compile_result.video_config.model_dump(),
            artifacts={}
        )
        
        # Store gate results as artifact
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO run_artifacts (run_id, kind, url, meta)
                VALUES (:run_id, 'logs', 'inline://quality-pre', :meta)
            """), {
                "run_id": run_id,
                "meta": json.dumps({"phase": "pre", "ok": pre_gates.ok, "results": [r.model_dump() for r in pre_gates.results]})
            })
            conn.commit()
        
        if not pre_gates.ok:
            raise ValueError(f"Pre-render quality gates failed: {[r.message for r in pre_gates.results if not r.ok]}")
        
        # TODO: Generate voice, music, and other artifacts
        # TODO: Call Remotion render worker
        # TODO: Run post-render quality gates
        
        # For now, mark as succeeded (placeholder)
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE format_runs 
                SET status = 'succeeded', completed_at = NOW(), updated_at = NOW()
                WHERE id = :run_id
            """), {"run_id": run_id})
            conn.commit()
        
        logger.info(f"[FormatRun] Run {run_id} completed successfully")
        
    except Exception as e:
        logger.error(f"[FormatRun] Run {run_id} failed: {e}")
        
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE format_runs 
                SET status = 'failed', error_json = :error, completed_at = NOW(), updated_at = NOW()
                WHERE id = :run_id
            """), {
                "run_id": run_id,
                "error": json.dumps({"message": str(e), "type": type(e).__name__})
            })
            conn.commit()
