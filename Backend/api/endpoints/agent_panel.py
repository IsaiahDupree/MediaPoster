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
    minutes_ago: int = Query(default=60, le=1440)
):
    """
    Get unified event timeline for all agents or filtered by type.
    Shows thoughts, actions, and progress in chronological order.
    """
    from services.agent_framework import get_event_bus, AgentType, EventType
    
    bus = get_event_bus()
    
    # Parse filters
    agent_filter = None
    if agent_type:
        try:
            agent_filter = AgentType(agent_type)
        except ValueError as e:
            logger.debug(f"Silent exception: {e}")
    
    event_filter = None
    if event_type:
        try:
            event_filter = [EventType(event_type)]
        except ValueError as e:
            logger.debug(f"Silent exception: {e}")
    
    since = datetime.now() - timedelta(minutes=minutes_ago)
    
    timeline = await bus.get_timeline(
        agent_type=agent_filter,
        event_types=event_filter,
        limit=limit,
        since=since
    )
    
    return {
        "success": True,
        "events": timeline,
        "count": len(timeline),
        "filters": {
            "agent_type": agent_type,
            "event_type": event_type,
            "limit": limit,
            "since": since.isoformat()
        }
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
