"""
Automation Center API Endpoints
================================
API for managing agent schedules, runs, and the automation center UI.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
import logging

router = APIRouter(prefix="/api/automation", tags=["Automation Center"])
logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM HEALTH
# =============================================================================

@router.get("/health")
async def get_system_health():
    """Get automation system health metrics."""
    from services.agent_framework import get_scheduler, get_event_bus
    
    scheduler = get_scheduler()
    bus = get_event_bus()
    
    # Count workers
    tasks = scheduler.get_all_tasks()
    workers_online = sum(1 for t in tasks.values() if t and t.get('status') == 'running')
    
    # Get queue depth (queued runs)
    from services.agent_framework import get_run_manager
    run_manager = get_run_manager()
    recent = run_manager.get_recent_runs(limit=50)
    queue_depth = sum(1 for r in recent if r.get('status') == 'queued')
    
    # Get last tick
    last_tick = None
    for t in tasks.values():
        if t and t.get('last_run'):
            if not last_tick or t['last_run'] > last_tick:
                last_tick = t['last_run']
    
    # Count failures
    failures_24h = sum(1 for r in recent if r.get('status') == 'failed')
    
    return {
        "success": True,
        "health": {
            "workers_online": workers_online,
            "queue_depth": queue_depth,
            "last_tick": last_tick,
            "failures_24h": failures_24h
        }
    }


# =============================================================================
# SCHEDULES
# =============================================================================

@router.get("/schedules")
async def get_schedules(agent_type: Optional[str] = None):
    """Get all scheduled tasks."""
    from sqlalchemy import create_engine, text
    import os
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        query = """
            SELECT id, workspace_id, agent_type, topic, schedule_name,
                   interval_seconds, enabled, next_run_at, last_run_at, config_json
            FROM agent_schedules
        """
        params = {}
        
        if agent_type:
            query += " WHERE agent_type = :agent_type"
            params["agent_type"] = agent_type
        
        query += " ORDER BY agent_type, schedule_name"
        
        result = conn.execute(text(query), params)
        
        schedules = [
            {
                "id": str(row[0]),
                "workspace_id": str(row[1]) if row[1] else None,
                "agent_type": row[2],
                "topic": row[3],
                "schedule_name": row[4],
                "interval_seconds": row[5],
                "enabled": row[6],
                "next_run_at": row[7].isoformat() if row[7] else None,
                "last_run_at": row[8].isoformat() if row[8] else None,
                "config": row[9]
            }
            for row in result
        ]
    
    return {"success": True, "schedules": schedules}


@router.post("/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: str, enabled: bool = True):
    """Enable or disable a schedule."""
    from sqlalchemy import create_engine, text
    import os
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE agent_schedules SET enabled = :enabled, updated_at = NOW()
            WHERE id = :id
        """), {"id": schedule_id, "enabled": enabled})
        conn.commit()
    
    return {"success": True, "enabled": enabled}


@router.post("/schedules/{schedule_id}/run")
async def run_schedule_now(schedule_id: str):
    """Immediately trigger a scheduled task."""
    from services.agent_framework import get_run_manager
    from sqlalchemy import create_engine, text
    import os
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    # Get schedule info
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT agent_type, config_json FROM agent_schedules WHERE id = :id
        """), {"id": schedule_id})
        row = result.fetchone()
        
        if not row:
            return {"success": False, "error": "Schedule not found"}
        
        agent_type = row[0]
        config = row[1] or {}
    
    # Create a run
    run_manager = get_run_manager()
    run_id = run_manager.create_run(
        agent_type=agent_type,
        schedule_id=schedule_id,
        context=config
    )
    
    return {"success": True, "run_id": run_id, "message": "Run queued"}


# =============================================================================
# RUNS
# =============================================================================

@router.get("/runs")
async def get_runs(
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100)
):
    """Get recent runs."""
    from services.agent_framework import get_run_manager
    
    run_manager = get_run_manager()
    runs = run_manager.get_recent_runs(agent_type=agent_type, limit=limit)
    
    if status:
        runs = [r for r in runs if r.get('status') == status]
    
    return {"success": True, "runs": runs}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get run details."""
    from services.agent_framework import get_run_manager
    
    run_manager = get_run_manager()
    run = run_manager.get_run(run_id)
    
    if not run:
        return {"success": False, "error": "Run not found"}
    
    return {"success": True, "run": run}


@router.get("/runs/{run_id}/steps")
async def get_run_steps(run_id: str):
    """Get steps for a run."""
    from services.agent_framework import get_run_manager
    
    run_manager = get_run_manager()
    steps = run_manager.get_run_steps(run_id)
    
    return {"success": True, "steps": steps}


@router.get("/runs/{run_id}/timeline")
async def get_run_timeline(run_id: str, limit: int = Query(default=100, le=500)):
    """Get event timeline for a run."""
    from services.agent_framework import get_run_manager
    
    run_manager = get_run_manager()
    events = run_manager.get_run_timeline(run_id, limit=limit)
    
    return {"success": True, "events": events}


@router.get("/runs/{run_id}/artifacts")
async def get_run_artifacts(run_id: str):
    """Get artifacts for a run."""
    from services.agent_framework import get_run_manager
    
    run_manager = get_run_manager()
    artifacts = run_manager.get_run_artifacts(run_id)
    
    return {"success": True, "artifacts": artifacts}


@router.post("/runs/{run_id}/pause")
async def pause_run(run_id: str):
    """Pause a running run."""
    from services.agent_framework import get_run_manager
    
    run_manager = get_run_manager()
    run_manager.pause_run(run_id)
    
    return {"success": True, "message": "Run paused"}


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """Cancel a run."""
    from services.agent_framework import get_run_manager
    
    run_manager = get_run_manager()
    run_manager.cancel_run(run_id)
    
    return {"success": True, "message": "Run canceled"}


@router.post("/runs/{run_id}/retry")
async def retry_run(run_id: str):
    """Retry a failed run."""
    from services.agent_framework import get_run_manager
    
    run_manager = get_run_manager()
    
    # Get original run
    original = run_manager.get_run(run_id)
    if not original:
        return {"success": False, "error": "Run not found"}
    
    # Create new run with same context
    new_run_id = run_manager.create_run(
        agent_type=original['agent_type'],
        schedule_id=original.get('schedule_id'),
        context=original.get('context', {})
    )
    
    return {"success": True, "run_id": new_run_id, "message": "Retry queued"}


# =============================================================================
# TOPICS (PUB/SUB INSPECTOR)
# =============================================================================

@router.get("/topics")
async def get_topics():
    """Get all registered topics."""
    import json
    from pathlib import Path
    
    registry_path = Path(__file__).parent.parent.parent / "services/agent_framework/registries/topic_registry.json"
    
    try:
        with open(registry_path) as f:
            registry = json.load(f)
        return {"success": True, "topics": registry.get("topics", {})}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/topics/{topic}/events")
async def get_topic_events(topic: str, limit: int = Query(default=50, le=200)):
    """Get recent events for a topic."""
    from sqlalchemy import create_engine, text
    import os
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, run_id, ts, event_type, severity, source_service, message
            FROM agent_events
            WHERE topic = :topic
            ORDER BY ts DESC
            LIMIT :limit
        """), {"topic": topic, "limit": limit})
        
        events = [
            {
                "id": str(row[0]),
                "run_id": str(row[1]) if row[1] else None,
                "timestamp": row[2].isoformat() if row[2] else None,
                "event_type": row[3],
                "severity": row[4],
                "source_service": row[5],
                "message": row[6]
            }
            for row in result
        ]
    
    return {"success": True, "events": events}


# =============================================================================
# SERVICES
# =============================================================================

@router.get("/services")
async def get_services():
    """Get service health information."""
    from services.agent_framework import get_scheduler
    
    scheduler = get_scheduler()
    tasks = scheduler.get_all_tasks()
    
    services = []
    for task_id, task in tasks.items():
        if task:
            services.append({
                "id": task_id,
                "name": task.get('name', task_id),
                "status": task.get('status', 'unknown'),
                "last_run": task.get('last_run'),
                "run_count": task.get('run_count', 0),
                "error_count": task.get('error_count', 0)
            })
    
    return {"success": True, "services": services}
