"""
Agent Panel API Endpoints
==========================
API for viewing AI agent progress, event timelines, and controlling background tasks.
"""

from loguru import logger
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import logging

router = APIRouter(prefix="/api/agents", tags=["Agent Panel"])
logger = logging.getLogger(__name__)


# =============================================================================
# AGENT STATUS & TIMELINE
# =============================================================================

@router.get("/status")
async def get_all_agent_status():
    """Get status of all AI agents."""
    from services.agent_framework import get_event_bus, get_scheduler
    
    bus = get_event_bus()
    scheduler = get_scheduler()
    
    return {
        "success": True,
        "agents": bus.get_all_states(),
        "tasks": scheduler.get_all_tasks(),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/timeline")
async def get_event_timeline(
    agent_type: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    minutes_ago: int = Query(default=1440, le=10080)  # Default 24h, max 7 days
):
    """
    Get unified event timeline for all agents or filtered by type.
    Shows thoughts, actions, and progress in chronological order.
    Fetches from database for persistence across restarts.
    """
    import os
    from sqlalchemy import create_engine, text
    import json
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    since = datetime.now() - timedelta(minutes=minutes_ago)
    
    # Map frontend agent types to database values
    agent_type_map = {
        "narrative": "narrative_planner",
        "experiments": "experiment_runner", 
        "content_mix": "content_mix_planner"
    }
    db_agent_type = agent_type_map.get(agent_type, agent_type) if agent_type else None
    
    try:
        with engine.connect() as conn:
            # Build query with optional filters
            query = """
                SELECT id, agent_type, event_type, title, description, 
                       event_data, created_at
                FROM agent_events
                WHERE created_at >= :since
            """
            params = {"since": since, "limit": limit}
            
            if db_agent_type:
                query += " AND agent_type = :agent_type"
                params["agent_type"] = db_agent_type
            
            if event_type:
                query += " AND event_type = :event_type"
                params["event_type"] = event_type
            
            query += " ORDER BY created_at DESC LIMIT :limit"
            
            result = conn.execute(text(query), params)
            
            events = []
            for row in result:
                event_data = row[5]
                if isinstance(event_data, str):
                    try:
                        event_data = json.loads(event_data)
                    except:
                        event_data = {}
                
                events.append({
                    "id": str(row[0]),
                    "agent_type": row[1],
                    "event_type": row[2],
                    "title": row[3],
                    "description": row[4],
                    "data": event_data,
                    "timestamp": row[6].isoformat() if row[6] else None
                })
            
            return {
                "success": True,
                "events": events,
                "count": len(events),
                "filters": {
                    "agent_type": agent_type,
                    "event_type": event_type,
                    "limit": limit,
                    "since": since.isoformat()
                }
            }
    except Exception as e:
        logger.error(f"[Timeline] Database error: {e}")
        return {
            "success": True,
            "events": [],
            "count": 0,
            "error": str(e)
        }


@router.get("/narrative-planner/timeline")
async def get_narrative_planner_timeline(limit: int = Query(default=50, le=200)):
    """Get event timeline for Narrative Planner agent."""
    from services.agent_framework import get_event_bus, AgentType
    
    bus = get_event_bus()
    events = bus.get_agent_history(AgentType.NARRATIVE_PLANNER, limit)
    state = bus.get_agent_state(AgentType.NARRATIVE_PLANNER)
    
    return {
        "success": True,
        "agent": "narrative_planner",
        "state": state,
        "events": events,
        "count": len(events)
    }


@router.get("/experiment-runner/timeline")
async def get_experiment_runner_timeline(limit: int = Query(default=50, le=200)):
    """Get event timeline for Experiment Runner agent."""
    from services.agent_framework import get_event_bus, AgentType
    
    bus = get_event_bus()
    events = bus.get_agent_history(AgentType.EXPERIMENT_RUNNER, limit)
    state = bus.get_agent_state(AgentType.EXPERIMENT_RUNNER)
    
    return {
        "success": True,
        "agent": "experiment_runner",
        "state": state,
        "events": events,
        "count": len(events)
    }


# =============================================================================
# BACKGROUND TASK CONTROL
# =============================================================================

@router.post("/scheduler/start")
async def start_scheduler():
    """Start the background agent scheduler."""
    from services.agent_framework import start_background_agents
    
    try:
        await start_background_agents()
        return {"success": True, "message": "Background agents started"}
    except Exception as e:
        logger.error(f"[API] Failed to start scheduler: {e}")
        return {"success": False, "error": str(e)}


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the background agent scheduler."""
    from services.agent_framework import stop_background_agents
    
    try:
        await stop_background_agents()
        return {"success": True, "message": "Background agents stopped"}
    except Exception as e:
        logger.error(f"[API] Failed to stop scheduler: {e}")
        return {"success": False, "error": str(e)}


@router.get("/scheduler/tasks")
async def get_scheduled_tasks():
    """Get all scheduled tasks and their status."""
    from services.agent_framework import get_scheduler
    
    scheduler = get_scheduler()
    return {
        "success": True,
        "tasks": scheduler.get_all_tasks()
    }


@router.post("/scheduler/task/{task_id}/pause")
async def pause_task(task_id: str):
    """Pause a specific scheduled task."""
    from services.agent_framework import get_scheduler
    
    scheduler = get_scheduler()
    scheduler.pause_task(task_id)
    
    return {
        "success": True,
        "message": f"Task {task_id} paused",
        "task": scheduler.get_task_status(task_id)
    }


@router.post("/scheduler/task/{task_id}/resume")
async def resume_task(task_id: str):
    """Resume a paused scheduled task."""
    from services.agent_framework import get_scheduler
    
    scheduler = get_scheduler()
    scheduler.resume_task(task_id)
    
    return {
        "success": True,
        "message": f"Task {task_id} resumed",
        "task": scheduler.get_task_status(task_id)
    }


@router.post("/scheduler/task/{task_id}/run")
async def run_task_now(task_id: str):
    """Immediately run a scheduled task."""
    from services.agent_framework import get_scheduler
    
    scheduler = get_scheduler()
    
    try:
        await scheduler.run_task_now(task_id)
        return {
            "success": True,
            "message": f"Task {task_id} executed",
            "task": scheduler.get_task_status(task_id)
        }
    except Exception as e:
        logger.error(f"[API] Failed to run task {task_id}: {e}")
        return {"success": False, "error": str(e)}


@router.post("/scheduler/task/{task_id}/interval")
async def set_task_interval(task_id: str, interval_seconds: int):
    """Update the interval for a scheduled task."""
    from services.agent_framework import get_scheduler
    
    if interval_seconds < 60:
        return {"success": False, "error": "Minimum interval is 60 seconds"}
    
    scheduler = get_scheduler()
    scheduler.set_interval(task_id, interval_seconds)
    
    return {
        "success": True,
        "message": f"Task {task_id} interval updated to {interval_seconds}s",
        "task": scheduler.get_task_status(task_id)
    }


# =============================================================================
# AGENT PANEL DATA
# =============================================================================

@router.get("/panel/narrative")
async def get_narrative_panel_data():
    """Get complete panel data for Narrative Planner agent."""
    from services.agent_framework import get_event_bus, get_scheduler, AgentType
    from services.narrative_scheduler.autonomous_planner import get_planner
    
    bus = get_event_bus()
    scheduler = get_scheduler()
    planner = get_planner()
    
    state = bus.get_agent_state(AgentType.NARRATIVE_PLANNER)
    events = bus.get_agent_history(AgentType.NARRATIVE_PLANNER, 30)
    task = scheduler.get_task_status("narrative_planner")
    
    try:
        planner_status = await planner.get_status()
        draft = await planner.get_draft_plan()
    except:
        planner_status = {}
        draft = None
    
    return {
        "success": True,
        "agent": {
            "type": "narrative_planner",
            "name": "Narrative Planner",
            "description": "AI agent that builds 7-day content plans"
        },
        "state": state,
        "task": task,
        "planner": planner_status,
        "draft_plan": draft,
        "timeline": events
    }


@router.get("/panel/experiments")
async def get_experiments_panel_data():
    """Get complete panel data for Experiment Runner agent."""
    from services.agent_framework import get_event_bus, get_scheduler, AgentType
    from services.experiments_scheduler.autonomous_runner import get_runner
    
    bus = get_event_bus()
    scheduler = get_scheduler()
    runner = get_runner()
    
    state = bus.get_agent_state(AgentType.EXPERIMENT_RUNNER)
    events = bus.get_agent_history(AgentType.EXPERIMENT_RUNNER, 30)
    task = scheduler.get_task_status("experiment_runner")
    
    try:
        runner_status = await runner.get_status()
        candidates = await runner.scan_backlog()
        backlog = [
            {
                "id": c.id,
                "hypothesis": c.hypothesis[:100],
                "priority": c.priority_score,
                "confidence": c.confidence
            }
            for c in candidates[:10]
        ]
    except:
        runner_status = {}
        backlog = []
    
    return {
        "success": True,
        "agent": {
            "type": "experiment_runner",
            "name": "Experiment Runner",
            "description": "AI agent that runs content experiments"
        },
        "state": state,
        "task": task,
        "runner": runner_status,
        "backlog": backlog,
        "timeline": events
    }


@router.get("/panel/combined")
async def get_combined_panel_data():
    """Get combined panel data for all agents."""
    from services.agent_framework import get_event_bus, get_scheduler
    
    bus = get_event_bus()
    scheduler = get_scheduler()
    
    # Get all events sorted by time
    all_events = []
    for agent_type in ["narrative_planner", "experiment_runner"]:
        from services.agent_framework import AgentType
        try:
            agent = AgentType(agent_type)
            events = bus.get_agent_history(agent, 20)
            all_events.extend(events)
        except Exception as e:
            logger.debug(f"Silent exception: {e}")
    
    # Sort by timestamp
    all_events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    
    return {
        "success": True,
        "agents": bus.get_all_states(),
        "tasks": scheduler.get_all_tasks(),
        "unified_timeline": all_events[:50],
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# AGENT STATES
# =============================================================================

@router.get("/states")
async def get_agent_states():
    """Get current states of all agents."""
    from services.agent_framework import get_event_bus
    
    bus = get_event_bus()
    
    return {
        "success": True,
        "states": bus.get_all_states(),
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# BUDGET TRACKING
# =============================================================================

@router.get("/budgets")
async def get_agent_budgets():
    """Get budget/cost tracking for all agents."""
    import os
    from sqlalchemy import create_engine, text
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Try to get from agent_budgets table if it exists
            result = conn.execute(text("""
                SELECT agent_type, api_calls_today, api_calls_limit, 
                       tokens_used, tokens_limit, cost_today, cost_limit
                FROM agent_budgets
                WHERE date = CURRENT_DATE
            """))
            budgets = [dict(row._mapping) for row in result]
            
            return {
                "success": True,
                "budgets": budgets
            }
    except Exception as e:
        # Table doesn't exist yet, return default budgets
        logger.debug(f"Budget table not found: {e}")
        return {
            "success": True,
            "budgets": [
                {
                    "agent_type": "narrative",
                    "api_calls_today": 0,
                    "api_calls_limit": 100,
                    "tokens_used": 0,
                    "tokens_limit": 500000,
                    "cost_today": 0.0,
                    "cost_limit": 5.0
                },
                {
                    "agent_type": "experiments",
                    "api_calls_today": 0,
                    "api_calls_limit": 50,
                    "tokens_used": 0,
                    "tokens_limit": 250000,
                    "cost_today": 0.0,
                    "cost_limit": 2.5
                },
                {
                    "agent_type": "content_mix",
                    "api_calls_today": 0,
                    "api_calls_limit": 100,
                    "tokens_used": 0,
                    "tokens_limit": 500000,
                    "cost_today": 0.0,
                    "cost_limit": 5.0
                }
            ]
        }


@router.post("/budgets/{agent_type}/track")
async def track_api_usage(agent_type: str, tokens: int = 0, cost: float = 0.0):
    """Track API usage for an agent."""
    import os
    from sqlalchemy import create_engine, text
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO agent_budgets (agent_type, date, api_calls_today, tokens_used, cost_today)
                VALUES (:agent_type, CURRENT_DATE, 1, :tokens, :cost)
                ON CONFLICT (agent_type, date) DO UPDATE SET
                    api_calls_today = agent_budgets.api_calls_today + 1,
                    tokens_used = agent_budgets.tokens_used + :tokens,
                    cost_today = agent_budgets.cost_today + :cost
            """), {"agent_type": agent_type, "tokens": tokens, "cost": cost})
            conn.commit()
            
        return {"success": True, "message": "Usage tracked"}
    except Exception as e:
        logger.warning(f"Failed to track budget: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# AGENT MEMORY (LEARNINGS)
# =============================================================================

@router.get("/memories")
async def get_agent_memories(
    agent_type: Optional[str] = None,
    limit: int = Query(default=10, le=50)
):
    """Get stored agent learnings/memories."""
    import os
    from sqlalchemy import create_engine, text
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            if agent_type:
                result = conn.execute(text("""
                    SELECT id, agent_type, learning, context, relevance_score, created_at
                    FROM agent_memories
                    WHERE agent_type = :agent_type
                    ORDER BY relevance_score DESC, created_at DESC
                    LIMIT :limit
                """), {"agent_type": agent_type, "limit": limit})
            else:
                result = conn.execute(text("""
                    SELECT id, agent_type, learning, context, relevance_score, created_at
                    FROM agent_memories
                    ORDER BY relevance_score DESC, created_at DESC
                    LIMIT :limit
                """), {"limit": limit})
            
            memories = [dict(row._mapping) for row in result]
            
            return {
                "success": True,
                "memories": memories
            }
    except Exception as e:
        logger.debug(f"Memory table not found: {e}")
        return {
            "success": True,
            "memories": []
        }


@router.post("/memories")
async def store_agent_memory(
    agent_type: str,
    learning: str,
    context: str = "",
    relevance_score: float = 0.5
):
    """Store a new agent learning/memory."""
    import os
    import uuid
    from sqlalchemy import create_engine, text
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    try:
        memory_id = str(uuid.uuid4())
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO agent_memories (id, agent_type, learning, context, relevance_score)
                VALUES (:id, :agent_type, :learning, :context, :relevance_score)
            """), {
                "id": memory_id,
                "agent_type": agent_type,
                "learning": learning,
                "context": context,
                "relevance_score": relevance_score
            })
            conn.commit()
            
        return {"success": True, "memory_id": memory_id}
    except Exception as e:
        logger.warning(f"Failed to store memory: {e}")
        return {"success": False, "error": str(e)}
