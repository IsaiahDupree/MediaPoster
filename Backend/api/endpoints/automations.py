"""
Automation Registry API Endpoints (BM-007)
===========================================
CRUD API for managing system automations, their schedules, and execution history.

Endpoints:
- GET /api/automations - List all automations
- GET /api/automations/{automation_id} - Get automation details
- POST /api/automations - Register new automation
- PUT /api/automations/{automation_id} - Update automation
- DELETE /api/automations/{automation_id} - Delete automation
- GET /api/automations/{automation_id}/runs - Get run history
- GET /api/automations/runs/active - Get active runs
- GET /api/automations/stats - Get registry statistics
- POST /api/automations/{automation_id}/start - Manually start a run
- POST /api/automations/{automation_id}/pause - Pause automation
- POST /api/automations/{automation_id}/resume - Resume automation
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

from services.automation_registry import (
    get_automation_registry,
    AutomationStatus,
    AutomationType,
    ScheduleType
)


router = APIRouter(prefix="/api/automations", tags=["Automation Registry"])


# ==================== Request Models ====================

class RegisterAutomationRequest(BaseModel):
    """Request to register a new automation"""
    name: str = Field(..., description="Human-readable automation name")
    automation_type: str = Field(..., description="Type of automation")
    description: Optional[str] = Field(None, description="Optional description")
    schedule_type: Optional[str] = Field(None, description="Schedule type (cron, interval, event_driven, one_time)")
    schedule_config: Optional[Dict[str, Any]] = Field(None, description="Schedule configuration")
    resource_requirements: Optional[Dict[str, Any]] = Field(None, description="Resource requirements")
    config: Optional[Dict[str, Any]] = Field(None, description="Automation-specific config")
    priority: int = Field(5, ge=1, le=10, description="Priority level (1-10)")
    max_concurrent_runs: int = Field(1, ge=1, description="Max concurrent runs")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    created_by: Optional[str] = Field(None, description="Creator identifier")


class UpdateAutomationRequest(BaseModel):
    """Request to update automation"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[Dict[str, Any]] = None
    resource_requirements: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    max_concurrent_runs: Optional[int] = Field(None, ge=1)
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class StartRunRequest(BaseModel):
    """Request to manually start a run"""
    triggered_by: str = Field("manual", description="Who/what triggered this run")
    trigger_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional context")


# ==================== Endpoints ====================

@router.get("/")
async def list_automations(
    status: Optional[str] = Query(None, description="Filter by status"),
    automation_type: Optional[str] = Query(None, description="Filter by type"),
    enabled_only: bool = Query(False, description="Only show enabled automations"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)")
):
    """
    List all automations with optional filters

    Returns:
        List of automation records with their current status and metrics
    """
    try:
        registry = get_automation_registry()

        # Parse tags if provided
        tag_list = tags.split(",") if tags else None

        automations = await registry.list_automations(
            status=status,
            automation_type=automation_type,
            tags=tag_list,
            enabled_only=enabled_only
        )

        return {
            "success": True,
            "data": {
                "automations": automations,
                "count": len(automations)
            }
        }

    except Exception as e:
        logger.error(f"Error listing automations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{automation_id}")
async def get_automation(automation_id: str):
    """
    Get automation details by ID

    Returns:
        Automation record with full configuration and metrics
    """
    try:
        registry = get_automation_registry()
        automation = await registry.get_automation(automation_id)

        if not automation:
            raise HTTPException(status_code=404, detail="Automation not found")

        return {
            "success": True,
            "data": automation
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def register_automation(request: RegisterAutomationRequest):
    """
    Register a new automation

    Creates a new automation entry in the registry with the provided configuration.
    The automation will be active by default.
    """
    try:
        registry = get_automation_registry()

        automation_id = await registry.register_automation(
            name=request.name,
            automation_type=request.automation_type,
            description=request.description,
            schedule_type=request.schedule_type,
            schedule_config=request.schedule_config,
            resource_requirements=request.resource_requirements,
            config=request.config,
            priority=request.priority,
            max_concurrent_runs=request.max_concurrent_runs,
            tags=request.tags,
            created_by=request.created_by
        )

        return {
            "success": True,
            "message": "Automation registered successfully",
            "data": {
                "automation_id": automation_id
            }
        }

    except Exception as e:
        logger.error(f"Error registering automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{automation_id}")
async def update_automation(automation_id: str, request: UpdateAutomationRequest):
    """
    Update automation configuration

    Updates one or more fields of an existing automation.
    Only provided fields will be updated.
    """
    try:
        registry = get_automation_registry()

        # Build updates dict (exclude None values)
        updates = {
            k: v for k, v in request.model_dump().items()
            if v is not None
        }

        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        updated = await registry.update_automation(automation_id, **updates)

        if not updated:
            raise HTTPException(status_code=404, detail="Automation not found")

        return {
            "success": True,
            "message": "Automation updated successfully",
            "data": {
                "automation_id": automation_id,
                "updated_fields": list(updates.keys())
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{automation_id}")
async def delete_automation(automation_id: str):
    """
    Delete automation

    Permanently deletes an automation and all its run history.
    This action cannot be undone.
    """
    try:
        registry = get_automation_registry()
        deleted = await registry.delete_automation(automation_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Automation not found")

        return {
            "success": True,
            "message": "Automation deleted successfully",
            "data": {
                "automation_id": automation_id
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{automation_id}/runs")
async def get_run_history(
    automation_id: str,
    limit: int = Query(50, ge=1, le=500, description="Max runs to return"),
    status: Optional[str] = Query(None, description="Filter by run status")
):
    """
    Get run history for an automation

    Returns:
        List of automation runs with execution details and metrics
    """
    try:
        registry = get_automation_registry()

        runs = await registry.get_run_history(
            automation_id=automation_id,
            limit=limit,
            status=status
        )

        return {
            "success": True,
            "data": {
                "runs": runs,
                "count": len(runs)
            }
        }

    except Exception as e:
        logger.error(f"Error getting run history for {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/active")
async def get_active_runs():
    """
    Get all currently running automations

    Returns:
        List of active runs with their start times and automation details
    """
    try:
        registry = get_automation_registry()
        runs = await registry.get_active_runs()

        return {
            "success": True,
            "data": {
                "active_runs": runs,
                "count": len(runs)
            }
        }

    except Exception as e:
        logger.error(f"Error getting active runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Get automation registry statistics

    Returns:
        Overall statistics including:
        - Total automations by status
        - Currently running automations
        - Run statistics (last 24h)
        - Success/failure rates
    """
    try:
        registry = get_automation_registry()
        stats = await registry.get_stats()

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        logger.error(f"Error getting automation stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{automation_id}/start")
async def start_run(automation_id: str, request: StartRunRequest = StartRunRequest()):
    """
    Manually start an automation run

    Triggers an immediate execution of the automation.
    Will fail if max concurrent runs is reached or automation is disabled.
    """
    try:
        registry = get_automation_registry()

        run_id = await registry.start_run(
            automation_id=automation_id,
            triggered_by=request.triggered_by,
            trigger_metadata=request.trigger_metadata
        )

        if not run_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot start run (automation disabled or max concurrent runs reached)"
            )

        return {
            "success": True,
            "message": "Run started successfully",
            "data": {
                "run_id": run_id,
                "automation_id": automation_id
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting run for {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{automation_id}/pause")
async def pause_automation(automation_id: str):
    """
    Pause automation

    Sets automation status to 'paused'. No new runs will be started.
    Currently running executions will complete.
    """
    try:
        registry = get_automation_registry()

        updated = await registry.update_automation(
            automation_id,
            status=AutomationStatus.PAUSED.value
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Automation not found")

        return {
            "success": True,
            "message": "Automation paused",
            "data": {
                "automation_id": automation_id,
                "status": AutomationStatus.PAUSED.value
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{automation_id}/resume")
async def resume_automation(automation_id: str):
    """
    Resume automation

    Sets automation status back to 'active'. Scheduled runs will resume.
    """
    try:
        registry = get_automation_registry()

        updated = await registry.update_automation(
            automation_id,
            status=AutomationStatus.ACTIVE.value
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Automation not found")

        return {
            "success": True,
            "message": "Automation resumed",
            "data": {
                "automation_id": automation_id,
                "status": AutomationStatus.ACTIVE.value
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
