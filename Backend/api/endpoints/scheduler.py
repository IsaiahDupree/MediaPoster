"""
Scheduler API Endpoints
========================
Endpoints for scheduler tick and worker processing.
Called by cron jobs to process scheduled tasks.
"""

from fastapi import APIRouter, BackgroundTasks
from typing import Optional
import logging
import os
from datetime import datetime
from sqlalchemy import create_engine, text

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


# =============================================================================
# SCHEDULER TICK - Creates runs from due schedules
# =============================================================================

@router.post("/tick")
async def scheduler_tick():
    """
    Process due schedules and create runs.
    Called by cron every minute.
    """
    from services.agent_framework import get_run_manager
    
    engine = create_engine(DATABASE_URL)
    run_manager = get_run_manager()
    created = 0
    
    try:
        with engine.connect() as conn:
            # Find due schedules
            now_iso = datetime.utcnow().isoformat()
            result = conn.execute(text("""
                SELECT id, workspace_id, agent_type, topic, config_json, interval_seconds
                FROM agent_schedules
                WHERE enabled = true AND next_run_at <= :now
                LIMIT 50
            """), {"now": now_iso})
            
            schedules = list(result)
            
            for schedule in schedules:
                schedule_id = str(schedule[0])
                workspace_id = str(schedule[1]) if schedule[1] else None
                agent_type = schedule[2]
                topic = schedule[3]
                config = schedule[4] or {}
                interval_seconds = schedule[5] or 86400
                
                # Create run
                run_id = run_manager.create_run(
                    agent_type=agent_type,
                    schedule_id=schedule_id,
                    context={**config, "topic": topic}
                )
                
                # Enqueue to queue
                conn.execute(text("""
                    INSERT INTO agent_queue (workspace_id, run_id, topic, payload_json)
                    VALUES (:workspace_id, :run_id, :topic, :payload)
                """), {
                    "workspace_id": workspace_id,
                    "run_id": run_id,
                    "topic": topic,
                    "payload": str(config).replace("'", '"') if config else "{}"
                })
                
                # Update next_run_at
                next_run = datetime.utcnow().timestamp() + interval_seconds
                next_run_iso = datetime.fromtimestamp(next_run).isoformat()
                conn.execute(text("""
                    UPDATE agent_schedules 
                    SET next_run_at = :next_run, last_run_at = NOW()
                    WHERE id = :id
                """), {"id": schedule_id, "next_run": next_run_iso})
                
                created += 1
                logger.info(f"[Scheduler] Created run {run_id} for schedule {schedule_id}")
            
            conn.commit()
    
    except Exception as e:
        logger.error(f"[Scheduler] Tick error: {e}")
        return {"success": False, "error": str(e)}
    
    return {"success": True, "created": created}


# =============================================================================
# WORKER PROCESS - Consumes queue and dispatches to service handlers
# =============================================================================

@router.post("/worker/process")
async def worker_process(background_tasks: BackgroundTasks, batch_size: int = 5):
    """
    Process queued jobs and dispatch to service handlers.
    Called by cron every minute or run as background worker.
    """
    from services.agent_framework import get_run_manager
    from services.agent_framework.dispatcher import dispatch_topic
    
    engine = create_engine(DATABASE_URL)
    run_manager = get_run_manager()
    processed = 0
    
    try:
        with engine.connect() as conn:
            # Claim jobs using atomic update
            result = conn.execute(text("""
                UPDATE agent_queue
                SET status = 'processing', 
                    locked_at = NOW(), 
                    locked_by = 'api_worker',
                    attempts = attempts + 1
                WHERE id IN (
                    SELECT id FROM agent_queue
                    WHERE status = 'queued' AND available_at <= NOW()
                    ORDER BY created_at ASC
                    LIMIT :batch_size
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, run_id, topic, payload_json
            """), {"batch_size": batch_size})
            
            jobs = list(result)
            conn.commit()
            
            for job in jobs:
                job_id = str(job[0])
                run_id = str(job[1])
                topic = job[2]
                payload = job[3] or {}
                
                # Start run
                run_manager.start_run(run_id)
                
                try:
                    # Dispatch to service handler
                    await dispatch_topic(topic, run_id, payload)
                    
                    # Mark job complete
                    conn.execute(text("""
                        UPDATE agent_queue SET status = 'done' WHERE id = :id
                    """), {"id": job_id})
                    
                    # Complete run
                    run_manager.complete_run(run_id)
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"[Worker] Job {job_id} failed: {e}")
                    
                    # Mark job failed
                    conn.execute(text("""
                        UPDATE agent_queue 
                        SET status = 'failed', last_error = :error
                        WHERE id = :id
                    """), {"id": job_id, "error": str(e)})
                    
                    # Fail run
                    run_manager.fail_run(run_id, str(e))
                
                conn.commit()
    
    except Exception as e:
        logger.error(f"[Worker] Process error: {e}")
        return {"success": False, "error": str(e)}
    
    return {"success": True, "processed": processed}


# =============================================================================
# MANUAL TRIGGER - For testing
# =============================================================================

@router.post("/trigger/{schedule_id}")
async def trigger_schedule(schedule_id: str):
    """Manually trigger a schedule for testing."""
    from services.agent_framework import get_run_manager
    
    engine = create_engine(DATABASE_URL)
    run_manager = get_run_manager()
    
    try:
        with engine.connect() as conn:
            # Get schedule
            result = conn.execute(text("""
                SELECT agent_type, topic, config_json FROM agent_schedules WHERE id = :id
            """), {"id": schedule_id})
            row = result.fetchone()
            
            if not row:
                return {"success": False, "error": "Schedule not found"}
            
            agent_type = row[0]
            topic = row[1]
            config = row[2] or {}
            
            # Create and start run
            run_id = run_manager.create_run(
                agent_type=agent_type,
                schedule_id=schedule_id,
                context={**config, "topic": topic, "manual_trigger": True}
            )
            
            # Enqueue
            conn.execute(text("""
                INSERT INTO agent_queue (run_id, topic, payload_json)
                VALUES (:run_id, :topic, :payload)
            """), {
                "run_id": run_id,
                "topic": topic,
                "payload": "{}"
            })
            conn.commit()
            
            return {"success": True, "run_id": run_id, "topic": topic}
    
    except Exception as e:
        logger.error(f"[Scheduler] Trigger error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def scheduler_health():
    """Get scheduler health status."""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Queue stats
            queue_result = conn.execute(text("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'queued') as queued,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing,
                    COUNT(*) FILTER (WHERE status = 'done') as done,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed
                FROM agent_queue
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """))
            queue_stats = queue_result.fetchone()
            
            # Schedule stats
            schedule_result = conn.execute(text("""
                SELECT 
                    COUNT(*) FILTER (WHERE enabled = true) as enabled,
                    COUNT(*) FILTER (WHERE enabled = false) as disabled,
                    COUNT(*) FILTER (WHERE next_run_at <= NOW() AND enabled = true) as due
                FROM agent_schedules
            """))
            schedule_stats = schedule_result.fetchone()
            
            return {
                "success": True,
                "queue": {
                    "queued": queue_stats[0] if queue_stats else 0,
                    "processing": queue_stats[1] if queue_stats else 0,
                    "done_24h": queue_stats[2] if queue_stats else 0,
                    "failed_24h": queue_stats[3] if queue_stats else 0
                },
                "schedules": {
                    "enabled": schedule_stats[0] if schedule_stats else 0,
                    "disabled": schedule_stats[1] if schedule_stats else 0,
                    "due_now": schedule_stats[2] if schedule_stats else 0
                }
            }
    
    except Exception as e:
        return {"success": False, "error": str(e)}
