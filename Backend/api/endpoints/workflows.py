"""
Workflows API
=============
API endpoints for workflow tracking and status.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any

from services.workflow_manager import WorkflowManager
from services.event_bus import EventBus, Topics

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("")
async def list_workflows(
    status: Optional[str] = Query(None, description="Filter by status"),
    workflow_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(20, le=100)
):
    """List recent workflows with optional filters."""
    manager = WorkflowManager.get_instance()
    workflows = manager.get_recent_workflows(
        limit=limit,
        workflow_type=workflow_type,
        status=status
    )
    
    return {
        "workflows": workflows,
        "count": len(workflows)
    }


@router.get("/active")
async def get_active_workflows():
    """Get all currently active (in_progress) workflows."""
    manager = WorkflowManager.get_instance()
    workflows = manager.get_active_workflows()
    
    return {
        "workflows": workflows,
        "count": len(workflows)
    }


@router.get("/stats")
async def get_workflow_stats():
    """Get workflow manager statistics."""
    manager = WorkflowManager.get_instance()
    return manager.get_stats()


@router.get("/{correlation_id}")
async def get_workflow(correlation_id: str):
    """Get workflow status by correlation ID."""
    manager = WorkflowManager.get_instance()
    workflow = manager.get_workflow(correlation_id)
    
    if not workflow:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow {correlation_id} not found"
        )
    
    return workflow


@router.get("/{correlation_id}/events")
async def get_workflow_events(correlation_id: str):
    """Get all events for a workflow."""
    manager = WorkflowManager.get_instance()
    events = manager.get_workflow_events(correlation_id)
    
    if not events:
        # Check if workflow exists
        workflow = manager.get_workflow(correlation_id)
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {correlation_id} not found"
            )
    
    return {
        "correlation_id": correlation_id,
        "events": events,
        "count": len(events)
    }
